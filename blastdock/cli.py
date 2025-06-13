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
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

# Import version and system info
from ._version import __version__, get_system_info, check_python_version

# Import core modules
from .core.template_manager import TemplateManager
from .core.deployment_manager import DeploymentManager
from .core.monitor import Monitor
from .core.config import get_config_manager, get_config

# Import utilities
from .utils.logging import get_logger, initialize_logging, log_exception
from .utils.filesystem import paths, initialize_directories
from .utils.validators import InputValidator

# Import exceptions
from .exceptions import (
    BlastDockError, TemplateNotFoundError, ProjectNotFoundError,
    ConfigurationError, ValidationError, TraefikError, TraefikNotInstalledError,
    TraefikNotRunningError, DomainError, DomainNotAvailableError,
    SSLError, PortError, MigrationError
)

# Import Traefik modules
from .traefik.manager import TraefikManager
from .traefik.installer import TraefikInstaller
from .traefik.ssl import SSLManager
from .domains.manager import DomainManager
from .ports.manager import PortManager
from .migration.traefik_migrator import TraefikMigrator

# Initialize console
console = Console()

# Global logger (will be initialized in CLI setup)
logger = None


def signal_handler(signum, frame):
    """Handle keyboard interrupt signals gracefully"""
    console.print("\n[yellow]Operation cancelled by user[/yellow]")
    sys.exit(130)  # Standard exit code for SIGINT


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


