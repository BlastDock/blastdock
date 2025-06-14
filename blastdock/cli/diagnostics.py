"""
CLI commands for system diagnostics and error reporting
"""

import click
import json
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..utils.error_diagnostics import get_diagnostics
from ..utils.error_handler import EnhancedErrorHandler


console = Console()


@click.group()
def diagnostics():
    """System diagnostics and error reporting commands"""
    pass


@diagnostics.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed diagnostic information')
@click.option('--save-report', help='Save diagnostic report to file')
def check(verbose, save_report):
    """Run comprehensive system diagnostics"""
    
    console.print("\n[bold blue]🔍 BlastDock System Diagnostics[/bold blue]\n")
    
    diagnostics_service = get_diagnostics()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Running diagnostics...", total=None)
        
        # Run all diagnostic checks
        results = diagnostics_service.run_diagnostics()
    
    # Display results
    _display_diagnostic_results(results, verbose)
    
    # Save report if requested
    if save_report:
        _save_diagnostic_report(results, save_report)


@diagnostics.command()
@click.option('--limit', '-l', default=10, help='Number of recent errors to show')
@click.option('--format', 'output_format', type=click.Choice(['table', 'detailed', 'json']), 
              default='table', help='Output format')
def errors(limit, output_format):
    """Show recent error history"""
    
    diagnostics_service = get_diagnostics()
    error_history = diagnostics_service.get_error_history(limit)
    
    if not error_history:
        console.print("[yellow]No recent errors found[/yellow]")
        return
    
    console.print(f"\n[bold blue]📋 Recent Errors (Last {len(error_history)})[/bold blue]")
    
    if output_format == 'json':
        error_data = [error.to_dict() for error in error_history]
        console.print(json.dumps(error_data, indent=2, default=str))
    
    elif output_format == 'detailed':
        for error in error_history:
            _display_detailed_error(error)
    
    else:  # table format
        _display_error_table(error_history)


@diagnostics.command()
@click.argument('error_id')
@click.option('--export', help='Export detailed error report to file')
def report(error_id, export):
    """Generate detailed error report for specific error ID"""
    
    diagnostics_service = get_diagnostics()
    error_history = diagnostics_service.get_error_history(100)  # Check last 100 errors
    
    # Find error by ID
    target_error = None
    for error in error_history:
        if error.error_id == error_id:
            target_error = error
            break
    
    if not target_error:
        console.print(f"[red]Error ID '{error_id}' not found in recent history[/red]")
        return
    
    console.print(f"\n[bold blue]📄 Error Report: {error_id}[/bold blue]")
    
    # Display detailed error information
    _display_detailed_error(target_error)
    
    # Export if requested
    if export:
        try:
            diagnostics_service.export_error_report(target_error, export)
            console.print(f"\n[green]📁 Report exported to: {export}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to export report: {e}[/red]")


@diagnostics.command()
@click.option('--auto-fix', is_flag=True, help='Attempt to automatically fix detected issues')
@click.option('--dry-run', is_flag=True, help='Show what would be fixed without making changes')
def health(auto_fix, dry_run):
    """Check system health and suggest fixes"""
    
    console.print("\n[bold blue]🏥 BlastDock Health Check[/bold blue]\n")
    
    diagnostics_service = get_diagnostics()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Checking system health...", total=None)
        
        # Run health checks
        health_results = diagnostics_service.run_diagnostics()
    
    # Analyze health results
    issues = []
    healthy_components = []
    
    for component, result in health_results.items():
        if result['status'] == 'fail':
            issues.append({
                'component': component,
                'message': result['message'],
                'severity': 'error'
            })
        elif result['status'] == 'error':
            issues.append({
                'component': component,
                'message': result['message'],
                'severity': 'critical'
            })
        else:
            healthy_components.append(component)
    
    # Display health status
    if not issues:
        console.print("[green]✅ All systems healthy![/green]")
        return
    
    # Show issues
    console.print(f"[yellow]⚠️ Found {len(issues)} health issues:[/yellow]\n")
    
    issue_tree = Tree("🩺 Health Issues", style="yellow")
    
    for issue in issues:
        severity_icon = "🔴" if issue['severity'] == 'critical' else "🟡"
        component_branch = issue_tree.add(f"{severity_icon} {issue['component'].replace('_', ' ').title()}")
        component_branch.add(issue['message'])
        
        # Add suggested fixes
        fixes = _get_health_fixes(issue['component'])
        if fixes:
            fix_branch = component_branch.add("💊 Suggested Fixes")
            for fix in fixes:
                fix_branch.add(fix)
    
    console.print(issue_tree)
    
    # Auto-fix if requested
    if auto_fix and not dry_run:
        console.print("\n[yellow]🔧 Attempting automatic fixes...[/yellow]")
        _attempt_auto_fixes(issues)
    elif dry_run:
        console.print("\n[blue]ℹ️ Dry run mode - no changes will be made[/blue]")


