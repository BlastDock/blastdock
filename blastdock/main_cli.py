#!/usr/bin/env python3
"""
BlastDock CLI - Enhanced Docker Deployment CLI Tool
Main CLI interface for managing Docker application deployments
"""

import sys
import os
import signal
import click
from rich.console import Console

# Import version and system info
from ._version import __version__, get_system_info, check_python_version

# Import core modules
from .core.template_manager import TemplateManager
from .core.deployment_manager import DeploymentManager
from .core.monitor import Monitor
from .core.config import get_config_manager, get_config
from .core.traefik import TraefikIntegrator
from .core.domain import DomainManager

# Import utilities
from .utils.logging import get_logger, initialize_logging
from .utils.filesystem import paths, initialize_directories
from .utils.error_handler import handle_cli_error

# Import CLI command groups
from .cli.deploy import deploy_group
from .cli.marketplace import marketplace_group
from .cli.monitoring import monitoring as monitoring_group
from .cli.templates import templates as templates_group
from .cli.diagnostics import diagnostics as diagnostics_group
from .cli.security import security as security_group
from .cli.performance import performance as performance_group
from .cli.config_commands import config_group

# Initialize console
console = Console()

# Global logger
logger = None

def signal_handler(signum, frame):
    """Handle keyboard interrupt signals gracefully"""
    console.print("\n[yellow]Operation cancelled by user[/yellow]")
    sys.exit(130)

# Set up signal handlers
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)

def setup_cli_environment(verbose: bool = False, quiet: bool = False, 
                         log_level: str = None, profile: str = "default"):
    """Setup CLI environment with logging and configuration"""
    global logger
    
    # Determine log level
    if log_level:
        level = log_level.upper()
    elif verbose:
        level = "DEBUG"
    elif quiet:
        level = "ERROR"
    else:
        level = "INFO"
    
    # Initialize logging
    initialize_logging(
        log_level=level,
        log_to_console=not quiet,
        log_to_file=True
    )
    
    # Get logger
    logger = get_logger("cli")
    
    # Initialize directories
    try:
        initialize_directories()
    except Exception as e:
        logger.error(f"Failed to initialize directories: {e}")
        if not quiet:
            console.print(f"[yellow]Warning: Could not initialize directories: {e}[/yellow]")
    
    # Load configuration
    try:
        config_manager = get_config_manager(profile)
        config = config_manager.config
        logger.debug(f"Loaded configuration for profile '{profile}'")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        if not quiet:
            console.print(f"[yellow]Warning: Could not load configuration: {e}[/yellow]")

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Suppress non-error output')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
              help='Set logging level')
@click.option('--profile', default='default', help='Configuration profile to use')
@click.version_option(version=__version__, prog_name='BlastDock')
@click.pass_context
def cli(ctx, verbose, quiet, log_level, profile):
    """BlastDock - Docker Deployment CLI Tool
    
    Simplify Docker application deployment with pre-built templates,
    smart Traefik integration, and advanced monitoring.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store options in context
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    ctx.obj['log_level'] = log_level
    ctx.obj['profile'] = profile
    
    # Setup environment
    setup_cli_environment(verbose, quiet, log_level, profile)
    
    # Check Python version
    if not check_python_version():
        console.print("[red]Error: BlastDock requires Python 3.8 or higher[/red]")
        sys.exit(1)

# Legacy commands for backward compatibility
@cli.command()
@click.argument('template_name')
@click.option('--interactive', '-i', is_flag=True, help='Interactive configuration mode')
@click.option('--name', help='Project name')
@click.option('--traefik/--no-traefik', default=None, help='Enable/disable Traefik')
@click.pass_context
def init(ctx, template_name, interactive, name, traefik):
    """Initialize a new deployment (legacy - use 'deploy create' instead)"""
    console.print("[yellow]Note: 'init' is deprecated. Use 'blastdock deploy create' instead[/yellow]")
    ctx.invoke(deploy_group.commands['create'], 
               project_name=name or click.prompt("Project name"),
               template=template_name,
               traefik=traefik)

@cli.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def list(output_format):
    """List all deployments (legacy - use 'deploy list' instead)"""
    console.print("[yellow]Note: 'list' is deprecated. Use 'blastdock deploy list' instead[/yellow]")
    ctx = click.get_current_context()
    ctx.invoke(deploy_group.commands['list'], format=output_format)

@cli.command()
@click.pass_context
def templates(ctx):
    """List available templates (legacy - use 'marketplace search' instead)"""
    console.print("[yellow]Note: 'templates' is deprecated. Use 'blastdock marketplace search' instead[/yellow]")
    ctx.invoke(marketplace_group.commands['search'])

# Traefik Management Commands
@cli.group()
def traefik():
    """Traefik reverse proxy management"""
    pass

@traefik.command()
@click.option('--email', required=True, help='Email for Let\'s Encrypt certificates')
@click.option('--domain', default='localhost', help='Default domain for deployments')
@click.option('--dashboard/--no-dashboard', default=True, help='Enable Traefik dashboard')
@click.option('--dashboard-domain', help='Custom domain for Traefik dashboard')
def install(email, domain, dashboard, dashboard_domain):
    """Install Traefik with Let's Encrypt support"""
    # Implementation will be added
    console.print("[yellow]Traefik installation command coming soon[/yellow]")

