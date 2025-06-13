"""
Traefik Installer - Handles automatic installation and configuration of Traefik
"""

import os
import yaml
import json
from typing import Dict, Optional, Tuple, List
from pathlib import Path

from ..utils.logging import get_logger
from ..utils.filesystem import paths
from ..utils.docker_utils import DockerClient
from ..core.config import get_config_manager
from .manager import TraefikManager

logger = get_logger(__name__)


class TraefikInstaller:
    """Handles Traefik installation and initial configuration"""
    
    def __init__(self):
        self.docker_client = DockerClient()
        self.traefik_manager = TraefikManager()
        self.config_manager = get_config_manager()
        self.traefik_dir = paths.data_dir / "traefik"
        self.letsencrypt_dir = self.traefik_dir / "letsencrypt"
    
    def install(self, email: str, default_domain: str = "blastdock.local", 
               enable_dashboard: bool = True, dashboard_domain: Optional[str] = None) -> bool:
        """Install Traefik with Let's Encrypt support"""
        try:
            logger.info("Starting Traefik installation...")
            
            # Check if already installed
            if self.traefik_manager.is_installed():
                logger.warning("Traefik is already installed")
                return True
            
            # Validate email
            if not self._validate_email(email):
                logger.error("Invalid email address provided")
                return False
            
            # Create directories
            self._create_directories()
            
            # Create network
            if not self.traefik_manager.create_network():
                logger.error("Failed to create Traefik network")
                return False
            
            # Generate configuration files
            self._generate_traefik_config(email, default_domain, enable_dashboard, dashboard_domain)
            self._generate_docker_compose(email, default_domain, enable_dashboard, dashboard_domain)
            
            # Deploy Traefik
            if not self._deploy_traefik():
                logger.error("Failed to deploy Traefik")
                return False
            
            # Update BlastDock configuration
            self._update_blastdock_config(email, default_domain, enable_dashboard, dashboard_domain)
            
            # Wait for Traefik to be ready
            if not self._wait_for_traefik():
                logger.warning("Traefik may not be fully ready, but installation completed")
            
            logger.info("Traefik installation completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during Traefik installation: {e}")
            return False
    
    def uninstall(self, remove_data: bool = False) -> bool:
        """Uninstall Traefik"""
        try:
            logger.info("Uninstalling Traefik...")
            
            # Use TraefikManager to remove
            success = self.traefik_manager.remove(remove_data=remove_data)
            
            if success:
                # Clean up configuration
                docker_compose_file = self.traefik_dir / "docker-compose.yml"
                if docker_compose_file.exists():
                    docker_compose_file.unlink()
                
                # Update BlastDock config
                self._remove_traefik_from_config()
                
                logger.info("Traefik uninstalled successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Error during Traefik uninstall: {e}")
            return False
    
    def upgrade(self, new_version: str = "latest") -> bool:
        """Upgrade Traefik to a new version"""
        try:
            logger.info(f"Upgrading Traefik to version {new_version}...")
            
            if not self.traefik_manager.is_installed():
                logger.error("Traefik is not installed")
                return False
            
            # Stop current Traefik
            self.traefik_manager.stop()
            
            # Update docker-compose with new version
            compose_file = self.traefik_dir / "docker-compose.yml"
            if compose_file.exists():
                with open(compose_file, 'r') as f:
                    compose_data = yaml.safe_load(f)
                
                # Update image version
                if 'services' in compose_data and 'traefik' in compose_data['services']:
                    current_image = compose_data['services']['traefik']['image']
                    image_base = current_image.split(':')[0]
                    compose_data['services']['traefik']['image'] = f"{image_base}:{new_version}"
                    
                    with open(compose_file, 'w') as f:
                        yaml.dump(compose_data, f, default_flow_style=False)
            
            # Deploy updated Traefik
            if not self._deploy_traefik():
                logger.error("Failed to deploy upgraded Traefik")
                return False
            
            logger.info("Traefik upgraded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during Traefik upgrade: {e}")
            return False
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _create_directories(self):
        """Create necessary directories for Traefik"""
        self.traefik_dir.mkdir(parents=True, exist_ok=True)
        self.letsencrypt_dir.mkdir(parents=True, exist_ok=True)
        
        # Create acme.json with correct permissions
        acme_file = self.letsencrypt_dir / "acme.json"
        if not acme_file.exists():
            acme_file.touch()
            acme_file.chmod(0o600)  # Set restrictive permissions
    
    def _generate_traefik_config(self, email: str, default_domain: str, 
                                enable_dashboard: bool, dashboard_domain: Optional[str]):
        """Generate Traefik configuration file"""
        config = {
            'global': {
                'checkNewVersion': False,
                'sendAnonymousUsage': False
            },
            'api': {
                'dashboard': enable_dashboard,
                'insecure': enable_dashboard  # Allow dashboard on port 8080
            },
            'entryPoints': {
                'web': {
                    'address': ':80',
                    'http': {
                        'redirections': {
                            'entryPoint': {
                                'to': 'websecure',
                                'scheme': 'https',
                                'permanent': True
                            }
                        }
                    }
                },
                'websecure': {
                    'address': ':443'
                }
            },
            'providers': {
                'docker': {
                    'endpoint': 'unix:///var/run/docker.sock',
                    'exposedByDefault': False,
                    'network': TraefikManager.TRAEFIK_NETWORK
                }
            },
            'certificatesResolvers': {
                'letsencrypt': {
                    'acme': {
                        'email': email,
                        'storage': '/letsencrypt/acme.json',
                        'httpChallenge': {
                            'entryPoint': 'web'
                        }
                    }
                }
            },
            'log': {
                'level': 'INFO'
            },
            'accessLog': {}
        }
        
        config_file = self.traefik_dir / "traefik.yml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Generated Traefik configuration at {config_file}")
    
    def _generate_docker_compose(self, email: str, default_domain: str,
                                enable_dashboard: bool, dashboard_domain: Optional[str]):
        """Generate Docker Compose file for Traefik"""
        
        if not dashboard_domain:
            dashboard_domain = f"traefik.{default_domain}"
        
        compose_config = {
            'version': '3.8',
            'services': {
                'traefik': {
                    'image': 'traefik:v3.0',
                    'container_name': TraefikManager.TRAEFIK_CONTAINER_NAME,
                    'restart': 'unless-stopped',
                    'ports': [
                        '80:80',
                        '443:443'
                    ],
                    'volumes': [
                        '/var/run/docker.sock:/var/run/docker.sock:ro',
                        f'{self.traefik_dir}/traefik.yml:/traefik.yml:ro',
                        f'{self.letsencrypt_dir}:/letsencrypt'
                    ],
                    'networks': [TraefikManager.TRAEFIK_NETWORK],
                    'labels': [
                        'traefik.enable=true',
                        f'traefik.docker.network={TraefikManager.TRAEFIK_NETWORK}'
                    ],
                    'environment': [
                        f'TRAEFIK_API_DASHBOARD={str(enable_dashboard).lower()}',
                        f'TRAEFIK_CERTIFICATESRESOLVERS_LETSENCRYPT_ACME_EMAIL={email}'
                    ]
                }
            },
            'networks': {
                TraefikManager.TRAEFIK_NETWORK: {
                    'external': True
                }
            }
        }
        
        # Add dashboard configuration if enabled
        if enable_dashboard:
            compose_config['services']['traefik']['ports'].append('8080:8080')
            
            # Add dashboard labels for external access
            if not dashboard_domain.endswith('.local'):
                dashboard_labels = [
                    f'traefik.http.routers.dashboard.rule=Host(`{dashboard_domain}`)',
                    'traefik.http.routers.dashboard.entrypoints=websecure',
                    'traefik.http.routers.dashboard.tls.certresolver=letsencrypt',
                    'traefik.http.routers.dashboard.service=api@internal'
                ]
                compose_config['services']['traefik']['labels'].extend(dashboard_labels)
        
        compose_file = self.traefik_dir / "docker-compose.yml"
        with open(compose_file, 'w') as f:
            yaml.dump(compose_config, f, default_flow_style=False)
        
        logger.info(f"Generated Docker Compose file at {compose_file}")
    
    def _deploy_traefik(self) -> bool:
        """Deploy Traefik using Docker Compose"""
        try:
            compose_file = self.traefik_dir / "docker-compose.yml"
            
            # Use docker-compose to deploy
            result = self.docker_client.compose_up(
                str(compose_file),
                project_name=TraefikManager.TRAEFIK_PROJECT_NAME,
                detached=True
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error deploying Traefik: {e}")
            return False
    
    def _update_blastdock_config(self, email: str, default_domain: str,
                               enable_dashboard: bool, dashboard_domain: Optional[str]):
        """Update BlastDock configuration with Traefik settings"""
        try:
            config = self.config_manager.config
            
            # Update Traefik configuration
            config['traefik'] = {
                'enabled': True,
                'network': TraefikManager.TRAEFIK_NETWORK,
                'letsencrypt_email': email,
                'default_cert_resolver': 'letsencrypt',
                'dashboard_enabled': enable_dashboard,
                'dashboard_domain': dashboard_domain or f"traefik.{default_domain}"
            }
            
            # Update domain configuration
            if 'domains' not in config:
                config['domains'] = {}
            
            config['domains'].update({
                'default_domain': default_domain,
                'wildcard_enabled': True,
                'reserved_subdomains': ['www', 'mail', 'ftp', 'traefik', 'api']
            })
            
            # Update SSL configuration
            config['ssl'] = {
                'default_enabled': True,
                'force_https': True,
                'hsts_enabled': True
            }
            
            # Save configuration
            self.config_manager.save_config()
            logger.info("Updated BlastDock configuration with Traefik settings")
            
        except Exception as e:
            logger.error(f"Error updating BlastDock configuration: {e}")
    
    def _remove_traefik_from_config(self):
        """Remove Traefik configuration from BlastDock config"""
        try:
            config = self.config_manager.config
            
            if 'traefik' in config:
                config['traefik']['enabled'] = False
            
            self.config_manager.save_config()
            logger.info("Removed Traefik from BlastDock configuration")
            
        except Exception as e:
            logger.error(f"Error removing Traefik from configuration: {e}")
    
    def _wait_for_traefik(self, timeout: int = 30) -> bool:
        """Wait for Traefik to be ready"""
        import time
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.traefik_manager.is_running():
                time.sleep(2)  # Additional wait for full initialization
                return True
            time.sleep(1)
        
        return False
    
    def get_installation_requirements(self) -> Dict[str, str]:
        """Get system requirements for Traefik installation"""
        return {
            'docker': 'Docker Engine 20.10+',
            'docker_compose': 'Docker Compose 2.0+',
            'ports': 'Ports 80, 443, and 8080 available',
            'permissions': 'Docker socket access',
            'disk_space': 'At least 100MB free space'
        }
    
    def check_installation_requirements(self) -> Tuple[bool, List[str]]:
        """Check if system meets installation requirements"""
        issues = []
        
        # Check Docker
        try:
            docker_info = self.docker_client.get_docker_info()
            if not docker_info:
                issues.append("Docker is not running or accessible")
        except Exception:
            issues.append("Docker is not installed or accessible")
        
        # Check Docker Compose
        try:
            self.docker_client.check_compose_version()
        except Exception:
            issues.append("Docker Compose is not available")
        
        # Check port availability
        ports_to_check = [80, 443, 8080]
        for port in ports_to_check:
            if self._is_port_in_use(port):
                issues.append(f"Port {port} is already in use")
        
        # Check disk space
        if not self._check_disk_space():
            issues.append("Insufficient disk space (need at least 100MB)")
        
        return len(issues) == 0, issues
    
    def _is_port_in_use(self, port: int) -> bool:
        """Check if a port is already in use"""
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def _check_disk_space(self, required_mb: int = 100) -> bool:
        """Check if there's enough disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(paths.data_dir)
            free_mb = free / (1024 * 1024)
            return free_mb >= required_mb
        except Exception:
            return True  # Assume OK if we can't check