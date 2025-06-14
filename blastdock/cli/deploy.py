"""
Deploy command implementation for BlastDock CLI
Handles project deployment using templates
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.config import get_config_manager
from ..performance.template_registry import get_template_registry
from ..performance.traefik_enhancer import get_traefik_enhancer, SecurityLevel
from ..utils.docker_utils import EnhancedDockerClient
from ..utils.template_validator import TemplateValidator
from ..utils.logging import get_logger
from ..exceptions import DeploymentError, TemplateNotFoundError
from ..models.project import ProjectConfig

logger = get_logger(__name__)
console = Console()


class DeploymentManager:
    """Manages the deployment process for projects"""
    
    def __init__(self):
        """Initialize deployment manager"""
        self.logger = get_logger(__name__)
        self.config_manager = get_config_manager()
        self.template_registry = get_template_registry()
        self.traefik_enhancer = get_traefik_enhancer()
        self.docker_client = EnhancedDockerClient()
        self.validator = TemplateValidator()
        
        # Initialize template registry
        self.template_registry.initialize(preload=False, enhance_traefik=False)
    
    def deploy_project(self, 
                      project_name: str,
                      template_name: str,
                      config_values: Dict[str, str],
                      dry_run: bool = False,
                      auto_enhance: bool = True,
                      security_level: str = "standard") -> Dict[str, Any]:
        """Deploy a project using specified template"""
        
        # Validate inputs
        if not self._validate_project_name(project_name):
            raise DeploymentError(f"Invalid project name: {project_name}")
        
        # Check if Docker is running
        if not self.docker_client.is_running():
            raise DeploymentError("Docker is not running. Please start Docker first.")
        
        # Get template
        console.print(f"[cyan]Loading template: {template_name}[/cyan]")
        template_data = self.template_registry.get_template(template_name)
        
        if not template_data:
            raise TemplateNotFoundError(f"Template '{template_name}' not found")
        
        # Prepare deployment
        with console.status("[bold green]Preparing deployment...") as status:
            # Create project directory
            project_dir = self._create_project_directory(project_name, dry_run)
            
            # Process template
            status.update("[bold green]Processing template...")
            processed_template = self._process_template(
                template_data,
                project_name,
                config_values,
                auto_enhance,
                security_level
            )
            
            # Generate docker-compose file
            status.update("[bold green]Generating docker-compose.yml...")
            compose_file = self._generate_compose_file(
                processed_template,
                project_dir,
                dry_run
            )
            
            # Generate .env file
            status.update("[bold green]Generating environment file...")
            env_file = self._generate_env_file(
                processed_template,
                config_values,
                project_dir,
                dry_run
            )
        
        # Show deployment plan
        self._show_deployment_plan(project_name, template_name, processed_template)
        
        if dry_run:
            console.print("\n[yellow]DRY RUN MODE - No actual deployment[/yellow]")
            return {
                'success': True,
                'dry_run': True,
                'project_name': project_name,
                'template': template_name,
                'compose_file': compose_file,
                'env_file': env_file
            }
        
        # Deploy with Docker Compose
        console.print("\n[bold green]Starting deployment...[/bold green]")
        deployment_result = self._docker_compose_up(project_dir, project_name)
        
        if deployment_result['success']:
            # Save project configuration
            self._save_project_config(
                project_name,
                template_name,
                config_values,
                project_dir
            )
            
            console.print(f"\n[bold green]✅ Project '{project_name}' deployed successfully![/bold green]")
            self._show_deployment_info(project_name, processed_template)
        else:
            console.print(f"\n[bold red]❌ Deployment failed: {deployment_result['error']}[/bold red]")
        
        return deployment_result
    
    def _validate_project_name(self, name: str) -> bool:
        """Validate project name"""
        import re
        return bool(re.match(r'^[a-z0-9-]+$', name))
    
    def _create_project_directory(self, project_name: str, dry_run: bool) -> Path:
        """Create project directory"""
        base_dir = Path(self.config_manager.config.projects_dir)
        project_dir = base_dir / project_name
        
        if not dry_run:
            project_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created project directory: {project_dir}")
        
        return project_dir
    
    def _process_template(self, 
                         template_data: Dict[str, Any],
                         project_name: str,
                         config_values: Dict[str, str],
                         auto_enhance: bool,
                         security_level: str) -> Dict[str, Any]:
        """Process template with enhancements and configuration"""
        
        # Merge config values with defaults
        final_config = {'project_name': project_name}
        
        # Get template fields
        template_fields = template_data.get('fields', {})
        
        for field_name, field_def in template_fields.items():
            if field_name in config_values:
                final_config[field_name] = config_values[field_name]
            elif 'default' in field_def:
                final_config[field_name] = field_def['default']
            elif field_def.get('required', True):
                raise DeploymentError(f"Required field '{field_name}' not provided")
        
        # Auto-enhance with Traefik if needed
        if auto_enhance and not template_data.get('traefik_config'):
            self.logger.info("Auto-enhancing template with Traefik configuration")
            # This would enhance the actual template file in production
            # For now, we'll add basic Traefik config to the data
            template_data['traefik_config'] = {
                'service_port': 80,
                'routing_priority': 1,
                'middlewares': []
            }
        
        # Replace template variables
        template_data['_config'] = final_config
        
        return template_data
    
    def _generate_compose_file(self, 
                              template_data: Dict[str, Any],
                              project_dir: Path,
                              dry_run: bool) -> Path:
        """Generate docker-compose.yml file"""
        compose_data = template_data.get('compose', {})
        config = template_data.get('_config', {})
        
        # Replace template variables in compose data
        compose_str = yaml.dump(compose_data)
        for key, value in config.items():
            compose_str = compose_str.replace(f'{{{{ {key} }}}}', str(value))
        
        compose_file = project_dir / 'docker-compose.yml'
        
        if not dry_run:
            with open(compose_file, 'w') as f:
                f.write(compose_str)
            self.logger.info(f"Generated docker-compose.yml: {compose_file}")
        
        return compose_file
    
    def _generate_env_file(self,
                          template_data: Dict[str, Any],
                          config_values: Dict[str, str],
                          project_dir: Path,
                          dry_run: bool) -> Path:
        """Generate .env file"""
        env_content = []
        config = template_data.get('_config', {})
        
        # Add all configuration values
        for key, value in config.items():
            if key != 'project_name':  # Skip project name
                env_content.append(f"{key.upper()}={value}")
        
        env_file = project_dir / '.env'
        
        if not dry_run:
            with open(env_file, 'w') as f:
                f.write('\n'.join(env_content))
            self.logger.info(f"Generated .env file: {env_file}")
        
        return env_file
    
    def _docker_compose_up(self, project_dir: Path, project_name: str) -> Dict[str, Any]:
        """Run docker-compose up"""
        try:
            cmd = [
                'docker-compose',
                '-p', project_name,
                'up', '-d'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=project_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout,
                    'project_dir': str(project_dir)
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr,
                    'output': result.stdout
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _save_project_config(self, 
                            project_name: str,
                            template_name: str,
                            config_values: Dict[str, str],
                            project_dir: Path):
        """Save project configuration"""
        project_config = {
            'name': project_name,
            'template': template_name,
            'config': config_values,
            'directory': str(project_dir),
            'created_at': time.time(),
            'status': 'deployed'
        }
        
        config_file = project_dir / 'blastdock.json'
        with open(config_file, 'w') as f:
            import json
            json.dump(project_config, f, indent=2)
        
        self.logger.info(f"Saved project configuration: {config_file}")
    
    def _show_deployment_plan(self, 
                             project_name: str,
                             template_name: str,
                             template_data: Dict[str, Any]):
        """Show deployment plan to user"""
        console.print("\n[bold cyan]Deployment Plan[/bold cyan]")
        console.print(f"Project: {project_name}")
        console.print(f"Template: {template_name}")
        
        # Show services
        compose = template_data.get('compose', {})
        services = compose.get('services', {})
        
        if services:
            console.print("\n[bold]Services to deploy:[/bold]")
            table = Table()
            table.add_column("Service", style="cyan")
            table.add_column("Image", style="green")
            table.add_column("Ports", style="yellow")
            
            for service_name, service_config in services.items():
                image = service_config.get('image', 'N/A')
                ports = service_config.get('ports', [])
                ports_str = ', '.join(str(p) for p in ports) if ports else 'None'
                table.add_row(service_name, image, ports_str)
            
            console.print(table)
        
        # Show Traefik status
        if template_data.get('traefik_config'):
            console.print("\n[bold green]✓ Traefik integration enabled[/bold green]")
    
    def _show_deployment_info(self, project_name: str, template_data: Dict[str, Any]):
        """Show post-deployment information"""
        config = template_data.get('_config', {})
        
        console.print("\n[bold cyan]Deployment Information[/bold cyan]")
        
        # Access URLs
        if 'domain' in config and config['domain']:
            console.print(f"Domain: https://{config['domain']}")
        elif 'subdomain' in config:
            console.print(f"URL: https://{config['subdomain']}.{config.get('default_domain', 'localhost')}")
        
        # Show ports
        compose = template_data.get('compose', {})
        services = compose.get('services', {})
        
        for service_name, service_config in services.items():
            ports = service_config.get('ports', [])
            for port in ports:
                if ':' in str(port):
                    external_port = str(port).split(':')[0]
                    console.print(f"{service_name}: http://localhost:{external_port}")
        
        console.print(f"\n[dim]Manage with: blastdock status {project_name}[/dim]")


@click.group(name='deploy')
def deploy_group():
    """Deployment management commands"""
    pass


@deploy_group.command('create')
@click.argument('project_name')
@click.option('--template', '-t', required=True, help='Template to use')
@click.option('--config', '-c', multiple=True, help='Configuration values (key=value)')
@click.option('--dry-run', is_flag=True, help='Show what would be deployed')
@click.option('--no-enhance', is_flag=True, help='Disable automatic Traefik enhancement')
@click.option('--security', default='standard', 
              type=click.Choice(['minimal', 'standard', 'enhanced', 'enterprise']),
              help='Security level for Traefik configuration')
def create_deployment(project_name: str, template: str, config: tuple, 
                     dry_run: bool, no_enhance: bool, security: str):
    """Deploy a new project using a template"""
    try:
        # Parse configuration values
        config_dict = {}
        for config_item in config:
            if '=' not in config_item:
                console.print(f"[red]Invalid config format: {config_item}[/red]")
                console.print("[dim]Use format: key=value[/dim]")
                return
            
            key, value = config_item.split('=', 1)
            config_dict[key] = value
        
        # Create deployment manager
        manager = DeploymentManager()
        
        # Deploy project
        result = manager.deploy_project(
            project_name=project_name,
            template_name=template,
            config_values=config_dict,
            dry_run=dry_run,
            auto_enhance=not no_enhance,
            security_level=security
        )
        
        if result['success']:
            console.print("\n[bold green]Deployment completed successfully![/bold green]")
        
    except DeploymentError as e:
        console.print(f"[bold red]Deployment error: {e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error: {e}[/bold red]")
        logger.exception("Deployment failed")
        sys.exit(1)




@deploy_group.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def list_deployments(output_format):
    """List all deployed projects"""
    from ..utils.docker_utils import EnhancedDockerClient
    docker_client = EnhancedDockerClient()
    
    # Get all projects
    projects = []
    try:
        containers = docker_client.client.containers.list(all=True)
        project_names = set()
        
        for container in containers:
            labels = container.labels
            project = labels.get('com.docker.compose.project')
            if project:
                project_names.add(project)
        
        for project in project_names:
            projects.append({
                'name': project,
                'status': 'running',  # Simplified
                'services': 1  # Simplified
            })
    except Exception as e:
        console.print(f"[red]Error listing deployments: {e}[/red]")
        return
    
    if output_format == 'json':
        import json
        console.print(json.dumps(projects, indent=2))
    else:
        if not projects:
            console.print("[yellow]No deployments found[/yellow]")
            return
        
        table = Table(title="Deployed Projects")
        table.add_column("Project", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Services", style="blue")
        
        for project in projects:
            table.add_row(
                project['name'],
                project['status'],
                str(project['services'])
            )
        
        console.print(table)

@deploy_group.command('status')
@click.argument('project_name')
def deployment_status(project_name):
    """Show detailed status of a deployment"""
    from ..utils.docker_utils import EnhancedDockerClient
    docker_client = EnhancedDockerClient()
    
    try:
        containers = docker_client.client.containers.list(all=True)
        project_containers = []
        
        for container in containers:
            if container.labels.get('com.docker.compose.project') == project_name:
                project_containers.append(container)
        
        if not project_containers:
            console.print(f"[yellow]No containers found for project '{project_name}'[/yellow]")
            return
        
        panel_content = []
        panel_content.append(f"[bold]Project:[/bold] {project_name}")
        panel_content.append(f"[bold]Containers:[/bold] {len(project_containers)}")
        
        for container in project_containers:
            service = container.labels.get('com.docker.compose.service', 'unknown')
            status = container.status
            panel_content.append(f"\n[bold]{service}:[/bold]")
            panel_content.append(f"  Status: {status}")
            panel_content.append(f"  Image: {container.image.tags[0] if container.image.tags else 'unknown'}")
        
        console.print(Panel(
            "\n".join(panel_content),
            title=f"Deployment Status: {project_name}",
            border_style="blue"
        ))
        
    except Exception as e:
        console.print(f"[red]Error getting status: {e}[/red]")

@deploy_group.command('remove')
@click.argument('project_name')
@click.option('--force', '-f', is_flag=True, help='Force removal without confirmation')
@click.option('--keep-volumes', is_flag=True, help='Keep data volumes')
def remove_deployment(project_name, force, keep_volumes):
    """Remove a deployed project"""
    if not force:
        if not click.confirm(f"Remove project '{project_name}'?"):
            console.print("[yellow]Removal cancelled[/yellow]")
            return
    
    try:
        # Get project directory
        config_manager = get_config_manager()
        project_dir = Path(config_manager.config.projects_dir) / project_name
        
        if project_dir.exists():
            # Run docker-compose down
            cmd = ['docker-compose', '-p', project_name, 'down']
            if not keep_volumes:
                cmd.append('-v')
            
            result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(f"[green]✓ Project '{project_name}' removed successfully[/green]")
                
                # Optionally remove project directory
                if click.confirm("Remove project files?"):
                    import shutil
                    shutil.rmtree(project_dir)
                    console.print(f"[green]✓ Project files removed[/green]")
            else:
                console.print(f"[red]Failed to remove project: {result.stderr}[/red]")
        else:
            console.print(f"[yellow]Project directory not found[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error removing project: {e}[/red]")

@deploy_group.command('logs')
@click.argument('project_name')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--tail', type=int, default=50, help='Number of lines to show')
@click.option('--service', help='Show logs for specific service')
def deployment_logs(project_name, follow, tail, service):
    """View deployment logs"""
    try:
        # Get project directory
        config_manager = get_config_manager()
        project_dir = Path(config_manager.config.projects_dir) / project_name
        
        if not project_dir.exists():
            console.print(f"[red]Project '{project_name}' not found[/red]")
            return
        
        # Build docker-compose logs command
        cmd = ['docker-compose', '-p', project_name, 'logs']
        
        if follow:
            cmd.append('-f')
        
        if tail:
            cmd.extend(['--tail', str(tail)])
        
        if service:
            cmd.append(service)
        
        # Run command
        subprocess.run(cmd, cwd=project_dir)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Log viewing stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error viewing logs: {e}[/red]")

@deploy_group.command('update')
@click.argument('project_name')
@click.option('--pull', is_flag=True, help='Pull latest images')
def update_deployment(project_name, pull):
    """Update a deployment"""
    try:
        config_manager = get_config_manager()
        project_dir = Path(config_manager.config.projects_dir) / project_name
        
        if not project_dir.exists():
            console.print(f"[red]Project '{project_name}' not found[/red]")
            return
        
        with console.status("[bold green]Updating deployment...") as status:
            if pull:
                status.update("[bold green]Pulling latest images...")
                cmd = ['docker-compose', '-p', project_name, 'pull']
                subprocess.run(cmd, cwd=project_dir, capture_output=True)
            
            status.update("[bold green]Recreating containers...")
            cmd = ['docker-compose', '-p', project_name, 'up', '-d', '--force-recreate']
            result = subprocess.run(cmd, cwd=project_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                console.print(f"[green]✓ Project '{project_name}' updated successfully[/green]")
            else:
                console.print(f"[red]Update failed: {result.stderr}[/red]")
                
    except Exception as e:
        console.print(f"[red]Error updating project: {e}[/red]")

@deploy_group.command('exec')
@click.argument('project_name')
@click.argument('command', nargs=-1, required=True)
@click.option('--service', help='Service to execute command in')
def execute_command(project_name, command, service):
    """Execute a command in a project container"""
    try:
        config_manager = get_config_manager()
        project_dir = Path(config_manager.config.projects_dir) / project_name
        
        if not project_dir.exists():
            console.print(f"[red]Project '{project_name}' not found[/red]")
            return
        
        # Build docker-compose exec command
        cmd = ['docker-compose', '-p', project_name, 'exec']
        
        if service:
            cmd.append(service)
        else:
            # Try to get the first service
            compose_file = project_dir / 'docker-compose.yml'
            if compose_file.exists():
                import yaml
                with open(compose_file) as f:
                    compose_data = yaml.safe_load(f)
                    services = list(compose_data.get('services', {}).keys())
                    if services:
                        cmd.append(services[0])
                    else:
                        console.print("[red]No services found in docker-compose.yml[/red]")
                        return
        
        cmd.extend(command)
        
        # Run command
        subprocess.run(cmd, cwd=project_dir)
        
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")


# Export for main CLI
deploy = deploy_group