@traefik.command()
def status():
    """Show Traefik status and configuration"""
    # Implementation will be added
    console.print("[yellow]Traefik status command coming soon[/yellow]")

@traefik.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--tail', type=int, default=100, help='Number of recent lines to show')
def logs(follow, tail):
    """View Traefik logs"""
    # Implementation will be added
    console.print("[yellow]Traefik logs command coming soon[/yellow]")

@traefik.command()
def dashboard():
    """Open Traefik dashboard in browser"""
    # Implementation will be added
    console.print("[yellow]Traefik dashboard command coming soon[/yellow]")

@traefik.command()
@click.option('--force', '-f', is_flag=True, help='Force restart without confirmation')
def restart(force):
    """Restart Traefik"""
    # Implementation will be added
    console.print("[yellow]Traefik restart command coming soon[/yellow]")

@traefik.command()
@click.option('--remove-data', is_flag=True, help='Also remove SSL certificates and data')
@click.option('--force', '-f', is_flag=True, help='Force removal without confirmation')
def remove(remove_data, force):
    """Remove Traefik installation"""
    # Implementation will be added
    console.print("[yellow]Traefik remove command coming soon[/yellow]")

# Domain Management Commands
@cli.group()
def domain():
    """Domain and subdomain management"""
    pass

@domain.command("set-default")
@click.argument('domain_name')
def set_default(domain_name):
    """Set the default domain for new deployments"""
    domain_manager = DomainManager()
    config_manager = get_config_manager()
    config_manager.set_value('default_domain', domain_name)
    console.print(f"[green]✓ Set default domain to: {domain_name}[/green]")

@domain.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def list_domains(output_format):
    """List all used domains and subdomains"""
    # Implementation will be added
    console.print("[yellow]Domain list command coming soon[/yellow]")

@domain.command()
@click.argument('domain_name')
def check(domain_name):
    """Check domain availability and DNS status"""
    domain_manager = DomainManager()
    result = domain_manager.validate_domain_availability(domain_name)
    if result['available']:
        console.print(f"[green]✓ Domain {domain_name} is available[/green]")
    else:
        console.print(f"[red]✗ Domain {domain_name} is not available[/red]")
        if result.get('error'):
            console.print(f"[yellow]Error: {result['error']}[/yellow]")

# Port Management Commands
@cli.group()
def ports():
    """Port allocation and conflict management"""
    pass

@ports.command('list')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def list_ports(output_format):
    """Show all port allocations"""
    # Implementation will be added
    console.print("[yellow]Port list command coming soon[/yellow]")

@ports.command()
def conflicts():
    """Check for port conflicts"""
    # Implementation will be added
    console.print("[yellow]Port conflicts command coming soon[/yellow]")

# SSL Certificate Management Commands
@cli.group()
def ssl():
    """SSL certificate management"""
    pass

@ssl.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def status(output_format):
    """Show SSL certificate status for all domains"""
    # Implementation will be added
    console.print("[yellow]SSL status command coming soon[/yellow]")

@ssl.command()
@click.argument('domain')
def renew(domain):
    """Force renewal of SSL certificate for a domain"""
    # Implementation will be added
    console.print("[yellow]SSL renew command coming soon[/yellow]")

@ssl.command('test')
@click.argument('domain')
def test_ssl(domain):
    """Test SSL configuration for a domain"""
    # Implementation will be added
    console.print("[yellow]SSL test command coming soon[/yellow]")

# Migration Commands
@cli.group()
def migrate():
    """Migration tools for Traefik integration"""
    pass

@migrate.command("to-traefik")
@click.argument('project_name', required=False)
@click.option('--all', 'migrate_all', is_flag=True, help='Migrate all compatible projects')
@click.option('--dry-run', is_flag=True, help='Show what would be done')
def to_traefik(project_name, migrate_all, dry_run):
    """Migrate project(s) to use Traefik reverse proxy"""
    # Implementation will be added
    console.print("[yellow]Migration to Traefik command coming soon[/yellow]")

@migrate.command()
@click.argument('project_name')
def rollback(project_name):
    """Rollback a Traefik migration"""
    # Implementation will be added
    console.print("[yellow]Migration rollback command coming soon[/yellow]")

# Add all command groups
cli.add_command(deploy_group)
cli.add_command(marketplace_group)
cli.add_command(monitoring_group)
cli.add_command(templates_group)
cli.add_command(diagnostics_group)
cli.add_command(security_group)
cli.add_command(performance_group)
cli.add_command(config_group)

def main():
    """Main entry point with global exception handling"""
    try:
        cli()
    except (KeyboardInterrupt, click.exceptions.Abort, EOFError):
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {str(e)}[/red]")
        console.print("[dim]Check logs for more details[/dim]")
        logger.exception("Unexpected error in CLI")
        sys.exit(1)

if __name__ == '__main__':
    main()
