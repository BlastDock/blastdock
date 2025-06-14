"""
Traefik integration module for BlastDock

This module handles automatic Traefik label injection and network management
for services that require web access.
"""

import copy
from typing import Dict, Any, List, Optional
from ..utils.logging import get_logger
from .config import get_config

logger = get_logger(__name__)


class TraefikIntegrator:
    """
    Handles automatic Traefik integration for BlastDock deployments.
    
    This class is responsible for:
    - Detecting web services from template metadata
    - Injecting Traefik labels into compose configurations
    - Managing Traefik networks
    - Generating dynamic routing rules
    """
    
    def __init__(self, domain_manager=None):
        """
        Initialize TraefikIntegrator.
        
        Args:
            domain_manager: Optional DomainManager instance for domain configuration
        """
        self.domain_manager = domain_manager
        self.config = get_config()
        self.traefik_network = self.config.docker.traefik_network or "traefik"
        
    def process_compose(self, compose_data: Dict[str, Any], project_name: str, 
                       template_data: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a compose configuration to inject Traefik labels and networks.
        
        Args:
            compose_data: The docker-compose configuration
            project_name: The project name
            template_data: The full template data including metadata
            user_config: User-provided configuration values
            
        Returns:
            Modified compose configuration with Traefik integration
        """
        # Check if Traefik is enabled
        if not self._is_traefik_enabled(user_config, template_data):
            logger.debug(f"Traefik not enabled for project {project_name}")
            return compose_data
            
        # Deep copy to avoid modifying the original
        compose = copy.deepcopy(compose_data)
        
        # Get template metadata
        template_info = template_data.get('template_info', {})
        traefik_config = template_data.get('traefik_config', {})
        
        if not template_info.get('traefik_compatible', False):
            logger.debug(f"Template not marked as Traefik compatible for project {project_name}")
            return compose_data
            
        # Add Traefik network to compose
        self._add_traefik_network(compose)
        
        # Get the primary web service
        web_service = self._get_web_service(compose, template_info, traefik_config)
        if not web_service:
            logger.warning(f"No web service found for project {project_name}")
            return compose_data
            
        # Generate domain configuration
        domain_config = self._get_domain_config(project_name, user_config)
        
        # Inject Traefik labels into the web service
        self._inject_traefik_labels(
            compose['services'][web_service],
            project_name,
            web_service,
            domain_config,
            traefik_config
        )
        
        # Add Traefik network to the web service
        self._add_service_to_traefik_network(compose['services'][web_service])
        
        # Remove host port bindings for the web service if using Traefik
        self._remove_host_ports(compose['services'][web_service], traefik_config)
        
        return compose
        
    def _is_traefik_enabled(self, user_config: Dict[str, Any], 
                           template_data: Dict[str, Any]) -> bool:
        """Check if Traefik should be enabled for this deployment."""
        # Check user config first
        if 'traefik_enabled' in user_config:
            return user_config['traefik_enabled']
            
        # Check template default
        fields = template_data.get('fields', {})
        if 'traefik_enabled' in fields:
            return fields['traefik_enabled'].get('default', True)
            
        # Default to enabled if template is Traefik compatible
        template_info = template_data.get('template_info', {})
        return template_info.get('traefik_compatible', False)
        
    def _add_traefik_network(self, compose: Dict[str, Any]) -> None:
        """Add Traefik network to compose configuration."""
        if 'networks' not in compose:
            compose['networks'] = {}
            
        compose['networks'][self.traefik_network] = {
            'external': True
        }
        
    def _get_web_service(self, compose: Dict[str, Any], template_info: Dict[str, Any],
                        traefik_config: Dict[str, Any]) -> Optional[str]:
        """Determine the primary web service from the compose configuration."""
        services = compose.get('services', {})
        
        # Check traefik_config for explicit web service
        if traefik_config.get('web_service'):
            service_name = traefik_config['web_service']
            if service_name in services:
                return service_name
                
        # Check template_info for web service hint
        template_services = template_info.get('services', [])
        if template_services and isinstance(template_services, list):
            # First service is typically the main web service
            primary_service = template_services[0]
            if primary_service in services:
                return primary_service
                
        # Auto-detect based on common patterns
        for service_name, service_config in services.items():
            # Skip database services
            if any(db in service_name.lower() for db in ['mysql', 'postgres', 'redis', 'mongo', 'mariadb']):
                continue
                
            # Check if service exposes web ports
            ports = service_config.get('ports', [])
            for port in ports:
                port_str = str(port)
                if any(web_port in port_str for web_port in ['80:', '443:', '8080:', '3000:', '2368:']):
                    return service_name
                    
        return None
        
    def _get_domain_config(self, project_name: str, user_config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate domain configuration for the project."""
        if self.domain_manager:
            return self.domain_manager.get_domain_config(project_name, user_config)
            
        # Fallback domain configuration
        domain = user_config.get('domain', '')
        subdomain = user_config.get('subdomain', project_name)
        
        if domain:
            # Custom domain provided
            host = domain
        else:
            # Use subdomain with default domain
            default_domain = self.config.default_domain or 'localhost'
            host = f"{subdomain}.{default_domain}"
            
        return {
            'host': host,
            'tls': user_config.get('ssl_enabled', True),
            'subdomain': subdomain,
            'domain': domain
        }
        
    def _inject_traefik_labels(self, service: Dict[str, Any], project_name: str,
                               service_name: str, domain_config: Dict[str, Any],
                               traefik_config: Dict[str, Any]) -> None:
        """Inject Traefik labels into a service configuration."""
        if 'labels' not in service:
            service['labels'] = []
            
        # Convert dict labels to list format if needed
        if isinstance(service['labels'], dict):
            labels_list = []
            for key, value in service['labels'].items():
                labels_list.append(f"{key}={value}")
            service['labels'] = labels_list
            
        # Router name for this service
        router_name = f"{project_name}-{service_name}"
        
        # Basic labels
        labels = [
            "traefik.enable=true",
            f"traefik.http.routers.{router_name}.rule=Host(`{domain_config['host']}`)",
            f"traefik.http.routers.{router_name}.entrypoints=web",
        ]
        
        # Service configuration
        service_port = traefik_config.get('service_port', 80)
        labels.append(f"traefik.http.services.{router_name}.loadbalancer.server.port={service_port}")
        
        # TLS configuration
        if domain_config.get('tls', True):
            labels.extend([
                f"traefik.http.routers.{router_name}-secure.rule=Host(`{domain_config['host']}`)",
                f"traefik.http.routers.{router_name}-secure.entrypoints=websecure",
                f"traefik.http.routers.{router_name}-secure.tls=true",
                f"traefik.http.routers.{router_name}-secure.service={router_name}",
            ])
            
            # Certificate resolver
            cert_resolver = self.config.docker.traefik_cert_resolver or "letsencrypt"
            labels.append(f"traefik.http.routers.{router_name}-secure.tls.certresolver={cert_resolver}")
            
            # HTTP to HTTPS redirect
            labels.extend([
                f"traefik.http.routers.{router_name}.middlewares={router_name}-redirect",
                f"traefik.http.middlewares.{router_name}-redirect.redirectscheme.scheme=https",
                f"traefik.http.middlewares.{router_name}-redirect.redirectscheme.permanent=true",
            ])
            
        # Add custom middlewares from traefik_config
        middlewares = traefik_config.get('middlewares', [])
        if middlewares:
            middleware_names = []
            for idx, middleware in enumerate(middlewares):
                mw_name = middleware.get('name', f"{router_name}-mw-{idx}")
                middleware_names.append(mw_name)
                
                # Add middleware configuration labels
                mw_config = middleware.get('config', {})
                for mw_type, mw_settings in mw_config.items():
                    if mw_type == 'headers':
                        for header_type, headers in mw_settings.items():
                            if isinstance(headers, dict):
                                for header, value in headers.items():
                                    labels.append(
                                        f"traefik.http.middlewares.{mw_name}.headers.{header_type}.{header}={value}"
                                    )
                                    
            # Apply middlewares to secure router
            if domain_config.get('tls', True) and middleware_names:
                existing_mw = f"{router_name}-redirect"
                all_middlewares = f"{existing_mw}," + ",".join(middleware_names)
                labels.append(f"traefik.http.routers.{router_name}-secure.middlewares={','.join(middleware_names)}")
                
        # Routing priority
        priority = traefik_config.get('routing_priority', 1)
        labels.append(f"traefik.http.routers.{router_name}.priority={priority}")
        if domain_config.get('tls', True):
            labels.append(f"traefik.http.routers.{router_name}-secure.priority={priority}")
            
        # Add all labels to the service
        service['labels'].extend(labels)
        
    def _add_service_to_traefik_network(self, service: Dict[str, Any]) -> None:
        """Add Traefik network to a service."""
        if 'networks' not in service:
            service['networks'] = []
            
        # Handle both list and dict network formats
        if isinstance(service['networks'], list):
            if self.traefik_network not in service['networks']:
                service['networks'].append(self.traefik_network)
        elif isinstance(service['networks'], dict):
            if self.traefik_network not in service['networks']:
                service['networks'][self.traefik_network] = {}
                
    def _remove_host_ports(self, service: Dict[str, Any], traefik_config: Dict[str, Any]) -> None:
        """Remove host port bindings when using Traefik."""
        # Only remove ports that match the service port
        service_port = traefik_config.get('service_port', 80)
        
        if 'ports' in service:
            filtered_ports = []
            for port in service['ports']:
                port_str = str(port)
                # Keep non-web ports (e.g., database ports)
                if f":{service_port}" not in port_str:
                    filtered_ports.append(port)
                else:
                    logger.debug(f"Removing host port binding: {port}")
                    
            if filtered_ports:
                service['ports'] = filtered_ports
            else:
                del service['ports']
    def _enable_traefik_for_service(self, service_config, service_name, project_name, user_config, port):
        """Enable Traefik for a specific service"""
        if not self._should_enable_traefik(service_config):
            return service_config
        
        # Add Traefik labels
        labels = self._generate_traefik_labels(service_name, project_name, user_config, port)
        service_config = service_config.copy()
        service_config.setdefault('labels', {}).update(labels)
        
        return service_config
    
    def _add_traefik_network(self, compose_data):
        """Add Traefik network to compose data"""
        compose_data = compose_data.copy()
        
        # Add networks section
        compose_data.setdefault('networks', {})['traefik'] = {
            'external': True
        }
        
        # Add network to all services
        for service_name, service_config in compose_data.get('services', {}).items():
            service_config.setdefault('networks', []).append('traefik')
        
        return compose_data
    
    def _generate_traefik_labels(self, service_name, project_name, config, port):
        """Generate Traefik labels for a service"""
        domain = self._get_service_domain(project_name, service_name, config)
        
        labels = {
            'traefik.enable': 'true',
            f'traefik.http.routers.{project_name}-{service_name}.rule': f'Host(`{domain}`)',
            f'traefik.http.services.{project_name}-{service_name}.loadbalancer.server.port': str(port)
        }
        
        # Add SSL labels if enabled
        if config.get('ssl_enabled', True):
            labels.update(self._generate_ssl_labels(service_name, config))
        
        return labels
    
    def _should_enable_traefik(self, service_config):
        """Check if Traefik should be enabled for this service"""
        # Enable Traefik if service has ports exposed
        return 'ports' in service_config and len(service_config['ports']) > 0
    
    def _extract_port_from_service(self, service_config):
        """Extract port from service configuration"""
        ports = service_config.get('ports', [])
        if not ports:
            return None
        
        # Get first port mapping
        port_mapping = str(ports[0])
        if ':' in port_mapping:
            # Format: "8080:80" -> return 80 (container port)
            return int(port_mapping.split(':')[1])
        else:
            # Format: "80" -> return 80
            return int(port_mapping)
    
    def _get_service_domain(self, project_name, service_name, config):
        """Get domain for a service"""
        if 'domain' in config:
            return config['domain']
        elif 'subdomain' in config:
            return f"{config['subdomain']}.localhost"
        else:
            return f"{project_name}-{service_name}.localhost"
    
    def _generate_ssl_labels(self, service_name, config):
        """Generate SSL labels"""
        if not config.get('ssl_enabled', False):
            return {}
        
        return {
            f'traefik.http.routers.{service_name}.tls': 'true',
            f'traefik.http.routers.{service_name}.tls.certresolver': 'letsencrypt'
        }

