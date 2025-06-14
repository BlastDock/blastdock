"""
Enhanced error handling and user-friendly error display system
"""

import sys
import os
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.columns import Columns
from rich.tree import Tree

from ..exceptions import (
    BlastDockError, ErrorSeverity, get_error_severity,
    DockerNotAvailableError, TraefikNotInstalledError, TraefikNotRunningError,
    TemplateNotFoundError, ProjectNotFoundError, PortConflictError,
    DomainNotAvailableError, SSLCertificateError
)
from .error_diagnostics import get_diagnostics, ErrorContext
from .logging import get_logger

logger = get_logger(__name__)
console = Console()


class EnhancedErrorHandler:
    """Enhanced error handler with user-friendly messaging and recovery suggestions"""
    
    def __init__(self, show_diagnostics: bool = False, auto_report: bool = False):
        """Initialize error handler
        
        Args:
            show_diagnostics: Show detailed diagnostic information
            auto_report: Automatically generate error reports
        """
        self.show_diagnostics = show_diagnostics
        self.auto_report = auto_report
        self.diagnostics = get_diagnostics()
        
        # Error message templates
        self.error_templates = {
            'DockerNotAvailableError': {
                'title': '🐳 Docker Not Available',
                'description': 'Docker daemon is not running or not accessible',
                'icon': '❌',
                'color': 'red'
            },
            'TraefikNotInstalledError': {
                'title': '🔀 Traefik Not Installed',
                'description': 'Traefik reverse proxy is required but not installed',
                'icon': '⚠️',
                'color': 'yellow'
            },
            'TraefikNotRunningError': {
                'title': '🔀 Traefik Not Running',
                'description': 'Traefik is installed but not currently running',
                'icon': '⚠️',
                'color': 'yellow'
            },
            'TemplateNotFoundError': {
                'title': '📄 Template Not Found',
                'description': 'The requested template could not be found',
                'icon': '❌',
                'color': 'red'
            },
            'ProjectNotFoundError': {
                'title': '📁 Project Not Found',
                'description': 'The requested project does not exist',
                'icon': '❌',
                'color': 'red'
            },
            'PortConflictError': {
                'title': '🔌 Port Conflict',
                'description': 'Port is already in use by another service',
                'icon': '⚠️',
                'color': 'yellow'
            },
            'DomainNotAvailableError': {
                'title': '🌐 Domain Not Available',
                'description': 'The requested domain cannot be used',
                'icon': '❌',
                'color': 'red'
            },
            'SSLCertificateError': {
                'title': '🔒 SSL Certificate Error',
                'description': 'SSL certificate operation failed',
                'icon': '⚠️',
                'color': 'yellow'
            }
        }
    
    def handle_error(self, 
                    exception: Exception,
                    operation_context: Dict[str, Any] = None,
                    exit_on_critical: bool = True) -> Optional[ErrorContext]:
        """Handle error with enhanced user experience
        
        Args:
            exception: The exception to handle
            operation_context: Context information about the operation
            exit_on_critical: Whether to exit on critical errors
            
        Returns:
            ErrorContext if error was handled, None if application should exit
        """
        
        # Diagnose the error
        error_context = self.diagnostics.diagnose_error(exception, operation_context)
        
        # Display user-friendly error message
        self._display_error_message(error_context, exception)
        
        # Show solutions and recovery options
        self._display_solutions(error_context)
        
        # Show diagnostics if requested
        if self.show_diagnostics:
            self._display_diagnostics(error_context)
        
        # Generate error report if requested
        if self.auto_report:
            self._generate_error_report(error_context)
        
        # Handle critical errors
        if error_context.severity == ErrorSeverity.CRITICAL and exit_on_critical:
            self._handle_critical_error(error_context)
            return None
        
        return error_context
    
    def _display_error_message(self, error_context: ErrorContext, exception: Exception):
        """Display user-friendly error message"""
        
        # Get error template
        error_type = error_context.error_type
        template = self.error_templates.get(error_type, {
            'title': f'⚠️ {error_type}',
            'description': 'An error occurred',
            'icon': '❌',
            'color': 'red'
        })
        
        # Create main error panel
        error_content = []
        
        # Error description
        error_content.append(f"[bold]{template['description']}[/bold]")
        error_content.append("")
        
        # Error message
        error_content.append(f"[dim]Error Message:[/dim]")
        error_content.append(f"  {error_context.error_message}")
        
        # Context information
        if error_context.project_name:
            error_content.append("")
            error_content.append(f"[dim]Project:[/dim] {error_context.project_name}")
        
        if error_context.template_name:
            error_content.append(f"[dim]Template:[/dim] {error_context.template_name}")
        
        if error_context.operation:
            error_content.append(f"[dim]Operation:[/dim] {error_context.operation}")
        
        # Error ID for support
        error_content.append("")
        error_content.append(f"[dim]Error ID:[/dim] [cyan]{error_context.error_id}[/cyan]")
        
        # Create panel
        console.print(Panel(
            "\n".join(error_content),
            title=f"{template['icon']} {template['title']}",
            border_style=template['color'],
            expand=False
        ))
    
    def _display_solutions(self, error_context: ErrorContext):
        """Display solution suggestions"""
        
        if not error_context.suggested_solutions:
            return
        
        console.print("\n[bold blue]💡 Suggested Solutions[/bold blue]")
        
        # Create solution tree
        tree = Tree("🔧 Recovery Options", style="blue")
        
        # Immediate solutions
        immediate_branch = tree.add("⚡ Immediate Actions", style="yellow")
        for i, solution in enumerate(error_context.suggested_solutions[:3], 1):
            immediate_branch.add(f"{i}. {solution}")
        
        # Additional solutions
        if len(error_context.suggested_solutions) > 3:
            additional_branch = tree.add("🔍 Additional Options", style="cyan")
            for i, solution in enumerate(error_context.suggested_solutions[3:], 4):
                additional_branch.add(f"{i}. {solution}")
        
        # Recovery commands
        if error_context.recovery_commands:
            commands_branch = tree.add("⌨️ Recovery Commands", style="green")
            for command in error_context.recovery_commands[:5]:
                commands_branch.add(f"[code]{command}[/code]")
        
        console.print(tree)
    
    def _display_diagnostics(self, error_context: ErrorContext):
        """Display diagnostic information"""
        
        console.print("\n[bold yellow]🔍 System Diagnostics[/bold yellow]")
        
        # System status table
        status_table = Table(title="System Status", show_header=True, header_style="bold magenta")
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("Details")
        
        # Docker status
        if error_context.docker_status:
            docker_status = error_context.docker_status
            if docker_status.get('available'):
                status_table.add_row(
                    "Docker",
                    "✅ Available",
                    f"Containers: {docker_status.get('containers_running', 0)}/{docker_status.get('containers_total', 0)}"
                )
            else:
                status_table.add_row(
                    "Docker",
                    "❌ Unavailable",
                    docker_status.get('error', 'Not running')
                )
        
        # Traefik status
        if error_context.traefik_status:
            traefik_status = error_context.traefik_status
            if traefik_status.get('running'):
                status_table.add_row(
                    "Traefik",
                    "✅ Running",
                    f"Services: {traefik_status.get('services_count', 0)}"
                )
            elif traefik_status.get('installed'):
                status_table.add_row(
                    "Traefik",
                    "⚠️ Installed",
                    "Not running"
                )
            else:
                status_table.add_row(
                    "Traefik",
                    "❌ Not Installed",
                    ""
                )
        
        # Disk space
        if error_context.disk_space:
            disk_status = error_context.disk_space
            if 'error' not in disk_status:
                status_table.add_row(
                    "Disk Space",
                    "ℹ️ Available",
                    f"Free: {disk_status.get('current_dir_free', 'Unknown')}"
                )
        
        # Network connectivity
        if error_context.network_status:
            network_status = error_context.network_status
            if 'error' not in network_status:
                internet_ok = network_status.get('internet_https', False)
                status_table.add_row(
                    "Network",
                    "✅ Connected" if internet_ok else "⚠️ Limited",
                    "Internet accessible" if internet_ok else "Check connectivity"
                )
        
        console.print(status_table)
        
        # System information
        if error_context.system_info:
            system_info = []
            system_info.append(f"Platform: {error_context.system_info.get('platform', 'Unknown')}")
            system_info.append(f"Python: {error_context.python_version}")
            system_info.append(f"BlastDock: {error_context.blastdock_version}")
            
            console.print(Panel(
                "\n".join(system_info),
                title="System Information",
                border_style="blue",
                expand=False
            ))
    
    def _generate_error_report(self, error_context: ErrorContext):
        """Generate and save error report"""
        try:
            report_file = f"blastdock_error_report_{error_context.error_id}.json"
            self.diagnostics.export_error_report(error_context, report_file)
            
            console.print(f"\n[green]📄 Error report saved: {report_file}[/green]")
            console.print(f"[dim]Include this file when reporting issues[/dim]")
            
        except Exception as e:
            logger.error(f"Failed to generate error report: {e}")
    
    def _handle_critical_error(self, error_context: ErrorContext):
        """Handle critical errors that require application exit"""
        
        console.print(Panel(
            "[bold red]⚠️ CRITICAL ERROR ⚠️[/bold red]\n\n"
            "BlastDock cannot continue due to a critical system error.\n"
            "Please resolve the issue and try again.\n\n"
            f"Error ID: [cyan]{error_context.error_id}[/cyan]",
            border_style="red",
            expand=False
        ))
        
        # Show immediate recovery actions
        if error_context.suggested_solutions:
            console.print("\n[bold yellow]🚨 Immediate Actions Required:[/bold yellow]")
            for i, solution in enumerate(error_context.suggested_solutions[:3], 1):
                console.print(f"  {i}. {solution}")
        
        # Exit with appropriate code
        sys.exit(1)
    
    def display_error_summary(self, errors: List[ErrorContext]):
        """Display summary of multiple errors"""
        if not errors:
            return
        
        console.print(f"\n[bold red]📋 Error Summary ({len(errors)} errors)[/bold red]")
        
        # Create summary table
        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("Time", style="cyan", width=10)
        summary_table.add_column("Type", style="yellow", width=20)
        summary_table.add_column("Severity", width=10)
        summary_table.add_column("Message", style="white")
        
        for error in errors[-10:]:  # Show last 10 errors
            # Format timestamp
            time_str = error.timestamp.strftime("%H:%M:%S")
            
            # Color severity
            severity = error.severity
            if severity == ErrorSeverity.CRITICAL:
                severity_display = "[bold red]CRITICAL[/bold red]"
            elif severity == ErrorSeverity.ERROR:
                severity_display = "[red]ERROR[/red]"
            elif severity == ErrorSeverity.WARNING:
                severity_display = "[yellow]WARNING[/yellow]"
            else:
                severity_display = "[blue]INFO[/blue]"
            
            # Truncate message
            message = error.error_message[:60] + "..." if len(error.error_message) > 60 else error.error_message
            
            summary_table.add_row(
                time_str,
                error.error_type,
                severity_display,
                message
            )
        
        console.print(summary_table)


