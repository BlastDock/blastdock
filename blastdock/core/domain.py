"""
Domain management module for BlastDock

This module handles domain configuration, validation, and SSL setup for services.
"""

import re
import socket
from typing import Dict, Any, Optional, Tuple, List
from ..utils.logging import get_logger
from ..config import get_config
from ..utils.validators import validate_domain

logger = get_logger(__name__)


class DomainManager:
    """
    Manages domain configuration for BlastDock deployments.
    
    This class handles:
    - Domain configuration (auto-subdomain or custom)
    - Domain validation and availability checks
    - SSL/TLS configuration
    - Routing rule generation
    """
    
    def __init__(self):
        """Initialize DomainManager."""
        self.config = get_config()
        self.default_domain = self.config.network.default_domain or "localhost"
        
    def get_domain_config(self, project_name: str, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate domain configuration for a project.
        
        Args:
            project_name: The project name
            user_config: User-provided configuration
            
        Returns:
            Domain configuration dictionary
        """
        # Extract domain settings from user config
        custom_domain = user_config.get('domain', '').strip()
        subdomain = user_config.get('subdomain', project_name).strip()
        ssl_enabled = user_config.get('ssl_enabled', True)
        
        # Sanitize subdomain
        subdomain = self._sanitize_subdomain(subdomain)
        
        if custom_domain:
            # User provided a custom domain
            domain_config = self._configure_custom_domain(custom_domain, ssl_enabled)
        else:
            # Use auto-subdomain
            domain_config = self._configure_auto_subdomain(subdomain, ssl_enabled)
            
        # Add metadata
        domain_config.update({
            'project_name': project_name,
            'subdomain': subdomain,
            'custom_domain': bool(custom_domain),
            'ssl_enabled': ssl_enabled
        })
        
        logger.info(f"Domain configuration for {project_name}: {domain_config['host']}")
        return domain_config
        
    def _configure_custom_domain(self, domain: str, ssl_enabled: bool) -> Dict[str, Any]:
        """Configure a custom domain."""
        # Validate the domain
        valid, error = validate_domain(domain)
        if not valid:
            raise ValueError(f"Invalid domain: {error}")
            
        # Check if domain includes subdomain
        parts = domain.split('.')
        if len(parts) > 2:
            # It's a full domain with subdomain
            host = domain
            base_domain = '.'.join(parts[-2:])
            subdomain_part = '.'.join(parts[:-2])
        else:
            # It's just a base domain
            host = domain
            base_domain = domain
            subdomain_part = None
            
        return {
            'host': host,
            'base_domain': base_domain,
            'subdomain_part': subdomain_part,
            'tls': ssl_enabled,
            'tls_domains': [host] if ssl_enabled else [],
            'routing_rule': f"Host(`{host}`)"
        }
        
    def _configure_auto_subdomain(self, subdomain: str, ssl_enabled: bool) -> Dict[str, Any]:
        """Configure an automatic subdomain."""
        # Construct the full domain
        host = f"{subdomain}.{self.default_domain}"
        
        # For localhost, disable SSL by default
        if self.default_domain == "localhost":
            ssl_enabled = False
            
        return {
            'host': host,
            'base_domain': self.default_domain,
            'subdomain_part': subdomain,
            'tls': ssl_enabled,
            'tls_domains': [host] if ssl_enabled else [],
            'routing_rule': f"Host(`{host}`)"
        }
        
    def _sanitize_subdomain(self, subdomain: str) -> str:
        """Sanitize a subdomain to ensure it's valid."""
        # Convert to lowercase
        subdomain = subdomain.lower()
        
        # Replace underscores with hyphens
        subdomain = subdomain.replace('_', '-')
        
        # Remove any characters that aren't alphanumeric or hyphens
        subdomain = re.sub(r'[^a-z0-9-]', '', subdomain)
        
        # Remove leading/trailing hyphens
        subdomain = subdomain.strip('-')
        
        # Ensure it doesn't start with a number
        if subdomain and subdomain[0].isdigit():
            subdomain = f"app-{subdomain}"
            
        # Ensure it's not empty
        if not subdomain:
            subdomain = "app"
            
        return subdomain
        
    def validate_domain_availability(self, domain: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a domain is available (can be resolved).
        
        Args:
            domain: The domain to check
            
        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            # Try to resolve the domain
            socket.gethostbyname(domain)
            # If successful, domain exists and is configured
            return True, None
        except socket.gaierror:
            # Domain cannot be resolved - this is expected for new domains
            return True, None
        except Exception as e:
            return False, f"Error checking domain: {str(e)}"
            
    def generate_ssl_config(self, domain_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate SSL/TLS configuration for a domain.
        
        Args:
            domain_config: Domain configuration dictionary
            
        Returns:
            SSL configuration dictionary
        """
        if not domain_config.get('tls', False):
            return {
                'enabled': False
            }
            
        # Determine certificate resolver based on domain
        if domain_config.get('base_domain') == 'localhost':
            # Use self-signed for localhost
            cert_resolver = 'self-signed'
        else:
            # Use Let's Encrypt for public domains
            cert_resolver = self.config.docker.traefik_cert_resolver or 'letsencrypt'
            
        return {
            'enabled': True,
            'cert_resolver': cert_resolver,
            'domains': domain_config.get('tls_domains', [domain_config['host']]),
            'redirect_http': True,
            'strict_sni': False
        }
        
    def generate_routing_rules(self, domain_config: Dict[str, Any], 
                             additional_rules: Optional[List[str]] = None) -> str:
        """
        Generate Traefik routing rules for a domain configuration.
        
        Args:
            domain_config: Domain configuration dictionary
            additional_rules: Optional additional routing rules
            
        Returns:
            Traefik routing rule string
        """
        rules = [domain_config.get('routing_rule', f"Host(`{domain_config['host']}`)")]
        
        if additional_rules:
            rules.extend(additional_rules)
            
        # Combine rules with AND operator
        if len(rules) > 1:
            return " && ".join(f"({rule})" for rule in rules)
        else:
            return rules[0]
            
    def get_domain_url(self, domain_config: Dict[str, Any], path: str = "") -> str:
        """
        Get the full URL for a domain configuration.
        
        Args:
            domain_config: Domain configuration dictionary
            path: Optional path to append
            
        Returns:
            Full URL string
        """
        protocol = "https" if domain_config.get('tls', False) else "http"
        host = domain_config['host']
        
        # Ensure path starts with /
        if path and not path.startswith('/'):
            path = f"/{path}"
            
        return f"{protocol}://{host}{path}"
        
    def update_hosts_file_hint(self, domain_config: Dict[str, Any]) -> Optional[str]:
        """
        Generate a hint for updating /etc/hosts if needed.
        
        Args:
            domain_config: Domain configuration dictionary
            
        Returns:
            Hosts file entry hint or None
        """
        host = domain_config['host']
        
        # Only provide hint for non-localhost domains that might not resolve
        if 'localhost' in host or self._can_resolve_domain(host):
            return None
            
        return f"127.0.0.1    {host}"
        
    def _can_resolve_domain(self, domain: str) -> bool:
        """Check if a domain can be resolved."""
        try:
            socket.gethostbyname(domain)
            return True
        except:
            return False