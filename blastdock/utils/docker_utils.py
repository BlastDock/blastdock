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
        """Run docker-compose up"""
        import subprocess
        import os
        
        cmd = ['docker-compose']
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
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def compose_down(self, project_path, project_name=None):
        """Run docker-compose down"""
        import subprocess
        
        cmd = ['docker-compose']
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
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def compose_logs(self, project_path, project_name=None, service=None, follow=False):
        """Get docker-compose logs"""
        import subprocess
        
        cmd = ['docker-compose']
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
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
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
    
    def get_container_logs(self, container_name, tail=100):
        """Get logs from a specific container"""
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs
        except DockerException as e:
            logger.error(f"Error getting container logs: {e}")
            return f"Error: {str(e)}"