def handle_cli_error(exception: Exception, 
                    command: str = None,
                    project_name: str = None,
                    template_name: str = None,
                    show_diagnostics: bool = False,
                    auto_report: bool = False) -> Optional[ErrorContext]:
    """Handle CLI errors with enhanced user experience
    
    Args:
        exception: The exception to handle
        command: CLI command that caused the error
        project_name: Project name if applicable
        template_name: Template name if applicable
        show_diagnostics: Show detailed diagnostics
        auto_report: Auto-generate error report
        
    Returns:
        ErrorContext or None if application should exit
    """
    
    # Create operation context
    operation_context = {
        'command': command,
        'project_name': project_name,
        'template_name': template_name,
        'operation': 'cli_command'
    }
    
    # Create enhanced error handler
    error_handler = EnhancedErrorHandler(
        show_diagnostics=show_diagnostics,
        auto_report=auto_report
    )
    
    # Handle the error
    return error_handler.handle_error(exception, operation_context)


def create_user_friendly_error_message(exception: Exception) -> str:
    """Create user-friendly error message for simple display"""
    
    error_messages = {
        DockerNotAvailableError: "Docker is not running. Please start Docker and try again.",
        TraefikNotInstalledError: "Traefik is not installed. Run 'blastdock traefik install' first.",
        TraefikNotRunningError: "Traefik is not running. Run 'blastdock traefik restart' to start it.",
        TemplateNotFoundError: "Template not found. Run 'blastdock templates list' to see available templates.",
        ProjectNotFoundError: "Project not found. Run 'blastdock list' to see existing projects.",
        PortConflictError: "Port is already in use. Try a different port or stop the conflicting service.",
        DomainNotAvailableError: "Domain is not available. Choose a different domain name.",
        SSLCertificateError: "SSL certificate error. Check domain configuration and try again."
    }
    
    # Get user-friendly message
    for error_type, message in error_messages.items():
        if isinstance(exception, error_type):
            return message
    
    # Default message for unknown errors
    if isinstance(exception, BlastDockError):
        return str(exception)
    
    return f"An unexpected error occurred: {str(exception)}"


def get_recovery_suggestions(exception: Exception) -> List[str]:
    """Get quick recovery suggestions for an exception"""
    
    suggestions = {
        DockerNotAvailableError: [
            "Start Docker Desktop",
            "Check Docker daemon: sudo systemctl status docker",
            "Restart Docker: sudo systemctl restart docker"
        ],
        TraefikNotInstalledError: [
            "Install Traefik: blastdock traefik install --email your@email.com --domain yourdomain.com"
        ],
        TraefikNotRunningError: [
            "Start Traefik: blastdock traefik restart"
        ],
        TemplateNotFoundError: [
            "List templates: blastdock templates list",
            "Check template name spelling"
        ],
        ProjectNotFoundError: [
            "List projects: blastdock list",
            "Check project name spelling"
        ],
        PortConflictError: [
            "Check port usage: blastdock ports list",
            "Find process using port: netstat -tuln | grep <port>",
            "Use different port number"
        ]
    }
    
    for error_type, suggestion_list in suggestions.items():
        if isinstance(exception, error_type):
            return suggestion_list
    
    return ["Check logs for more details", "Verify system requirements"]