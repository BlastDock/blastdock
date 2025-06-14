"""
Enhanced Docker Compose management with comprehensive error handling
"""

import os
import yaml
import time
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import subprocess

from ..utils.logging import get_logger
from .client import get_docker_client
from .errors import DockerComposeError, create_docker_error

logger = get_logger(__name__)


class ComposeManager:
    """Enhanced Docker Compose manager with robust error handling"""
    
    def __init__(self, project_dir: Optional[str] = None, project_name: Optional[str] = None):
        """Initialize Compose manager"""
        self.project_dir = project_dir
        self.project_name = project_name
        self.docker_client = get_docker_client()
        self.logger = get_logger(__name__)
        
        # Default compose file names to try
        self.compose_files = [
            'docker-compose.yml',
            'docker-compose.yaml',
            'compose.yml',
            'compose.yaml'
        ]
    
    def find_compose_file(self, directory: Optional[str] = None) -> Optional[str]:
        """Find the compose file in the given directory"""
        search_dir = directory or self.project_dir or os.getcwd()
        
        for filename in self.compose_files:
            compose_path = os.path.join(search_dir, filename)
            if os.path.isfile(compose_path):
                self.logger.debug(f"Found compose file: {compose_path}")
                return compose_path
        
        return None
    
    def validate_compose_file(self, compose_file: str) -> Dict[str, Any]:
        """Validate Docker Compose file and return analysis"""
        validation = {
            'valid': False,
            'version': None,
            'services': [],
            'networks': [],
            'volumes': [],
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
        
        try:
            if not os.path.isfile(compose_file):
                validation['errors'].append(f"Compose file not found: {compose_file}")
                return validation
            
            # Parse YAML
            with open(compose_file, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f)
            
            if not isinstance(compose_data, dict):
                validation['errors'].append("Invalid compose file format")
                return validation
            
            # Check version
            version = compose_data.get('version')
            if version:
                validation['version'] = version
                try:
                    version_num = float(version)
                    if version_num < 3.0:
                        validation['warnings'].append(f"Compose file version {version} is outdated")
                        validation['recommendations'].append("Consider upgrading to version 3.8 or higher")
                except ValueError:
                    validation['warnings'].append(f"Could not parse version: {version}")
            else:
                validation['warnings'].append("No version specified in compose file")
                validation['recommendations'].append("Add 'version: \"3.8\"' to your compose file")
            
            # Analyze services
            services = compose_data.get('services', {})
            if not services:
                validation['errors'].append("No services defined in compose file")
                return validation
            
            validation['services'] = list(services.keys())
            
            # Check service configurations
            for service_name, service_config in services.items():
                if not isinstance(service_config, dict):
                    validation['errors'].append(f"Invalid configuration for service: {service_name}")
                    continue
                
                # Check for common issues
                if 'image' not in service_config and 'build' not in service_config:
                    validation['errors'].append(f"Service {service_name} has no image or build configuration")
                
                # Check ports
                if 'ports' in service_config:
                    ports = service_config['ports']
                    for port in ports:
                        if isinstance(port, str) and ':' in port:
                            try:
                                host_port = port.split(':')[0]
                                int(host_port)  # Validate port number
                            except ValueError:
                                validation['warnings'].append(f"Invalid port format in {service_name}: {port}")
                
                # Check health checks
                if 'healthcheck' not in service_config:
                    validation['recommendations'].append(f"Consider adding health check for service: {service_name}")
                
                # Check restart policy
                if 'restart' not in service_config:
                    validation['recommendations'].append(f"Consider adding restart policy for service: {service_name}")
            
            # Analyze networks
            networks = compose_data.get('networks', {})
            validation['networks'] = list(networks.keys())
            
            # Analyze volumes
            volumes = compose_data.get('volumes', {})
            validation['volumes'] = list(volumes.keys())
            
            # Additional validations
            try:
                # Test compose file syntax with docker-compose config
                result = self.docker_client.execute_compose_command(
                    ['config', '--quiet'],
                    compose_file=compose_file,
                    cwd=os.path.dirname(compose_file)
                )
                validation['valid'] = True
                
            except Exception as e:
                validation['errors'].append(f"Compose file syntax error: {str(e)}")
            
        except yaml.YAMLError as e:
            validation['errors'].append(f"YAML parsing error: {str(e)}")
        except Exception as e:
            validation['errors'].append(f"Validation error: {str(e)}")
        
        self.logger.debug(f"Compose file validation result: {validation}")
        return validation
    
    def build_services(self, services: Optional[List[str]] = None, 
                      no_cache: bool = False, parallel: bool = True,
                      compose_file: Optional[str] = None) -> Dict[str, Any]:
        """Build services with enhanced error handling"""
        compose_file = compose_file or self.find_compose_file()
        if not compose_file:
            raise DockerComposeError("No compose file found")
        
        cmd = ['build']
        
        if no_cache:
            cmd.append('--no-cache')
        
        if parallel:
            cmd.append('--parallel')
        
        if services:
            cmd.extend(services)
        
        build_result = {
            'success': False,
            'services_built': [],
            'build_time': 0,
            'output': '',
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            result = self.docker_client.execute_compose_command(
                cmd,
                compose_file=compose_file,
                project_name=self.project_name,
                cwd=os.path.dirname(compose_file)
            )
            
            build_result['success'] = True
            build_result['output'] = result.stdout
            build_result['build_time'] = time.time() - start_time
            
            # Parse built services from output
            if services:
                build_result['services_built'] = services
            else:
                # Try to extract built services from output
                validation = self.validate_compose_file(compose_file)
                build_result['services_built'] = validation['services']
            
        except Exception as e:
            build_result['errors'].append(str(e))
            build_result['build_time'] = time.time() - start_time
            raise DockerComposeError(
                f"Failed to build services",
                compose_file=compose_file,
                service=services[0] if services and len(services) == 1 else None
            )
        
        self.logger.info(f"Build completed: {build_result}")
        return build_result
    
    def start_services(self, services: Optional[List[str]] = None,
                      detached: bool = True, remove_orphans: bool = True,
                      compose_file: Optional[str] = None) -> Dict[str, Any]:
        """Start services with comprehensive monitoring"""
        compose_file = compose_file or self.find_compose_file()
        if not compose_file:
            raise DockerComposeError("No compose file found")
        
        cmd = ['up']
        
        if detached:
            cmd.append('-d')
        
        if remove_orphans:
            cmd.append('--remove-orphans')
        
        if services:
            cmd.extend(services)
        
        start_result = {
            'success': False,
            'services_started': [],
            'startup_time': 0,
            'output': '',
            'container_info': {},
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            result = self.docker_client.execute_compose_command(
                cmd,
                compose_file=compose_file,
                project_name=self.project_name,
                cwd=os.path.dirname(compose_file)
            )
            
            start_result['success'] = True
            start_result['output'] = result.stdout
            start_result['startup_time'] = time.time() - start_time
            
            # Get container information
            start_result['container_info'] = self.get_service_status(compose_file)
            
            # Determine which services were started
            if services:
                start_result['services_started'] = services
            else:
                start_result['services_started'] = list(start_result['container_info'].keys())
            
        except Exception as e:
            start_result['errors'].append(str(e))
            start_result['startup_time'] = time.time() - start_time
            raise DockerComposeError(
                f"Failed to start services",
                compose_file=compose_file,
                service=services[0] if services and len(services) == 1 else None
            )
        
        self.logger.info(f"Services started: {start_result}")
        return start_result
    
    def stop_services(self, services: Optional[List[str]] = None,
                     timeout: int = 10, compose_file: Optional[str] = None) -> Dict[str, Any]:
        """Stop services gracefully"""
        compose_file = compose_file or self.find_compose_file()
        if not compose_file:
            raise DockerComposeError("No compose file found")
        
        cmd = ['stop', '-t', str(timeout)]
        
        if services:
            cmd.extend(services)
        
        stop_result = {
            'success': False,
            'services_stopped': [],
            'stop_time': 0,
            'output': '',
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            result = self.docker_client.execute_compose_command(
                cmd,
                compose_file=compose_file,
                project_name=self.project_name,
                cwd=os.path.dirname(compose_file)
            )
            
            stop_result['success'] = True
            stop_result['output'] = result.stdout
            stop_result['stop_time'] = time.time() - start_time
            
            if services:
                stop_result['services_stopped'] = services
            else:
                # Get all services
                validation = self.validate_compose_file(compose_file)
                stop_result['services_stopped'] = validation['services']
            
        except Exception as e:
            stop_result['errors'].append(str(e))
            stop_result['stop_time'] = time.time() - start_time
            raise DockerComposeError(
                f"Failed to stop services",
                compose_file=compose_file,
                service=services[0] if services and len(services) == 1 else None
            )
        
        self.logger.info(f"Services stopped: {stop_result}")
        return stop_result
    
    def remove_services(self, volumes: bool = False, force: bool = False,
                       compose_file: Optional[str] = None) -> Dict[str, Any]:
        """Remove containers and optionally volumes"""
        compose_file = compose_file or self.find_compose_file()
        if not compose_file:
            raise DockerComposeError("No compose file found")
        
        cmd = ['down']
        
        if volumes:
            cmd.append('--volumes')
        
        if force:
            cmd.append('--remove-orphans')
        
        remove_result = {
            'success': False,
            'containers_removed': [],
            'volumes_removed': [],
            'networks_removed': [],
            'remove_time': 0,
            'output': '',
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            result = self.docker_client.execute_compose_command(
                cmd,
                compose_file=compose_file,
                project_name=self.project_name,
                cwd=os.path.dirname(compose_file)
            )
            
            remove_result['success'] = True
            remove_result['output'] = result.stdout
            remove_result['remove_time'] = time.time() - start_time
            
            # Parse output to get removed resources
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'Removing' in line and 'container' in line.lower():
                    # Extract container name
                    parts = line.split()
                    if len(parts) >= 2:
                        remove_result['containers_removed'].append(parts[-1])
                elif 'Removing' in line and 'volume' in line.lower():
                    # Extract volume name
                    parts = line.split()
                    if len(parts) >= 2:
                        remove_result['volumes_removed'].append(parts[-1])
                elif 'Removing' in line and 'network' in line.lower():
                    # Extract network name
                    parts = line.split()
                    if len(parts) >= 2:
                        remove_result['networks_removed'].append(parts[-1])
            
        except Exception as e:
            remove_result['errors'].append(str(e))
            remove_result['remove_time'] = time.time() - start_time
            raise DockerComposeError(
                f"Failed to remove services",
                compose_file=compose_file
            )
        
        self.logger.info(f"Services removed: {remove_result}")
        return remove_result
    
    def get_service_status(self, compose_file: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Get detailed status of all services"""
        compose_file = compose_file or self.find_compose_file()
        if not compose_file:
            raise DockerComposeError("No compose file found")
        
        try:
            result = self.docker_client.execute_compose_command(
                ['ps', '--format', 'json'],
                compose_file=compose_file,
                project_name=self.project_name,
                cwd=os.path.dirname(compose_file)
            )
            
            import json
            containers = []
            
            # Parse JSON output (each line is a JSON object)
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        container = json.loads(line)
                        containers.append(container)
                    except json.JSONDecodeError:
                        # Fallback to parsing plain text output
                        break
            
            # If JSON parsing failed, try plain text parsing
            if not containers:
                result = self.docker_client.execute_compose_command(
                    ['ps'],
                    compose_file=compose_file,
                    project_name=self.project_name,
                    cwd=os.path.dirname(compose_file)
                )
                # Parse plain text output (basic implementation)
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            containers.append({
                                'Name': parts[0],
                                'State': parts[-1],
                                'Service': parts[0].split('_')[1] if '_' in parts[0] else parts[0]
                            })
            
            # Organize by service
            service_status = {}
            for container in containers:
                service_name = container.get('Service', container.get('Name', ''))
                service_status[service_name] = {
                    'name': container.get('Name', ''),
                    'state': container.get('State', 'unknown'),
                    'status': container.get('Status', ''),
                    'ports': container.get('Publishers', []),
                    'health': container.get('Health', 'none')
                }
            
            return service_status
            
        except Exception as e:
            self.logger.error(f"Failed to get service status: {e}")
            raise DockerComposeError(f"Failed to get service status", compose_file=compose_file)
    
    def get_service_logs(self, service: Optional[str] = None, tail: int = 100,
                        follow: bool = False, compose_file: Optional[str] = None) -> str:
        """Get logs for services"""
        compose_file = compose_file or self.find_compose_file()
        if not compose_file:
            raise DockerComposeError("No compose file found")
        
        cmd = ['logs', '--tail', str(tail)]
        
        if follow:
            cmd.append('--follow')
        
        if service:
            cmd.append(service)
        
        try:
            result = self.docker_client.execute_compose_command(
                cmd,
                compose_file=compose_file,
                project_name=self.project_name,
                cwd=os.path.dirname(compose_file)
            )
            
            return result.stdout
            
        except Exception as e:
            raise DockerComposeError(
                f"Failed to get logs",
                compose_file=compose_file,
                service=service
            )
    
    def scale_service(self, service: str, replicas: int,
                     compose_file: Optional[str] = None) -> Dict[str, Any]:
        """Scale a specific service"""
        compose_file = compose_file or self.find_compose_file()
        if not compose_file:
            raise DockerComposeError("No compose file found")
        
        cmd = ['up', '-d', '--scale', f'{service}={replicas}', service]
        
        scale_result = {
            'success': False,
            'service': service,
            'replicas': replicas,
            'scale_time': 0,
            'output': '',
            'errors': []
        }
        
        start_time = time.time()
        
        try:
            result = self.docker_client.execute_compose_command(
                cmd,
                compose_file=compose_file,
                project_name=self.project_name,
                cwd=os.path.dirname(compose_file)
            )
            
            scale_result['success'] = True
            scale_result['output'] = result.stdout
            scale_result['scale_time'] = time.time() - start_time
            
        except Exception as e:
            scale_result['errors'].append(str(e))
            scale_result['scale_time'] = time.time() - start_time
            raise DockerComposeError(
                f"Failed to scale service {service}",
                compose_file=compose_file,
                service=service
            )
        
        self.logger.info(f"Service scaled: {scale_result}")
        return scale_result