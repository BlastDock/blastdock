"""
Enhanced Docker network management with comprehensive error handling
"""

import json
from typing import Dict, List, Optional, Any

from ..utils.logging import get_logger
from .client import get_docker_client
from .errors import NetworkError, create_docker_error

logger = get_logger(__name__)


class NetworkManager:
    """Enhanced Docker network manager"""
    
    def __init__(self):
        """Initialize network manager"""
        self.docker_client = get_docker_client()
        self.logger = get_logger(__name__)
    
    def list_networks(self, filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """List networks with optional filtering"""
        cmd = ['docker', 'network', 'ls', '--format', '{{json .}}']
        
        # Add filters
        if filters:
            for key, value in filters.items():
                cmd.extend(['--filter', f'{key}={value}'])
        
        try:
            result = self.docker_client.execute_command(cmd)
            
            networks = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        network = json.loads(line)
                        networks.append(network)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse network JSON: {e}")
                        continue
            
            return networks
            
        except Exception as e:
            raise create_docker_error(e, "List networks")
    
    def get_network_info(self, network_name: str) -> Dict[str, Any]:
        """Get detailed information about a network"""
        try:
            result = self.docker_client.execute_command([
                'docker', 'network', 'inspect', network_name, '--format', '{{json .}}'
            ])
            
            network_info = json.loads(result.stdout)
            
            # Handle both single network and array responses
            if isinstance(network_info, list):
                network_info = network_info[0] if network_info else {}
            
            # Extract useful information
            extracted_info = {
                'id': network_info.get('Id', ''),
                'name': network_info.get('Name', ''),
                'driver': network_info.get('Driver', ''),
                'scope': network_info.get('Scope', ''),
                'created': network_info.get('Created', ''),
                'internal': network_info.get('Internal', False),
                'attachable': network_info.get('Attachable', False),
                'ingress': network_info.get('Ingress', False),
                'ipam': network_info.get('IPAM', {}),
                'containers': network_info.get('Containers', {}),
                'options': network_info.get('Options', {}),
                'labels': network_info.get('Labels', {})
            }
            
            return extracted_info
            
        except Exception as e:
            raise NetworkError(
                f"Failed to get network information",
                network_name=network_name
            )
    
    def create_network(self, name: str, driver: str = 'bridge',
                      subnet: Optional[str] = None, gateway: Optional[str] = None,
                      ip_range: Optional[str] = None, internal: bool = False,
                      attachable: bool = False, labels: Optional[Dict[str, str]] = None,
                      options: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a new network"""
        create_result = {
            'success': False,
            'network_name': name,
            'network_id': None,
            'driver': driver,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'network', 'create']
            
            # Driver
            cmd.extend(['--driver', driver])
            
            # IPAM configuration
            if subnet or gateway or ip_range:
                ipam_opts = []
                if subnet:
                    ipam_opts.append(f'subnet={subnet}')
                if gateway:
                    ipam_opts.append(f'gateway={gateway}')
                if ip_range:
                    ipam_opts.append(f'ip-range={ip_range}')
                
                cmd.extend(['--subnet', subnet] if subnet else [])
                cmd.extend(['--gateway', gateway] if gateway else [])
                cmd.extend(['--ip-range', ip_range] if ip_range else [])
            
            # Network options
            if internal:
                cmd.append('--internal')
            
            if attachable:
                cmd.append('--attachable')
            
            # Labels
            if labels:
                for key, value in labels.items():
                    cmd.extend(['--label', f'{key}={value}'])
            
            # Driver options
            if options:
                for key, value in options.items():
                    cmd.extend(['--opt', f'{key}={value}'])
            
            # Network name
            cmd.append(name)
            
            result = self.docker_client.execute_command(cmd)
            
            network_id = result.stdout.strip()
            create_result['success'] = True
            create_result['network_id'] = network_id
            
            return create_result
            
        except Exception as e:
            create_result['errors'].append(str(e))
            raise NetworkError(
                f"Failed to create network {name}",
                network_name=name
            )
    
    def remove_network(self, network_name: str, force: bool = False) -> Dict[str, Any]:
        """Remove a network"""
        remove_result = {
            'success': False,
            'network_name': network_name,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'network', 'rm']
            
            if force:
                cmd.append('-f')
            
            cmd.append(network_name)
            
            self.docker_client.execute_command(cmd)
            
            remove_result['success'] = True
            return remove_result
            
        except Exception as e:
            remove_result['errors'].append(str(e))
            raise NetworkError(
                f"Failed to remove network {network_name}",
                network_name=network_name
            )
    
    def connect_container(self, network_name: str, container_name: str,
                         alias: Optional[str] = None, ip: Optional[str] = None,
                         link: Optional[List[str]] = None) -> Dict[str, Any]:
        """Connect a container to a network"""
        connect_result = {
            'success': False,
            'network_name': network_name,
            'container_name': container_name,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'network', 'connect']
            
            # Network alias
            if alias:
                cmd.extend(['--alias', alias])
            
            # IP address
            if ip:
                cmd.extend(['--ip', ip])
            
            # Links (deprecated but still supported)
            if link:
                for link_target in link:
                    cmd.extend(['--link', link_target])
            
            cmd.extend([network_name, container_name])
            
            self.docker_client.execute_command(cmd)
            
            connect_result['success'] = True
            return connect_result
            
        except Exception as e:
            connect_result['errors'].append(str(e))
            raise NetworkError(
                f"Failed to connect container {container_name} to network {network_name}",
                network_name=network_name
            )
    
    def disconnect_container(self, network_name: str, container_name: str,
                           force: bool = False) -> Dict[str, Any]:
        """Disconnect a container from a network"""
        disconnect_result = {
            'success': False,
            'network_name': network_name,
            'container_name': container_name,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'network', 'disconnect']
            
            if force:
                cmd.append('-f')
            
            cmd.extend([network_name, container_name])
            
            self.docker_client.execute_command(cmd)
            
            disconnect_result['success'] = True
            return disconnect_result
            
        except Exception as e:
            disconnect_result['errors'].append(str(e))
            raise NetworkError(
                f"Failed to disconnect container {container_name} from network {network_name}",
                network_name=network_name
            )
    
    def prune_networks(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Remove unused networks"""
        prune_result = {
            'success': False,
            'networks_removed': 0,
            'networks': [],
            'errors': []
        }
        
        try:
            cmd = ['docker', 'network', 'prune', '-f']
            
            # Add filters
            if filters:
                for key, value in filters.items():
                    cmd.extend(['--filter', f'{key}={value}'])
            
            result = self.docker_client.execute_command(cmd)
            
            prune_result['success'] = True
            
            # Parse output for removed networks
            output_lines = result.stdout.split('\n')
            networks_removed = []
            
            for line in output_lines:
                if 'Deleted Networks:' in line:
                    continue
                elif line.strip() and len(line.strip()) > 10:  # Network IDs are long
                    networks_removed.append(line.strip())
            
            prune_result['networks_removed'] = len(networks_removed)
            prune_result['networks'] = networks_removed
            
            return prune_result
            
        except Exception as e:
            prune_result['errors'].append(str(e))
            raise create_docker_error(e, "Prune networks")
    
    def get_network_containers(self, network_name: str) -> List[Dict[str, Any]]:
        """Get all containers connected to a network"""
        try:
            network_info = self.get_network_info(network_name)
            containers_info = network_info.get('containers', {})
            
            containers = []
            for container_id, container_data in containers_info.items():
                containers.append({
                    'id': container_id,
                    'name': container_data.get('Name', ''),
                    'endpoint_id': container_data.get('EndpointID', ''),
                    'mac_address': container_data.get('MacAddress', ''),
                    'ipv4_address': container_data.get('IPv4Address', ''),
                    'ipv6_address': container_data.get('IPv6Address', '')
                })
            
            return containers
            
        except Exception as e:
            raise NetworkError(
                f"Failed to get containers for network {network_name}",
                network_name=network_name
            )
    
    def check_network_connectivity(self, network_name: str, 
                                 test_containers: Optional[List[str]] = None) -> Dict[str, Any]:
        """Check connectivity within a network"""
        connectivity_result = {
            'network_name': network_name,
            'reachable_containers': [],
            'unreachable_containers': [],
            'connectivity_matrix': {},
            'errors': []
        }
        
        try:
            # Get containers in the network
            if test_containers:
                containers = [{'name': name} for name in test_containers]
            else:
                containers = self.get_network_containers(network_name)
            
            if len(containers) < 2:
                connectivity_result['errors'].append("Not enough containers to test connectivity")
                return connectivity_result
            
            # Test connectivity between containers
            from .containers import ContainerManager
            container_manager = ContainerManager()
            
            for i, container_a in enumerate(containers):
                container_a_name = container_a.get('name', container_a.get('id', ''))
                connectivity_result['connectivity_matrix'][container_a_name] = {}
                
                for j, container_b in enumerate(containers):
                    if i == j:
                        continue
                    
                    container_b_name = container_b.get('name', container_b.get('id', ''))
                    
                    try:
                        # Try to ping from container A to container B
                        exec_result = container_manager.execute_command_in_container(
                            container_a_name,
                            ['ping', '-c', '1', '-W', '2', container_b_name]
                        )
                        
                        reachable = exec_result['success']
                        connectivity_result['connectivity_matrix'][container_a_name][container_b_name] = reachable
                        
                        if reachable and container_b_name not in connectivity_result['reachable_containers']:
                            connectivity_result['reachable_containers'].append(container_b_name)
                        elif not reachable and container_b_name not in connectivity_result['unreachable_containers']:
                            connectivity_result['unreachable_containers'].append(container_b_name)
                    
                    except Exception as e:
                        connectivity_result['connectivity_matrix'][container_a_name][container_b_name] = False
                        connectivity_result['errors'].append(
                            f"Failed to test connectivity from {container_a_name} to {container_b_name}: {str(e)}"
                        )
            
            return connectivity_result
            
        except Exception as e:
            connectivity_result['errors'].append(str(e))
            return connectivity_result
    
    def get_network_usage_stats(self) -> Dict[str, Any]:
        """Get network usage statistics"""
        stats = {
            'total_networks': 0,
            'networks_by_driver': {},
            'networks_by_scope': {},
            'internal_networks': 0,
            'attachable_networks': 0,
            'networks_with_containers': 0,
            'container_count_by_network': {}
        }
        
        try:
            networks = self.list_networks()
            stats['total_networks'] = len(networks)
            
            for network in networks:
                # Count by driver
                driver = network.get('Driver', 'unknown')
                stats['networks_by_driver'][driver] = stats['networks_by_driver'].get(driver, 0) + 1
                
                # Count by scope
                scope = network.get('Scope', 'unknown')
                stats['networks_by_scope'][scope] = stats['networks_by_scope'].get(scope, 0) + 1
                
                # Get detailed info for each network
                try:
                    network_info = self.get_network_info(network.get('Name', ''))
                    
                    if network_info.get('internal', False):
                        stats['internal_networks'] += 1
                    
                    if network_info.get('attachable', False):
                        stats['attachable_networks'] += 1
                    
                    container_count = len(network_info.get('containers', {}))
                    if container_count > 0:
                        stats['networks_with_containers'] += 1
                        stats['container_count_by_network'][network.get('Name', '')] = container_count
                
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for network {network.get('Name', '')}: {e}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get network usage stats: {e}")
            return stats