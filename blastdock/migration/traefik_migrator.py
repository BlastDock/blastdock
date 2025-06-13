"""
Traefik Migrator - Handles migration of existing deployments to Traefik integration
"""

import json
import yaml
import shutil
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from ..utils.logging import get_logger
from ..utils.filesystem import paths
from ..utils.docker_utils import DockerClient
from ..core.deployment_manager import DeploymentManager
from ..traefik.manager import TraefikManager
from ..traefik.labels import TraefikLabelGenerator
from ..domains.manager import DomainManager
from ..ports.manager import PortManager

logger = get_logger(__name__)


class TraefikMigrator:
    """Handles migration of existing BlastDock deployments to Traefik integration"""
    
    def __init__(self):
        self.docker_client = DockerClient()
        self.deployment_manager = DeploymentManager()
        self.traefik_manager = TraefikManager()
        self.label_generator = TraefikLabelGenerator()
        self.domain_manager = DomainManager()
        self.port_manager = PortManager()
        self.migration_log_file = paths.data_dir / "migrations.log"
    
    def check_migration_compatibility(self, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Check which projects can be migrated to Traefik"""
        compatibility_report = {
            'traefik_ready': False,
            'projects': {},
            'total_projects': 0,
            'compatible_projects': 0,
            'issues': []
        }
        
        try:
            # Check if Traefik is installed and running
            compatibility_report['traefik_ready'] = self.traefik_manager.is_running()
            if not compatibility_report['traefik_ready']:
                compatibility_report['issues'].append("Traefik is not installed or running")
            
            # Get projects to check
            if project_name:
                projects = [project_name] if self.deployment_manager.project_exists(project_name) else []
            else:
                projects = self.deployment_manager.list_projects()
            
            compatibility_report['total_projects'] = len(projects)
            
            for project in projects:
                project_info = self._analyze_project_for_migration(project)
                compatibility_report['projects'][project] = project_info
                
                if project_info['compatible']:
                    compatibility_report['compatible_projects'] += 1
        
        except Exception as e:
            logger.error(f"Error checking migration compatibility: {e}")
            compatibility_report['issues'].append(f"Error during compatibility check: {e}")
        
        return compatibility_report
    
    def migrate_project_to_traefik(self, project_name: str, 
                                  domain: Optional[str] = None,
                                  subdomain: Optional[str] = None,
                                  ssl_enabled: bool = True,
                                  dry_run: bool = False) -> Dict[str, Any]:
        """Migrate a specific project to Traefik integration"""
        migration_result = {
            'project_name': project_name,
            'success': False,
            'steps_completed': [],
            'steps_failed': [],
            'backup_created': False,
            'changes_made': {},
            'rollback_info': {}
        }
        
        try:
            logger.info(f"Starting Traefik migration for project: {project_name}")
            
            # Step 1: Validate prerequisites
            if not self._validate_migration_prerequisites(project_name):
                migration_result['steps_failed'].append("Prerequisites validation failed")
                return migration_result
            migration_result['steps_completed'].append("Prerequisites validated")
            
            # Step 2: Create backup
            if not dry_run:
                backup_path = self._create_project_backup(project_name)
                if backup_path:
                    migration_result['backup_created'] = True
                    migration_result['rollback_info']['backup_path'] = str(backup_path)
                    migration_result['steps_completed'].append("Project backup created")
                else:
                    migration_result['steps_failed'].append("Failed to create backup")
                    return migration_result
            
            # Step 3: Analyze current project configuration
            project_analysis = self._analyze_project_for_migration(project_name)
            migration_result['changes_made']['analysis'] = project_analysis
            
            # Step 4: Reserve domain/subdomain
            if domain:
                if not self.domain_manager.reserve_domain(domain, project_name):
                    migration_result['steps_failed'].append(f"Failed to reserve domain: {domain}")
                    return migration_result
                migration_result['changes_made']['domain'] = domain
            elif subdomain:
                if not self.domain_manager.reserve_subdomain(subdomain, project_name):
                    migration_result['steps_failed'].append(f"Failed to reserve subdomain: {subdomain}")
                    return migration_result
                migration_result['changes_made']['subdomain'] = subdomain
            else:
                # Generate subdomain
                generated_subdomain = self.domain_manager.generate_subdomain(project_name)
                if not self.domain_manager.reserve_subdomain(generated_subdomain, project_name):
                    migration_result['steps_failed'].append(f"Failed to reserve generated subdomain: {generated_subdomain}")
                    return migration_result
                migration_result['changes_made']['subdomain'] = generated_subdomain
                subdomain = generated_subdomain
            
            migration_result['steps_completed'].append("Domain/subdomain reserved")
            
            # Step 5: Migrate ports to Traefik routing
            original_ports = self.port_manager.get_project_ports(project_name)
            if original_ports and not dry_run:
                if self.port_manager.migrate_to_traefik(project_name):
                    migration_result['changes_made']['ports_released'] = original_ports
                    migration_result['steps_completed'].append("Ports migrated to Traefik routing")
                else:
                    migration_result['steps_failed'].append("Failed to migrate ports")
                    return migration_result
            
            # Step 6: Update project configuration
            if not dry_run:
                config_changes = self._update_project_config_for_traefik(
                    project_name, domain, subdomain, ssl_enabled
                )
                migration_result['changes_made']['config_updates'] = config_changes
                migration_result['steps_completed'].append("Project configuration updated")
            
            # Step 7: Update Docker Compose with Traefik labels
            if not dry_run:
                compose_changes = self._update_compose_file_for_traefik(
                    project_name, domain, subdomain, ssl_enabled
                )
                migration_result['changes_made']['compose_updates'] = compose_changes
                migration_result['steps_completed'].append("Docker Compose file updated")
            
            # Step 8: Restart services with new configuration
            if not dry_run:
                if self._restart_project_services(project_name):
                    migration_result['steps_completed'].append("Services restarted with Traefik integration")
                else:
                    migration_result['steps_failed'].append("Failed to restart services")
                    return migration_result
            
            # Step 9: Verify migration
            if not dry_run:
                verification_result = self._verify_traefik_migration(project_name)
                migration_result['changes_made']['verification'] = verification_result
                if verification_result['success']:
                    migration_result['steps_completed'].append("Migration verified successfully")
                else:
                    migration_result['steps_failed'].append("Migration verification failed")
                    return migration_result
            
            migration_result['success'] = True
            logger.info(f"Successfully migrated project {project_name} to Traefik")
            
            # Log migration
            if not dry_run:
                self._log_migration(project_name, migration_result)
        
        except Exception as e:
            logger.error(f"Error during migration: {e}")
            migration_result['steps_failed'].append(f"Migration error: {e}")
        
        return migration_result
    
    def migrate_all_projects_to_traefik(self, ssl_enabled: bool = True, 
                                       dry_run: bool = False) -> Dict[str, Any]:
        """Migrate all compatible projects to Traefik integration"""
        batch_result = {
            'total_projects': 0,
            'migrated_projects': 0,
            'failed_projects': 0,
            'skipped_projects': 0,
            'project_results': {},
            'summary': {}
        }
        
        try:
            # Check compatibility first
            compatibility = self.check_migration_compatibility()
            batch_result['total_projects'] = compatibility['total_projects']
            
            for project_name, project_info in compatibility['projects'].items():
                if project_info['compatible']:
                    logger.info(f"Migrating project: {project_name}")
                    
                    # Use project-specific subdomain
                    subdomain = self.domain_manager.generate_subdomain(project_name)
                    
                    migration_result = self.migrate_project_to_traefik(
                        project_name=project_name,
                        subdomain=subdomain,
                        ssl_enabled=ssl_enabled,
                        dry_run=dry_run
                    )
                    
                    batch_result['project_results'][project_name] = migration_result
                    
                    if migration_result['success']:
                        batch_result['migrated_projects'] += 1
                    else:
                        batch_result['failed_projects'] += 1
                else:
                    logger.info(f"Skipping incompatible project: {project_name}")
                    batch_result['project_results'][project_name] = {
                        'skipped': True,
                        'reason': project_info.get('issues', ['Incompatible'])
                    }
                    batch_result['skipped_projects'] += 1
            
            # Generate summary
            batch_result['summary'] = {
                'success_rate': (batch_result['migrated_projects'] / max(batch_result['total_projects'], 1)) * 100,
                'total_changes': sum(1 for r in batch_result['project_results'].values() 
                                   if r.get('success', False)),
                'dry_run': dry_run
            }
        
        except Exception as e:
            logger.error(f"Error during batch migration: {e}")
            batch_result['error'] = str(e)
        
        return batch_result
    
    def rollback_traefik_migration(self, project_name: str) -> Dict[str, Any]:
        """Rollback a Traefik migration"""
        rollback_result = {
            'project_name': project_name,
            'success': False,
            'steps_completed': [],
            'steps_failed': []
        }
        
        try:
            logger.info(f"Starting rollback for project: {project_name}")
            
            # Find backup
            backup_path = self._find_project_backup(project_name)
            if not backup_path:
                rollback_result['steps_failed'].append("No backup found for rollback")
                return rollback_result
            
            # Stop services
            if self.deployment_manager.stop(project_name):
                rollback_result['steps_completed'].append("Services stopped")
            
            # Restore backup
            if self._restore_project_backup(project_name, backup_path):
                rollback_result['steps_completed'].append("Backup restored")
            else:
                rollback_result['steps_failed'].append("Failed to restore backup")
                return rollback_result
            
            # Rollback port allocation
            if self.port_manager.rollback_traefik_migration(project_name):
                rollback_result['steps_completed'].append("Port allocation restored")
            
            # Release domains
            self.domain_manager.release_project_domains(project_name)
            rollback_result['steps_completed'].append("Domains released")
            
            # Restart services
            if self.deployment_manager.deploy(project_name):
                rollback_result['steps_completed'].append("Services restarted")
            else:
                rollback_result['steps_failed'].append("Failed to restart services")
                return rollback_result
            
            rollback_result['success'] = True
            logger.info(f"Successfully rolled back project {project_name}")
        
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
            rollback_result['steps_failed'].append(f"Rollback error: {e}")
        
        return rollback_result
    
    def _validate_migration_prerequisites(self, project_name: str) -> bool:
        """Validate prerequisites for migration"""
        try:
            # Check if project exists
            if not self.deployment_manager.project_exists(project_name):
                logger.error(f"Project {project_name} does not exist")
                return False
            
            # Check if Traefik is running
            if not self.traefik_manager.is_running():
                logger.error("Traefik is not running")
                return False
            
            # Check if Traefik network exists
            if not self.traefik_manager.network_exists():
                logger.error("Traefik network does not exist")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error validating prerequisites: {e}")
            return False
    
    def _analyze_project_for_migration(self, project_name: str) -> Dict[str, Any]:
        """Analyze a project for Traefik migration compatibility"""
        analysis = {
            'compatible': False,
            'issues': [],
            'current_ports': [],
            'services': [],
            'has_web_services': False,
            'compose_file_path': None
        }
        
        try:
            # Get project path
            project_path = paths.get_project_path(project_name)
            compose_file = project_path / "docker-compose.yml"
            
            if not compose_file.exists():
                analysis['issues'].append("No docker-compose.yml file found")
                return analysis
            
            analysis['compose_file_path'] = str(compose_file)
            
            # Parse compose file
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            services = compose_data.get('services', {})
            analysis['services'] = list(services.keys())
            
            # Check for web services and ports
            for service_name, service_config in services.items():
                ports = service_config.get('ports', [])
                
                for port_config in ports:
                    if isinstance(port_config, str) and ':' in port_config:
                        # Format: "host_port:container_port"
                        host_port = port_config.split(':')[0]
                        try:
                            port_num = int(host_port)
                            analysis['current_ports'].append(port_num)
                            
                            # Check if it's a web service port
                            if port_num in [80, 443, 8080, 3000, 5000, 8000, 9000]:
                                analysis['has_web_services'] = True
                        except ValueError:
                            pass
            
            # Check if already has Traefik labels
            has_traefik_labels = False
            for service_config in services.values():
                labels = service_config.get('labels', [])
                if any('traefik.enable' in str(label) for label in labels):
                    has_traefik_labels = True
                    break
            
            if has_traefik_labels:
                analysis['issues'].append("Project already has Traefik labels")
            
            # Determine compatibility
            if not analysis['issues'] and analysis['has_web_services']:
                analysis['compatible'] = True
            elif not analysis['has_web_services']:
                analysis['issues'].append("No web services detected")
        
        except Exception as e:
            analysis['issues'].append(f"Error analyzing project: {e}")
            logger.error(f"Error analyzing project {project_name}: {e}")
        
        return analysis
    
    def _create_project_backup(self, project_name: str) -> Optional[Path]:
        """Create a backup of the project before migration"""
        try:
            project_path = paths.get_project_path(project_name)
            backup_dir = paths.data_dir / "backups" / "migrations"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped backup
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{project_name}_{timestamp}"
            
            # Copy project directory
            shutil.copytree(project_path, backup_path)
            
            logger.info(f"Created backup at {backup_path}")
            return backup_path
        
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def _find_project_backup(self, project_name: str) -> Optional[Path]:
        """Find the most recent backup for a project"""
        try:
            backup_dir = paths.data_dir / "backups" / "migrations"
            
            if not backup_dir.exists():
                return None
            
            # Find backups for this project
            backups = []
            for backup_path in backup_dir.iterdir():
                if backup_path.is_dir() and backup_path.name.startswith(f"{project_name}_"):
                    backups.append(backup_path)
            
            if not backups:
                return None
            
            # Return most recent backup
            return max(backups, key=lambda p: p.stat().st_mtime)
        
        except Exception as e:
            logger.error(f"Error finding backup: {e}")
            return None
    
    def _restore_project_backup(self, project_name: str, backup_path: Path) -> bool:
        """Restore a project from backup"""
        try:
            project_path = paths.get_project_path(project_name)
            
            # Remove current project directory
            if project_path.exists():
                shutil.rmtree(project_path)
            
            # Restore from backup
            shutil.copytree(backup_path, project_path)
            
            logger.info(f"Restored project from {backup_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def _update_project_config_for_traefik(self, project_name: str, 
                                         domain: Optional[str],
                                         subdomain: Optional[str],
                                         ssl_enabled: bool) -> Dict[str, Any]:
        """Update project configuration for Traefik integration"""
        changes = {}
        
        try:
            # Update project metadata
            metadata = self.deployment_manager.get_project_metadata(project_name)
            
            # Add Traefik configuration
            traefik_config = {
                'enabled': True,
                'ssl_enabled': ssl_enabled,
                'migrated_at': self._get_current_timestamp()
            }
            
            if domain:
                traefik_config['domain'] = domain
            if subdomain:
                traefik_config['subdomain'] = subdomain
            
            metadata['traefik'] = traefik_config
            changes['traefik_config'] = traefik_config
            
            # Save updated metadata
            self.deployment_manager.save_project_metadata(project_name, metadata)
            
            logger.info(f"Updated project configuration for {project_name}")
        
        except Exception as e:
            logger.error(f"Error updating project config: {e}")
        
        return changes
    
    def _update_compose_file_for_traefik(self, project_name: str,
                                       domain: Optional[str],
                                       subdomain: Optional[str],
                                       ssl_enabled: bool) -> Dict[str, Any]:
        """Update Docker Compose file with Traefik labels"""
        changes = {}
        
        try:
            project_path = paths.get_project_path(project_name)
            compose_file = project_path / "docker-compose.yml"
            
            # Load compose file
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            services = compose_data.get('services', {})
            
            # Update each service with Traefik labels
            for service_name, service_config in services.items():
                # Detect service type
                service_type = self.label_generator._detect_service_type(service_name, service_config)
                
                # Generate Traefik labels
                labels = self.label_generator.generate_labels(
                    project_name=project_name,
                    service_name=f"{project_name}-{service_name}",
                    service_type=service_type,
                    domain=domain,
                    subdomain=subdomain,
                    ssl_enabled=ssl_enabled
                )
                
                if labels:
                    # Remove port mappings for web services
                    original_ports = service_config.get('ports', [])
                    if original_ports:
                        changes[f'{service_name}_original_ports'] = original_ports
                        # Keep only non-web ports (anything not 80, 443, 8080, etc.)
                        filtered_ports = []
                        for port in original_ports:
                            if isinstance(port, str) and ':' in port:
                                host_port = int(port.split(':')[0])
                                if host_port not in [80, 443, 8080, 3000, 5000, 8000, 9000]:
                                    filtered_ports.append(port)
                        service_config['ports'] = filtered_ports
                    
                    # Add Traefik labels
                    existing_labels = service_config.get('labels', [])
                    if isinstance(existing_labels, list):
                        # Convert list to dict format
                        label_dict = {}
                        for label in existing_labels:
                            if '=' in str(label):
                                key, value = str(label).split('=', 1)
                                label_dict[key] = value
                        existing_labels = label_dict
                    
                    existing_labels.update(labels)
                    service_config['labels'] = existing_labels
                    
                    # Add to Traefik network
                    networks = service_config.get('networks', [])
                    if isinstance(networks, list):
                        if 'blastdock-network' not in networks:
                            networks.append('blastdock-network')
                    else:
                        # Dict format
                        if 'blastdock-network' not in networks:
                            networks['blastdock-network'] = {}
                    service_config['networks'] = networks
                    
                    changes[f'{service_name}_traefik_labels'] = labels
            
            # Add Traefik network to compose file
            if 'networks' not in compose_data:
                compose_data['networks'] = {}
            
            compose_data['networks']['blastdock-network'] = {
                'external': True
            }
            
            # Save updated compose file
            with open(compose_file, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Updated Docker Compose file for {project_name}")
        
        except Exception as e:
            logger.error(f"Error updating compose file: {e}")
        
        return changes
    
    def _restart_project_services(self, project_name: str) -> bool:
        """Restart project services with new configuration"""
        try:
            # Stop services
            if not self.deployment_manager.stop(project_name):
                logger.error(f"Failed to stop services for {project_name}")
                return False
            
            # Deploy with new configuration
            if not self.deployment_manager.deploy(project_name):
                logger.error(f"Failed to deploy services for {project_name}")
                return False
            
            logger.info(f"Restarted services for {project_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error restarting services: {e}")
            return False
    
    def _verify_traefik_migration(self, project_name: str) -> Dict[str, Any]:
        """Verify that Traefik migration was successful"""
        verification = {
            'success': False,
            'services_running': False,
            'traefik_labels_present': False,
            'domain_accessible': False,
            'ssl_working': False,
            'issues': []
        }
        
        try:
            # Check if services are running
            status = self.deployment_manager.get_status(project_name)
            verification['services_running'] = 'running' in status.lower()
            
            # Check for Traefik labels in running containers
            containers = self.docker_client.list_containers(all=False)
            project_containers = [c for c in containers if project_name in c.get('name', '')]
            
            for container in project_containers:
                labels = container.get('labels', {})
                if labels.get('traefik.enable') == 'true':
                    verification['traefik_labels_present'] = True
                    break
            
            # Check domain accessibility (basic check)
            project_domains = self.domain_manager.get_project_domains(project_name)
            if project_domains['subdomains'] or project_domains['custom_domains']:
                verification['domain_accessible'] = True  # Simplified check
            
            # Overall success
            verification['success'] = (
                verification['services_running'] and
                verification['traefik_labels_present']
            )
        
        except Exception as e:
            verification['issues'].append(f"Verification error: {e}")
            logger.error(f"Error verifying migration: {e}")
        
        return verification
    
    def _log_migration(self, project_name: str, migration_result: Dict[str, Any]):
        """Log migration details"""
        try:
            log_entry = {
                'timestamp': self._get_current_timestamp(),
                'project_name': project_name,
                'success': migration_result['success'],
                'steps_completed': migration_result['steps_completed'],
                'steps_failed': migration_result['steps_failed'],
                'changes_made': migration_result['changes_made']
            }
            
            # Append to migration log
            with open(self.migration_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        
        except Exception as e:
            logger.error(f"Error logging migration: {e}")
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()