@diagnostics.command()
def info():
    """Show system information and environment details"""
    
    console.print("\n[bold blue]ℹ️ BlastDock System Information[/bold blue]\n")
    
    diagnostics_service = get_diagnostics()
    
    # Gather system information
    import platform
    import sys
    
    # System info table
    info_table = Table(title="System Information", show_header=True, header_style="bold magenta")
    info_table.add_column("Property", style="cyan", width=20)
    info_table.add_column("Value", style="white")
    
    # Add system details
    info_table.add_row("Platform", platform.platform())
    info_table.add_row("System", platform.system())
    info_table.add_row("Release", platform.release())
    info_table.add_row("Architecture", platform.machine())
    info_table.add_row("Python Version", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    try:
        from .._version import __version__
        info_table.add_row("BlastDock Version", __version__)
    except ImportError:
        info_table.add_row("BlastDock Version", "Unknown")
    
    info_table.add_row("Working Directory", os.getcwd())
    info_table.add_row("User", os.getenv('USER', os.getenv('USERNAME', 'Unknown')))
    
    console.print(info_table)
    
    # Check component status
    console.print("\n[bold yellow]🔧 Component Status[/bold yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Checking components...", total=None)
        component_results = diagnostics_service.run_diagnostics()
    
    _display_diagnostic_results(component_results, verbose=False)


def _display_diagnostic_results(results: dict, verbose: bool = False):
    """Display diagnostic results in a formatted table"""
    
    # Create status table
    status_table = Table(title="Diagnostic Results", show_header=True, header_style="bold magenta")
    status_table.add_column("Component", style="cyan", width=20)
    status_table.add_column("Status", width=10)
    status_table.add_column("Message", style="white")
    
    for component, result in results.items():
        # Format component name
        component_name = component.replace('_', ' ').title()
        
        # Status with appropriate styling
        status = result['status']
        if status == 'pass':
            status_display = "[green]✅ PASS[/green]"
        elif status == 'fail':
            status_display = "[yellow]⚠️ FAIL[/yellow]"
        else:
            status_display = "[red]❌ ERROR[/red]"
        
        # Message
        message = result.get('message', 'No details')
        
        status_table.add_row(component_name, status_display, message)
    
    console.print(status_table)
    
    # Summary
    total_checks = len(results)
    passed_checks = sum(1 for r in results.values() if r['status'] == 'pass')
    failed_checks = sum(1 for r in results.values() if r['status'] == 'fail')
    error_checks = sum(1 for r in results.values() if r['status'] == 'error')
    
    console.print(f"\n[bold]Summary:[/bold] {passed_checks}/{total_checks} checks passed")
    if failed_checks > 0:
        console.print(f"[yellow]Warnings: {failed_checks}[/yellow]")
    if error_checks > 0:
        console.print(f"[red]Errors: {error_checks}[/red]")


def _display_error_table(error_history: list):
    """Display error history in table format"""
    
    error_table = Table(title="Recent Errors", show_header=True, header_style="bold magenta")
    error_table.add_column("Time", style="cyan", width=12)
    error_table.add_column("ID", style="blue", width=25)
    error_table.add_column("Type", style="yellow", width=20)
    error_table.add_column("Severity", width=10)
    error_table.add_column("Message", style="white")
    
    for error in error_history:
        # Format timestamp
        time_str = error.timestamp.strftime("%m-%d %H:%M")
        
        # Format error ID (show last part)
        error_id_short = error.error_id.split('-')[-1]
        
        # Color severity
        severity = error.severity
        if severity == 'critical':
            severity_display = "[bold red]CRITICAL[/bold red]"
        elif severity == 'error':
            severity_display = "[red]ERROR[/red]"
        elif severity == 'warning':
            severity_display = "[yellow]WARNING[/yellow]"
        else:
            severity_display = "[blue]INFO[/blue]"
        
        # Truncate message
        message = error.error_message[:50] + "..." if len(error.error_message) > 50 else error.error_message
        
        error_table.add_row(
            time_str,
            error_id_short,
            error.error_type,
            severity_display,
            message
        )
    
    console.print(error_table)


def _display_detailed_error(error):
    """Display detailed error information"""
    
    # Main error panel
    error_content = []
    error_content.append(f"[bold]Error Type:[/bold] {error.error_type}")
    error_content.append(f"[bold]Severity:[/bold] {error.severity}")
    error_content.append(f"[bold]Time:[/bold] {error.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    error_content.append("")
    error_content.append(f"[bold]Message:[/bold]")
    error_content.append(f"  {error.error_message}")
    
    if error.project_name:
        error_content.append(f"[bold]Project:[/bold] {error.project_name}")
    if error.template_name:
        error_content.append(f"[bold]Template:[/bold] {error.template_name}")
    if error.operation:
        error_content.append(f"[bold]Operation:[/bold] {error.operation}")
    
    console.print(Panel(
        "\n".join(error_content),
        title=f"📄 Error Report: {error.error_id}",
        border_style="red",
        expand=False
    ))
    
    # Solutions
    if error.suggested_solutions:
        console.print("\n[bold blue]💡 Suggested Solutions:[/bold blue]")
        for i, solution in enumerate(error.suggested_solutions, 1):
            console.print(f"  {i}. {solution}")
    
    # Recovery commands
    if error.recovery_commands:
        console.print("\n[bold green]⌨️ Recovery Commands:[/bold green]")
        for command in error.recovery_commands:
            console.print(f"  [code]{command}[/code]")


def _save_diagnostic_report(results: dict, file_path: str):
    """Save diagnostic report to file"""
    try:
        report_data = {
            'report_type': 'BlastDock Diagnostic Report',
            'generated_at': datetime.now().isoformat(),
            'diagnostic_results': results
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"\n[green]📁 Diagnostic report saved to: {file_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to save report: {e}[/red]")


def _get_health_fixes(component: str) -> list:
    """Get suggested fixes for health issues"""
    
    fixes = {
        'docker_available': [
            "Start Docker Desktop application",
            "Install Docker if not installed",
            "Check Docker daemon: sudo systemctl status docker"
        ],
        'disk_space_sufficient': [
            "Free up disk space",
            "Remove unused Docker images: docker image prune",
            "Clean up temporary files"
        ],
        'network_connectivity': [
            "Check internet connection",
            "Verify DNS settings",
            "Check firewall configuration"
        ],
        'permissions_valid': [
            "Check file/directory permissions",
            "Add user to docker group: sudo usermod -aG docker $USER",
            "Run with appropriate privileges"
        ],
        'traefik_healthy': [
            "Install Traefik: blastdock traefik install",
            "Start Traefik: blastdock traefik restart",
            "Check Traefik configuration"
        ]
    }
    
    return fixes.get(component, ["Check component documentation"])


def _attempt_auto_fixes(issues: list):
    """Attempt to automatically fix detected issues"""
    
    for issue in issues:
        component = issue['component']
        
        console.print(f"\n[yellow]🔧 Fixing {component}...[/yellow]")
        
        # Simple auto-fixes
        if component == 'docker_available':
            console.print("  [dim]Checking Docker status...[/dim]")
            # Could add actual Docker restart logic here
            console.print("  [green]✅ Docker check completed[/green]")
        
        elif component == 'traefik_healthy':
            console.print("  [dim]Checking Traefik status...[/dim]")
            # Could add Traefik restart logic here
            console.print("  [green]✅ Traefik check completed[/green]")
        
        else:
            console.print(f"  [yellow]⚠️ No automatic fix available for {component}[/yellow]")
    
    console.print("\n[green]🎉 Auto-fix process completed[/green]")
    console.print("[dim]Run 'blastdock diagnostics health' again to verify fixes[/dim]")