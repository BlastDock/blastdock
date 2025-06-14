"""
Enhanced Docker utility functions for BlastDock
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any, Iterator
import docker
from docker.errors import DockerException, NotFound, APIError

from .logging import get_logger

logger = get_logger(__name__)


class DockerError(Exception):
    """Base Docker error"""
    pass


class DockerNotFoundError(DockerError):
    """Docker not found error"""
    pass


class DockerNotRunningError(DockerError):
    """Docker not running error"""
    pass


class EnhancedDockerClient:
    """Enhanced Docker client with comprehensive functionality"""
    
    def __init__(self):
        """Initialize Docker client"""
        self.logger = get_logger(__name__)
        self._client = None
        self._compose_manager = None
        
    @property
    def client(self):
        """Get Docker client instance"""
        if self._client is None:
            try:
                self._client = docker.from_env()
            except DockerException as e:
                self.logger.error(f"Failed to connect to Docker: {e}")
                raise DockerNotRunningError("Docker is not running or accessible")
        return self._client
    
    def is_running(self) -> bool:
        """Check if Docker daemon is running"""
        try:
            self.client.ping()
            return True
        except Exception:
            return False
    
    def is_docker_running(self) -> bool:
        """Alias for is_running() to maintain interface consistency"""
        return self.is_running()
    
    def get_container_by_name(self, name: str):
        """Get container by name"""
        try:
            return self.client.containers.get(name)
        except NotFound:
            return None
        except Exception as e:
            self.logger.error(f"Error getting container {name}: {e}")
            return None
    
    def list_containers(self, all: bool = False) -> List[Any]:
        """List all containers"""
        try:
            return self.client.containers.list(all=all)
        except Exception as e:
            self.logger.error(f"Error listing containers: {e}")
            return []
    
    def get_container_stats(self, container_name: str) -> Dict[str, Any]:
        """Get container stats"""
        container = self.get_container_by_name(container_name)
        if container:
            try:
                return container.stats(stream=False)
            except Exception as e:
                self.logger.error(f"Error getting stats for {container_name}: {e}")
        return {}
    
    def get_container_logs(self, container_name: str, tail: int = 100) -> str:
        """Get container logs"""
        container = self.get_container_by_name(container_name)
        if container:
            try:
                return container.logs(tail=tail).decode('utf-8')
            except Exception as e:
                self.logger.error(f"Error getting logs for {container_name}: {e}")
        return ""
    
    def execute_command(self, container_name: str, command: List[str]) -> str:
        """Execute command in container"""
        container = self.get_container_by_name(container_name)
        if container:
            try:
                result = container.exec_run(command)
                return result.output.decode('utf-8')
            except Exception as e:
                self.logger.error(f"Error executing command in {container_name}: {e}")
        return ""
    
    def stop_container(self, container_name: str):
        """Stop a container"""
        container = self.get_container_by_name(container_name)
        if container:
            try:
                container.stop()
                return True
            except Exception as e:
                self.logger.error(f"Error stopping container {container_name}: {e}")
        return False
    
    def remove_container(self, container_name: str, force: bool = False):
        """Remove a container"""
        container = self.get_container_by_name(container_name)
        if container:
            try:
                container.remove(force=force)
                return True
            except Exception as e:
                self.logger.error(f"Error removing container {container_name}: {e}")
        return False
    
    def create_network(self, name: str, driver: str = "bridge") -> bool:
        """Create a Docker network"""
        try:
            self.client.networks.create(name, driver=driver)
            return True
        except Exception as e:
            self.logger.error(f"Error creating network {name}: {e}")
            return False
    
    def get_network(self, name: str):
        """Get network by name"""
        try:
            return self.client.networks.get(name)
        except NotFound:
            return None
        except Exception as e:
            self.logger.error(f"Error getting network {name}: {e}")
            return None
    
    def list_images(self) -> List[Any]:
        """List all images"""
        try:
            return self.client.images.list()
        except Exception as e:
            self.logger.error(f"Error listing images: {e}")
            return []
    
    def pull_image(self, image_name: str) -> bool:
        """Pull an image"""
        try:
            self.client.images.pull(image_name)
            return True
        except Exception as e:
            self.logger.error(f"Error pulling image {image_name}: {e}")
            return False
    
    def get_docker_info(self) -> Dict[str, Any]:
        """Get Docker system info"""
        try:
            return self.client.info()
        except Exception as e:
            self.logger.error(f"Error getting Docker info: {e}")
            return {}
    
    def get_docker_version(self) -> Dict[str, Any]:
        """Get Docker version info"""
        try:
            return self.client.version()
        except Exception as e:
            self.logger.error(f"Error getting Docker version: {e}")
            return {}


# Compatibility aliases
DockerClient = EnhancedDockerClient
