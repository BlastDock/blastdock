"""
Traefik Label Generator - Generates appropriate Traefik labels for services
"""

from typing import Dict, List, Optional, Any, Tuple
from ..utils.logging import get_logger
from ..domains.manager import DomainManager
from ..core.config import get_config

logger = get_logger(__name__)


class TraefikLabelGenerator:
    """Generates Traefik labels for Docker services"""
    
    # Service-specific configurations
    SERVICE_CONFIGS = {
        'wordpress': {
            'port': 80,
            'middlewares': ['wordpress-headers'],
            'health_check': '/',
            'priority': 1
        },
        'n8n': {
            'port': 5678,
            'middlewares': ['n8n-headers'],
            'health_check': '/healthz',
            'priority': 1
        },
        'ghost': {
            'port': 2368,
            'middlewares': ['ghost-headers'],
            'health_check': '/ghost/api/v4/admin/site/',
            'priority': 1
        },
        'nextcloud': {
            'port': 80,
            'middlewares': ['nextcloud-headers', 'nextcloud-redirects'],
            'health_check': '/status.php',
            'priority': 1
        },
        'grafana': {
            'port': 3000,
            'middlewares': ['grafana-headers'],
            'health_check': '/api/health',
            'priority': 1
        },
        'portainer': {
            'port': 9000,
            'middlewares': ['portainer-headers'],
            'health_check': '/api/status',
            'priority': 1
        },
        'jellyfin': {
            'port': 8096,
            'middlewares': ['jellyfin-headers'],
            'health_check': '/health',
            'priority': 1
        },
        'gitea': {
            'port': 3000,
            'middlewares': ['gitea-headers'],
            'health_check': '/api/v1/version',
            'priority': 1
        },
        'nginx': {
            'port': 80,
            'middlewares': ['nginx-headers'],
            'health_check': '/',
            'priority': 1
        },
        'apache': {
            'port': 80,
            'middlewares': ['apache-headers'],
            'health_check': '/',
            'priority': 1
        }
    }
    
    # Predefined middleware configurations
    MIDDLEWARE_CONFIGS = {
        'wordpress-headers': {
            'headers': {
                'customRequestHeaders': {
                    'X-Forwarded-Proto': 'https',
                    'X-Forwarded-For': '{{ .RemoteAddr }}',
                    'X-Real-IP': '{{ .RemoteAddr }}'
                },
                'customResponseHeaders': {
                    'X-Frame-Options': 'SAMEORIGIN',
                    'X-Content-Type-Options': 'nosniff'
                }
            }
        },
        'n8n-headers': {
            'headers': {
                'customRequestHeaders': {
                    'X-Forwarded-Proto': 'https'
                },
                'customResponseHeaders': {
                    'X-Frame-Options': 'SAMEORIGIN'
                }
            }
        },
        'nextcloud-redirects': {
            'redirectRegex': {
                'regex': 'https://(.*)/.well-known/(card|cal)dav',
                'replacement': 'https://${1}/remote.php/dav/'
            }
        },
        'security-headers': {
            'headers': {
                'customResponseHeaders': {
                    'X-Frame-Options': 'DENY',
                    'X-Content-Type-Options': 'nosniff',
                    'X-XSS-Protection': '1; mode=block',
                    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
                    'Referrer-Policy': 'strict-origin-when-cross-origin'
                }
            }
        }
    }
    
    def __init__(self):
        self.domain_manager = DomainManager()
        self.config = get_config()
    
    def generate_labels(self, project_name: str, service_name: str, 
                       service_type: str, domain: Optional[str] = None,
                       subdomain: Optional[str] = None,
                       ssl_enabled: bool = True,
                       custom_labels: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generate complete Traefik labels for a service"""
        try:
            labels = {}
            
            # Determine the domain to use
            if domain:
                service_domain = domain
            elif subdomain:
                default_domain = self.domain_manager.get_default_domain()
                service_domain = f"{subdomain}.{default_domain}"
            else:
                # Generate subdomain based on project name
                generated_subdomain = self.domain_manager.generate_subdomain(project_name)
                default_domain = self.domain_manager.get_default_domain()
                service_domain = f"{generated_subdomain}.{default_domain}"
            
            # Get service configuration
            service_config = self.SERVICE_CONFIGS.get(service_type, {})
            service_port = service_config.get('port', 80)
            
            # Basic Traefik labels
            labels.update(self._generate_basic_labels(service_name, service_domain))
            
            # Routing labels
            labels.update(self._generate_routing_labels(service_name, service_domain, ssl_enabled))
            
            # Service labels
            labels.update(self._generate_service_labels(service_name, service_port))
            
            # SSL/TLS labels
            if ssl_enabled:
                labels.update(self._generate_ssl_labels(service_name))
            
            # Middleware labels
            middlewares = service_config.get('middlewares', [])
            if ssl_enabled:
                middlewares.append('security-headers')
            
            if middlewares:
                labels.update(self._generate_middleware_labels(service_name, middlewares))
            
            # Health check labels (if supported)
            health_check = service_config.get('health_check')
            if health_check:
                labels.update(self._generate_health_check_labels(service_name, health_check))
            
            # Priority labels
            priority = service_config.get('priority', 1)
            labels[f'traefik.http.routers.{service_name}.priority'] = str(priority)
            
            # Custom labels override
            if custom_labels:
                labels.update(custom_labels)
            
            logger.info(f"Generated {len(labels)} Traefik labels for {service_name}")
            return labels
            
        except Exception as e:
            logger.error(f"Error generating Traefik labels: {e}")
            return {}
    
    def generate_middleware_config(self, middleware_name: str) -> Optional[Dict[str, Any]]:
        """Generate middleware configuration"""
        return self.MIDDLEWARE_CONFIGS.get(middleware_name)
    
    def generate_labels_for_template(self, project_name: str, template_name: str,
                                   template_config: Dict[str, Any],
                                   project_config: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """Generate labels for all services in a template"""
        service_labels = {}
        
        try:
            # Get Traefik configuration from project config
            traefik_config = project_config.get('traefik', {})
            domain = traefik_config.get('domain')
            subdomain = traefik_config.get('subdomain')
            ssl_enabled = traefik_config.get('ssl_enabled', True)
            
            # Get services from template
            compose_config = template_config.get('compose', {})
            services = compose_config.get('services', {})
            
            for service_name, service_config in services.items():
                # Determine service type
                service_type = self._detect_service_type(service_name, service_config)
                
                # Generate labels for this service
                labels = self.generate_labels(
                    project_name=project_name,
                    service_name=f"{project_name}-{service_name}",
                    service_type=service_type,
                    domain=domain,
                    subdomain=subdomain,
                    ssl_enabled=ssl_enabled
                )
                
                if labels:
                    service_labels[service_name] = labels
            
            return service_labels
            
        except Exception as e:
            logger.error(f"Error generating template labels: {e}")
            return {}
    
    def _generate_basic_labels(self, service_name: str, domain: str) -> Dict[str, str]:
        """Generate basic Traefik labels"""
        network = self.config.get('traefik', {}).get('network', 'blastdock-network')
        
        return {
            'traefik.enable': 'true',
            'traefik.docker.network': network,
        }
    
    def _generate_routing_labels(self, service_name: str, domain: str, ssl_enabled: bool) -> Dict[str, str]:
        """Generate routing labels"""
        labels = {
            f'traefik.http.routers.{service_name}.rule': f'Host(`{domain}`)'
        }
        
        # Set entrypoints based on SSL configuration
        if ssl_enabled:
            labels[f'traefik.http.routers.{service_name}.entrypoints'] = 'websecure'
            # Also create HTTP router for redirect
            labels[f'traefik.http.routers.{service_name}-http.rule'] = f'Host(`{domain}`)'
            labels[f'traefik.http.routers.{service_name}-http.entrypoints'] = 'web'
            labels[f'traefik.http.routers.{service_name}-http.middlewares'] = 'https-redirect'
        else:
            labels[f'traefik.http.routers.{service_name}.entrypoints'] = 'web'
        
        return labels
    
    def _generate_service_labels(self, service_name: str, port: int) -> Dict[str, str]:
        """Generate service labels"""
        return {
            f'traefik.http.services.{service_name}.loadbalancer.server.port': str(port)
        }
    
    def _generate_ssl_labels(self, service_name: str) -> Dict[str, str]:
        """Generate SSL/TLS labels"""
        cert_resolver = self.config.get('traefik', {}).get('default_cert_resolver', 'letsencrypt')
        
        return {
            f'traefik.http.routers.{service_name}.tls': 'true',
            f'traefik.http.routers.{service_name}.tls.certresolver': cert_resolver
        }
    
    def _generate_middleware_labels(self, service_name: str, middlewares: List[str]) -> Dict[str, str]:
        """Generate middleware labels"""
        middleware_list = ','.join(middlewares)
        return {
            f'traefik.http.routers.{service_name}.middlewares': middleware_list
        }
    
    def _generate_health_check_labels(self, service_name: str, health_path: str) -> Dict[str, str]:
        """Generate health check labels"""
        return {
            f'traefik.http.services.{service_name}.loadbalancer.healthcheck.path': health_path,
            f'traefik.http.services.{service_name}.loadbalancer.healthcheck.interval': '30s',
            f'traefik.http.services.{service_name}.loadbalancer.healthcheck.timeout': '5s'
        }
    
    def _detect_service_type(self, service_name: str, service_config: Dict[str, Any]) -> str:
        """Detect service type from service configuration"""
        # Check image name for known patterns
        image = service_config.get('image', '').lower()
        
        # Direct image name matches
        if 'wordpress' in image:
            return 'wordpress'
        elif 'n8nio/n8n' in image:
            return 'n8n'
        elif 'ghost' in image:
            return 'ghost'
        elif 'nextcloud' in image:
            return 'nextcloud'
        elif 'grafana' in image:
            return 'grafana'
        elif 'portainer' in image:
            return 'portainer'
        elif 'jellyfin' in image:
            return 'jellyfin'
        elif 'gitea' in image:
            return 'gitea'
        elif 'nginx' in image:
            return 'nginx'
        elif 'apache' in image or 'httpd' in image:
            return 'apache'
        
        # Check service name patterns
        service_name_lower = service_name.lower()
        for service_type in self.SERVICE_CONFIGS.keys():
            if service_type in service_name_lower:
                return service_type
        
        # Check exposed ports
        ports = service_config.get('ports', [])
        for port_config in ports:
            if isinstance(port_config, str):
                if ':80' in port_config or ':8080' in port_config:
                    return 'nginx'  # Default web service
                elif ':3000' in port_config:
                    return 'grafana'  # Common Grafana port
                elif ':5678' in port_config:
                    return 'n8n'
        
        # Default fallback
        return 'generic'
    
    def validate_labels(self, labels: Dict[str, str]) -> Tuple[bool, List[str]]:
        """Validate generated labels"""
        errors = []
        
        # Check required labels
        required_labels = [
            'traefik.enable',
            'traefik.docker.network'
        ]
        
        for required in required_labels:
            if required not in labels:
                errors.append(f"Missing required label: {required}")
        
        # Check router configuration
        routers = set()
        for label_key in labels.keys():
            if '.routers.' in label_key:
                router_name = label_key.split('.routers.')[1].split('.')[0]
                routers.add(router_name)
        
        # Validate each router has required configuration
        for router in routers:
            router_labels = [k for k in labels.keys() if f'.routers.{router}.' in k]
            
            # Check for rule
            if not any('rule' in label for label in router_labels):
                errors.append(f"Router {router} missing rule configuration")
            
            # Check for entrypoints
            if not any('entrypoints' in label for label in router_labels):
                errors.append(f"Router {router} missing entrypoints configuration")
        
        return len(errors) == 0, errors
    
    def update_service_config(self, service_type: str, config: Dict[str, Any]) -> bool:
        """Update service configuration"""
        try:
            if service_type in self.SERVICE_CONFIGS:
                self.SERVICE_CONFIGS[service_type].update(config)
                logger.info(f"Updated configuration for service type: {service_type}")
                return True
            else:
                logger.error(f"Unknown service type: {service_type}")
                return False
        except Exception as e:
            logger.error(f"Error updating service config: {e}")
            return False
    
    def add_middleware_config(self, name: str, config: Dict[str, Any]) -> bool:
        """Add custom middleware configuration"""
        try:
            self.MIDDLEWARE_CONFIGS[name] = config
            logger.info(f"Added middleware configuration: {name}")
            return True
        except Exception as e:
            logger.error(f"Error adding middleware config: {e}")
            return False
    
    def get_supported_services(self) -> List[str]:
        """Get list of supported service types"""
        return list(self.SERVICE_CONFIGS.keys())
    
    def get_service_config(self, service_type: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific service type"""
        return self.SERVICE_CONFIGS.get(service_type)