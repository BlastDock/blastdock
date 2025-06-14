"""
Enhanced Docker client with robust error handling and connection management
"""

import time
import subprocess
import shlex
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from ..utils.logging import get_logger
from .errors import (
    DockerError, DockerNotFoundError, DockerNotRunningError,
    DockerConnectionError, create_docker_error
)

logger = get_logger(__name__)


class DockerClient:
    """Enhanced Docker client with comprehensive error handling"""
    
    def __init__(self, timeout: int = 300, max_retries: int = 3):
        """Initialize Docker client with configuration"""
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = get_logger(__name__)
        
        # Connection state
        self._connection_verified = False
        self._docker_version = None
        self._docker_compose_version = None
        
        self.logger.debug("Docker client initialized")
    
    def _run_command(self, cmd: List[str], cwd: Optional[str] = None,
                    capture_output: bool = True, check: bool = True,
                    timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Run Docker command with error handling and retries"""
        timeout = timeout or self.timeout
        
        # Log the command (safely)
        safe_cmd = ' '.join(shlex.quote(arg) for arg in cmd)
        self.logger.debug(f"Running Docker command: {safe_cmd}")
        
        for attempt in range(self.max_retries):
            try:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=capture_output,
                    text=True,
                    timeout=timeout,
                    check=check
                )
                
                if result.stdout:
                    self.logger.debug(f"Command output: {result.stdout[:500]}...")
                if result.stderr and result.returncode == 0:
                    self.logger.debug(f"Command stderr: {result.stderr[:500]}...")
                
                return result
                
            except subprocess.TimeoutExpired as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Command timed out after {timeout}s: {safe_cmd}")
                    raise DockerError(
                        f"Docker command timed out after {timeout} seconds",
                        f"Command: {safe_cmd}",
                        [
                            "Increase timeout value",
                            "Check Docker daemon performance",
                            "Verify system resources availability"
                        ]
                    )
                else:
                    self.logger.warning(f"Command timeout, retrying (attempt {attempt + 1})")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except subprocess.CalledProcessError as e:
                if attempt == self.max_retries - 1:
                    self.logger.error(f"Command failed: {safe_cmd}, exit code: {e.returncode}")
                    self.logger.error(f"Command stderr: {e.stderr}")
                    
                    # Create contextual error
                    context = {
                        'command': safe_cmd,
                        'exit_code': e.returncode,
                        'stderr': e.stderr
                    }
                    raise create_docker_error(e, f"Docker command", context)
                else:
                    # Some commands might fail transiently
                    if e.returncode in [125, 126, 127]:  # Don't retry these
                        raise create_docker_error(e, f"Docker command")
                    self.logger.warning(f"Command failed, retrying (attempt {attempt + 1})")
                    time.sleep(1)
                    
            except FileNotFoundError as e:
                self.logger.error("Docker command not found")
                raise DockerNotFoundError("Docker CLI not found in PATH")
                
            except PermissionError as e:
                self.logger.error("Permission denied for Docker command")
                raise DockerConnectionError("Permission denied accessing Docker")
        
        # Should not reach here
        raise DockerError("Unexpected error in Docker command execution")
    
    def check_docker_availability(self) -> Dict[str, Any]:
        """Check if Docker is available and working"""
        availability = {
            'docker_available': False,
            'docker_running': False,
            'docker_compose_available': False,
            'docker_version': None,
            'docker_compose_version': None,
            'errors': [],
            'warnings': []
        }
        
        # Check Docker CLI
        try:
            result = self._run_command(['docker', '--version'], check=False)
            if result.returncode == 0:
                availability['docker_available'] = True
                version_line = result.stdout.strip()
                # Extract version (e.g., "Docker version 20.10.21, build baeda1f")
                if 'version' in version_line:
                    try:
                        version = version_line.split()[2].rstrip(',')
                        availability['docker_version'] = version
                        self._docker_version = version
                    except (IndexError, ValueError):
                        availability['warnings'].append("Could not parse Docker version")
            else:
                availability['errors'].append("Docker CLI not responding")
                
        except Exception as e:
            availability['errors'].append(f"Docker CLI check failed: {str(e)}")
        
        # Check Docker daemon
        if availability['docker_available']:
            try:
                result = self._run_command(['docker', 'info'], check=False)
                if result.returncode == 0:
                    availability['docker_running'] = True
                else:
                    availability['errors'].append("Docker daemon not running or not accessible")
                    
            except Exception as e:
                availability['errors'].append(f"Docker daemon check failed: {str(e)}")
        
        # Check Docker Compose
        try:
            # Try docker compose (newer plugin)
            result = self._run_command(['docker', 'compose', 'version'], check=False)
            if result.returncode == 0:
                availability['docker_compose_available'] = True
                version_line = result.stdout.strip()
                if 'version' in version_line:
                    try:
                        # Extract version from "Docker Compose version v2.12.2"
                        parts = version_line.split()
                        for part in parts:
                            if part.startswith('v') and '.' in part:
                                availability['docker_compose_version'] = part
                                self._docker_compose_version = part
                                break
                    except (IndexError, ValueError):
                        availability['warnings'].append("Could not parse Docker Compose version")
            else:
                # Try legacy docker-compose
                result = self._run_command(['docker-compose', '--version'], check=False)
                if result.returncode == 0:
                    availability['docker_compose_available'] = True
                    version_line = result.stdout.strip()
                    if 'version' in version_line:
                        try:
                            # Extract version from "docker-compose version 1.29.2"
                            version = version_line.split()[2].rstrip(',')
                            availability['docker_compose_version'] = version
                            self._docker_compose_version = version
                        except (IndexError, ValueError):
                            availability['warnings'].append("Could not parse Docker Compose version")
                else:
                    availability['errors'].append("Docker Compose not available")
                    
        except Exception as e:
            availability['errors'].append(f"Docker Compose check failed: {str(e)}")
        
        # Update connection state
        self._connection_verified = availability['docker_running']
        
        self.logger.info(f"Docker availability check completed: {availability}")
        return availability
    
    def ensure_connection(self):
        """Ensure Docker connection is available, raise error if not"""
        if not self._connection_verified:
            availability = self.check_docker_availability()
            
            if not availability['docker_available']:
                raise DockerNotFoundError()
            
            if not availability['docker_running']:
                raise DockerNotRunningError()
            
            if not availability['docker_compose_available']:
                self.logger.warning("Docker Compose not available")
    
    def get_version_info(self) -> Dict[str, Optional[str]]:
        """Get Docker and Docker Compose version information"""
        if not self._docker_version or not self._docker_compose_version:
            self.check_docker_availability()
        
        return {
            'docker_version': self._docker_version,
            'docker_compose_version': self._docker_compose_version
        }
    
    def execute_command(self, cmd: List[str], cwd: Optional[str] = None,
                       capture_output: bool = True, check: bool = True,
                       timeout: Optional[int] = None) -> subprocess.CompletedProcess:
        """Execute a Docker command with error handling"""
        self.ensure_connection()
        return self._run_command(cmd, cwd, capture_output, check, timeout)
    
    def execute_compose_command(self, cmd: List[str], compose_file: Optional[str] = None,
                               project_name: Optional[str] = None,
                               cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """Execute a Docker Compose command with proper error handling"""
        self.ensure_connection()
        
        # Build compose command
        compose_cmd = []
        
        # Use modern docker compose if available, fallback to docker-compose
        if self._docker_compose_version and self._docker_compose_version.startswith('v'):
            compose_cmd = ['docker', 'compose']
        else:
            compose_cmd = ['docker-compose']
        
        # Add compose file
        if compose_file:
            compose_cmd.extend(['-f', compose_file])
        
        # Add project name
        if project_name:
            compose_cmd.extend(['-p', project_name])
        
        # Add the actual command
        compose_cmd.extend(cmd)
        
        try:
            return self._run_command(compose_cmd, cwd)
        except Exception as e:
            context = {
                'compose_file': compose_file,
                'project_name': project_name,
                'command': ' '.join(cmd)
            }
            raise create_docker_error(e, "Docker Compose operation", context)
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive Docker system information"""
        self.ensure_connection()
        
        info = {
            'versions': self.get_version_info(),
            'system': {},
            'storage': {},
            'runtime': {}
        }
        
        try:
            # Get docker info
            result = self.execute_command(['docker', 'info', '--format', '{{json .}}'])
            import json
            docker_info = json.loads(result.stdout)
            
            info['system'] = {
                'containers': docker_info.get('Containers', 0),
                'containers_running': docker_info.get('ContainersRunning', 0),
                'containers_stopped': docker_info.get('ContainersStopped', 0),
                'images': docker_info.get('Images', 0),
                'server_version': docker_info.get('ServerVersion'),
                'operating_system': docker_info.get('OperatingSystem'),
                'architecture': docker_info.get('Architecture'),
                'cpus': docker_info.get('NCPU'),
                'memory': docker_info.get('MemTotal')
            }
            
            if 'Driver' in docker_info:
                info['storage']['driver'] = docker_info['Driver']
                info['storage']['driver_status'] = docker_info.get('DriverStatus', [])
            
            info['runtime']['default_runtime'] = docker_info.get('DefaultRuntime')
            info['runtime']['runtimes'] = list(docker_info.get('Runtimes', {}).keys())
            
        except Exception as e:
            self.logger.warning(f"Failed to get detailed Docker info: {e}")
            info['error'] = str(e)
        
        return info
    
    def cleanup_resources(self, aggressive: bool = False) -> Dict[str, Any]:
        """Clean up Docker resources to free space"""
        self.ensure_connection()
        
        cleanup_results = {
            'containers_removed': 0,
            'images_removed': 0,
            'volumes_removed': 0,
            'networks_removed': 0,
            'space_reclaimed': '0B',
            'errors': []
        }
        
        try:
            # Remove stopped containers
            result = self.execute_command(['docker', 'container', 'prune', '-f'])
            if 'Total reclaimed space' in result.stdout:
                # Parse space reclaimed
                import re
                space_match = re.search(r'Total reclaimed space: ([\d.]+\w+)', result.stdout)
                if space_match:
                    cleanup_results['space_reclaimed'] = space_match.group(1)
            
            # Count removed containers
            container_match = re.search(r'Deleted Containers:\n(.+?)(?:\n\n|\Z)', result.stdout, re.DOTALL)
            if container_match:
                cleanup_results['containers_removed'] = len(container_match.group(1).strip().split('\n'))
                
        except Exception as e:
            cleanup_results['errors'].append(f"Container cleanup failed: {str(e)}")
        
        try:
            # Remove dangling images
            if aggressive:
                result = self.execute_command(['docker', 'image', 'prune', '-a', '-f'])
            else:
                result = self.execute_command(['docker', 'image', 'prune', '-f'])
                
            # Count removed images
            image_match = re.search(r'Deleted Images:\n(.+?)(?:\n\n|\Z)', result.stdout, re.DOTALL)
            if image_match:
                cleanup_results['images_removed'] = len(image_match.group(1).strip().split('\n'))
                
        except Exception as e:
            cleanup_results['errors'].append(f"Image cleanup failed: {str(e)}")
        
        try:
            # Remove unused volumes
            result = self.execute_command(['docker', 'volume', 'prune', '-f'])
            
            # Count removed volumes
            volume_match = re.search(r'Deleted Volumes:\n(.+?)(?:\n\n|\Z)', result.stdout, re.DOTALL)
            if volume_match:
                cleanup_results['volumes_removed'] = len(volume_match.group(1).strip().split('\n'))
                
        except Exception as e:
            cleanup_results['errors'].append(f"Volume cleanup failed: {str(e)}")
        
        try:
            # Remove unused networks
            result = self.execute_command(['docker', 'network', 'prune', '-f'])
            
            # Count removed networks
            network_match = re.search(r'Deleted Networks:\n(.+?)(?:\n\n|\Z)', result.stdout, re.DOTALL)
            if network_match:
                cleanup_results['networks_removed'] = len(network_match.group(1).strip().split('\n'))
                
        except Exception as e:
            cleanup_results['errors'].append(f"Network cleanup failed: {str(e)}")
        
        self.logger.info(f"Docker cleanup completed: {cleanup_results}")
        return cleanup_results


# Global client instance
_docker_client: Optional[DockerClient] = None


def get_docker_client() -> DockerClient:
    """Get the global Docker client instance"""
    global _docker_client
    if _docker_client is None:
        _docker_client = DockerClient()
    return _docker_client


def reset_docker_client():
    """Reset the global Docker client instance"""
    global _docker_client
    _docker_client = None