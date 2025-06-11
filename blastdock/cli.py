#!/usr/bin/env python3
"""
Docker Deployment CLI Tool
Main CLI interface for managing Docker application deployments
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import os
import sys

from .core.template_manager import TemplateManager
from .core.deployment_manager import DeploymentManager
from .core.monitor import Monitor
from .utils.helpers import get_deploys_dir

console = Console()

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Docker Deployment CLI Tool - Simplify Docker application deployment"""
    pass

@cli.command()
@click.argument('template_name')
@click.option('--interactive', '-i', is_flag=True, help='Interactive configuration mode')
def init(template_name, interactive):
    """Initialize a new deployment from a template"""
    try:
        template_manager = TemplateManager()
        
        if not template_manager.template_exists(template_name):
            console.print(f"[red]Template '{template_name}' not found![/red]")
            console.print("\nAvailable templates:")
            templates = template_manager.list_templates()
            for template in templates:
                console.print(f"  • {template}")
            return
        
        project_name = click.prompt("Enter project name", type=str)
        
        if interactive:
            config = template_manager.interactive_config(template_name)
        else:
            config = template_manager.get_default_config(template_name)
        
        deployment_manager = DeploymentManager()
        deployment_manager.create_deployment(project_name, template_name, config)
        
        console.print(f"[green]Successfully initialized project '{project_name}' with template '{template_name}'[/green]")
        console.print(f"Project created in: {get_deploys_dir()}/{project_name}")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('project_name')
def deploy(project_name):
    """Deploy an application"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            console.print(f"[red]Project '{project_name}' not found![/red]")
            return
        
        with console.status("[bold green]Deploying application..."):
            deployment_manager.deploy(project_name)
        
        console.print(f"[green]Successfully deployed '{project_name}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Deployment failed: {str(e)}[/red]")

@cli.command()
def list():
    """List all deployments"""
    try:
        deployment_manager = DeploymentManager()
        projects = deployment_manager.list_projects()
        
        if not projects:
            console.print("[yellow]No deployments found[/yellow]")
            return
        
        table = Table(title="Docker Deployments")
        table.add_column("Project Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Template", style="blue")
        table.add_column("Created", style="magenta")
        
        monitor = Monitor()
        for project in projects:
            status = monitor.get_status(project)
            template = deployment_manager.get_project_template(project)
            created = deployment_manager.get_project_created_date(project)
            table.add_row(project, status, template, created)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('project_name')
def status(project_name):
    """Check deployment status"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            console.print(f"[red]Project '{project_name}' not found![/red]")
            return
        
        monitor = Monitor()
        status_info = monitor.get_detailed_status(project_name)
        
        console.print(Panel(
            status_info,
            title=f"Status: {project_name}",
            border_style="blue"
        ))
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('project_name')
def stop(project_name):
    """Stop a deployment"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            console.print(f"[red]Project '{project_name}' not found![/red]")
            return
        
        if click.confirm(f"Are you sure you want to stop '{project_name}'?"):
            with console.status("[bold yellow]Stopping deployment..."):
                deployment_manager.stop(project_name)
            console.print(f"[green]Successfully stopped '{project_name}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('project_name')
def remove(project_name):
    """Remove a deployment"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            console.print(f"[red]Project '{project_name}' not found![/red]")
            return
        
        console.print(f"[red]Warning: This will permanently remove '{project_name}' and all its data![/red]")
        if click.confirm("Are you sure you want to continue?"):
            with console.status("[bold red]Removing deployment..."):
                deployment_manager.remove(project_name)
            console.print(f"[green]Successfully removed '{project_name}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('project_name')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--service', '-s', help='Show logs for specific service')
def logs(project_name, follow, service):
    """View deployment logs"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            console.print(f"[red]Project '{project_name}' not found![/red]")
            return
        
        deployment_manager.show_logs(project_name, follow=follow, service=service)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
def templates():
    """List available templates"""
    try:
        template_manager = TemplateManager()
        templates = template_manager.list_templates()
        
        console.print("[bold blue]Available Templates:[/bold blue]")
        for template in templates:
            info = template_manager.get_template_info(template)
            console.print(f"  • [cyan]{template}[/cyan] - {info.get('description', 'No description')}")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('project_name')
def config(project_name):
    """Show project configuration details"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            console.print(f"[red]Project '{project_name}' not found![/red]")
            return
        
        project_dir = os.path.join(get_deploys_dir(), project_name)
        config_file = os.path.join(project_dir, ".blastdock.json")
        env_file = os.path.join(project_dir, ".env")
        
        console.print(f"[bold cyan]Configuration for project:[/bold cyan] [bold green]{project_name}[/bold green]\n")
        
        # Display project metadata
        if os.path.exists(config_file):
            try:
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    
                    table = Table(title="Project Metadata")
                    table.add_column("Property", style="cyan")
                    table.add_column("Value", style="green")
                    
                    for key, value in config.items():
                        # Handle dict and list values safely
                        try:
                            if type(value) in (dict, list):
                                value = json.dumps(value, indent=2)
                        except:
                            pass
                        table.add_row(str(key), str(value))
                    
                    console.print(table)
            except Exception as e:
                console.print(f"[bold red]Error reading config file:[/bold red] {str(e)}")
        else:
            console.print("[yellow]No .blastdock.json configuration file found[/yellow]")
        
        # Display environment variables
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r') as f:
                    env_vars = {}
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key] = value
                    
                    if env_vars:
                        table = Table(title="Environment Variables")
                        table.add_column("Variable", style="cyan")
                        table.add_column("Value", style="green")
                        
                        for key, value in env_vars.items():
                            # Mask passwords and sensitive information
                            if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                                value = "*****"
                            table.add_row(str(key), str(value))
                        
                        console.print(table)
                    else:
                        console.print("[yellow]No environment variables found[/yellow]")
            except Exception as e:
                console.print(f"[bold red]Error reading .env file:[/bold red] {str(e)}")
        else:
            console.print("[yellow]No .env file found[/yellow]")
            
        # Display docker-compose.yml information
        compose_file = os.path.join(project_dir, "docker-compose.yml")
        if os.path.exists(compose_file):
            try:
                import yaml
                with open(compose_file, 'r') as f:
                    compose_data = yaml.safe_load(f)
                
                if compose_data and 'services' in compose_data:
                    services = compose_data['services']
                    
                    table = Table(title="Services Configuration")
                    table.add_column("Service", style="cyan")
                    table.add_column("Image", style="blue")
                    table.add_column("Ports", style="magenta")
                    table.add_column("Volumes", style="yellow")
                    
                    for service_name, service_config in services.items():
                        image = service_config.get('image', 'N/A')
                        
                        # Handle ports safely
                        ports = service_config.get('ports', [])
                        try:
                            if type(ports) == list:
                                ports_str = '\n'.join(str(p) for p in ports) if ports else 'N/A'
                            else:
                                ports_str = str(ports)
                        except:
                            ports_str = 'Error parsing ports'
                        
                        # Handle volumes safely
                        volumes = service_config.get('volumes', [])
                        try:
                            if type(volumes) == list:
                                volumes_str = '\n'.join(str(v) for v in volumes) if volumes else 'N/A'
                            else:
                                volumes_str = str(volumes)
                        except:
                            volumes_str = 'Error parsing volumes'
                        
                        table.add_row(str(service_name), str(image), ports_str, volumes_str)
                    
                    console.print(table)
            except Exception as e:
                console.print(f"[bold red]Error reading docker-compose.yml:[/bold red] {str(e)}")
        else:
            console.print("[yellow]No docker-compose.yml file found[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")

if __name__ == '__main__':
    cli()