def handle_exception(e: Exception, command: str = "command"):
    """Centralized exception handling"""
    if isinstance(e, BlastDockError):
        logger.error(f"{command} failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        if isinstance(e, (TemplateNotFoundError, ProjectNotFoundError)):
            sys.exit(2)  # Not found
        else:
            sys.exit(1)  # General error
    else:
        logger.error(f"Unexpected error in {command}: {e}", exc_info=True)
        console.print(f"[red]Unexpected error: {e}[/red]")
        console.print("[dim]Check logs for more details[/dim]")
        sys.exit(1)


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
    
    Simplify Docker application deployment with pre-built templates.
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


@cli.command()
@click.argument('template_name')
@click.option('--interactive', '-i', is_flag=True, help='Interactive configuration mode')
@click.option('--name', help='Project name (skip prompt)')
@click.option('--domain', help='Custom domain for Traefik routing')
@click.option('--subdomain', help='Custom subdomain for Traefik routing')
@click.option('--ssl/--no-ssl', default=None, help='Enable/disable SSL certificates')
@click.option('--traefik/--no-traefik', default=None, help='Enable/disable Traefik integration')
@click.pass_context
def init(ctx, template_name, interactive, name, domain, subdomain, ssl, traefik):
    """Initialize a new deployment from a template"""
    try:
        template_manager = TemplateManager()
        
        # Validate template exists
        if not template_manager.template_exists(template_name):
            available_templates = template_manager.list_templates()
            console.print(f"[red]Template '{template_name}' not found![/red]")
            
            if available_templates:
                console.print("\n[bold]Available templates:[/bold]")
                for template in available_templates:
                    info = template_manager.get_template_info(template)
                    description = info.get('description', 'No description')
                    console.print(f"  [cyan]{template}[/cyan] - {description}")
            else:
                console.print("[yellow]No templates available[/yellow]")
            
            raise TemplateNotFoundError(template_name)
        
        # Get project name
        if name:
            project_name = name
        else:
            project_name = click.prompt("Enter project name", type=str)
        
        # Validate project name
        is_valid, error = InputValidator.validate_project_name(project_name)
        if not is_valid:
            raise ValidationError(f"Invalid project name: {error}")
        
        # Check Traefik availability
        traefik_manager = TraefikManager()
        traefik_available = traefik_manager.is_running()
        
        # Determine Traefik integration settings
        if traefik is None:
            # Auto-detect based on Traefik availability
            use_traefik = traefik_available
        else:
            use_traefik = traefik
        
        if use_traefik and not traefik_available:
            console.print("[yellow]Warning: Traefik integration requested but Traefik is not running[/yellow]")
            console.print("[dim]You can install Traefik with: blastdock traefik install[/dim]")
            if not click.confirm("Continue without Traefik integration?"):
                return
            use_traefik = False
        
        # Get configuration
        if interactive:
            console.print(f"[bold]Configuring {template_name} template...[/bold]")
            config = template_manager.interactive_config(template_name)
            
            # Interactive Traefik configuration
            if use_traefik:
                console.print(f"\n[bold]Traefik Configuration:[/bold]")
                if not domain and not subdomain:
                    subdomain = click.prompt("Subdomain (leave empty for auto-generated)", 
                                           default="", show_default=False)
                    if not subdomain:
                        subdomain = None
                
                if ssl is None:
                    ssl = click.confirm("Enable SSL certificates?", default=True)
        else:
            config = template_manager.get_default_config(template_name)
        
        # Set up domain/subdomain for Traefik
        if use_traefik:
            domain_manager = DomainManager()
            
            if domain:
                # Validate and reserve custom domain
                if not domain_manager.reserve_domain(domain, project_name):
                    console.print(f"[red]Failed to reserve domain: {domain}[/red]")
                    return
            elif subdomain:
                # Reserve specific subdomain
                if not domain_manager.reserve_subdomain(subdomain, project_name):
                    console.print(f"[red]Failed to reserve subdomain: {subdomain}[/red]")
                    return
            else:
                # Generate and reserve subdomain
                subdomain = domain_manager.generate_subdomain(project_name)
                if not domain_manager.reserve_subdomain(subdomain, project_name):
                    console.print(f"[red]Failed to reserve generated subdomain: {subdomain}[/red]")
                    return
            
            # Set SSL default
            if ssl is None:
                ssl = True  # Default to SSL when using Traefik
        
        # Create enhanced configuration with Traefik settings
        enhanced_config = config.copy()
        if use_traefik:
            enhanced_config['traefik'] = {
                'enabled': True,
                'domain': domain,
                'subdomain': subdomain,
                'ssl_enabled': ssl
            }
        
        # Create deployment
        deployment_manager = DeploymentManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Creating project '{project_name}'...", total=None)
            deployment_manager.create_deployment(project_name, template_name, enhanced_config)
        
        # Success message
        console.print(f"[green]✓ Successfully created project '{project_name}'[/green]")
        console.print(f"[dim]Location: {paths.get_project_path(project_name)}[/dim]")
        
        # Show Traefik information
        if use_traefik:
            if domain:
                protocol = "https" if ssl else "http"
                console.print(f"[dim]Domain: {protocol}://{domain}[/dim]")
            elif subdomain:
                default_domain = DomainManager().get_default_domain()
                full_domain = f"{subdomain}.{default_domain}"
                protocol = "https" if ssl else "http"
                console.print(f"[dim]URL: {protocol}://{full_domain}[/dim]")
            
            if ssl:
                console.print("[dim]SSL certificates will be automatically provisioned[/dim]")
        
        console.print(f"\n[bold]Next steps:[/bold]")
        console.print(f"  blastdock deploy {project_name}")
        
        logger.info(f"Successfully initialized project '{project_name}' with template '{template_name}'")
        
    except (KeyboardInterrupt, click.exceptions.Abort, EOFError):
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        handle_exception(e, "init")


@cli.command()
@click.argument('project_name')
@click.option('--force', '-f', is_flag=True, help='Force deployment without confirmation')
@click.option('--enable-ssl', is_flag=True, help='Enable SSL for Traefik integration')
@click.option('--domain', help='Override domain for Traefik routing')
@click.pass_context
def deploy(ctx, project_name, force, enable_ssl, domain):
    """Deploy an application"""
    try:
        deployment_manager = DeploymentManager()
        
        # Check if project exists
        if not deployment_manager.project_exists(project_name):
            available_projects = deployment_manager.list_projects()
            console.print(f"[red]Project '{project_name}' not found![/red]")
            
            if available_projects:
                console.print("\n[bold]Available projects:[/bold]")
                for project in available_projects[:5]:  # Show first 5
                    console.print(f"  [cyan]{project}[/cyan]")
                if len(available_projects) > 5:
                    console.print(f"  [dim]... and {len(available_projects) - 5} more[/dim]")
            
            raise ProjectNotFoundError(project_name)
        
        # Get configuration for confirmation prompts
        config_manager = get_config_manager(ctx.obj['profile'])
        
        # Confirmation prompt
        if not force and config_manager.should_confirm_destructive_operations():
            if not click.confirm(f"Deploy project '{project_name}'?"):
                console.print("[yellow]Deployment cancelled[/yellow]")
                return
        
        # Deploy with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Deploying '{project_name}'...", total=None)
            deployment_manager.deploy(project_name)
        
        # Success message
        console.print(f"[green]✓ Successfully deployed '{project_name}'[/green]")
        
        # Show status
        monitor = Monitor()
        status = monitor.get_status(project_name)
        console.print(f"[dim]Status: {status}[/dim]")
        
        # Show Traefik access information
        try:
            domain_manager = DomainManager()
            project_domains = domain_manager.get_project_domains(project_name)
            
            if project_domains['custom_domains'] or project_domains['subdomains']:
                console.print(f"\n[bold]Access URLs:[/bold]")
                
                for custom_domain in project_domains['custom_domains']:
                    protocol = "https" if enable_ssl else "http"
                    console.print(f"  {protocol}://{custom_domain}")
                
                for subdomain in project_domains['subdomains']:
                    default_domain = domain_manager.get_default_domain()
                    full_domain = f"{subdomain}.{default_domain}"
                    protocol = "https" if enable_ssl else "http"
                    console.print(f"  {protocol}://{full_domain}")
        except Exception as e:
            logger.debug(f"Could not show Traefik access information: {e}")
        
        logger.info(f"Successfully deployed project '{project_name}'")
        
    except (KeyboardInterrupt, click.exceptions.Abort, EOFError):
        console.print("\n[yellow]Deployment cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        handle_exception(e, "deploy")


@cli.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def list(ctx, output_format):
    """List all deployments"""
    try:
        deployment_manager = DeploymentManager()
        projects = deployment_manager.list_projects()
        
        if not projects:
            console.print("[yellow]No deployments found[/yellow]")
            console.print("[dim]Use 'blastdock init <template>' to create your first deployment[/dim]")
            return
        
        if output_format == 'json':
            import json
            project_data = []
            monitor = Monitor()
            
            for project in projects:
                try:
                    status = monitor.get_status(project)
                    template = deployment_manager.get_project_template(project)
                    created = deployment_manager.get_project_created_date(project)
                    
                    project_data.append({
                        'name': project,
                        'status': status,
                        'template': template,
                        'created': created
                    })
                except Exception as e:
                    logger.warning(f"Failed to get info for project {project}: {e}")
                    project_data.append({
                        'name': project,
                        'status': 'unknown',
                        'template': 'unknown',
                        'created': 'unknown'
                    })
            
            console.print(json.dumps(project_data, indent=2))
        else:
            # Table format
            table = Table(title="BlastDock Deployments")
            table.add_column("Project Name", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Template", style="blue")
            table.add_column("Created", style="magenta")
            
            monitor = Monitor()
            for project in projects:
                try:
                    status = monitor.get_status(project)
                    template = deployment_manager.get_project_template(project)
                    created = deployment_manager.get_project_created_date(project)
                    
                    # Color code status
                    if status.lower() in ['running', 'up']:
                        status_display = f"[green]{status}[/green]"
                    elif status.lower() in ['stopped', 'down']:
                        status_display = f"[red]{status}[/red]"
                    else:
                        status_display = f"[yellow]{status}[/yellow]"
                    
                    table.add_row(project, status_display, template, created)
                except Exception as e:
                    logger.warning(f"Failed to get info for project {project}: {e}")
                    table.add_row(project, "[red]error[/red]", "unknown", "unknown")
            
            console.print(table)
        
        logger.debug(f"Listed {len(projects)} projects")
        
    except Exception as e:
        handle_exception(e, "list")


@cli.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.pass_context
def templates(ctx, output_format):
    """List available templates"""
    try:
        template_manager = TemplateManager()
        available_templates = template_manager.list_templates()
        
        if not available_templates:
            console.print("[yellow]No templates available[/yellow]")
            return
        
        if output_format == 'json':
            import json
            template_data = []
            
            for template in available_templates:
                try:
                    info = template_manager.get_template_info(template)
                    template_data.append({
                        'name': template,
                        'description': info.get('description', 'No description'),
                        'version': info.get('version', 'unknown'),
                        'services': info.get('services', [])
                    })
                except Exception as e:
                    logger.warning(f"Failed to get info for template {template}: {e}")
                    template_data.append({
                        'name': template,
                        'description': 'Error loading template info',
                        'version': 'unknown',
                        'services': []
                    })
            
            console.print(json.dumps(template_data, indent=2))
        else:
            # Table format
            table = Table(title="Available Templates")
            table.add_column("Template", style="cyan", no_wrap=True)
            table.add_column("Description", style="white")
            table.add_column("Services", style="blue")
            table.add_column("Version", style="magenta")
            
            for template in available_templates:
                try:
                    info = template_manager.get_template_info(template)
                    description = info.get('description', 'No description')
                    version = info.get('version', 'unknown')
                    services = ', '.join(info.get('services', []))
                    
                    table.add_row(template, description, services, version)
                except Exception as e:
                    logger.warning(f"Failed to get info for template {template}: {e}")
                    table.add_row(template, "Error loading template info", "", "unknown")
            
            console.print(table)
        
        logger.debug(f"Listed {len(available_templates)} templates")
        
    except Exception as e:
        handle_exception(e, "templates")


@cli.command()
@click.argument('project_name')
@click.pass_context 
def status(ctx, project_name):
    """Check deployment status"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            raise ProjectNotFoundError(project_name)
        
        monitor = Monitor()
        status_text = monitor.get_detailed_status(project_name)
        
        # Display the status (it's already a Rich Text object with formatting)
        console.print(Panel(
            status_text,
            title=f"Status: {project_name}",
            border_style="blue"
        ))
        
        logger.debug(f"Retrieved status for project '{project_name}'")
        
    except Exception as e:
        handle_exception(e, "status")


@cli.command()
@click.argument('project_name')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--service', '-s', help='Show logs for specific service')
@click.option('--tail', type=int, default=50, help='Number of recent lines to show')
@click.pass_context
def logs(ctx, project_name, follow, service, tail):
    """View deployment logs"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            raise ProjectNotFoundError(project_name)
        
        monitor = Monitor()
        
        if follow:
            console.print(f"[dim]Following logs for '{project_name}' (Ctrl+C to stop)[/dim]")
            monitor.follow_logs(project_name, service)
        else:
            logs = monitor.get_logs(project_name, service, tail=tail)
            if logs:
                console.print(logs)
            else:
                console.print("[yellow]No logs available[/yellow]")
        
        logger.debug(f"Retrieved logs for project '{project_name}'")
        
    except (KeyboardInterrupt, click.exceptions.Abort, EOFError):
        console.print("\n[dim]Log following stopped[/dim]")
        sys.exit(130)
    except Exception as e:
        handle_exception(e, "logs")


@cli.command()
@click.argument('project_name')
@click.option('--force', '-f', is_flag=True, help='Force stop without confirmation')
@click.pass_context
def stop(ctx, project_name, force):
    """Stop a deployment"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            raise ProjectNotFoundError(project_name)
        
        # Get configuration for confirmation prompts
        config_manager = get_config_manager(ctx.obj['profile'])
        
        # Confirmation prompt
        if not force and config_manager.should_confirm_destructive_operations():
            if not click.confirm(f"Stop project '{project_name}'?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        
        # Stop with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Stopping '{project_name}'...", total=None)
            deployment_manager.stop(project_name)
        
        console.print(f"[green]✓ Successfully stopped '{project_name}'[/green]")
        logger.info(f"Successfully stopped project '{project_name}'")
        
    except (KeyboardInterrupt, click.exceptions.Abort, EOFError):
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        handle_exception(e, "stop")


@cli.command()
@click.argument('project_name')
@click.option('--force', '-f', is_flag=True, help='Force removal without confirmation')
@click.option('--keep-data', is_flag=True, help='Keep data volumes')
@click.pass_context
def remove(ctx, project_name, force, keep_data):
    """Remove a deployment"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            raise ProjectNotFoundError(project_name)
        
        # Get configuration for confirmation prompts
        config_manager = get_config_manager(ctx.obj['profile'])
        
        # Confirmation prompt
        if not force and config_manager.should_confirm_destructive_operations():
            console.print(f"[red]Warning: This will permanently remove '{project_name}'[/red]")
            if not keep_data:
                console.print("[red]This will also remove all data volumes![/red]")
            
            if not click.confirm(f"Remove project '{project_name}'?"):
                console.print("[yellow]Operation cancelled[/yellow]")
                return
        
        # Remove with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(f"Removing '{project_name}'...", total=None)
            deployment_manager.remove(project_name, keep_data=keep_data)
        
        console.print(f"[green]✓ Successfully removed '{project_name}'[/green]")
        logger.info(f"Successfully removed project '{project_name}' (keep_data={keep_data})")
        
    except (KeyboardInterrupt, click.exceptions.Abort, EOFError):
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        handle_exception(e, "remove")


@cli.command()
@click.argument('project_name')
@click.pass_context
def config(ctx, project_name):
    """Show project configuration"""
    try:
        deployment_manager = DeploymentManager()
        
        if not deployment_manager.project_exists(project_name):
            raise ProjectNotFoundError(project_name)
        
        config_data = deployment_manager.get_project_config(project_name)
        
        # Create configuration panel
        panel_content = []
        
        for key, value in config_data.items():
            if isinstance(value, dict):
                panel_content.append(f"[bold]{key}:[/bold]")
                for sub_key, sub_value in value.items():
                    panel_content.append(f"  {sub_key}: {sub_value}")
            else:
                panel_content.append(f"[bold]{key}:[/bold] {value}")
        
        console.print(Panel(
            "\n".join(panel_content),
            title=f"Configuration: {project_name}",
            border_style="blue"
        ))
        
        logger.debug(f"Retrieved configuration for project '{project_name}'")
        
    except Exception as e:
        handle_exception(e, "config")


@cli.command()
@click.pass_context
def version(ctx):
    """Show version and system information"""
    try:
        system_info = get_system_info()
        
        # Create version panel
        panel_content = []
        panel_content.append(f"[bold]BlastDock Version:[/bold] {system_info['blastdock_version']}")
        panel_content.append(f"[bold]Python Version:[/bold] {system_info['python_version']}")
        panel_content.append(f"[bold]Platform:[/bold] {system_info['platform']}")
        panel_content.append(f"[bold]Architecture:[/bold] {system_info['architecture']}")
        panel_content.append(f"[bold]System:[/bold] {system_info['system']}")
        
        # Add configuration info
        try:
            config_manager = get_config_manager(ctx.obj['profile'])
            panel_content.append(f"\n[bold]Configuration Profile:[/bold] {ctx.obj['profile']}")
            panel_content.append(f"[bold]Config Directory:[/bold] {paths.config_dir}")
            panel_content.append(f"[bold]Data Directory:[/bold] {paths.data_dir}")
            panel_content.append(f"[bold]Log Directory:[/bold] {paths.log_dir}")
        except Exception:
            pass
        
        console.print(Panel(
            "\n".join(panel_content),
            title="BlastDock System Information",
            border_style="green"
        ))
        
    except Exception as e:
        handle_exception(e, "version")


# Traefik Management Commands
@cli.group()
def traefik():
    """Traefik reverse proxy management"""
    pass


@traefik.command()
@click.option('--email', required=True, help='Email for Let\'s Encrypt certificates')
@click.option('--domain', default='blastdock.local', help='Default domain for deployments')
@click.option('--dashboard/--no-dashboard', default=True, help='Enable Traefik dashboard')
@click.option('--dashboard-domain', help='Custom domain for Traefik dashboard')
@click.pass_context
def install(ctx, email, domain, dashboard, dashboard_domain):
    """Install Traefik with Let's Encrypt support"""
    try:
        installer = TraefikInstaller()
        
        # Check requirements
        console.print("[dim]Checking installation requirements...[/dim]")
        requirements_ok, issues = installer.check_installation_requirements()
        
        if not requirements_ok:
            console.print("[red]Installation requirements not met:[/red]")
            for issue in issues:
                console.print(f"  • {issue}")
            return
        
        console.print("[green]✓ Requirements check passed[/green]")
        
        # Confirm installation
        if not click.confirm(f"Install Traefik with domain '{domain}'?"):
            console.print("[yellow]Installation cancelled[/yellow]")
            return
        
        # Install Traefik
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Installing Traefik...", total=None)
            success = installer.install(email, domain, dashboard, dashboard_domain)
        
        if success:
            console.print("[green]✓ Traefik installed successfully[/green]")
            
            # Show access information
            traefik_manager = TraefikManager()
            dashboard_url = traefik_manager.get_dashboard_url()
            if dashboard_url:
                console.print(f"[dim]Dashboard: {dashboard_url}[/dim]")
            
        else:
            console.print("[red]✗ Traefik installation failed[/red]")
            console.print("[dim]Check logs for more details[/dim]")
    
    except Exception as e:
        handle_exception(e, "traefik install")


@traefik.command()
def status():
    """Show Traefik status and configuration"""
    try:
        traefik_manager = TraefikManager()
        status = traefik_manager.get_status()
        
        # Create status panel
        panel_content = []
        
        # Basic status
        if status['running']:
            panel_content.append("[green]✓ Running[/green]")
        elif status['installed']:
            panel_content.append("[yellow]⚠ Installed but not running[/yellow]")
        else:
            panel_content.append("[red]✗ Not installed[/red]")
        
        if status['version']:
            panel_content.append(f"[bold]Version:[/bold] {status['version']}")
        
        if status['uptime']:
            panel_content.append(f"[bold]Uptime:[/bold] {status['uptime']}")
        
        panel_content.append(f"[bold]Services:[/bold] {status['services_count']}")
        panel_content.append(f"[bold]Network:[/bold] {'✓' if status['network_exists'] else '✗'}")
        
        if status['dashboard_url']:
            panel_content.append(f"[bold]Dashboard:[/bold] {status['dashboard_url']}")
        
        # SSL certificates
        if status['ssl_certificates']:
            panel_content.append(f"\n[bold]SSL Certificates:[/bold]")
            for cert in status['ssl_certificates'][:3]:  # Show first 3
                panel_content.append(f"  • {cert['domain']}")
            if len(status['ssl_certificates']) > 3:
                panel_content.append(f"  ... and {len(status['ssl_certificates']) - 3} more")
        
        console.print(Panel(
            "\n".join(panel_content),
            title="Traefik Status",
            border_style="blue"
        ))
    
    except Exception as e:
        handle_exception(e, "traefik status")


@traefik.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--tail', type=int, default=100, help='Number of recent lines to show')
def logs(follow, tail):
    """View Traefik logs"""
    try:
        traefik_manager = TraefikManager()
        
        if not traefik_manager.is_running():
            console.print("[red]Traefik is not running[/red]")
            return
        
        if follow:
            console.print("[dim]Following Traefik logs (Ctrl+C to stop)[/dim]")
        
        logs_output = traefik_manager.get_logs(follow=follow, tail=tail)
        console.print(logs_output)
    
    except (KeyboardInterrupt, click.exceptions.Abort, EOFError):
        console.print("\n[dim]Log following stopped[/dim]")
        sys.exit(130)
    except Exception as e:
        handle_exception(e, "traefik logs")


@traefik.command()
def dashboard():
    """Open Traefik dashboard in browser"""
    try:
        traefik_manager = TraefikManager()
        dashboard_url = traefik_manager.get_dashboard_url()
        
        if not dashboard_url:
            console.print("[red]Traefik dashboard is not accessible[/red]")
            return
        
        console.print(f"Opening dashboard: {dashboard_url}")
        
        # Try to open in browser
        import webbrowser
        webbrowser.open(dashboard_url)
    
    except Exception as e:
        handle_exception(e, "traefik dashboard")


@traefik.command()
@click.option('--force', '-f', is_flag=True, help='Force restart without confirmation')
def restart(force):
    """Restart Traefik"""
    try:
        traefik_manager = TraefikManager()
        
        if not force:
            if not click.confirm("Restart Traefik? This may cause brief service interruption."):
                console.print("[yellow]Restart cancelled[/yellow]")
                return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Restarting Traefik...", total=None)
            success = traefik_manager.restart()
        
        if success:
            console.print("[green]✓ Traefik restarted successfully[/green]")
        else:
            console.print("[red]✗ Failed to restart Traefik[/red]")
    
    except Exception as e:
        handle_exception(e, "traefik restart")


@traefik.command()
@click.option('--remove-data', is_flag=True, help='Also remove SSL certificates and data')
@click.option('--force', '-f', is_flag=True, help='Force removal without confirmation')
def remove(remove_data, force):
    """Remove Traefik installation"""
    try:
        if not force:
            console.print("[red]Warning: This will remove Traefik and may affect running deployments[/red]")
            if remove_data:
                console.print("[red]This will also remove all SSL certificates![/red]")
            
            if not click.confirm("Continue with removal?"):
                console.print("[yellow]Removal cancelled[/yellow]")
                return
        
        traefik_manager = TraefikManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Removing Traefik...", total=None)
            success = traefik_manager.remove(remove_data=remove_data)
        
        if success:
            console.print("[green]✓ Traefik removed successfully[/green]")
        else:
            console.print("[red]✗ Failed to remove Traefik[/red]")
    
    except Exception as e:
        handle_exception(e, "traefik remove")


# Domain Management Commands
@cli.group()
def domain():
    """Domain and subdomain management"""
    pass


@domain.command("set-default")
@click.argument('domain_name')
def set_default(domain_name):
    """Set the default domain for new deployments"""
    try:
        domain_manager = DomainManager()
        
        if domain_manager.set_default_domain(domain_name):
            console.print(f"[green]✓ Set default domain to: {domain_name}[/green]")
        else:
            console.print(f"[red]✗ Failed to set default domain[/red]")
    
    except Exception as e:
        handle_exception(e, "domain set-default")


@domain.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def list(output_format):
    """List all used domains and subdomains"""
    try:
        domain_manager = DomainManager()
        domains_data = domain_manager.list_all_domains()
        
        if output_format == 'json':
            import json
            console.print(json.dumps(domains_data, indent=2))
        else:
            # Subdomains table
            if domains_data['subdomains']:
                table = Table(title="Used Subdomains")
                table.add_column("Subdomain", style="cyan")
                table.add_column("Full Domain", style="blue")
                table.add_column("Project", style="green")
                table.add_column("Reserved", style="magenta")
                
                for subdomain in domains_data['subdomains']:
                    table.add_row(
                        subdomain['name'],
                        subdomain['full_domain'],
                        subdomain['project'],
                        subdomain['reserved_at']
                    )
                
                console.print(table)
            
            # Custom domains table
            if domains_data['custom_domains']:
                table = Table(title="Custom Domains")
                table.add_column("Domain", style="cyan")
                table.add_column("Project", style="green")
                table.add_column("Reserved", style="magenta")
                
                for domain in domains_data['custom_domains']:
                    table.add_row(
                        domain['name'],
                        domain['project'],
                        domain['reserved_at']
                    )
                
                console.print(table)
            
            # Reserved subdomains
            if domains_data['reserved_subdomains']:
                console.print(f"\n[bold]Reserved subdomains:[/bold] {', '.join(domains_data['reserved_subdomains'])}")
            
            if not any([domains_data['subdomains'], domains_data['custom_domains']]):
                console.print("[yellow]No domains or subdomains in use[/yellow]")
    
    except Exception as e:
        handle_exception(e, "domain list")


@domain.command()
@click.argument('domain_name')
def check(domain_name):
    """Check domain availability and DNS status"""
    try:
        from .domains.validator import DomainValidator
        
        validator = DomainValidator()
        domain_info = validator.get_domain_info(domain_name)
        
        # Create info panel
        panel_content = []
        panel_content.append(f"[bold]Domain:[/bold] {domain_info['domain']}")
        panel_content.append(f"[bold]Valid Format:[/bold] {'✓' if domain_info['valid'] else '✗'}")
        panel_content.append(f"[bold]DNS Resolution:[/bold] {'✓' if domain_info['resolves'] else '✗'}")
        
        if domain_info['ip_address']:
            panel_content.append(f"[bold]IP Address:[/bold] {domain_info['ip_address']}")
        
        if domain_info['error']:
            panel_content.append(f"[bold]Error:[/bold] {domain_info['error']}")
        
        if domain_info['suggestions']:
            panel_content.append(f"\n[bold]Suggestions:[/bold]")
            for suggestion in domain_info['suggestions']:
                panel_content.append(f"  • {suggestion}")
        
        border_style = "green" if domain_info['valid'] else "red"
        console.print(Panel(
            "\n".join(panel_content),
            title="Domain Information",
            border_style=border_style
        ))
    
    except Exception as e:
        handle_exception(e, "domain check")


# Port Management Commands
@cli.group()
def ports():
    """Port allocation and conflict management"""
    pass


@ports.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def list(output_format):
    """Show all port allocations"""
    try:
        port_manager = PortManager()
        ports_data = port_manager.list_all_ports()
        
        if output_format == 'json':
            import json
            console.print(json.dumps(ports_data, indent=2, default=str))
        else:
            # Allocated ports
            if ports_data['allocated']:
                table = Table(title="Allocated Ports")
                table.add_column("Port", style="cyan")
                table.add_column("Project", style="green")
                table.add_column("Service", style="blue")
                table.add_column("In Use", style="magenta")
                
                for port_info in ports_data['allocated']:
                    in_use = "✓" if port_info['in_use'] else "✗"
                    table.add_row(
                        str(port_info['port']),
                        port_info['project'],
                        port_info['service'],
                        in_use
                    )
                
                console.print(table)
            
            # Summary
            summary = port_manager.get_port_usage_summary()
            console.print(f"\n[bold]Summary:[/bold]")
            console.print(f"  Allocated: {summary['allocated_ports']}")
            console.print(f"  Reserved: {summary['reserved_ports']}")
            console.print(f"  Available in range: {summary['available_in_range']}")
            console.print(f"  Range utilization: {summary['utilization_percentage']:.1f}%")
    
    except Exception as e:
        handle_exception(e, "ports list")


@ports.command()
def conflicts():
    """Check for port conflicts"""
    try:
        port_manager = PortManager()
        conflicts = port_manager.check_port_conflicts()
        
        if not conflicts:
            console.print("[green]✓ No port conflicts detected[/green]")
            return
        
        console.print(f"[red]Found {len(conflicts)} port conflicts:[/red]")
        
        for conflict in conflicts:
            panel_content = []
            panel_content.append(f"[bold]Port:[/bold] {conflict['port']}")
            panel_content.append(f"[bold]Type:[/bold] {conflict['type']}")
            
            if 'allocated_to' in conflict:
                allocated = conflict['allocated_to']
                panel_content.append(f"[bold]Allocated to:[/bold] {allocated['project']}/{allocated['service']}")
            
            if 'actual_usage' in conflict:
                usage = conflict['actual_usage']
                panel_content.append(f"[bold]Actually used by:[/bold] {usage.get('process', 'unknown')}")
            
            console.print(Panel(
                "\n".join(panel_content),
                title=f"Port Conflict: {conflict['port']}",
                border_style="red"
            ))
    
    except Exception as e:
        handle_exception(e, "ports conflicts")


@ports.command()
@click.argument('port', type=int)
@click.option('--reason', help='Reason for reservation')
def reserve(port, reason):
    """Reserve a specific port"""
    try:
        port_manager = PortManager()
        
        if port_manager.reserve_port(port, reason or "Manual reservation"):
            console.print(f"[green]✓ Reserved port {port}[/green]")
        else:
            console.print(f"[red]✗ Failed to reserve port {port}[/red]")
    
    except Exception as e:
        handle_exception(e, "ports reserve")


@ports.command()
@click.argument('port', type=int)
def release(port):
    """Release a reserved port"""
    try:
        port_manager = PortManager()
        
        if port_manager.unreserve_port(port):
            console.print(f"[green]✓ Released port {port}[/green]")
        else:
            console.print(f"[red]✗ Failed to release port {port}[/red]")
    
    except Exception as e:
        handle_exception(e, "ports release")


# Migration Commands
@cli.group()
def migrate():
    """Migration tools for Traefik integration"""
    pass


@migrate.command("to-traefik")
@click.argument('project_name', required=False)
@click.option('--domain', help='Custom domain for the project')
@click.option('--subdomain', help='Custom subdomain for the project')
@click.option('--ssl/--no-ssl', default=True, help='Enable SSL certificates')
@click.option('--dry-run', is_flag=True, help='Show what would be done without making changes')
@click.option('--all', 'migrate_all', is_flag=True, help='Migrate all compatible projects')
def to_traefik(project_name, domain, subdomain, ssl, dry_run, migrate_all):
    """Migrate project(s) to use Traefik reverse proxy"""
    try:
        migrator = TraefikMigrator()
        
        if migrate_all:
            console.print("[dim]Checking all projects for migration compatibility...[/dim]")
            result = migrator.migrate_all_projects_to_traefik(ssl_enabled=ssl, dry_run=dry_run)
            
            console.print(f"\n[bold]Migration Summary:[/bold]")
            console.print(f"  Total projects: {result['total_projects']}")
            console.print(f"  Migrated: {result['migrated_projects']}")
            console.print(f"  Failed: {result['failed_projects']}")
            console.print(f"  Skipped: {result['skipped_projects']}")
            
            if result['project_results']:
                for project, proj_result in result['project_results'].items():
                    if proj_result.get('success'):
                        console.print(f"  [green]✓ {project}[/green]")
                    elif proj_result.get('skipped'):
                        console.print(f"  [yellow]- {project} (skipped)[/yellow]")
                    else:
                        console.print(f"  [red]✗ {project}[/red]")
        
        elif project_name:
            if dry_run:
                console.print(f"[dim]Dry run: would migrate project '{project_name}'[/dim]")
            
            result = migrator.migrate_project_to_traefik(
                project_name=project_name,
                domain=domain,
                subdomain=subdomain,
                ssl_enabled=ssl,
                dry_run=dry_run
            )
            
            if result['success']:
                console.print(f"[green]✓ Successfully migrated {project_name} to Traefik[/green]")
                
                if result['changes_made'].get('subdomain'):
                    subdomain = result['changes_made']['subdomain']
                    default_domain = DomainManager().get_default_domain()
                    full_domain = f"{subdomain}.{default_domain}"
                    protocol = "https" if ssl else "http"
                    console.print(f"[dim]Access at: {protocol}://{full_domain}[/dim]")
            else:
                console.print(f"[red]✗ Failed to migrate {project_name}[/red]")
                for step in result['steps_failed']:
                    console.print(f"  • {step}")
        else:
            # Show compatibility report
            compatibility = migrator.check_migration_compatibility()
            
            console.print(f"[bold]Migration Compatibility Report[/bold]")
            console.print(f"Traefik ready: {'✓' if compatibility['traefik_ready'] else '✗'}")
            console.print(f"Total projects: {compatibility['total_projects']}")
            console.print(f"Compatible projects: {compatibility['compatible_projects']}")
            
            if compatibility['projects']:
                table = Table(title="Project Compatibility")
                table.add_column("Project", style="cyan")
                table.add_column("Compatible", style="green")
                table.add_column("Issues", style="red")
                
                for project, info in compatibility['projects'].items():
                    compatible = "✓" if info['compatible'] else "✗"
                    issues = ", ".join(info['issues']) if info['issues'] else "-"
                    table.add_row(project, compatible, issues)
                
                console.print(table)
            
            console.print(f"\n[dim]Use --all to migrate all compatible projects[/dim]")
            console.print(f"[dim]Use '<project_name>' to migrate a specific project[/dim]")
    
    except Exception as e:
        handle_exception(e, "migrate to-traefik")


@migrate.command()
@click.argument('project_name')
def rollback(project_name):
    """Rollback a Traefik migration"""
    try:
        migrator = TraefikMigrator()
        
        console.print(f"[yellow]Warning: This will rollback Traefik migration for {project_name}[/yellow]")
        if not click.confirm("Continue with rollback?"):
            console.print("[yellow]Rollback cancelled[/yellow]")
            return
        
        result = migrator.rollback_traefik_migration(project_name)
        
        if result['success']:
            console.print(f"[green]✓ Successfully rolled back {project_name}[/green]")
        else:
            console.print(f"[red]✗ Failed to rollback {project_name}[/red]")
            for step in result['steps_failed']:
                console.print(f"  • {step}")
    
    except Exception as e:
        handle_exception(e, "migrate rollback")


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
    try:
        ssl_manager = SSLManager()
        certificates = ssl_manager.list_all_certificates()
        
        if output_format == 'json':
            import json
            console.print(json.dumps(certificates, indent=2, default=str))
        else:
            if not certificates:
                console.print("[yellow]No SSL certificates found[/yellow]")
                return
            
            table = Table(title="SSL Certificates")
            table.add_column("Domain", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Expires", style="magenta")
            table.add_column("Days Left", style="yellow")
            
            for cert in certificates:
                status_text = "✓ Valid" if cert['is_valid'] else "✗ Invalid"
                expires_at = cert.get('expires_at', 'Unknown')
                days_left = cert.get('days_until_expiry', 'Unknown')
                
                # Color code days left
                if isinstance(days_left, int):
                    if days_left <= 7:
                        days_left = f"[red]{days_left}[/red]"
                    elif days_left <= 30:
                        days_left = f"[yellow]{days_left}[/yellow]"
                    else:
                        days_left = f"[green]{days_left}[/green]"
                
                table.add_row(cert['domain'], status_text, str(expires_at), str(days_left))
            
            console.print(table)
    
    except Exception as e:
        handle_exception(e, "ssl status")


@ssl.command()
@click.argument('domain')
def renew(domain):
    """Force renewal of SSL certificate for a domain"""
    try:
        ssl_manager = SSLManager()
        
        console.print(f"[dim]Forcing certificate renewal for {domain}...[/dim]")
        
        if ssl_manager.force_certificate_renewal(domain):
            console.print(f"[green]✓ Certificate renewal initiated for {domain}[/green]")
            console.print("[dim]Check status in a few minutes[/dim]")
        else:
            console.print(f"[red]✗ Failed to renew certificate for {domain}[/red]")
    
    except Exception as e:
        handle_exception(e, "ssl renew")


@ssl.command()
@click.argument('domain')
def test(domain):
    """Test SSL configuration for a domain"""
    try:
        ssl_manager = SSLManager()
        test_result = ssl_manager.test_ssl_configuration(domain)
        
        # Create test results panel
        panel_content = []
        panel_content.append(f"[bold]Domain:[/bold] {test_result['domain']}")
        panel_content.append(f"[bold]HTTPS Accessible:[/bold] {'✓' if test_result['https_accessible'] else '✗'}")
        panel_content.append(f"[bold]SSL Working:[/bold] {'✓' if test_result['ssl_working'] else '✗'}")
        panel_content.append(f"[bold]Certificate Valid:[/bold] {'✓' if test_result['certificate_valid'] else '✗'}")
        panel_content.append(f"[bold]Certificate Trusted:[/bold] {'✓' if test_result['certificate_trusted'] else '✗'}")
        
        if test_result['tls_version']:
            panel_content.append(f"[bold]TLS Version:[/bold] {test_result['tls_version']}")
        
        if test_result['cipher_suite']:
            panel_content.append(f"[bold]Cipher Suite:[/bold] {test_result['cipher_suite']}")
        
        if test_result['error']:
            panel_content.append(f"[bold]Error:[/bold] {test_result['error']}")
        
        border_style = "green" if test_result['ssl_working'] else "red"
        console.print(Panel(
            "\n".join(panel_content),
            title=f"SSL Test Results: {domain}",
            border_style=border_style
        ))
    
    except Exception as e:
        handle_exception(e, "ssl test")


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
        sys.exit(1)


if __name__ == '__main__':
    main()