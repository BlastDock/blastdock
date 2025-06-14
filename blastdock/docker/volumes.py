"""
Enhanced Docker volume management with comprehensive error handling
"""

import json
from typing import Dict, List, Optional, Any

from ..utils.logging import get_logger
from .client import get_docker_client
from .errors import VolumeError, create_docker_error

logger = get_logger(__name__)


class VolumeManager:
    """Enhanced Docker volume manager"""
    
    def __init__(self):
        """Initialize volume manager"""
        self.docker_client = get_docker_client()
        self.logger = get_logger(__name__)
    
    def list_volumes(self, filters: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """List volumes with optional filtering"""
        cmd = ['docker', 'volume', 'ls', '--format', '{{json .}}']
        
        # Add filters
        if filters:
            for key, value in filters.items():
                cmd.extend(['--filter', f'{key}={value}'])
        
        try:
            result = self.docker_client.execute_command(cmd)
            
            volumes = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        volume = json.loads(line)
                        volumes.append(volume)
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Failed to parse volume JSON: {e}")
                        continue
            
            return volumes
            
        except Exception as e:
            raise create_docker_error(e, "List volumes")
    
    def get_volume_info(self, volume_name: str) -> Dict[str, Any]:
        """Get detailed information about a volume"""
        try:
            result = self.docker_client.execute_command([
                'docker', 'volume', 'inspect', volume_name, '--format', '{{json .}}'
            ])
            
            volume_info = json.loads(result.stdout)
            
            # Handle both single volume and array responses
            if isinstance(volume_info, list):
                volume_info = volume_info[0] if volume_info else {}
            
            # Extract useful information
            extracted_info = {
                'name': volume_info.get('Name', ''),
                'driver': volume_info.get('Driver', ''),
                'mountpoint': volume_info.get('Mountpoint', ''),
                'created_at': volume_info.get('CreatedAt', ''),
                'status': volume_info.get('Status', {}),
                'labels': volume_info.get('Labels', {}),
                'scope': volume_info.get('Scope', ''),
                'options': volume_info.get('Options', {}),
                'usage_data': volume_info.get('UsageData', {})
            }
            
            return extracted_info
            
        except Exception as e:
            raise VolumeError(
                f"Failed to get volume information",
                volume_name=volume_name
            )
    
    def create_volume(self, name: str, driver: str = 'local',
                     labels: Optional[Dict[str, str]] = None,
                     options: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a new volume"""
        create_result = {
            'success': False,
            'volume_name': name,
            'driver': driver,
            'mountpoint': '',
            'errors': []
        }
        
        try:
            cmd = ['docker', 'volume', 'create']
            
            # Driver
            cmd.extend(['--driver', driver])
            
            # Labels
            if labels:
                for key, value in labels.items():
                    cmd.extend(['--label', f'{key}={value}'])
            
            # Driver options
            if options:
                for key, value in options.items():
                    cmd.extend(['--opt', f'{key}={value}'])
            
            # Volume name
            cmd.append(name)
            
            result = self.docker_client.execute_command(cmd)
            
            created_name = result.stdout.strip()
            create_result['success'] = True
            create_result['volume_name'] = created_name
            
            # Get volume info to retrieve mountpoint
            try:
                volume_info = self.get_volume_info(name)
                create_result['mountpoint'] = volume_info.get('mountpoint', '')
            except Exception as e:
                create_result['errors'].append(f"Could not get volume info after creation: {str(e)}")
            
            return create_result
            
        except Exception as e:
            create_result['errors'].append(str(e))
            raise VolumeError(
                f"Failed to create volume {name}",
                volume_name=name
            )
    
    def remove_volume(self, volume_name: str, force: bool = False) -> Dict[str, Any]:
        """Remove a volume"""
        remove_result = {
            'success': False,
            'volume_name': volume_name,
            'errors': []
        }
        
        try:
            cmd = ['docker', 'volume', 'rm']
            
            if force:
                cmd.append('-f')
            
            cmd.append(volume_name)
            
            self.docker_client.execute_command(cmd)
            
            remove_result['success'] = True
            return remove_result
            
        except Exception as e:
            remove_result['errors'].append(str(e))
            raise VolumeError(
                f"Failed to remove volume {volume_name}",
                volume_name=volume_name
            )
    
    def prune_volumes(self, filters: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Remove unused volumes"""
        prune_result = {
            'success': False,
            'volumes_removed': 0,
            'space_reclaimed': '0B',
            'volumes': [],
            'errors': []
        }
        
        try:
            cmd = ['docker', 'volume', 'prune', '-f']
            
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
            
            # Parse removed volumes
            output_lines = output.split('\n')
            volumes_removed = []
            
            for line in output_lines:
                if 'Deleted Volumes:' in line:
                    continue
                elif line.strip() and not line.startswith('Total'):
                    volumes_removed.append(line.strip())
            
            prune_result['volumes_removed'] = len(volumes_removed)
            prune_result['volumes'] = volumes_removed
            
            return prune_result
            
        except Exception as e:
            prune_result['errors'].append(str(e))
            raise create_docker_error(e, "Prune volumes")
    
    def get_volume_usage(self, volume_name: str) -> Dict[str, Any]:
        """Get volume usage information"""
        usage_info = {
            'volume_name': volume_name,
            'size_bytes': 0,
            'ref_count': 0,
            'containers_using': [],
            'mountpoint': '',
            'available': True,
            'errors': []
        }
        
        try:
            # Get volume info
            volume_info = self.get_volume_info(volume_name)
            usage_info['mountpoint'] = volume_info.get('mountpoint', '')
            
            # Get usage data if available
            usage_data = volume_info.get('usage_data', {})
            if usage_data:
                usage_info['size_bytes'] = usage_data.get('Size', 0)
                usage_info['ref_count'] = usage_data.get('RefCount', 0)
            
            # Find containers using this volume
            try:
                from .containers import ContainerManager
                container_manager = ContainerManager()
                
                all_containers = container_manager.list_containers(all_containers=True)
                
                for container in all_containers:
                    container_name = container.get('Names', '')
                    
                    try:
                        container_info = container_manager.get_container_info(container_name)
                        mounts = container_info.get('mounts', [])
                        
                        for mount in mounts:
                            if mount.get('Name') == volume_name or mount.get('Source') == usage_info['mountpoint']:
                                usage_info['containers_using'].append({
                                    'container_name': container_name,
                                    'mount_destination': mount.get('Destination', ''),
                                    'mode': mount.get('Mode', ''),
                                    'rw': mount.get('RW', True)
                                })
                    
                    except Exception as e:
                        # Skip containers we can't inspect
                        continue
                
                usage_info['ref_count'] = len(usage_info['containers_using'])
                
            except Exception as e:
                usage_info['errors'].append(f"Could not determine container usage: {str(e)}")
            
            # Check if volume is available (not in use by running containers)
            running_containers_using = [
                c for c in usage_info['containers_using'] 
                if self._is_container_running(c['container_name'])
            ]
            usage_info['available'] = len(running_containers_using) == 0
            
            return usage_info
            
        except Exception as e:
            usage_info['errors'].append(str(e))
            usage_info['available'] = False
            return usage_info
    
    def _is_container_running(self, container_name: str) -> bool:
        """Check if a container is currently running"""
        try:
            from .containers import ContainerManager
            container_manager = ContainerManager()
            
            container_info = container_manager.get_container_info(container_name)
            return container_info.get('state', {}).get('Status') == 'running'
        except:
            return False
    
    def backup_volume(self, volume_name: str, backup_path: str,
                     compression: str = 'gzip') -> Dict[str, Any]:
        """Backup a volume to a tar file"""
        backup_result = {
            'success': False,
            'volume_name': volume_name,
            'backup_path': backup_path,
            'backup_size': 0,
            'compression': compression,
            'errors': []
        }
        
        try:
            # Create a temporary container to access the volume
            temp_container_name = f"blastdock_backup_{volume_name}_{int(time.time())}"
            
            from .containers import ContainerManager
            container_manager = ContainerManager()
            
            # Create container with volume mounted
            create_result = container_manager.create_container(
                image='alpine:latest',
                name=temp_container_name,
                command=['sleep', '3600'],
                volumes={volume_name: '/backup_source'}
            )
            
            if not create_result['success']:
                raise VolumeError(f"Failed to create backup container")
            
            try:
                # Start the container
                container_manager.start_container(temp_container_name)
                
                # Create backup inside container
                tar_cmd = ['tar', '-czf', '/backup.tar.gz', '-C', '/backup_source', '.']
                if compression == 'none':
                    tar_cmd = ['tar', '-cf', '/backup.tar', '-C', '/backup_source', '.']
                elif compression == 'bzip2':
                    tar_cmd = ['tar', '-cjf', '/backup.tar.bz2', '-C', '/backup_source', '.']
                
                exec_result = container_manager.execute_command_in_container(
                    temp_container_name, tar_cmd
                )
                
                if not exec_result['success']:
                    raise VolumeError(f"Failed to create backup archive: {exec_result['stderr']}")
                
                # Copy backup file out of container
                backup_file = '/backup.tar.gz'
                if compression == 'none':
                    backup_file = '/backup.tar'
                elif compression == 'bzip2':
                    backup_file = '/backup.tar.bz2'
                
                copy_result = container_manager.copy_from_container(
                    temp_container_name, backup_file, backup_path
                )
                
                if not copy_result['success']:
                    raise VolumeError(f"Failed to copy backup file")
                
                backup_result['success'] = True
                
                # Get backup file size
                try:
                    import os
                    backup_result['backup_size'] = os.path.getsize(backup_path)
                except:
                    pass
            
            finally:
                # Clean up temporary container
                try:
                    container_manager.remove_container(temp_container_name, force=True)
                except:
                    pass
            
            return backup_result
            
        except Exception as e:
            backup_result['errors'].append(str(e))
            raise VolumeError(
                f"Failed to backup volume {volume_name}",
                volume_name=volume_name
            )
    
    def restore_volume(self, volume_name: str, backup_path: str) -> Dict[str, Any]:
        """Restore a volume from a backup file"""
        restore_result = {
            'success': False,
            'volume_name': volume_name,
            'backup_path': backup_path,
            'errors': []
        }
        
        try:
            import os
            if not os.path.exists(backup_path):
                raise VolumeError(f"Backup file not found: {backup_path}")
            
            # Create volume if it doesn't exist
            try:
                self.get_volume_info(volume_name)
            except VolumeError:
                # Volume doesn't exist, create it
                create_result = self.create_volume(volume_name)
                if not create_result['success']:
                    raise VolumeError(f"Failed to create volume for restore")
            
            # Create temporary container to restore into the volume
            temp_container_name = f"blastdock_restore_{volume_name}_{int(time.time())}"
            
            from .containers import ContainerManager
            container_manager = ContainerManager()
            
            # Create container with volume mounted
            create_result = container_manager.create_container(
                image='alpine:latest',
                name=temp_container_name,
                command=['sleep', '3600'],
                volumes={volume_name: '/restore_target'}
            )
            
            if not create_result['success']:
                raise VolumeError(f"Failed to create restore container")
            
            try:
                # Start the container
                container_manager.start_container(temp_container_name)
                
                # Copy backup file into container
                copy_result = container_manager.copy_to_container(
                    temp_container_name, backup_path, '/backup_file'
                )
                
                if not copy_result['success']:
                    raise VolumeError(f"Failed to copy backup file to container")
                
                # Extract backup into volume
                if backup_path.endswith('.tar.gz') or backup_path.endswith('.tgz'):
                    extract_cmd = ['tar', '-xzf', '/backup_file', '-C', '/restore_target']
                elif backup_path.endswith('.tar.bz2') or backup_path.endswith('.tbz2'):
                    extract_cmd = ['tar', '-xjf', '/backup_file', '-C', '/restore_target']
                elif backup_path.endswith('.tar'):
                    extract_cmd = ['tar', '-xf', '/backup_file', '-C', '/restore_target']
                else:
                    # Assume gzip
                    extract_cmd = ['tar', '-xzf', '/backup_file', '-C', '/restore_target']
                
                exec_result = container_manager.execute_command_in_container(
                    temp_container_name, extract_cmd
                )
                
                if not exec_result['success']:
                    raise VolumeError(f"Failed to extract backup: {exec_result['stderr']}")
                
                restore_result['success'] = True
            
            finally:
                # Clean up temporary container
                try:
                    container_manager.remove_container(temp_container_name, force=True)
                except:
                    pass
            
            return restore_result
            
        except Exception as e:
            restore_result['errors'].append(str(e))
            raise VolumeError(
                f"Failed to restore volume {volume_name}",
                volume_name=volume_name
            )
    
    def get_volume_usage_stats(self) -> Dict[str, Any]:
        """Get volume usage statistics"""
        stats = {
            'total_volumes': 0,
            'volumes_by_driver': {},
            'volumes_with_containers': 0,
            'total_size_bytes': 0,
            'orphaned_volumes': 0,
            'volume_details': []
        }
        
        try:
            volumes = self.list_volumes()
            stats['total_volumes'] = len(volumes)
            
            for volume in volumes:
                volume_name = volume.get('Name', '')
                driver = volume.get('Driver', 'unknown')
                
                # Count by driver
                stats['volumes_by_driver'][driver] = stats['volumes_by_driver'].get(driver, 0) + 1
                
                try:
                    # Get usage info
                    usage_info = self.get_volume_usage(volume_name)
                    
                    volume_detail = {
                        'name': volume_name,
                        'driver': driver,
                        'size_bytes': usage_info.get('size_bytes', 0),
                        'ref_count': usage_info.get('ref_count', 0),
                        'containers_using': len(usage_info.get('containers_using', [])),
                        'available': usage_info.get('available', True)
                    }
                    
                    stats['volume_details'].append(volume_detail)
                    stats['total_size_bytes'] += volume_detail['size_bytes']
                    
                    if volume_detail['containers_using'] > 0:
                        stats['volumes_with_containers'] += 1
                    elif volume_detail['ref_count'] == 0:
                        stats['orphaned_volumes'] += 1
                
                except Exception as e:
                    self.logger.warning(f"Failed to get usage info for volume {volume_name}: {e}")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get volume usage stats: {e}")
            return stats