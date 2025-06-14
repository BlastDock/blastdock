"""
Docker-related test fixtures
"""

import json
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, MagicMock


class DockerResponseFixtures:
    """Collection of Docker API response fixtures"""
    
    @staticmethod
    def container_inspect_response(
        container_id: str = "abc123def456",
        name: str = "test-container",
        image: str = "nginx:latest",
        status: str = "running",
        health_status: Optional[str] = None
    ) -> str:
        """Generate container inspect JSON response"""
        response = {
            "Id": container_id,
            "Name": f"/{name}",
            "Image": image,
            "State": {
                "Status": status,
                "Running": status == "running",
                "Paused": False,
                "Restarting": False,
                "Dead": False,
                "Pid": 12345 if status == "running" else 0,
                "ExitCode": 0,
                "StartedAt": "2023-01-01T12:00:00Z"
            },
            "Config": {
                "Image": image,
                "Env": ["PATH=/usr/bin", "NGINX_VERSION=1.21.0"],
                "Labels": {
                    "app": "test",
                    "environment": "testing"
                }
            },
            "NetworkSettings": {
                "Ports": {
                    "80/tcp": [{"HostPort": "8080"}],
                    "443/tcp": None
                },
                "Networks": {
                    "bridge": {
                        "IPAddress": "172.17.0.2",
                        "Gateway": "172.17.0.1"
                    }
                }
            },
            "Mounts": []
        }
        
        if health_status:
            response["State"]["Health"] = {
                "Status": health_status,
                "FailingStreak": 0 if health_status == "healthy" else 3,
                "Log": [{
                    "Start": "2023-01-01T12:00:00Z",
                    "End": "2023-01-01T12:00:01Z",
                    "ExitCode": 0 if health_status == "healthy" else 1,
                    "Output": f"Health check {'passed' if health_status == 'healthy' else 'failed'}"
                }]
            }
        
        return json.dumps(response)
    
    @staticmethod
    def container_list_response(containers: Optional[List[Dict[str, Any]]] = None) -> str:
        """Generate container list JSON response"""
        if containers is None:
            containers = [
                {
                    "ID": "abc123",
                    "Names": "/test-web",
                    "Image": "nginx:latest",
                    "Status": "Up 2 hours",
                    "State": "running",
                    "Labels": {"com.docker.compose.service": "web"}
                },
                {
                    "ID": "def456",
                    "Names": "/test-db",
                    "Image": "postgres:13",
                    "Status": "Up 2 hours",
                    "State": "running",
                    "Labels": {"com.docker.compose.service": "db"}
                }
            ]
        
        return '\n'.join(json.dumps(container) for container in containers)
    
    @staticmethod
    def docker_version_response() -> str:
        """Generate docker version response"""
        return json.dumps({
            "Client": {
                "Version": "20.10.0",
                "ApiVersion": "1.41",
                "Os": "linux",
                "Arch": "amd64"
            },
            "Server": {
                "Version": "20.10.0",
                "ApiVersion": "1.41",
                "Os": "linux",
                "Arch": "amd64"
            }
        })
    
    @staticmethod
    def docker_info_response() -> str:
        """Generate docker info response"""
        return json.dumps({
            "Containers": 5,
            "ContainersRunning": 2,
            "ContainersPaused": 0,
            "ContainersStopped": 3,
            "Images": 10,
            "ServerVersion": "20.10.0",
            "MemTotal": 8589934592,  # 8GB
            "NCPU": 4,
            "OperatingSystem": "Ubuntu 20.04",
            "OSType": "linux",
            "Architecture": "x86_64"
        })
    
    @staticmethod
    def docker_system_df_response() -> str:
        """Generate docker system df response"""
        return json.dumps({
            "Images": [
                {
                    "Repository": "nginx",
                    "Tag": "latest",
                    "Size": 142000000,
                    "SharedSize": 0,
                    "Containers": 1
                }
            ],
            "Containers": [
                {
                    "Id": "abc123",
                    "Names": ["/test-container"],
                    "SizeRw": 10240
                }
            ],
            "Volumes": [
                {
                    "Name": "test-volume",
                    "Size": 1048576
                }
            ],
            "BuildCache": []
        })
    
    @staticmethod
    def compose_ps_response(project_name: str = "test-project") -> str:
        """Generate docker-compose ps response"""
        return f"""{project_name}_web_1    nginx:latest    "nginx -g 'daemon off;'"    Up    0.0.0.0:8080->80/tcp
{project_name}_db_1     postgres:13     "docker-entrypoint.s..."    Up    5432/tcp"""
    
    @staticmethod
    def container_stats_response() -> str:
        """Generate container stats response"""
        return json.dumps({
            "read": "2023-01-01T12:00:00Z",
            "cpu_stats": {
                "cpu_usage": {
                    "total_usage": 2000000000,
                    "usage_in_kernelmode": 500000000,
                    "usage_in_usermode": 1500000000
                },
                "system_cpu_usage": 10000000000,
                "online_cpus": 4
            },
            "precpu_stats": {
                "cpu_usage": {
                    "total_usage": 1000000000
                },
                "system_cpu_usage": 8000000000
            },
            "memory_stats": {
                "usage": 512000000,  # 512MB
                "limit": 1073741824  # 1GB
            },
            "networks": {
                "eth0": {
                    "rx_bytes": 1048576,
                    "tx_bytes": 2097152
                }
            }
        })


