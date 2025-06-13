"""
Domain Validator - Validates domain names, subdomains, and DNS configuration
"""

import re
import socket
from typing import List, Tuple, Optional
from urllib.parse import urlparse

from ..utils.logging import get_logger

logger = get_logger(__name__)


class DomainValidator:
    """Validates domains, subdomains, and DNS configuration"""
    
    # RFC compliant domain regex
    DOMAIN_REGEX = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
    )
    
    # Subdomain regex (more restrictive)
    SUBDOMAIN_REGEX = re.compile(r'^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$')
    
    # Reserved domain names that shouldn't be used
    RESERVED_DOMAINS = {
        'localhost', 'example.com', 'example.org', 'example.net',
        'test', 'invalid', 'local'
    }
    
    # Common TLDs for validation
    COMMON_TLDS = {
        'com', 'org', 'net', 'edu', 'gov', 'mil', 'int',
        'co', 'io', 'ai', 'app', 'dev', 'tech', 'cloud',
        'local'  # Special case for development
    }
    
    def validate_domain(self, domain: str) -> bool:
        """Validate a domain name"""
        if not domain or not isinstance(domain, str):
            return False
        
        # Basic length check
        if len(domain) > 253:
            return False
        
        # Convert to lowercase for validation
        domain = domain.lower().strip()
        
        # Check for empty or whitespace
        if not domain:
            return False
        
        # Check against regex
        if not self.DOMAIN_REGEX.match(domain):
            return False
        
        # Check each label
        labels = domain.split('.')
        for label in labels:
            if not self._validate_label(label):
                return False
        
        # Check if it's a reserved domain
        if domain in self.RESERVED_DOMAINS:
            logger.warning(f"Domain {domain} is reserved")
            return False
        
        return True
    
    def validate_subdomain(self, subdomain: str) -> bool:
        """Validate a subdomain (single label)"""
        if not subdomain or not isinstance(subdomain, str):
            return False
        
        # Convert to lowercase
        subdomain = subdomain.lower().strip()
        
        # Check length
        if len(subdomain) > 63 or len(subdomain) < 1:
            return False
        
        # Check against regex
        return bool(self.SUBDOMAIN_REGEX.match(subdomain))
    
    def validate_url(self, url: str) -> bool:
        """Validate a full URL"""
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Validate the domain part
            domain = parsed.netloc.split(':')[0]  # Remove port if present
            return self.validate_domain(domain)
            
        except Exception:
            return False
    
    def check_dns_resolution(self, domain: str) -> Tuple[bool, Optional[str]]:
        """Check if a domain resolves in DNS"""
        try:
            # Try to resolve the domain
            result = socket.gethostbyname(domain)
            return True, result
        except socket.gaierror as e:
            return False, str(e)
        except Exception as e:
            return False, f"DNS resolution error: {e}"
    
    def check_domain_availability(self, domain: str) -> Tuple[bool, str]:
        """Check if a domain is available for use"""
        # First validate the domain format
        if not self.validate_domain(domain):
            return False, "Invalid domain format"
        
        # Check DNS resolution
        resolves, error = self.check_dns_resolution(domain)
        
        if domain.endswith('.local'):
            # .local domains are for development use
            return True, "Local development domain"
        
        if not resolves:
            return True, "Domain is available (does not resolve)"
        else:
            return False, f"Domain already resolves to {error}"
    
    def suggest_alternatives(self, domain: str) -> List[str]:
        """Suggest alternative domain names"""
        suggestions = []
        
        if not domain:
            return suggestions
        
        # Clean the domain
        base_domain = domain.lower().strip()
        
        # If it has a TLD, work with the base name
        if '.' in base_domain:
            parts = base_domain.split('.')
            base_name = parts[0]
            tld = '.'.join(parts[1:])
        else:
            base_name = base_domain
            tld = 'local'  # Default for development
        
        # Generate variations
        variations = [
            f"{base_name}-app.{tld}",
            f"{base_name}-site.{tld}",
            f"{base_name}-web.{tld}",
            f"my-{base_name}.{tld}",
            f"{base_name}-1.{tld}",
            f"{base_name}-2.{tld}",
            f"{base_name}-dev.{tld}",
            f"{base_name}-staging.{tld}"
        ]
        
        # Filter valid suggestions
        for suggestion in variations:
            if self.validate_domain(suggestion):
                suggestions.append(suggestion)
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def extract_subdomain_from_domain(self, domain: str, base_domain: str) -> Optional[str]:
        """Extract subdomain from a full domain given a base domain"""
        if not domain or not base_domain:
            return None
        
        domain = domain.lower().strip()
        base_domain = base_domain.lower().strip()
        
        # Check if domain ends with base domain
        if not domain.endswith(f".{base_domain}"):
            return None
        
        # Extract the subdomain part
        subdomain = domain[:-len(f".{base_domain}")]
        
        # Validate the extracted subdomain
        if self.validate_subdomain(subdomain):
            return subdomain
        
        return None
    
    def get_domain_info(self, domain: str) -> dict:
        """Get comprehensive information about a domain"""
        info = {
            'domain': domain,
            'valid': False,
            'resolves': False,
            'ip_address': None,
            'error': None,
            'labels': [],
            'tld': None,
            'is_subdomain': False,
            'suggestions': []
        }
        
        try:
            # Validate format
            info['valid'] = self.validate_domain(domain)
            
            if info['valid']:
                # Parse domain parts
                labels = domain.lower().split('.')
                info['labels'] = labels
                info['tld'] = labels[-1] if labels else None
                info['is_subdomain'] = len(labels) > 2
                
                # Check DNS resolution
                resolves, result = self.check_dns_resolution(domain)
                info['resolves'] = resolves
                if resolves:
                    info['ip_address'] = result
                else:
                    info['error'] = result
            else:
                info['error'] = "Invalid domain format"
                info['suggestions'] = self.suggest_alternatives(domain)
        
        except Exception as e:
            info['error'] = f"Error analyzing domain: {e}"
        
        return info
    
    def _validate_label(self, label: str) -> bool:
        """Validate a single domain label"""
        if not label:
            return False
        
        # Length check
        if len(label) > 63:
            return False
        
        # Can't start or end with hyphen
        if label.startswith('-') or label.endswith('-'):
            return False
        
        # Must contain only alphanumeric and hyphens
        if not re.match(r'^[a-zA-Z0-9-]+$', label):
            return False
        
        return True
    
    def validate_wildcard_domain(self, domain: str) -> bool:
        """Validate a wildcard domain (e.g., *.example.com)"""
        if not domain or not isinstance(domain, str):
            return False
        
        domain = domain.strip()
        
        # Must start with *.
        if not domain.startswith('*.'):
            return False
        
        # Validate the base domain part
        base_domain = domain[2:]  # Remove *.
        return self.validate_domain(base_domain)
    
    def is_local_domain(self, domain: str) -> bool:
        """Check if a domain is for local development"""
        if not domain:
            return False
        
        domain = domain.lower()
        return (
            domain.endswith('.local') or
            domain.endswith('.localhost') or
            domain == 'localhost' or
            domain.startswith('127.') or
            domain.startswith('192.168.') or
            domain.startswith('10.') or
            (domain.startswith('172.') and self._is_private_ip_range(domain))
        )
    
    def _is_private_ip_range(self, ip: str) -> bool:
        """Check if IP is in private range 172.16.0.0 to 172.31.255.255"""
        try:
            parts = ip.split('.')
            if len(parts) >= 2 and parts[0] == '172':
                second_octet = int(parts[1])
                return 16 <= second_octet <= 31
        except (ValueError, IndexError):
            pass
        return False
    
    def normalize_domain(self, domain: str) -> str:
        """Normalize a domain name"""
        if not domain:
            return ""
        
        # Convert to lowercase and strip whitespace
        normalized = domain.lower().strip()
        
        # Remove trailing dot if present
        if normalized.endswith('.'):
            normalized = normalized[:-1]
        
        return normalized