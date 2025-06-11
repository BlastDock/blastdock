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

if __name__ == '__main__':
    cli()