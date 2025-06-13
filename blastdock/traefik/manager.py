"""
Traefik Manager - Core Traefik integration and management
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from ..utils.docker_utils import DockerClient
from ..utils.logging import get_logger
from ..utils.filesystem import paths
from ..core.config import get_config

logger = get_logger(__name__)


class TraefikManager:
    """Manages Traefik installation, configuration, and integration"""
    
    TRAEFIK_CONTAINER_NAME = "blastdock-traefik"
    TRAEFIK_NETWORK = "blastdock-network"
    TRAEFIK_PROJECT_NAME = "blastdock-traefik"
    
    def __init__(self):
        self.docker_client = DockerClient()
        self.config = get_config()
        self.traefik_dir = paths.data_dir / "traefik"
        self.letsencrypt_dir = self.traefik_dir / "letsencrypt"
        
    def is_installed(self) -> bool:
        """Check if Traefik is installed and running"""
        try:
            containers = self.docker_client.list_containers()
            for container in containers:
                if container.get('name') == self.TRAEFIK_CONTAINER_NAME:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking Traefik installation: {e}")
            return False
    
    def is_running(self) -> bool:
        """Check if Traefik is currently running"""
        try:
            containers = self.docker_client.list_containers(all=False)
            for container in containers:
                if (container.get('name') == self.TRAEFIK_CONTAINER_NAME and 
                    container.get('state') == 'running'):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking Traefik status: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive Traefik status information"""
        status = {
            'installed': self.is_installed(),
            'running': self.is_running(),
            'network_exists': self.network_exists(),
            'dashboard_url': self.get_dashboard_url(),
            'version': None,
            'uptime': None,
            'services_count': 0,
            'ssl_certificates': []
        }
        
        if status['running']:
            try:
                # Get container details
                container_info = self.docker_client.get_container_info(self.TRAEFIK_CONTAINER_NAME)
                if container_info:
                    status['version'] = self._extract_traefik_version(container_info)
                    status['uptime'] = self._calculate_uptime(container_info)
                
                # Get services count
                status['services_count'] = self._count_traefik_services()
                
                # Get SSL certificates info
                status['ssl_certificates'] = self.get_ssl_certificates()
                
            except Exception as e:
                logger.warning(f"Error getting detailed Traefik status: {e}")
        
        return status
    
    def network_exists(self) -> bool:
        """Check if the Traefik network exists"""
        try:
            networks = self.docker_client.list_networks()
            return any(net.get('name') == self.TRAEFIK_NETWORK for net in networks)
        except Exception as e:
            logger.error(f"Error checking network existence: {e}")
            return False
    
    def create_network(self) -> bool:
        """Create the Traefik network if it doesn't exist"""
        if self.network_exists():
            logger.info(f"Network {self.TRAEFIK_NETWORK} already exists")
            return True
        
        try:
            self.docker_client.create_network(
                self.TRAEFIK_NETWORK,
                driver='bridge',
                attachable=True
            )
            logger.info(f"Created network {self.TRAEFIK_NETWORK}")
            return True
        except Exception as e:
            logger.error(f"Failed to create network {self.TRAEFIK_NETWORK}: {e}")
            return False
    
    def get_dashboard_url(self) -> Optional[str]:
        """Get the Traefik dashboard URL"""
        if not self.is_running():
            return None
        
        try:
            # Get dashboard domain from config
            traefik_config = self.config.get('traefik', {})
            dashboard_domain = traefik_config.get('dashboard_domain', 'traefik.blastdock.local')
            
            # Check if using custom domain or localhost
            if dashboard_domain.endswith('.local') or dashboard_domain.startswith('localhost'):
                return f"http://localhost:8080"  # Default dashboard port
            else:
                return f"https://{dashboard_domain}"
                
        except Exception as e:
            logger.error(f"Error getting dashboard URL: {e}")
            return "http://localhost:8080"
    
    def get_logs(self, follow: bool = False, tail: int = 100) -> str:
        """Get Traefik container logs"""
        try:
            return self.docker_client.get_container_logs(
                self.TRAEFIK_CONTAINER_NAME,
                follow=follow,
                tail=tail
            )
        except Exception as e:
            logger.error(f"Error getting Traefik logs: {e}")
            return f"Error retrieving logs: {e}"
    
    def restart(self) -> bool:
        """Restart the Traefik container"""
        try:
            if not self.is_installed():
                logger.error("Traefik is not installed")
                return False
            
            logger.info("Restarting Traefik...")
            self.docker_client.restart_container(self.TRAEFIK_CONTAINER_NAME)
            logger.info("Traefik restarted successfully")
            return True
        except Exception as e:
            logger.error(f"Error restarting Traefik: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the Traefik container"""
        try:
            if not self.is_running():
                logger.info("Traefik is not running")
                return True
            
            logger.info("Stopping Traefik...")
            self.docker_client.stop_container(self.TRAEFIK_CONTAINER_NAME)
            logger.info("Traefik stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping Traefik: {e}")
            return False
    
    def start(self) -> bool:
        """Start the Traefik container"""
        try:
            if not self.is_installed():
                logger.error("Traefik is not installed")
                return False
            
            if self.is_running():
                logger.info("Traefik is already running")
                return True
            
            logger.info("Starting Traefik...")
            self.docker_client.start_container(self.TRAEFIK_CONTAINER_NAME)
            logger.info("Traefik started successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting Traefik: {e}")
            return False
    
    def remove(self, remove_data: bool = False) -> bool:
        """Remove Traefik installation"""
        try:
            # Stop Traefik first
            if self.is_running():
                self.stop()
            
            # Remove container
            if self.is_installed():
                logger.info("Removing Traefik container...")
                self.docker_client.remove_container(self.TRAEFIK_CONTAINER_NAME, force=True)
            
            # Remove network
            if self.network_exists():
                logger.info(f"Removing network {self.TRAEFIK_NETWORK}...")
                self.docker_client.remove_network(self.TRAEFIK_NETWORK)
            
            # Remove data if requested
            if remove_data and self.traefik_dir.exists():
                logger.info("Removing Traefik data...")
                import shutil
                shutil.rmtree(self.traefik_dir)
            
            logger.info("Traefik removed successfully")
            return True
        except Exception as e:
            logger.error(f"Error removing Traefik: {e}")
            return False
    
    def get_ssl_certificates(self) -> List[Dict[str, Any]]:
        """Get information about SSL certificates"""
        certificates = []
        
        try:
            acme_file = self.letsencrypt_dir / "acme.json"
            if acme_file.exists():
                with open(acme_file, 'r') as f:
                    acme_data = json.load(f)
                
                # Parse ACME data to extract certificate information
                resolvers = acme_data.get('letsencrypt', {}).get('Certificates', [])
                for cert in resolvers:
                    certificates.append({
                        'domain': cert.get('domain', {}).get('main', 'unknown'),
                        'sans': cert.get('domain', {}).get('sans', []),
                        'url': cert.get('url', ''),
                        'stable_url': cert.get('stableURL', '')
                    })
        except Exception as e:
            logger.warning(f"Error reading SSL certificates: {e}")
        
        return certificates
    
    def _extract_traefik_version(self, container_info: Dict) -> Optional[str]:
        """Extract Traefik version from container info"""
        try:
            image = container_info.get('image', '')
            if ':' in image:
                return image.split(':')[-1]
            return None
        except Exception:
            return None
    
    def _calculate_uptime(self, container_info: Dict) -> Optional[str]:
        """Calculate container uptime"""
        try:
            from datetime import datetime
            created = container_info.get('created')
            if created:
                created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
                uptime = datetime.now(created_time.tzinfo) - created_time
                return str(uptime).split('.')[0]  # Remove microseconds
            return None
        except Exception:
            return None
    
    def _count_traefik_services(self) -> int:
        """Count services managed by Traefik"""
        try:
            # Get all containers with Traefik labels
            containers = self.docker_client.list_containers(all=False)
            traefik_services = 0
            
            for container in containers:
                labels = container.get('labels', {})
                if labels.get('traefik.enable') == 'true':
                    traefik_services += 1
            
            return traefik_services
        except Exception as e:
            logger.warning(f"Error counting Traefik services: {e}")
            return 0
    
    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """Validate Traefik configuration"""
        issues = []
        
        # Check if Traefik is running
        if not self.is_running():
            issues.append("Traefik is not running")
        
        # Check network
        if not self.network_exists():
            issues.append(f"Network {self.TRAEFIK_NETWORK} does not exist")
        
        # Check SSL directory
        if not self.letsencrypt_dir.exists():
            issues.append("Let's Encrypt directory does not exist")
        
        # Check dashboard access
        dashboard_url = self.get_dashboard_url()
        if not dashboard_url:
            issues.append("Dashboard URL is not accessible")
        
        # Check configuration file
        config_file = self.traefik_dir / "traefik.yml"
        if not config_file.exists():
            issues.append("Traefik configuration file missing")
        
        return len(issues) == 0, issues