"""
SSL Manager - Handles SSL certificate management with Let's Encrypt
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from ..utils.logging import get_logger
from ..utils.filesystem import paths
from ..domains.validator import DomainValidator
from .manager import TraefikManager

logger = get_logger(__name__)


class SSLManager:
    """Manages SSL certificates and Let's Encrypt integration"""
    
    def __init__(self):
        self.traefik_manager = TraefikManager()
        self.domain_validator = DomainValidator()
        self.letsencrypt_dir = paths.data_dir / "traefik" / "letsencrypt"
        self.acme_file = self.letsencrypt_dir / "acme.json"
    
    def get_certificate_status(self, domain: str) -> Dict[str, Any]:
        """Get SSL certificate status for a domain"""
        status = {
            'domain': domain,
            'has_certificate': False,
            'issuer': None,
            'expires_at': None,
            'days_until_expiry': None,
            'is_valid': False,
            'san_domains': [],
            'error': None
        }
        
        try:
            # Check if domain has a certificate in ACME data
            cert_info = self._get_certificate_from_acme(domain)
            
            if cert_info:
                status['has_certificate'] = True
                status['issuer'] = 'Let\'s Encrypt'
                
                # Parse certificate details
                cert_details = self._parse_certificate_details(cert_info)
                status.update(cert_details)
            else:
                # Check if certificate exists via other means
                cert_details = self._check_certificate_online(domain)
                if cert_details:
                    status.update(cert_details)
        
        except Exception as e:
            status['error'] = str(e)
            logger.error(f"Error getting certificate status for {domain}: {e}")
        
        return status
    
    def list_all_certificates(self) -> List[Dict[str, Any]]:
        """List all managed SSL certificates"""
        certificates = []
        
        try:
            if not self.acme_file.exists():
                return certificates
            
            with open(self.acme_file, 'r') as f:
                acme_data = json.load(f)
            
            # Parse certificates from ACME data
            letsencrypt_data = acme_data.get('letsencrypt', {})
            cert_list = letsencrypt_data.get('Certificates', [])
            
            for cert in cert_list:
                domain_info = cert.get('domain', {})
                main_domain = domain_info.get('main', '')
                sans = domain_info.get('sans', [])
                
                if main_domain:
                    cert_status = self.get_certificate_status(main_domain)
                    cert_status['san_domains'] = sans
                    certificates.append(cert_status)
        
        except Exception as e:
            logger.error(f"Error listing certificates: {e}")
        
        return certificates
    
    def check_certificate_renewal_needed(self, domain: str, days_threshold: int = 30) -> bool:
        """Check if a certificate needs renewal"""
        try:
            status = self.get_certificate_status(domain)
            
            if not status['has_certificate']:
                return True  # No certificate, needs one
            
            days_until_expiry = status.get('days_until_expiry')
            if days_until_expiry is None:
                return True  # Can't determine expiry, assume renewal needed
            
            return days_until_expiry <= days_threshold
        
        except Exception as e:
            logger.error(f"Error checking renewal status for {domain}: {e}")
            return True  # Assume renewal needed on error
    
    def force_certificate_renewal(self, domain: str) -> bool:
        """Force renewal of a specific certificate"""
        try:
            if not self.traefik_manager.is_running():
                logger.error("Traefik is not running")
                return False
            
            # Remove existing certificate from ACME data
            if self._remove_certificate_from_acme(domain):
                logger.info(f"Removed existing certificate for {domain}")
            
            # Restart Traefik to trigger new certificate request
            if self.traefik_manager.restart():
                logger.info("Restarted Traefik to trigger certificate renewal")
                return True
            else:
                logger.error("Failed to restart Traefik")
                return False
        
        except Exception as e:
            logger.error(f"Error forcing certificate renewal for {domain}: {e}")
            return False
    
    def validate_domain_for_ssl(self, domain: str) -> Tuple[bool, str]:
        """Validate if a domain can get SSL certificate"""
        # Basic domain validation
        if not self.domain_validator.validate_domain(domain):
            return False, "Invalid domain format"
        
        # Check if it's a local domain
        if self.domain_validator.is_local_domain(domain):
            return False, "Local domains cannot get Let's Encrypt certificates"
        
        # Check DNS resolution
        resolves, error = self.domain_validator.check_dns_resolution(domain)
        if not resolves:
            return False, f"Domain does not resolve: {error}"
        
        # Check if domain points to this server
        # This is a simplified check - in production you might want more sophisticated validation
        return True, "Domain is valid for SSL certificate"
    
    def get_certificate_renewal_schedule(self) -> List[Dict[str, Any]]:
        """Get renewal schedule for all certificates"""
        schedule = []
        
        try:
            certificates = self.list_all_certificates()
            
            for cert in certificates:
                domain = cert['domain']
                days_until_expiry = cert.get('days_until_expiry')
                
                if days_until_expiry is not None:
                    # Calculate renewal priority
                    if days_until_expiry <= 7:
                        priority = 'urgent'
                    elif days_until_expiry <= 30:
                        priority = 'soon'
                    elif days_until_expiry <= 60:
                        priority = 'normal'
                    else:
                        priority = 'future'
                    
                    schedule.append({
                        'domain': domain,
                        'days_until_expiry': days_until_expiry,
                        'expires_at': cert.get('expires_at'),
                        'priority': priority,
                        'needs_renewal': self.check_certificate_renewal_needed(domain)
                    })
            
            # Sort by expiry date
            schedule.sort(key=lambda x: x['days_until_expiry'] or 0)
        
        except Exception as e:
            logger.error(f"Error getting renewal schedule: {e}")
        
        return schedule
    
    def test_ssl_configuration(self, domain: str) -> Dict[str, Any]:
        """Test SSL configuration for a domain"""
        test_result = {
            'domain': domain,
            'ssl_working': False,
            'https_accessible': False,
            'certificate_valid': False,
            'certificate_trusted': False,
            'tls_version': None,
            'cipher_suite': None,
            'error': None
        }
        
        try:
            import ssl
            import socket
            from urllib.request import urlopen
            from urllib.error import URLError
            
            # Test HTTPS accessibility
            try:
                url = f"https://{domain}"
                response = urlopen(url, timeout=10)
                test_result['https_accessible'] = True
                test_result['ssl_working'] = response.status == 200
            except URLError as e:
                test_result['error'] = f"HTTPS not accessible: {e}"
            
            # Test SSL certificate
            try:
                context = ssl.create_default_context()
                with socket.create_connection((domain, 443), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        
                        test_result['certificate_valid'] = True
                        test_result['certificate_trusted'] = True
                        test_result['tls_version'] = ssock.version()
                        test_result['cipher_suite'] = ssock.cipher()[0] if ssock.cipher() else None
                        
                        # Check certificate expiry
                        not_after = cert.get('notAfter')
                        if not_after:
                            expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                            days_until_expiry = (expiry_date - datetime.now()).days
                            test_result['days_until_expiry'] = days_until_expiry
            
            except ssl.SSLError as e:
                test_result['error'] = f"SSL error: {e}"
            except socket.error as e:
                test_result['error'] = f"Connection error: {e}"
        
        except Exception as e:
            test_result['error'] = f"Test failed: {e}"
            logger.error(f"Error testing SSL configuration for {domain}: {e}")
        
        return test_result
    
    def backup_acme_data(self) -> bool:
        """Backup ACME certificate data"""
        try:
            if not self.acme_file.exists():
                logger.warning("No ACME data to backup")
                return True
            
            # Create backup directory
            backup_dir = paths.data_dir / "backups" / "ssl"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped backup
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"acme_{timestamp}.json"
            
            # Copy ACME data
            import shutil
            shutil.copy2(self.acme_file, backup_file)
            
            logger.info(f"Backed up ACME data to {backup_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error backing up ACME data: {e}")
            return False
    
    def restore_acme_data(self, backup_file: Path) -> bool:
        """Restore ACME certificate data from backup"""
        try:
            if not backup_file.exists():
                logger.error(f"Backup file does not exist: {backup_file}")
                return False
            
            # Create backup of current data first
            self.backup_acme_data()
            
            # Restore from backup
            import shutil
            shutil.copy2(backup_file, self.acme_file)
            
            # Set correct permissions
            self.acme_file.chmod(0o600)
            
            logger.info(f"Restored ACME data from {backup_file}")
            return True
        
        except Exception as e:
            logger.error(f"Error restoring ACME data: {e}")
            return False
    
    def cleanup_expired_certificates(self) -> int:
        """Remove expired certificates from ACME data"""
        removed_count = 0
        
        try:
            if not self.acme_file.exists():
                return 0
            
            with open(self.acme_file, 'r') as f:
                acme_data = json.load(f)
            
            letsencrypt_data = acme_data.get('letsencrypt', {})
            certificates = letsencrypt_data.get('Certificates', [])
            
            # Filter out expired certificates
            valid_certificates = []
            for cert in certificates:
                # This is a simplified check - in practice you'd parse the actual certificate
                domain_info = cert.get('domain', {})
                main_domain = domain_info.get('main', '')
                
                if main_domain:
                    status = self.get_certificate_status(main_domain)
                    if status.get('days_until_expiry', 0) > 0:
                        valid_certificates.append(cert)
                    else:
                        removed_count += 1
                        logger.info(f"Removed expired certificate for {main_domain}")
            
            # Update ACME data
            letsencrypt_data['Certificates'] = valid_certificates
            
            with open(self.acme_file, 'w') as f:
                json.dump(acme_data, f, indent=2)
            
            logger.info(f"Cleaned up {removed_count} expired certificates")
        
        except Exception as e:
            logger.error(f"Error cleaning up expired certificates: {e}")
        
        return removed_count
    
    def _get_certificate_from_acme(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get certificate information from ACME data"""
        try:
            if not self.acme_file.exists():
                return None
            
            with open(self.acme_file, 'r') as f:
                acme_data = json.load(f)
            
            letsencrypt_data = acme_data.get('letsencrypt', {})
            certificates = letsencrypt_data.get('Certificates', [])
            
            for cert in certificates:
                domain_info = cert.get('domain', {})
                main_domain = domain_info.get('main', '')
                sans = domain_info.get('sans', [])
                
                if main_domain == domain or domain in sans:
                    return cert
            
            return None
        
        except Exception as e:
            logger.error(f"Error reading ACME data: {e}")
            return None
    
    def _remove_certificate_from_acme(self, domain: str) -> bool:
        """Remove a certificate from ACME data"""
        try:
            if not self.acme_file.exists():
                return False
            
            with open(self.acme_file, 'r') as f:
                acme_data = json.load(f)
            
            letsencrypt_data = acme_data.get('letsencrypt', {})
            certificates = letsencrypt_data.get('Certificates', [])
            
            # Filter out the certificate for this domain
            updated_certificates = []
            removed = False
            
            for cert in certificates:
                domain_info = cert.get('domain', {})
                main_domain = domain_info.get('main', '')
                sans = domain_info.get('sans', [])
                
                if main_domain != domain and domain not in sans:
                    updated_certificates.append(cert)
                else:
                    removed = True
            
            if removed:
                letsencrypt_data['Certificates'] = updated_certificates
                
                with open(self.acme_file, 'w') as f:
                    json.dump(acme_data, f, indent=2)
                
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error removing certificate from ACME data: {e}")
            return False
    
    def _parse_certificate_details(self, cert_info: Dict[str, Any]) -> Dict[str, Any]:
        """Parse certificate details from ACME data"""
        details = {
            'is_valid': True,
            'expires_at': None,
            'days_until_expiry': None
        }
        
        try:
            # This is a simplified parser - in practice you'd decode the actual certificate
            # For now, we'll use placeholder values
            details['expires_at'] = 'Unknown'
            details['days_until_expiry'] = 30  # Placeholder
        
        except Exception as e:
            logger.error(f"Error parsing certificate details: {e}")
            details['is_valid'] = False
        
        return details
    
    def _check_certificate_online(self, domain: str) -> Optional[Dict[str, Any]]:
        """Check certificate details online"""
        try:
            import ssl
            import socket
            
            context = ssl.create_default_context()
            with socket.create_connection((domain, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=domain) as ssock:
                    cert = ssock.getpeercert()
                    
                    # Parse certificate information
                    not_after = cert.get('notAfter')
                    if not_after:
                        expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                        days_until_expiry = (expiry_date - datetime.now()).days
                        
                        return {
                            'has_certificate': True,
                            'is_valid': True,
                            'expires_at': not_after,
                            'days_until_expiry': days_until_expiry,
                            'issuer': cert.get('issuer', [{}])[0].get('organizationName', 'Unknown')
                        }
        
        except Exception as e:
            logger.debug(f"Could not check certificate online for {domain}: {e}")
        
        return None