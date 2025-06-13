"""
Port Manager - Handles port allocation, conflict detection, and resolution
"""

import json
import socket
import subprocess
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path

from ..utils.logging import get_logger
from ..utils.filesystem import paths
from ..utils.docker_utils import DockerClient
from ..core.config import get_config_manager

logger = get_logger(__name__)


class PortManager:
    """Manages port allocation and conflict resolution for BlastDock deployments"""
    
    # System reserved ports that should never be allocated
    SYSTEM_RESERVED_PORTS = {
        20, 21,    # FTP
        22,        # SSH
        23,        # Telnet
        25,        # SMTP
        53,        # DNS
        67, 68,    # DHCP
        80,        # HTTP (reserved for Traefik)
        110,       # POP3
        143,       # IMAP
        443,       # HTTPS (reserved for Traefik)
        993,       # IMAPS
        995,       # POP3S
        8080,      # Common web alternate (reserved for Traefik dashboard)
    }
    
    # Default dynamic port range
    DEFAULT_DYNAMIC_RANGE = (8000, 9000)
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.docker_client = DockerClient()
        self.ports_file = paths.data_dir / "ports.json"
        self._load_ports()
    
    def _load_ports(self):
        """Load port allocation data from file"""
        try:
            if self.ports_file.exists():
                with open(self.ports_file, 'r') as f:
                    self.ports_data = json.load(f)
            else:
                self.ports_data = {
                    'allocated_ports': {},  # port -> project info
                    'reserved_ports': set(),
                    'dynamic_range': self.DEFAULT_DYNAMIC_RANGE,
                    'project_ports': {}  # project -> list of ports
                }
                self._save_ports()
        except Exception as e:
            logger.error(f"Error loading ports configuration: {e}")
            self.ports_data = {
                'allocated_ports': {},
                'reserved_ports': set(),
                'dynamic_range': self.DEFAULT_DYNAMIC_RANGE,
                'project_ports': {}
            }
    
    def _save_ports(self):
        """Save port allocation data to file"""
        try:
            # Convert sets to lists for JSON serialization
            save_data = self.ports_data.copy()
            if 'reserved_ports' in save_data:
                save_data['reserved_ports'] = list(save_data['reserved_ports'])
            
            with open(self.ports_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving ports configuration: {e}")
    
    def is_port_available(self, port: int) -> bool:
        """Check if a port is available for allocation"""
        # Check if port is in system reserved range
        if port in self.SYSTEM_RESERVED_PORTS:
            return False
        
        # Check if port is manually reserved
        reserved_ports = set(self.ports_data.get('reserved_ports', []))
        if port in reserved_ports:
            return False
        
        # Check if port is already allocated
        allocated_ports = self.ports_data.get('allocated_ports', {})
        if str(port) in allocated_ports:
            return False
        
        # Check if port is actually in use by the system
        return not self.is_port_in_use(port)
    
    def is_port_in_use(self, port: int) -> bool:
        """Check if a port is currently in use by any process"""
        try:
            # Try to bind to the port
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                return result == 0
        except Exception:
            return False
    
    def allocate_port(self, project_name: str, service_name: str, 
                     preferred_port: Optional[int] = None) -> Optional[int]:
        """Allocate a port for a service"""
        try:
            # If preferred port is specified and available, use it
            if preferred_port and self.is_port_available(preferred_port):
                self._assign_port(preferred_port, project_name, service_name)
                return preferred_port
            
            # Find next available port in dynamic range
            dynamic_range = self.ports_data.get('dynamic_range', self.DEFAULT_DYNAMIC_RANGE)
            start_port, end_port = dynamic_range
            
            for port in range(start_port, end_port + 1):
                if self.is_port_available(port):
                    self._assign_port(port, project_name, service_name)
                    return port
            
            logger.error(f"No available ports in dynamic range {dynamic_range}")
            return None
            
        except Exception as e:
            logger.error(f"Error allocating port: {e}")
            return None
    
    def release_port(self, port: int) -> bool:
        """Release an allocated port"""
        try:
            allocated_ports = self.ports_data.get('allocated_ports', {})
            port_str = str(port)
            
            if port_str in allocated_ports:
                port_info = allocated_ports[port_str]
                project_name = port_info.get('project_name')
                
                # Remove from allocated ports
                del allocated_ports[port_str]
                
                # Remove from project ports
                if project_name:
                    project_ports = self.ports_data.get('project_ports', {})
                    if project_name in project_ports:
                        if port in project_ports[project_name]:
                            project_ports[project_name].remove(port)
                        if not project_ports[project_name]:
                            del project_ports[project_name]
                
                self._save_ports()
                logger.info(f"Released port {port}")
                return True
            else:
                logger.warning(f"Port {port} was not allocated")
                return False
                
        except Exception as e:
            logger.error(f"Error releasing port: {e}")
            return False
    
    def release_project_ports(self, project_name: str) -> bool:
        """Release all ports allocated to a project"""
        try:
            project_ports = self.ports_data.get('project_ports', {}).get(project_name, [])
            released_ports = []
            
            for port in project_ports.copy():
                if self.release_port(port):
                    released_ports.append(port)
            
            if released_ports:
                logger.info(f"Released {len(released_ports)} ports for project {project_name}: {released_ports}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error releasing project ports: {e}")
            return False
    
    def get_project_ports(self, project_name: str) -> List[int]:
        """Get all ports allocated to a project"""
        project_ports = self.ports_data.get('project_ports', {})
        return project_ports.get(project_name, [])
    
    def reserve_port(self, port: int, reason: str = "Manual reservation") -> bool:
        """Reserve a port to prevent allocation"""
        try:
            if not self.is_port_available(port):
                logger.error(f"Port {port} is not available for reservation")
                return False
            
            reserved_ports = set(self.ports_data.get('reserved_ports', []))
            reserved_ports.add(port)
            self.ports_data['reserved_ports'] = reserved_ports
            
            self._save_ports()
            logger.info(f"Reserved port {port}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error reserving port: {e}")
            return False
    
    def unreserve_port(self, port: int) -> bool:
        """Remove a port from reserved list"""
        try:
            reserved_ports = set(self.ports_data.get('reserved_ports', []))
            if port in reserved_ports:
                reserved_ports.discard(port)
                self.ports_data['reserved_ports'] = reserved_ports
                self._save_ports()
                logger.info(f"Unreserved port {port}")
                return True
            else:
                logger.warning(f"Port {port} was not reserved")
                return False
                
        except Exception as e:
            logger.error(f"Error unreserving port: {e}")
            return False
    
    def check_port_conflicts(self) -> List[Dict[str, Any]]:
        """Check for port conflicts across all projects"""
        conflicts = []
        
        try:
            allocated_ports = self.ports_data.get('allocated_ports', {})
            
            # Check each allocated port
            for port_str, port_info in allocated_ports.items():
                port = int(port_str)
                
                # Check if port is actually in use
                if self.is_port_in_use(port):
                    # Try to determine what's using the port
                    process_info = self._get_port_process_info(port)
                    
                    conflicts.append({
                        'port': port,
                        'allocated_to': {
                            'project': port_info.get('project_name'),
                            'service': port_info.get('service_name'),
                            'allocated_at': port_info.get('allocated_at')
                        },
                        'actual_usage': process_info,
                        'type': 'port_in_use_conflict'
                    })
                
                # Check for Docker container conflicts
                docker_conflicts = self._check_docker_port_conflicts(port)
                if docker_conflicts:
                    conflicts.extend(docker_conflicts)
        
        except Exception as e:
            logger.error(f"Error checking port conflicts: {e}")
        
        return conflicts
    
    def get_available_ports(self, count: int = 10) -> List[int]:
        """Get a list of available ports"""
        available = []
        dynamic_range = self.ports_data.get('dynamic_range', self.DEFAULT_DYNAMIC_RANGE)
        start_port, end_port = dynamic_range
        
        for port in range(start_port, end_port + 1):
            if len(available) >= count:
                break
            if self.is_port_available(port):
                available.append(port)
        
        return available
    
    def get_port_usage_summary(self) -> Dict[str, Any]:
        """Get a summary of port usage"""
        allocated_ports = self.ports_data.get('allocated_ports', {})
        reserved_ports = set(self.ports_data.get('reserved_ports', []))
        dynamic_range = self.ports_data.get('dynamic_range', self.DEFAULT_DYNAMIC_RANGE)
        
        # Count ports by status
        total_allocated = len(allocated_ports)
        total_reserved = len(reserved_ports)
        total_system_reserved = len(self.SYSTEM_RESERVED_PORTS)
        
        # Calculate range statistics
        range_size = dynamic_range[1] - dynamic_range[0] + 1
        available_in_range = len(self.get_available_ports(range_size))
        
        return {
            'allocated_ports': total_allocated,
            'reserved_ports': total_reserved,
            'system_reserved_ports': total_system_reserved,
            'dynamic_range': dynamic_range,
            'range_size': range_size,
            'available_in_range': available_in_range,
            'utilization_percentage': ((range_size - available_in_range) / range_size) * 100
        }
    
    def list_all_ports(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all ports by category"""
        result = {
            'allocated': [],
            'reserved': [],
            'system_reserved': [],
            'available': []
        }
        
        try:
            # Allocated ports
            allocated_ports = self.ports_data.get('allocated_ports', {})
            for port_str, info in allocated_ports.items():
                result['allocated'].append({
                    'port': int(port_str),
                    'project': info.get('project_name'),
                    'service': info.get('service_name'),
                    'allocated_at': info.get('allocated_at'),
                    'in_use': self.is_port_in_use(int(port_str))
                })
            
            # Reserved ports
            reserved_ports = set(self.ports_data.get('reserved_ports', []))
            for port in sorted(reserved_ports):
                result['reserved'].append({
                    'port': port,
                    'reason': 'Manual reservation'
                })
            
            # System reserved ports
            for port in sorted(self.SYSTEM_RESERVED_PORTS):
                result['system_reserved'].append({
                    'port': port,
                    'reason': 'System service'
                })
            
            # Some available ports
            available_ports = self.get_available_ports(20)
            for port in available_ports:
                result['available'].append({
                    'port': port
                })
        
        except Exception as e:
            logger.error(f"Error listing ports: {e}")
        
        return result
    
    def migrate_to_traefik(self, project_name: str) -> bool:
        """Migrate a project from direct port exposure to Traefik routing"""
        try:
            project_ports = self.get_project_ports(project_name)
            
            if not project_ports:
                logger.info(f"Project {project_name} has no allocated ports to migrate")
                return True
            
            # Store migration info for potential rollback
            migration_info = {
                'project_name': project_name,
                'migrated_ports': project_ports,
                'migrated_at': self._get_current_timestamp()
            }
            
            # Release all project ports
            success = self.release_project_ports(project_name)
            
            if success:
                # Store migration info
                migrations_file = paths.data_dir / "port_migrations.json"
                migrations = []
                
                if migrations_file.exists():
                    with open(migrations_file, 'r') as f:
                        migrations = json.load(f)
                
                migrations.append(migration_info)
                
                with open(migrations_file, 'w') as f:
                    json.dump(migrations, f, indent=2)
                
                logger.info(f"Migrated project {project_name} to Traefik, released ports: {project_ports}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error migrating project to Traefik: {e}")
            return False
    
    def rollback_traefik_migration(self, project_name: str) -> bool:
        """Rollback a Traefik migration by reallocating original ports"""
        try:
            migrations_file = paths.data_dir / "port_migrations.json"
            
            if not migrations_file.exists():
                logger.error("No migration history found")
                return False
            
            with open(migrations_file, 'r') as f:
                migrations = json.load(f)
            
            # Find the migration for this project
            project_migration = None
            for migration in migrations:
                if migration.get('project_name') == project_name:
                    project_migration = migration
                    break
            
            if not project_migration:
                logger.error(f"No migration found for project {project_name}")
                return False
            
            # Try to reallocate the original ports
            migrated_ports = project_migration.get('migrated_ports', [])
            reallocated_ports = []
            
            for port in migrated_ports:
                if self.is_port_available(port):
                    self._assign_port(port, project_name, 'migrated_service')
                    reallocated_ports.append(port)
                else:
                    logger.warning(f"Cannot reallocate port {port}, it's no longer available")
            
            if reallocated_ports:
                logger.info(f"Reallocated ports for project {project_name}: {reallocated_ports}")
                
                # Remove from migration history
                migrations = [m for m in migrations if m.get('project_name') != project_name]
                with open(migrations_file, 'w') as f:
                    json.dump(migrations, f, indent=2)
            
            return len(reallocated_ports) > 0
            
        except Exception as e:
            logger.error(f"Error rolling back migration: {e}")
            return False
    
    def _assign_port(self, port: int, project_name: str, service_name: str):
        """Assign a port to a project/service"""
        allocated_ports = self.ports_data.get('allocated_ports', {})
        project_ports = self.ports_data.get('project_ports', {})
        
        # Add to allocated ports
        allocated_ports[str(port)] = {
            'project_name': project_name,
            'service_name': service_name,
            'allocated_at': self._get_current_timestamp()
        }
        
        # Add to project ports
        if project_name not in project_ports:
            project_ports[project_name] = []
        project_ports[project_name].append(port)
        
        self._save_ports()
        logger.info(f"Allocated port {port} to {project_name}/{service_name}")
    
    def _get_port_process_info(self, port: int) -> Dict[str, str]:
        """Get information about what process is using a port"""
        try:
            # Try netstat first
            result = subprocess.run(
                ['netstat', '-tlnp'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if f':{port} ' in line:
                        parts = line.split()
                        if len(parts) >= 7:
                            return {
                                'address': parts[3],
                                'process': parts[6] if parts[6] != '-' else 'unknown'
                            }
        except Exception:
            pass
        
        # Fallback to lsof
        try:
            result = subprocess.run(
                ['lsof', '-i', f':{port}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    return {
                        'command': parts[0] if len(parts) > 0 else 'unknown',
                        'pid': parts[1] if len(parts) > 1 else 'unknown'
                    }
        except Exception:
            pass
        
        return {'process': 'unknown'}
    
    def _check_docker_port_conflicts(self, port: int) -> List[Dict[str, Any]]:
        """Check for Docker container port conflicts"""
        conflicts = []
        
        try:
            containers = self.docker_client.list_containers(all=False)
            
            for container in containers:
                ports = container.get('ports', [])
                for port_mapping in ports:
                    if isinstance(port_mapping, dict):
                        public_port = port_mapping.get('PublicPort')
                        if public_port == port:
                            conflicts.append({
                                'port': port,
                                'type': 'docker_container_conflict',
                                'container': {
                                    'name': container.get('name'),
                                    'id': container.get('id'),
                                    'image': container.get('image'),
                                    'status': container.get('status')
                                }
                            })
        
        except Exception as e:
            logger.warning(f"Error checking Docker port conflicts: {e}")
        
        return conflicts
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def set_dynamic_range(self, start_port: int, end_port: int) -> bool:
        """Set the dynamic port allocation range"""
        try:
            if start_port >= end_port:
                logger.error("Start port must be less than end port")
                return False
            
            if start_port < 1024:
                logger.warning("Setting dynamic range below 1024 may conflict with system services")
            
            self.ports_data['dynamic_range'] = (start_port, end_port)
            self._save_ports()
            
            logger.info(f"Set dynamic port range to {start_port}-{end_port}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting dynamic range: {e}")
            return False