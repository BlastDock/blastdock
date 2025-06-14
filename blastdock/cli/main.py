"""
Main CLI module for BlastDock
Provides the primary command-line interface functionality
"""

import click
import sys
import os
from pathlib import Path

# Add the package to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from blastdock.cli.config_commands import config_group
from blastdock.cli.templates import templates
from blastdock.cli.monitoring import monitoring
from blastdock.cli.security import security
from blastdock.cli.performance import performance
from blastdock.cli.diagnostics import diagnostics
from blastdock.cli.deploy import deploy
from blastdock.cli.marketplace import marketplace
from blastdock.utils.logging import get_logger

logger = get_logger(__name__)


@click.group()
@click.version_option()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--config-file', type=click.Path(), help='Path to configuration file')
@click.pass_context
def cli(ctx, verbose, config_file):
    """BlastDock - Docker deployment management CLI"""
    # Ensure that ctx.obj exists and is a dict
    ctx.ensure_object(dict)
    
    # Store global options
    ctx.obj['verbose'] = verbose
    ctx.obj['config_file'] = config_file
    
    # Set up logging level
    if verbose:
        logger.setLevel('DEBUG')


# Add command groups
cli.add_command(config_group)
cli.add_command(templates)
cli.add_command(monitoring)
cli.add_command(security)
cli.add_command(performance)
cli.add_command(diagnostics)
cli.add_command(deploy)
cli.add_command(marketplace)


@cli.command()
@click.argument('project_name')
@click.option('--template', '-t', help='Template to use for deployment')
@click.option('--config', '-c', help='Configuration values (key=value)')
@click.option('--dry-run', is_flag=True, help='Show what would be deployed without actually deploying')
@click.pass_context
def deploy(ctx, project_name, template, config, dry_run):
    """Deploy a project using a template"""
    click.echo(f"Deploying project: {project_name}")
    
    if template:
        click.echo(f"Using template: {template}")
    
    if config:
        click.echo(f"Configuration: {config}")
    
    if dry_run:
        click.echo("Dry run mode - no actual deployment")
        return
    
    # TODO: Implement actual deployment logic
    click.echo("Deployment functionality not yet implemented")


@cli.command()
@click.argument('project_name')
@click.option('--force', is_flag=True, help='Force removal without confirmation')
@click.pass_context
def remove(ctx, project_name, force):
    """Remove a deployed project"""
    if not force:
        if not click.confirm(f"Are you sure you want to remove project '{project_name}'?"):
            click.echo("Cancelled")
            return
    
    click.echo(f"Removing project: {project_name}")
    
    # TODO: Implement actual removal logic
    click.echo("Removal functionality not yet implemented")


@cli.command()
@click.option('--status', is_flag=True, help='Show detailed status information')
@click.pass_context
def list(ctx, status):
    """List deployed projects"""
    click.echo("Listing deployed projects...")
    
    if status:
        click.echo("Including detailed status information")
    
    # TODO: Implement actual listing logic
    click.echo("No projects found (listing functionality not yet implemented)")


@cli.command()
@click.argument('project_name')
@click.pass_context
def status(ctx, project_name):
    """Show status of a deployed project"""
    click.echo(f"Status for project: {project_name}")
    
    # TODO: Implement actual status logic
    click.echo("Status functionality not yet implemented")


@cli.command()
@click.argument('project_name')
@click.option('--service', help='Restart specific service only')
@click.pass_context
def restart(ctx, project_name, service):
    """Restart a deployed project or specific service"""
    if service:
        click.echo(f"Restarting service '{service}' in project: {project_name}")
    else:
        click.echo(f"Restarting project: {project_name}")
    
    # TODO: Implement actual restart logic
    click.echo("Restart functionality not yet implemented")


@cli.command()
@click.argument('project_name')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--service', help='Show logs for specific service only')
@click.pass_context
def logs(ctx, project_name, lines, follow, service):
    """Show logs for a deployed project"""
    if service:
        click.echo(f"Showing logs for service '{service}' in project: {project_name}")
    else:
        click.echo(f"Showing logs for project: {project_name}")
    
    click.echo(f"Lines: {lines}, Follow: {follow}")
    
    # TODO: Implement actual logs logic
    click.echo("Logs functionality not yet implemented")


if __name__ == '__main__':
    cli()