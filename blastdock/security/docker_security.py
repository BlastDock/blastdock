"""
Docker security validation and checking for BlastDock
"""

import subprocess
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from ..utils.logging import get_logger
from ..exceptions import SecurityError, DockerError


logger = get_logger(__name__)


class DockerSecurityChecker:
    """Comprehensive Docker security validation and checking"""
    
    def __init__(self):
        """Initialize Docker security checker"""
        self.logger = get_logger(__name__)
        
        # Security policies
        self.DANGEROUS_CAPABILITIES = {
            'SYS_ADMIN', 'SYS_MODULE', 'SYS_PTRACE', 'SYS_BOOT',
            'MAC_ADMIN', 'MAC_OVERRIDE', 'SYS_RAWIO', 'SYS_TIME'
        }
        
        self.DANGEROUS_BIND_MOUNTS = {
            '/var/run/docker.sock', '/dev', '/proc', '/sys',
            '/boot', '/lib/modules', '/etc/passwd', '/etc/shadow'
        }
        
        self.UNSAFE_REGISTRIES = {
            'localhost', '127.0.0.1', 'docker.io/malicious'
        }
    
    def check_container_security(self, container_name: str) -> Dict[str, Any]:
        """Check security configuration of a running container"""
        try:
            # Get container inspection data
            result = subprocess.run(
                ['docker', 'inspect', container_name],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'container': container_name,
                    'accessible': False,
                    'error': result.stderr.strip()
                }
            
            inspect_data = json.loads(result.stdout)[0]
            
            # Analyze security configuration
            security_issues = []
            security_score = 100
            
            # Check privileged mode
            if inspect_data.get('HostConfig', {}).get('Privileged', False):
                security_issues.append({
                    'severity': 'critical',
                    'issue': 'Container running in privileged mode',
                    'description': 'Privileged containers have full access to host resources',
                    'recommendation': 'Remove privileged flag and use specific capabilities'
                })
                security_score -= 30
            
            # Check capabilities
            cap_add = inspect_data.get('HostConfig', {}).get('CapAdd', []) or []
            dangerous_caps = [cap for cap in cap_add if cap in self.DANGEROUS_CAPABILITIES]
            if dangerous_caps:
                security_issues.append({
                    'severity': 'high',
                    'issue': f'Dangerous capabilities added: {", ".join(dangerous_caps)}',
                    'description': 'These capabilities provide elevated system access',
                    'recommendation': 'Remove unnecessary capabilities'
                })
                security_score -= 20
            
            # Check bind mounts
            mounts = inspect_data.get('Mounts', [])
            dangerous_mounts = []
            for mount in mounts:
                if mount.get('Type') == 'bind':
                    source = mount.get('Source', '')
                    for dangerous_path in self.DANGEROUS_BIND_MOUNTS:
                        if source.startswith(dangerous_path):
                            dangerous_mounts.append(source)
            
            if dangerous_mounts:
                security_issues.append({
                    'severity': 'high',
                    'issue': f'Dangerous bind mounts: {", ".join(dangerous_mounts)}',
                    'description': 'These mounts provide access to sensitive host resources',
                    'recommendation': 'Use volumes instead of bind mounts when possible'
                })
                security_score -= 20
            
            # Check user
            user = inspect_data.get('Config', {}).get('User', '')
            if not user or user == 'root' or user == '0':
                security_issues.append({
                    'severity': 'medium',
                    'issue': 'Container running as root user',
                    'description': 'Root users have elevated privileges inside containers',
                    'recommendation': 'Use non-root user with USER directive'
                })
                security_score -= 15
            
            # Check network mode
            network_mode = inspect_data.get('HostConfig', {}).get('NetworkMode', '')
            if network_mode == 'host':
                security_issues.append({
                    'severity': 'high',
                    'issue': 'Container using host network',
                    'description': 'Host network mode bypasses Docker network isolation',
                    'recommendation': 'Use bridge or custom networks'
                })
                security_score -= 25
            
            # Check PID mode
            pid_mode = inspect_data.get('HostConfig', {}).get('PidMode', '')
            if pid_mode == 'host':
                security_issues.append({
                    'severity': 'high',
                    'issue': 'Container using host PID namespace',
                    'description': 'Can see and interact with host processes',
                    'recommendation': 'Remove PID mode or use container PID namespace'
                })
                security_score -= 25
            
            # Check IPC mode
            ipc_mode = inspect_data.get('HostConfig', {}).get('IpcMode', '')
            if ipc_mode == 'host':
                security_issues.append({
                    'severity': 'medium',
                    'issue': 'Container using host IPC namespace',
                    'description': 'Can access host IPC resources',
                    'recommendation': 'Use container IPC namespace'
                })
                security_score -= 10
            
            # Check read-only root filesystem
            read_only = inspect_data.get('HostConfig', {}).get('ReadonlyRootfs', False)
            if not read_only:
                security_issues.append({
                    'severity': 'low',
                    'issue': 'Root filesystem is writable',
                    'description': 'Writable root filesystem increases attack surface',
                    'recommendation': 'Use read-only root filesystem with tmpfs for writable areas'
                })
                security_score -= 5
            
            return {
                'container': container_name,
                'accessible': True,
                'security_score': max(0, security_score),
                'security_issues': security_issues,
                'configuration': {
                    'privileged': inspect_data.get('HostConfig', {}).get('Privileged', False),
                    'user': user,
                    'network_mode': network_mode,
                    'pid_mode': pid_mode,
                    'ipc_mode': ipc_mode,
                    'read_only': read_only,
                    'capabilities': cap_add,
                    'mounts_count': len(mounts)
                }
            }
            
        except subprocess.TimeoutExpired:
            return {
                'container': container_name,
                'accessible': False,
                'error': 'Docker command timed out'
            }
        except json.JSONDecodeError as e:
            return {
                'container': container_name,
                'accessible': False,
                'error': f'Failed to parse Docker output: {e}'
            }
        except Exception as e:
            return {
                'container': container_name,
                'accessible': False,
                'error': f'Unexpected error: {e}'
            }
    
    def check_image_security(self, image_name: str) -> Dict[str, Any]:
        """Check security of a Docker image"""
        try:
            # Get image inspection data
            result = subprocess.run(
                ['docker', 'inspect', image_name],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'image': image_name,
                    'accessible': False,
                    'error': result.stderr.strip()
                }
            
            inspect_data = json.loads(result.stdout)[0]
            
            security_issues = []
            security_score = 100
            
            # Check image source
            repo_tags = inspect_data.get('RepoTags', [])
            for tag in repo_tags:
                for unsafe_registry in self.UNSAFE_REGISTRIES:
                    if tag.startswith(unsafe_registry):
                        security_issues.append({
                            'severity': 'high',
                            'issue': f'Image from untrusted registry: {unsafe_registry}',
                            'description': 'Image may contain malicious code',
                            'recommendation': 'Use images from trusted registries'
                        })
                        security_score -= 30
            
            # Check image age
            created = inspect_data.get('Created', '')
            if created:
                try:
                    created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    age_days = (datetime.now(created_date.tzinfo) - created_date).days
                    
                    if age_days > 365:
                        security_issues.append({
                            'severity': 'medium',
                            'issue': f'Image is {age_days} days old',
                            'description': 'Old images may contain known vulnerabilities',
                            'recommendation': 'Use recent image versions'
                        })
                        security_score -= 15
                except Exception:
                    pass
            
            # Check for latest tag
            if any(':latest' in tag for tag in repo_tags):
                security_issues.append({
                    'severity': 'low',
                    'issue': 'Image uses latest tag',
                    'description': 'Latest tag makes builds non-reproducible',
                    'recommendation': 'Use specific version tags'
                })
                security_score -= 5
            
            # Check image size
            size = inspect_data.get('Size', 0)
            if size > 1000000000:  # 1GB
                security_issues.append({
                    'severity': 'low',
                    'issue': f'Large image size: {size // 1000000}MB',
                    'description': 'Large images have more attack surface',
                    'recommendation': 'Use minimal base images'
                })
                security_score -= 5
            
            # Check for exposed ports
            config = inspect_data.get('Config', {})
            exposed_ports = config.get('ExposedPorts', {})
            if exposed_ports:
                port_list = list(exposed_ports.keys())
                security_issues.append({
                    'severity': 'info',
                    'issue': f'Exposed ports: {", ".join(port_list)}',
                    'description': 'Ensure only necessary ports are exposed',
                    'recommendation': 'Review exposed ports for necessity'
                })
            
            return {
                'image': image_name,
                'accessible': True,
                'security_score': max(0, security_score),
                'security_issues': security_issues,
                'metadata': {
                    'created': created,
                    'size': size,
                    'tags': repo_tags,
                    'exposed_ports': list(exposed_ports.keys()) if exposed_ports else []
                }
            }
            
        except Exception as e:
            return {
                'image': image_name,
                'accessible': False,
                'error': f'Failed to inspect image: {e}'
            }
    
    def check_docker_daemon_security(self) -> Dict[str, Any]:
        """Check Docker daemon security configuration"""
        try:
            # Get Docker info
            result = subprocess.run(
                ['docker', 'info', '--format', 'json'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode != 0:
                return {
                    'accessible': False,
                    'error': result.stderr.strip()
                }
            
            docker_info = json.loads(result.stdout)
            
            security_issues = []
            security_score = 100
            
            # Check if daemon is running as root
            if docker_info.get('OSType') == 'linux':
                # On Linux, Docker typically runs as root, but check for rootless mode
                if 'rootless' not in docker_info.get('SecurityOptions', []):
                    security_issues.append({
                        'severity': 'medium',
                        'issue': 'Docker daemon running as root',
                        'description': 'Root daemon has elevated privileges',
                        'recommendation': 'Consider using rootless Docker'
                    })
                    security_score -= 10
            
            # Check experimental features
            if docker_info.get('ExperimentalBuild', False):
                security_issues.append({
                    'severity': 'low',
                    'issue': 'Experimental features enabled',
                    'description': 'Experimental features may have security issues',
                    'recommendation': 'Disable experimental features in production'
                })
                security_score -= 5
            
            # Check storage driver
            storage_driver = docker_info.get('Driver', '')
            if storage_driver in ['devicemapper', 'aufs']:
                security_issues.append({
                    'severity': 'medium',
                    'issue': f'Insecure storage driver: {storage_driver}',
                    'description': 'This storage driver has known security issues',
                    'recommendation': 'Use overlay2 storage driver'
                })
                security_score -= 15
            
            # Check for insecure registries
            insecure_registries = docker_info.get('RegistryConfig', {}).get('InsecureRegistryCIDRs', [])
            if insecure_registries:
                security_issues.append({
                    'severity': 'high',
                    'issue': f'Insecure registries configured: {", ".join(insecure_registries)}',
                    'description': 'Insecure registries can be compromised',
                    'recommendation': 'Use only secure, trusted registries'
                })
                security_score -= 25
            
            return {
                'accessible': True,
                'security_score': max(0, security_score),
                'security_issues': security_issues,
                'daemon_info': {
                    'version': docker_info.get('ServerVersion', ''),
                    'storage_driver': storage_driver,
                    'experimental': docker_info.get('ExperimentalBuild', False),
                    'security_options': docker_info.get('SecurityOptions', [])
                }
            }
            
        except Exception as e:
            return {
                'accessible': False,
                'error': f'Failed to get Docker info: {e}'
            }
    
    def scan_docker_compose_security(self, compose_content: str) -> Dict[str, Any]:
        """Scan Docker Compose content for security issues"""
        try:
            import yaml
            compose_data = yaml.safe_load(compose_content)
        except Exception as e:
            return {
                'valid': False,
                'error': f'Invalid YAML: {e}'
            }
        
        if not isinstance(compose_data, dict):
            return {
                'valid': False,
                'error': 'Compose file must be a dictionary'
            }
        
        security_issues = []
        security_score = 100
        
        services = compose_data.get('services', {})
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue
            
            # Check privileged mode
            if service_config.get('privileged', False):
                security_issues.append({
                    'service': service_name,
                    'severity': 'critical',
                    'issue': 'Privileged mode enabled',
                    'description': 'Service has full access to host resources',
                    'recommendation': 'Remove privileged flag'
                })
                security_score -= 30
            
            # Check user
            user = service_config.get('user', '')
            if not user or user == 'root' or user == '0':
                security_issues.append({
                    'service': service_name,
                    'severity': 'medium',
                    'issue': 'Running as root user',
                    'description': 'Service has elevated privileges',
                    'recommendation': 'Specify non-root user'
                })
                security_score -= 15
            
            # Check bind mounts
            volumes = service_config.get('volumes', [])
            for volume in volumes:
                if isinstance(volume, str) and ':' in volume:
                    host_path = volume.split(':')[0]
                    for dangerous_path in self.DANGEROUS_BIND_MOUNTS:
                        if host_path.startswith(dangerous_path):
                            security_issues.append({
                                'service': service_name,
                                'severity': 'high',
                                'issue': f'Dangerous bind mount: {host_path}',
                                'description': 'Mount provides access to sensitive host resources',
                                'recommendation': 'Use named volumes instead'
                            })
                            security_score -= 20
            
            # Check network mode
            if 'network_mode' in service_config:
                network_mode = service_config['network_mode']
                if network_mode == 'host':
                    security_issues.append({
                        'service': service_name,
                        'severity': 'high',
                        'issue': 'Host network mode',
                        'description': 'Service bypasses Docker network isolation',
                        'recommendation': 'Use bridge or custom networks'
                    })
                    security_score -= 25
            
            # Check capabilities
            cap_add = service_config.get('cap_add', [])
            dangerous_caps = [cap for cap in cap_add if cap in self.DANGEROUS_CAPABILITIES]
            if dangerous_caps:
                security_issues.append({
                    'service': service_name,
                    'severity': 'high',
                    'issue': f'Dangerous capabilities: {", ".join(dangerous_caps)}',
                    'description': 'These capabilities provide elevated system access',
                    'recommendation': 'Remove unnecessary capabilities'
                })
                security_score -= 20
            
            # Check environment variables for secrets
            environment = service_config.get('environment', [])
            if isinstance(environment, dict):
                env_items = environment.items()
            elif isinstance(environment, list):
                env_items = [(item.split('=', 1)[0], item.split('=', 1)[1]) 
                           for item in environment if '=' in item]
            else:
                env_items = []
            
            for env_name, env_value in env_items:
                if any(keyword in env_name.lower() for keyword in 
                       ['password', 'secret', 'key', 'token', 'api']):
                    if env_value and not env_value.startswith('${'):
                        security_issues.append({
                            'service': service_name,
                            'severity': 'high',
                            'issue': f'Hardcoded secret in environment: {env_name}',
                            'description': 'Secrets should not be hardcoded',
                            'recommendation': 'Use Docker secrets or external secret management'
                        })
                        security_score -= 20
        
        return {
            'valid': True,
            'security_score': max(0, security_score),
            'security_issues': security_issues,
            'services_analyzed': len(services)
        }
    
    def get_security_recommendations(self) -> List[str]:
        """Get general Docker security recommendations"""
        return [
            "Use official or trusted base images",
            "Keep images and containers updated",
            "Run containers as non-root users",
            "Use read-only root filesystems",
            "Avoid privileged containers",
            "Use specific image tags, not 'latest'", 
            "Limit container resources (CPU, memory)",
            "Use Docker secrets for sensitive data",
            "Enable Docker Content Trust",
            "Regularly scan images for vulnerabilities",
            "Use minimal base images (alpine, distroless)",
            "Implement proper network segmentation"
        ]


# Global checker instance
_docker_security_checker = None


def get_docker_security_checker() -> DockerSecurityChecker:
    """Get global Docker security checker instance"""
    global _docker_security_checker
    if _docker_security_checker is None:
        _docker_security_checker = DockerSecurityChecker()
    return _docker_security_checker