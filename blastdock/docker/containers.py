"""
Enhanced Docker container management with comprehensive error handling
"""

import json
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from ..utils.logging import get_logger
from .client import get_docker_client
from .errors import ContainerError, create_docker_error

logger = get_logger(__name__)


class ContainerManager:
    """Enhanced Docker container manager"""
    
    def __init__(self):
        """Initialize container manager"""
        self.docker_client = get_docker_client()
        self.logger = get_logger(__name__)
    
    def list_containers(self, all_containers: bool = False, 
                       filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """List containers with optional filtering"""
        cmd = ['docker', 'ps', '--format', '{{json .}}']
        
        if all_containers:
            cmd.append('-a')
        
        # Add filters
        if filters:
            for key, value in filters.items():
                cmd.extend(['--filter', f'{key}={value}'])
        
        try:
            result = self.docker_client.execute_command(cmd)
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        container = json.loads(line)
                        containers.append(container)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse container JSON: {e}")
                        continue
            
            return containers
            
        except Exception as e:
            raise create_docker_error(e, "List containers")
    
    def get_container_info(self, container_id: str) -> Dict[str, Any]:
        """Get detailed information about a container"""
        try:
            result = self.docker_client.execute_command([
                'docker', 'inspect', container_id, '--format', '{{json .}}'
            ])
            
            container_info = json.loads(result.stdout)
            
            # Extract useful information
            extracted_info = {
                'id': container_info.get('Id', '')[:12],
                'name': container_info.get('Name', '').lstrip('/'),
                'image': container_info.get('Config', {}).get('Image', ''),
                'state': container_info.get('State', {}),
                'created': container_info.get('Created', ''),
                'network_settings': container_info.get('NetworkSettings', {}),
                'mounts': container_info.get('Mounts', []),
                'config': container_info.get('Config', {}),
                'host_config': container_info.get('HostConfig', {}),
                'restart_count': container_info.get('RestartCount', 0),
                'platform': container_info.get('Platform', '')
            }
            
            return extracted_info
            
        except Exception as e:
            raise ContainerError(
                f"Failed to get container information",
                container_id=container_id
            )
    
    def start_container(self, container_id: str) -> Dict[str, Any]:
        """Start a container with monitoring"""
        start_result = {
            'success': False,
            'container_id': container_id,
            'start_time': 0,
            'final_state': 'unknown',
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            # Start the container
            self.docker_client.execute_command(['docker', 'start', container_id])
            
            # Wait for container to reach running state
            max_wait = 30  # seconds
            wait_time = 0
            
            while wait_time < max_wait:
                container_info = self.get_container_info(container_id)
                state = container_info['state'].get('Status', 'unknown')
                
                if state == 'running':
                    start_result['success'] = True
                    break
                elif state in ['exited', 'dead']:
                    start_result['errors'].append(f"Container failed to start, state: {state}")
                    break
                
                time.sleep(1)
                wait_time += 1
            
            if wait_time >= max_wait:
                start_result['errors'].append(f"Container start timeout after {max_wait} seconds")
            
            start_result['start_time'] = time.time() - start_time
            start_result['final_state'] = container_info['state'].get('Status', 'unknown')
            
            return start_result
            
        except Exception as e:
            start_result['start_time'] = time.time() - start_time
            start_result['errors'].append(str(e))
            raise ContainerError(
                f"Failed to start container",
                container_id=container_id
            )
    
    def stop_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """Stop a container gracefully"""
        stop_result = {
            'success': False,
            'container_id': container_id,
            'stop_time': 0,
            'final_state': 'unknown',
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            # Stop the container with timeout
            self.docker_client.execute_command([
                'docker', 'stop', '-t', str(timeout), container_id
            ])
            
            # Verify container stopped
            container_info = self.get_container_info(container_id)
            final_state = container_info['state'].get('Status', 'unknown')
            
            stop_result['success'] = final_state in ['exited', 'dead']
            stop_result['final_state'] = final_state
            stop_result['stop_time'] = time.time() - start_time
            
            if not stop_result['success']:
                stop_result['errors'].append(f"Container did not stop, state: {final_state}")
            
            return stop_result
            
        except Exception as e:
            stop_result['stop_time'] = time.time() - start_time
            stop_result['errors'].append(str(e))
            raise ContainerError(
                f"Failed to stop container",
                container_id=container_id
            )
    
    def remove_container(self, container_id: str, force: bool = False, 
                        remove_volumes: bool = False) -> Dict[str, Any]:
        """Remove a container"""
        remove_result = {
            'success': False,
            'container_id': container_id,
            'removed_volumes': [],
            'errors': []
        }
        
        try:
            # Get container info before removal
            try:
                container_info = self.get_container_info(container_id)
                container_name = container_info.get('name', container_id)
            except:
                container_name = container_id
            
            cmd = ['docker', 'rm']
            
            if force:
                cmd.append('-f')
            
            if remove_volumes:
                cmd.append('-v')
            
            cmd.append(container_id)
            
            result = self.docker_client.execute_command(cmd)
            
            remove_result['success'] = True
            
            # If volumes were removed, try to extract volume names from output
            if remove_volumes and result.stdout:
                # Volume removal is usually logged to stderr or not logged at all
                # We'll mark that volumes were requested to be removed
                remove_result['removed_volumes'] = ['volumes requested for removal']
            
            return remove_result
            
        except Exception as e:
            remove_result['errors'].append(str(e))
            raise ContainerError(
                f"Failed to remove container",
                container_id=container_id
            )
    
    def restart_container(self, container_id: str, timeout: int = 10) -> Dict[str, Any]:
        """Restart a container"""
        restart_result = {
            'success': False,
            'container_id': container_id,
            'restart_time': 0,
            'final_state': 'unknown',
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            # Restart the container
            self.docker_client.execute_command([
                'docker', 'restart', '-t', str(timeout), container_id
            ])
            
            # Wait for container to reach running state
            max_wait = 30  # seconds
            wait_time = 0
            
            while wait_time < max_wait:
                container_info = self.get_container_info(container_id)
                state = container_info['state'].get('Status', 'unknown')
                
                if state == 'running':
                    restart_result['success'] = True
                    break
                elif state in ['exited', 'dead']:
                    restart_result['errors'].append(f"Container failed to restart, state: {state}")
                    break
                
                time.sleep(1)
                wait_time += 1
            
            if wait_time >= max_wait:
                restart_result['errors'].append(f"Container restart timeout after {max_wait} seconds")
            
            restart_result['restart_time'] = time.time() - start_time
            restart_result['final_state'] = container_info['state'].get('Status', 'unknown')
            
            return restart_result
            
        except Exception as e:
            restart_result['restart_time'] = time.time() - start_time
            restart_result['errors'].append(str(e))
            raise ContainerError(
                f"Failed to restart container",
                container_id=container_id
            )
    
    def get_container_logs(self, container_id: str, tail: int = 100, 
                          since: Optional[str] = None, follow: bool = False) -> str:
        """Get container logs"""
        cmd = ['docker', 'logs']
        
        if tail > 0:
            cmd.extend(['--tail', str(tail)])
        
        if since:
            cmd.extend(['--since', since])
        
        if follow:
            cmd.append('--follow')
        
        cmd.append(container_id)
        
        try:
            result = self.docker_client.execute_command(cmd)
            return result.stdout
            
        except Exception as e:
            raise ContainerError(
                f"Failed to get container logs",
                container_id=container_id
            )
    
    def execute_command_in_container(self, container_id: str, command: List[str],
                                   interactive: bool = False, tty: bool = False,
                                   user: Optional[str] = None, workdir: Optional[str] = None) -> Dict[str, Any]:
        """Execute a command inside a container"""
        exec_result = {
            'success': False,
            'container_id': container_id,
            'command': command,
            'stdout': '',
            'stderr': '',
            'exit_code': None,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'exec']
            
            if interactive:
                cmd.append('-i')
            
            if tty:
                cmd.append('-t')
            
            if user:
                cmd.extend(['-u', user])
            
            if workdir:
                cmd.extend(['-w', workdir])
            
            cmd.append(container_id)
            cmd.extend(command)
            
            result = self.docker_client.execute_command(cmd, check=False)
            
            exec_result['success'] = result.returncode == 0
            exec_result['stdout'] = result.stdout
            exec_result['stderr'] = result.stderr
            exec_result['exit_code'] = result.returncode
            
            if result.returncode != 0:
                exec_result['errors'].append(f"Command exited with code {result.returncode}")
            
            return exec_result
            
        except Exception as e:
            exec_result['errors'].append(str(e))
            raise ContainerError(
                f"Failed to execute command in container",
                container_id=container_id
            )
    
    def copy_to_container(self, container_id: str, src_path: str, 
                         dest_path: str) -> Dict[str, Any]:
        """Copy files to a container"""
        copy_result = {
            'success': False,
            'container_id': container_id,
            'src_path': src_path,
            'dest_path': dest_path,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'cp', src_path, f'{container_id}:{dest_path}']
            
            self.docker_client.execute_command(cmd)
            copy_result['success'] = True
            
            return copy_result
            
        except Exception as e:
            copy_result['errors'].append(str(e))
            raise ContainerError(
                f"Failed to copy files to container",
                container_id=container_id
            )
    
    def copy_from_container(self, container_id: str, src_path: str, 
                           dest_path: str) -> Dict[str, Any]:
        """Copy files from a container"""
        copy_result = {
            'success': False,
            'container_id': container_id,
            'src_path': src_path,
            'dest_path': dest_path,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'cp', f'{container_id}:{src_path}', dest_path]
            
            self.docker_client.execute_command(cmd)
            copy_result['success'] = True
            
            return copy_result
            
        except Exception as e:
            copy_result['errors'].append(str(e))
            raise ContainerError(
                f"Failed to copy files from container",
                container_id=container_id
            )
    
    def get_container_stats(self, container_id: str, stream: bool = False) -> Dict[str, Any]:
        """Get container resource usage statistics"""
        try:
            cmd = ['docker', 'stats', container_id, '--format', '{{json .}}']
            
            if not stream:
                cmd.append('--no-stream')
            
            result = self.docker_client.execute_command(cmd)
            
            if stream:
                # For streaming, return the raw output
                return {'streaming_output': result.stdout}
            else:
                # Parse single stat result
                stats = json.loads(result.stdout)
                
                return {
                    'container_id': stats.get('Container', '')[:12],
                    'name': stats.get('Name', ''),
                    'cpu_percent': stats.get('CPUPerc', '0%'),
                    'memory_usage': stats.get('MemUsage', '0B / 0B'),
                    'memory_percent': stats.get('MemPerc', '0%'),
                    'network_io': stats.get('NetIO', '0B / 0B'),
                    'block_io': stats.get('BlockIO', '0B / 0B'),
                    'pids': stats.get('PIDs', '0')
                }
                
        except Exception as e:
            raise ContainerError(
                f"Failed to get container stats",
                container_id=container_id
            )
    
    def create_container(self, image: str, name: Optional[str] = None,
                        command: Optional[List[str]] = None,
                        environment: Optional[Dict[str, str]] = None,
                        ports: Optional[Dict[str, str]] = None,
                        volumes: Optional[Dict[str, str]] = None,
                        network: Optional[str] = None,
                        **kwargs) -> Dict[str, Any]:
        """Create a new container with specified configuration"""
        create_result = {
            'success': False,
            'container_id': None,
            'container_name': name,
            'image': image,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'create']
            
            if name:
                cmd.extend(['--name', name])
            
            # Environment variables
            if environment:
                for key, value in environment.items():
                    cmd.extend(['-e', f'{key}={value}'])
            
            # Port mappings
            if ports:
                for host_port, container_port in ports.items():
                    cmd.extend(['-p', f'{host_port}:{container_port}'])
            
            # Volume mounts
            if volumes:
                for host_path, container_path in volumes.items():
                    cmd.extend(['-v', f'{host_path}:{container_path}'])
            
            # Network
            if network:
                cmd.extend(['--network', network])
            
            # Add image
            cmd.append(image)
            
            # Add command if specified
            if command:
                cmd.extend(command)
            
            result = self.docker_client.execute_command(cmd)
            
            container_id = result.stdout.strip()
            create_result['success'] = True
            create_result['container_id'] = container_id
            
            return create_result
            
        except Exception as e:
            create_result['errors'].append(str(e))
            raise ContainerError(
                f"Failed to create container",
                container_name=name
            )
    
    def prune_containers(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Remove stopped containers"""
        prune_result = {
            'success': False,
            'containers_removed': 0,
            'space_reclaimed': '0B',
            'errors': []
        }
        
        try:
            cmd = ['docker', 'container', 'prune', '-f']
            
            # Add filters
            if filters:
                for key, value in filters.items():
                    cmd.extend(['--filter', f'{key}={value}'])
            
            result = self.docker_client.execute_command(cmd)
            
            prune_result['success'] = True
            
            # Parse output for metrics
            output = result.stdout
            if 'Total reclaimed space' in output:
                import re
                space_match = re.search(r'Total reclaimed space: ([\d.]+\w+)', output)
                if space_match:
                    prune_result['space_reclaimed'] = space_match.group(1)
            
            # Count removed containers (rough estimate from output)
            container_lines = [line for line in output.split('\n') if line.strip() and len(line) == 64]
            prune_result['containers_removed'] = len(container_lines)
            
            return prune_result
            
        except Exception as e:
            prune_result['errors'].append(str(e))
            raise create_docker_error(e, "Prune containers")