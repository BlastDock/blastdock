"""
Domain Manager - Handles domain and subdomain management for BlastDock
"""

import json
import re
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

from ..utils.logging import get_logger
from ..utils.filesystem import paths
from ..core.config import get_config_manager
from .validator import DomainValidator

logger = get_logger(__name__)


class DomainManager:
    """Manages domains and subdomains for BlastDock deployments"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.validator = DomainValidator()
        self.domains_file = paths.data_dir / "domains.json"
        self._load_domains()
    
    def _load_domains(self):
        """Load domain configuration from file"""
        try:
            if self.domains_file.exists():
                with open(self.domains_file, 'r') as f:
                    self.domains_data = json.load(f)
            else:
                self.domains_data = {
                    'used_domains': {},
                    'used_subdomains': {},
                    'reserved_subdomains': set(),
                    'custom_domains': {}
                }
                self._save_domains()
        except Exception as e:
            logger.error(f"Error loading domains configuration: {e}")
            self.domains_data = {
                'used_domains': {},
                'used_subdomains': {},
                'reserved_subdomains': set(),
                'custom_domains': {}
            }
    
    def _save_domains(self):
        """Save domain configuration to file"""
        try:
            # Convert sets to lists for JSON serialization
            save_data = self.domains_data.copy()
            if 'reserved_subdomains' in save_data:
                save_data['reserved_subdomains'] = list(save_data['reserved_subdomains'])
            
            with open(self.domains_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving domains configuration: {e}")
    
    def get_default_domain(self) -> str:
        """Get the default domain from configuration"""
        config = self.config_manager.config
        domains_config = config.get('domains', {})
        return domains_config.get('default_domain', 'blastdock.local')
    
    def set_default_domain(self, domain: str) -> bool:
        """Set the default domain"""
        try:
            if not self.validator.validate_domain(domain):
                logger.error(f"Invalid domain format: {domain}")
                return False
            
            config = self.config_manager.config
            if 'domains' not in config:
                config['domains'] = {}
            
            config['domains']['default_domain'] = domain
            self.config_manager.save_config()
            
            logger.info(f"Set default domain to: {domain}")
            return True
        except Exception as e:
            logger.error(f"Error setting default domain: {e}")
            return False
    
    def generate_subdomain(self, project_name: str, preferred_subdomain: Optional[str] = None) -> str:
        """Generate a unique subdomain for a project"""
        # Clean project name for subdomain use
        cleaned_name = self._clean_name_for_subdomain(project_name)
        
        # Use preferred subdomain if provided and valid
        if preferred_subdomain:
            cleaned_subdomain = self._clean_name_for_subdomain(preferred_subdomain)
            if self.is_subdomain_available(cleaned_subdomain):
                return cleaned_subdomain
        
        # Try the cleaned project name
        if self.is_subdomain_available(cleaned_name):
            return cleaned_name
        
        # Generate variations with numbers
        counter = 1
        while counter <= 100:  # Limit attempts to prevent infinite loop
            candidate = f"{cleaned_name}{counter}"
            if self.is_subdomain_available(candidate):
                return candidate
            counter += 1
        
        # Fallback with timestamp
        import time
        timestamp_suffix = str(int(time.time()))[-6:]
        return f"{cleaned_name}{timestamp_suffix}"
    
    def is_subdomain_available(self, subdomain: str) -> bool:
        """Check if a subdomain is available"""
        # Check reserved subdomains
        reserved = self.get_reserved_subdomains()
        if subdomain.lower() in reserved:
            return False
        
        # Check used subdomains
        used_subdomains = self.domains_data.get('used_subdomains', {})
        return subdomain.lower() not in used_subdomains
    
    def is_domain_available(self, domain: str) -> bool:
        """Check if a custom domain is available"""
        used_domains = self.domains_data.get('used_domains', {})
        return domain.lower() not in used_domains
    
    def reserve_subdomain(self, subdomain: str, project_name: str) -> bool:
        """Reserve a subdomain for a project"""
        try:
            if not self.is_subdomain_available(subdomain):
                logger.error(f"Subdomain {subdomain} is not available")
                return False
            
            self.domains_data['used_subdomains'][subdomain.lower()] = {
                'project_name': project_name,
                'reserved_at': self._get_current_timestamp(),
                'type': 'subdomain'
            }
            
            self._save_domains()
            logger.info(f"Reserved subdomain {subdomain} for project {project_name}")
            return True
        except Exception as e:
            logger.error(f"Error reserving subdomain: {e}")
            return False
    
    def reserve_domain(self, domain: str, project_name: str) -> bool:
        """Reserve a custom domain for a project"""
        try:
            if not self.validator.validate_domain(domain):
                logger.error(f"Invalid domain format: {domain}")
                return False
            
            if not self.is_domain_available(domain):
                logger.error(f"Domain {domain} is not available")
                return False
            
            self.domains_data['used_domains'][domain.lower()] = {
                'project_name': project_name,
                'reserved_at': self._get_current_timestamp(),
                'type': 'custom_domain'
            }
            
            self._save_domains()
            logger.info(f"Reserved domain {domain} for project {project_name}")
            return True
        except Exception as e:
            logger.error(f"Error reserving domain: {e}")
            return False
    
    def release_subdomain(self, subdomain: str) -> bool:
        """Release a reserved subdomain"""
        try:
            used_subdomains = self.domains_data.get('used_subdomains', {})
            if subdomain.lower() in used_subdomains:
                del used_subdomains[subdomain.lower()]
                self._save_domains()
                logger.info(f"Released subdomain: {subdomain}")
                return True
            else:
                logger.warning(f"Subdomain {subdomain} was not reserved")
                return False
        except Exception as e:
            logger.error(f"Error releasing subdomain: {e}")
            return False
    
    def release_domain(self, domain: str) -> bool:
        """Release a reserved domain"""
        try:
            used_domains = self.domains_data.get('used_domains', {})
            if domain.lower() in used_domains:
                del used_domains[domain.lower()]
                self._save_domains()
                logger.info(f"Released domain: {domain}")
                return True
            else:
                logger.warning(f"Domain {domain} was not reserved")
                return False
        except Exception as e:
            logger.error(f"Error releasing domain: {e}")
            return False
    
    def release_project_domains(self, project_name: str) -> bool:
        """Release all domains/subdomains for a project"""
        try:
            released = []
            
            # Release subdomains
            used_subdomains = self.domains_data.get('used_subdomains', {}).copy()
            for subdomain, info in used_subdomains.items():
                if info.get('project_name') == project_name:
                    del self.domains_data['used_subdomains'][subdomain]
                    released.append(f"subdomain: {subdomain}")
            
            # Release domains
            used_domains = self.domains_data.get('used_domains', {}).copy()
            for domain, info in used_domains.items():
                if info.get('project_name') == project_name:
                    del self.domains_data['used_domains'][domain]
                    released.append(f"domain: {domain}")
            
            if released:
                self._save_domains()
                logger.info(f"Released {len(released)} domains for project {project_name}: {', '.join(released)}")
            
            return True
        except Exception as e:
            logger.error(f"Error releasing project domains: {e}")
            return False
    
    def get_project_domains(self, project_name: str) -> Dict[str, List[str]]:
        """Get all domains and subdomains for a project"""
        result = {
            'subdomains': [],
            'custom_domains': []
        }
        
        try:
            # Check subdomains
            used_subdomains = self.domains_data.get('used_subdomains', {})
            for subdomain, info in used_subdomains.items():
                if info.get('project_name') == project_name:
                    result['subdomains'].append(subdomain)
            
            # Check custom domains
            used_domains = self.domains_data.get('used_domains', {})
            for domain, info in used_domains.items():
                if info.get('project_name') == project_name:
                    result['custom_domains'].append(domain)
        except Exception as e:
            logger.error(f"Error getting project domains: {e}")
        
        return result
    
    def list_all_domains(self) -> Dict[str, List[Dict[str, str]]]:
        """List all used domains and subdomains"""
        result = {
            'subdomains': [],
            'custom_domains': [],
            'reserved_subdomains': list(self.get_reserved_subdomains())
        }
        
        try:
            # Used subdomains
            used_subdomains = self.domains_data.get('used_subdomains', {})
            for subdomain, info in used_subdomains.items():
                result['subdomains'].append({
                    'name': subdomain,
                    'project': info.get('project_name', 'unknown'),
                    'full_domain': f"{subdomain}.{self.get_default_domain()}",
                    'reserved_at': info.get('reserved_at', 'unknown')
                })
            
            # Used custom domains
            used_domains = self.domains_data.get('used_domains', {})
            for domain, info in used_domains.items():
                result['custom_domains'].append({
                    'name': domain,
                    'project': info.get('project_name', 'unknown'),
                    'reserved_at': info.get('reserved_at', 'unknown')
                })
        except Exception as e:
            logger.error(f"Error listing domains: {e}")
        
        return result
    
    def get_reserved_subdomains(self) -> Set[str]:
        """Get list of reserved subdomains"""
        config = self.config_manager.config
        domains_config = config.get('domains', {})
        default_reserved = {'www', 'mail', 'ftp', 'traefik', 'api', 'admin', 'dashboard'}
        
        # Get from config
        config_reserved = set(domains_config.get('reserved_subdomains', []))
        
        # Get from domains data
        data_reserved = set(self.domains_data.get('reserved_subdomains', []))
        
        return default_reserved | config_reserved | data_reserved
    
    def add_reserved_subdomain(self, subdomain: str) -> bool:
        """Add a subdomain to the reserved list"""
        try:
            reserved = self.domains_data.get('reserved_subdomains', set())
            if isinstance(reserved, list):
                reserved = set(reserved)
            
            reserved.add(subdomain.lower())
            self.domains_data['reserved_subdomains'] = reserved
            self._save_domains()
            
            logger.info(f"Added {subdomain} to reserved subdomains")
            return True
        except Exception as e:
            logger.error(f"Error adding reserved subdomain: {e}")
            return False
    
    def remove_reserved_subdomain(self, subdomain: str) -> bool:
        """Remove a subdomain from the reserved list"""
        try:
            reserved = self.domains_data.get('reserved_subdomains', set())
            if isinstance(reserved, list):
                reserved = set(reserved)
            
            if subdomain.lower() in reserved:
                reserved.discard(subdomain.lower())
                self.domains_data['reserved_subdomains'] = reserved
                self._save_domains()
                logger.info(f"Removed {subdomain} from reserved subdomains")
                return True
            else:
                logger.warning(f"Subdomain {subdomain} was not in reserved list")
                return False
        except Exception as e:
            logger.error(f"Error removing reserved subdomain: {e}")
            return False
    
    def check_domain_conflicts(self) -> List[Dict[str, str]]:
        """Check for domain conflicts"""
        conflicts = []
        
        try:
            # Check for duplicate assignments
            used_subdomains = self.domains_data.get('used_subdomains', {})
            used_domains = self.domains_data.get('used_domains', {})
            
            # Check subdomain conflicts with custom domains
            default_domain = self.get_default_domain()
            for subdomain, info in used_subdomains.items():
                full_subdomain = f"{subdomain}.{default_domain}"
                if full_subdomain.lower() in used_domains:
                    conflicts.append({
                        'type': 'subdomain_domain_conflict',
                        'domain': full_subdomain,
                        'subdomain_project': info.get('project_name'),
                        'domain_project': used_domains[full_subdomain.lower()].get('project_name')
                    })
        except Exception as e:
            logger.error(f"Error checking domain conflicts: {e}")
        
        return conflicts
    
    def get_full_domain(self, project_name: str, subdomain: Optional[str] = None, 
                       custom_domain: Optional[str] = None) -> Optional[str]:
        """Get the full domain for a project"""
        try:
            if custom_domain:
                if self.validator.validate_domain(custom_domain):
                    return custom_domain
                return None
            
            if subdomain:
                default_domain = self.get_default_domain()
                return f"{subdomain}.{default_domain}"
            
            # Look up existing domains for project
            project_domains = self.get_project_domains(project_name)
            
            if project_domains['custom_domains']:
                return project_domains['custom_domains'][0]
            
            if project_domains['subdomains']:
                default_domain = self.get_default_domain()
                return f"{project_domains['subdomains'][0]}.{default_domain}"
            
            return None
        except Exception as e:
            logger.error(f"Error getting full domain: {e}")
            return None
    
    def _clean_name_for_subdomain(self, name: str) -> str:
        """Clean a name to be suitable for subdomain use"""
        # Convert to lowercase
        cleaned = name.lower()
        
        # Replace invalid characters with hyphens
        cleaned = re.sub(r'[^a-z0-9-]', '-', cleaned)
        
        # Remove leading/trailing hyphens
        cleaned = cleaned.strip('-')
        
        # Replace multiple consecutive hyphens with single hyphen
        cleaned = re.sub(r'-+', '-', cleaned)
        
        # Ensure it's not empty and not too long
        if not cleaned:
            cleaned = 'app'
        elif len(cleaned) > 50:
            cleaned = cleaned[:50].rstrip('-')
        
        return cleaned
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def migrate_legacy_domains(self) -> bool:
        """Migrate domains from legacy configuration format"""
        try:
            # This would handle migration from older BlastDock versions
            # For now, just ensure the current format is valid
            self._save_domains()
            logger.info("Domain migration completed")
            return True
        except Exception as e:
            logger.error(f"Error during domain migration: {e}")
            return False