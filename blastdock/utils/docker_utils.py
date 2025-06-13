"""
Docker utility functions
"""

import docker
from docker.errors import DockerException
import logging

logger = logging.getLogger(__name__)

class DockerClient:
    def __init__(self):
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            try:
                self._client = docker.from_env()
                # Test connection
                self._client.ping()
            except DockerException as e:
                raise Exception(f"Failed to connect to Docker: {str(e)}")
        return self._client
    
    def is_docker_running(self):
        """Check if Docker daemon is running"""
        try:
            docker.from_env().ping()
            return True
        except DockerException:
            return False
    
    def compose_up(self, project_path, project_name=None):
        """Run docker compose up"""
        import subprocess
        import os
        
        # Try modern docker compose first, fallback to docker-compose
        cmd_variants = [
            ['docker', 'compose'],
            ['docker-compose']
        ]
        
        for base_cmd in cmd_variants:
            cmd = base_cmd.copy()
            if project_name:
                cmd.extend(['-p', project_name])
            cmd.extend(['up', '-d'])
            
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return True, result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                if base_cmd == cmd_variants[-1]:  # Last attempt
                    if isinstance(e, subprocess.CalledProcessError):
                        return False, e.stderr
                    else:
                        return False, f"Neither 'docker compose' nor 'docker-compose' command found"
                continue  # Try next variant
    
    def compose_down(self, project_path, project_name=None):
        """Run docker compose down"""
        import subprocess
        
        # Try modern docker compose first, fallback to docker-compose
        cmd_variants = [
            ['docker', 'compose'],
            ['docker-compose']
        ]
        
        for base_cmd in cmd_variants:
            cmd = base_cmd.copy()
            if project_name:
                cmd.extend(['-p', project_name])
            cmd.extend(['down'])
            
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return True, result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                if base_cmd == cmd_variants[-1]:  # Last attempt
                    if isinstance(e, subprocess.CalledProcessError):
                        return False, e.stderr
                    else:
                        return False, f"Neither 'docker compose' nor 'docker-compose' command found"
                continue  # Try next variant
    
    def compose_down_with_volumes(self, project_path, project_name=None):
        """Run docker compose down with volume removal"""
        import subprocess
        
        # Try modern docker compose first, fallback to docker-compose
        cmd_variants = [
            ['docker', 'compose'],
            ['docker-compose']
        ]
        
        for base_cmd in cmd_variants:
            cmd = base_cmd.copy()
            if project_name:
                cmd.extend(['-p', project_name])
            cmd.extend(['down', '--volumes'])
            
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return True, result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                if base_cmd == cmd_variants[-1]:  # Last attempt
                    if isinstance(e, subprocess.CalledProcessError):
                        return False, e.stderr
                    else:
                        return False, f"Neither 'docker compose' nor 'docker-compose' command found"
                continue  # Try next variant
    
    def compose_logs(self, project_path, project_name=None, service=None, follow=False):
        """Get docker compose logs"""
        import subprocess
        
        # Try modern docker compose first, fallback to docker-compose
        cmd_variants = [
            ['docker', 'compose'],
            ['docker-compose']
        ]
        
        for base_cmd in cmd_variants:
            cmd = base_cmd.copy()
            if project_name:
                cmd.extend(['-p', project_name])
            cmd.append('logs')
            if follow:
                cmd.append('-f')
            if service:
                cmd.append(service)
            
            try:
                if follow:
                    # Stream logs
                    process = subprocess.Popen(
                        cmd,
                        cwd=project_path,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
                    
                    for line in iter(process.stdout.readline, ''):
                        print(line.rstrip())
                    
                    process.wait()
                    return True, ""
                else:
                    result = subprocess.run(
                        cmd,
                        cwd=project_path,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    return True, result.stdout
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                if base_cmd == cmd_variants[-1]:  # Last attempt
                    if isinstance(e, subprocess.CalledProcessError):
                        return False, e.stderr
                    else:
                        return False, f"Neither 'docker compose' nor 'docker-compose' command found"
                continue  # Try next variant
    
    def get_container_status(self, project_name):
        """Get status of containers for a project"""
        try:
            containers = self.client.containers.list(
                all=True,
                filters={'label': f'com.docker.compose.project={project_name}'}
            )
            
            status_info = []
            for container in containers:
                status_info.append({
                    'name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'unknown',
                    'ports': container.ports if container.ports else {}
                })
            
            return status_info
        except DockerException as e:
            logger.error(f"Error getting container status: {e}")
            return []
    
    def get_container_logs(self, container_name, tail=100, follow=False):
        """Get logs from a specific container"""
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, timestamps=True, follow=follow, stream=follow)
            if follow:
                # For streaming logs
                for log_line in logs:
                    yield log_line.decode('utf-8')
            else:
                return logs.decode('utf-8')
        except DockerException as e:
            logger.error(f"Error getting container logs: {e}")
            return f"Error: {str(e)}"
    
    def list_containers(self, all=True):
        """List Docker containers"""
        try:
            containers = self.client.containers.list(all=all)
            container_list = []
            for container in containers:
                container_list.append({
                    'id': container.id,
                    'name': container.name,
                    'image': container.image.tags[0] if container.image.tags else container.image.id,
                    'status': container.status,
                    'state': container.attrs['State']['Status'],
                    'created': container.attrs['Created'],
                    'ports': container.ports,
                    'labels': container.labels
                })
            return container_list
        except DockerException as e:
            logger.error(f"Error listing containers: {e}")
            return []
    
    def get_container_info(self, container_name):
        """Get detailed container information"""
        try:
            container = self.client.containers.get(container_name)
            return {
                'id': container.id,
                'name': container.name,
                'image': container.image.tags[0] if container.image.tags else container.image.id,
                'status': container.status,
                'state': container.attrs['State']['Status'],
                'created': container.attrs['Created'],
                'ports': container.ports,
                'labels': container.labels,
                'network_settings': container.attrs['NetworkSettings']
            }
        except DockerException as e:
            logger.error(f"Error getting container info: {e}")
            return None
    
    def list_networks(self):
        """List Docker networks"""
        try:
            networks = self.client.networks.list()
            network_list = []
            for network in networks:
                network_list.append({
                    'id': network.id,
                    'name': network.name,
                    'driver': network.attrs['Driver'],
                    'scope': network.attrs['Scope']
                })
            return network_list
        except DockerException as e:
            logger.error(f"Error listing networks: {e}")
            return []
    
    def create_network(self, name, driver='bridge', attachable=False):
        """Create Docker network"""
        try:
            network = self.client.networks.create(
                name=name,
                driver=driver,
                attachable=attachable
            )
            logger.info(f"Created network: {name}")
            return network
        except DockerException as e:
            logger.error(f"Error creating network {name}: {e}")
            raise
    
    def remove_network(self, name):
        """Remove Docker network"""
        try:
            network = self.client.networks.get(name)
            network.remove()
            logger.info(f"Removed network: {name}")
            return True
        except DockerException as e:
            logger.error(f"Error removing network {name}: {e}")
            return False
    
    def restart_container(self, container_name):
        """Restart a container"""
        try:
            container = self.client.containers.get(container_name)
            container.restart()
            logger.info(f"Restarted container: {container_name}")
            return True
        except DockerException as e:
            logger.error(f"Error restarting container {container_name}: {e}")
            return False
    
    def stop_container(self, container_name):
        """Stop a container"""
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            logger.info(f"Stopped container: {container_name}")
            return True
        except DockerException as e:
            logger.error(f"Error stopping container {container_name}: {e}")
            return False
    
    def start_container(self, container_name):
        """Start a container"""
        try:
            container = self.client.containers.get(container_name)
            container.start()
            logger.info(f"Started container: {container_name}")
            return True
        except DockerException as e:
            logger.error(f"Error starting container {container_name}: {e}")
            return False
    
    def remove_container(self, container_name, force=False):
        """Remove a container"""
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=force)
            logger.info(f"Removed container: {container_name}")
            return True
        except DockerException as e:
            logger.error(f"Error removing container {container_name}: {e}")
            return False
    
    def get_docker_info(self):
        """Get Docker system information"""
        try:
            return self.client.info()
        except DockerException as e:
            logger.error(f"Error getting Docker info: {e}")
            return None
    
    def check_compose_version(self):
        """Check if Docker Compose is available"""
        import subprocess
        try:
            # Try modern docker compose
            result = subprocess.run(['docker', 'compose', 'version'], 
                                  capture_output=True, text=True, check=True)
            return True, result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            try:
                # Try legacy docker-compose
                result = subprocess.run(['docker-compose', '--version'], 
                                      capture_output=True, text=True, check=True)
                return True, result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False, "Docker Compose not found"