class DockerMockFactory:
    """Factory for creating Docker client mocks"""
    
    @staticmethod
    def create_success_mock() -> Mock:
        """Create a mock that always returns success"""
        mock = Mock()
        mock.execute_command.return_value = Mock(
            success=True,
            stdout="",
            stderr="",
            exit_code=0
        )
        mock.check_docker_availability.return_value = {
            'docker_installed': True,
            'docker_running': True,
            'docker_version': '20.10.0',
            'compose_installed': True,
            'compose_version': '2.0.0'
        }
        return mock
    
    @staticmethod
    def create_failure_mock(error_type: str = "generic") -> Mock:
        """Create a mock that simulates failures"""
        mock = Mock()
        
        error_messages = {
            "not_found": "docker: command not found",
            "not_running": "Cannot connect to the Docker daemon",
            "permission": "permission denied while trying to connect",
            "container_not_found": "Error: No such container",
            "generic": "An error occurred"
        }
        
        mock.execute_command.return_value = Mock(
            success=False,
            stdout="",
            stderr=error_messages.get(error_type, error_messages["generic"]),
            exit_code=1
        )
        
        if error_type == "not_found":
            mock.check_docker_availability.return_value = {
                'docker_installed': False,
                'docker_running': False,
                'docker_version': None,
                'compose_installed': False,
                'compose_version': None
            }
        elif error_type == "not_running":
            mock.check_docker_availability.return_value = {
                'docker_installed': True,
                'docker_running': False,
                'docker_version': None,
                'compose_installed': True,
                'compose_version': None
            }
        
        return mock
    
    @staticmethod
    def create_command_mock(responses: List[Dict[str, Any]]) -> Mock:
        """Create a mock with specific command responses"""
        mock = Mock()
        mock.execute_command.side_effect = [
            Mock(**response) for response in responses
        ]
        return mock


class ComposeFileFixtures:
    """Collection of Docker Compose file fixtures"""
    
    @staticmethod
    def simple_compose() -> Dict[str, Any]:
        """Simple compose file with web service"""
        return {
            'version': '3.8',
            'services': {
                'web': {
                    'image': 'nginx:latest',
                    'ports': ['8080:80'],
                    'environment': {
                        'NGINX_HOST': 'localhost'
                    }
                }
            }
        }
    
    @staticmethod
    def multi_service_compose() -> Dict[str, Any]:
        """Compose file with multiple services"""
        return {
            'version': '3.8',
            'services': {
                'web': {
                    'image': 'nginx:latest',
                    'ports': ['8080:80'],
                    'depends_on': ['db'],
                    'networks': ['frontend', 'backend']
                },
                'db': {
                    'image': 'postgres:13',
                    'environment': {
                        'POSTGRES_DB': 'testdb',
                        'POSTGRES_USER': 'testuser',
                        'POSTGRES_PASSWORD': 'testpass'
                    },
                    'volumes': ['db-data:/var/lib/postgresql/data'],
                    'networks': ['backend']
                }
            },
            'networks': {
                'frontend': {},
                'backend': {}
            },
            'volumes': {
                'db-data': {}
            }
        }
    
    @staticmethod
    def compose_with_healthcheck() -> Dict[str, Any]:
        """Compose file with health checks"""
        return {
            'version': '3.8',
            'services': {
                'web': {
                    'image': 'nginx:latest',
                    'ports': ['8080:80'],
                    'healthcheck': {
                        'test': ['CMD', 'curl', '-f', 'http://localhost/'],
                        'interval': '30s',
                        'timeout': '3s',
                        'retries': 3,
                        'start_period': '40s'
                    }
                }
            }
        }
    
    @staticmethod
    def compose_with_build() -> Dict[str, Any]:
        """Compose file with build configuration"""
        return {
            'version': '3.8',
            'services': {
                'app': {
                    'build': {
                        'context': '.',
                        'dockerfile': 'Dockerfile',
                        'args': {
                            'NODE_VERSION': '16'
                        }
                    },
                    'ports': ['3000:3000'],
                    'volumes': ['./src:/app/src']
                }
            }
        }


class ContainerFixtures:
    """Collection of container-related fixtures"""
    
    @staticmethod
    def running_container() -> Dict[str, Any]:
        """Running container fixture"""
        return {
            'id': 'abc123def456',
            'name': 'test-container',
            'image': 'nginx:latest',
            'status': 'running',
            'ports': {'80/tcp': '8080'},
            'labels': {'app': 'test'}
        }
    
    @staticmethod
    def stopped_container() -> Dict[str, Any]:
        """Stopped container fixture"""
        return {
            'id': 'def456ghi789',
            'name': 'stopped-container',
            'image': 'nginx:latest',
            'status': 'exited',
            'exit_code': 0,
            'labels': {'app': 'test'}
        }
    
    @staticmethod
    def failed_container() -> Dict[str, Any]:
        """Failed container fixture"""
        return {
            'id': 'ghi789jkl012',
            'name': 'failed-container',
            'image': 'nginx:latest',
            'status': 'exited',
            'exit_code': 1,
            'error': 'Container failed to start',
            'labels': {'app': 'test'}
        }