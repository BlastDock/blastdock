"""
CLI commands for security management and validation
"""

import click
import json
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..security import (
    get_security_validator, get_docker_security_checker,
    get_template_security_scanner, get_config_security,
    get_secure_file_operations
)
from ..utils.filesystem import paths


console = Console()


@click.group()
def security():
    """Security validation and management commands"""
    pass


@security.command()
@click.option('--project', help='Scan specific project')
@click.option('--save-report', help='Save security report to file')
@click.option('--format', 'output_format', type=click.Choice(['table', 'detailed', 'json']), 
              default='table', help='Output format')
def scan(project, save_report, output_format):
    """Run comprehensive security scan"""
    
    console.print("\\n[bold blue]🔒 BlastDock Security Scan[/bold blue]\\n")
    
    security_validator = get_security_validator()
    docker_checker = get_docker_security_checker()
    template_scanner = get_template_security_scanner()
    
    scan_results = {
        'scan_timestamp': '',
        'docker_security': {},
        'template_security': {},
        'configuration_security': {},
        'overall_score': 0
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        # Docker security scan
        task = progress.add_task("Scanning Docker security...", total=None)
        docker_result = docker_checker.check_docker_daemon_security()
        scan_results['docker_security'] = docker_result
        
        # Template security scan
        progress.update(task, description="Scanning templates...")
        templates_dir = os.path.join(paths.data_dir, 'templates')
        if os.path.exists(templates_dir):
            template_result = template_scanner.scan_all_templates(templates_dir)
            scan_results['template_security'] = template_result
        
        # Configuration security
        progress.update(task, description="Checking configuration security...")
        config_security = get_config_security()
        config_status = config_security.get_security_status()
        scan_results['configuration_security'] = config_status
    
    # Calculate overall score
    scores = []
    if scan_results['docker_security'].get('security_score'):
        scores.append(scan_results['docker_security']['security_score'])
    if scan_results['template_security'].get('average_security_score'):
        scores.append(scan_results['template_security']['average_security_score'])
    
    overall_score = sum(scores) / len(scores) if scores else 0
    scan_results['overall_score'] = round(overall_score, 1)
    
    # Display results
    if output_format == 'json':
        console.print(json.dumps(scan_results, indent=2, default=str))
    else:
        _display_security_scan_results(scan_results, output_format == 'detailed')
    
    # Save report if requested
    if save_report:
        try:
            with open(save_report, 'w') as f:
                json.dump(scan_results, f, indent=2, default=str)
            console.print(f"\\n[green]📄 Security report saved to: {save_report}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to save report: {e}[/red]")


@security.command()
@click.argument('template_path')
@click.option('--detailed', is_flag=True, help='Show detailed security analysis')
def scan_template(template_path, detailed):
    """Scan specific template for security issues"""
    
    console.print(f"\\n[bold blue]🔍 Scanning Template: {template_path}[/bold blue]\\n")
    
    scanner = get_template_security_scanner()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning template...", total=None)
        result = scanner.scan_template(template_path)
    
    if not result.get('accessible'):
        console.print(f"[red]❌ Cannot access template: {result.get('error')}[/red]")
        return
    
    # Display results
    _display_template_scan_results(result, detailed)


@security.command()
@click.argument('container_name')
def scan_container(container_name):
    """Scan running container for security issues"""
    
    console.print(f"\\n[bold blue]🐳 Scanning Container: {container_name}[/bold blue]\\n")
    
    checker = get_docker_security_checker()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning container...", total=None)
        result = checker.check_container_security(container_name)
    
    if not result.get('accessible'):
        console.print(f"[red]❌ Cannot access container: {result.get('error')}[/red]")
        return
    
    # Display results
    _display_container_scan_results(result)


@security.command()
@click.argument('directory_path')
@click.option('--fix', is_flag=True, help='Attempt to fix security issues')
def scan_files(directory_path, fix):
    """Scan directory for file security issues"""
    
    console.print(f"\\n[bold blue]📁 Scanning Directory: {directory_path}[/bold blue]\\n")
    
    file_ops = get_secure_file_operations()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning files...", total=None)
        result = file_ops.scan_directory_security(directory_path)
    
    if not result.get('exists'):
        console.print(f"[red]❌ Directory not found: {result.get('error')}[/red]")
        return
    
    # Display results
    _display_file_scan_results(result, fix)


@security.command()
@click.option('--init-encryption', is_flag=True, help='Initialize configuration encryption')
@click.option('--master-password', help='Master password for encryption')
def config(init_encryption, master_password):
    """Manage security configuration"""
    
    console.print("\\n[bold blue]⚙️ Security Configuration[/bold blue]\\n")
    
    config_security = get_config_security()
    
    if init_encryption:
        console.print("[dim]Initializing configuration encryption...[/dim]")
        
        if not master_password:
            master_password = click.prompt("Enter master password", hide_input=True)
        
        if config_security.initialize_encryption(master_password):
            console.print("[green]✅ Encryption initialized successfully[/green]")
        else:
            console.print("[red]❌ Failed to initialize encryption[/red]")
            return
    
    # Show current security status
    status = config_security.get_security_status()
    
    status_table = Table(title="Security Configuration Status")
    status_table.add_column("Setting", style="cyan")
    status_table.add_column("Status", style="white")
    
    status_table.add_row("Encryption Enabled", "✅ Yes" if status['encryption_enabled'] else "❌ No")
    status_table.add_row("Key File", "✅ Exists" if status['key_file_exists'] else "❌ Missing")
    status_table.add_row("Salt File", "✅ Exists" if status['salt_file_exists'] else "❌ Missing")
    status_table.add_row("Key Iterations", str(status['key_derivation_iterations']))
    status_table.add_row("Sensitive Keys", str(status['sensitive_keys_count']))
    
    console.print(status_table)
    
    # Show security features
    console.print("\\n[bold]🛡️ Security Features:[/bold]")
    for feature in status['security_features']:
        console.print(f"  • {feature}")


@security.command()
def guidelines():
    """Show security guidelines and best practices"""
    
    console.print("\\n[bold blue]📋 BlastDock Security Guidelines[/bold blue]\\n")
    
    # Get guidelines from different components
    validator = get_security_validator()
    docker_checker = get_docker_security_checker()
    template_scanner = get_template_security_scanner()
    
    guidelines_tree = Tree("🛡️ Security Guidelines", style="bold blue")
    
    # Docker security
    docker_branch = guidelines_tree.add("🐳 Docker Security")
    for rec in docker_checker.get_security_recommendations():
        docker_branch.add(rec)
    
    # Template security
    template_branch = guidelines_tree.add("📄 Template Security")
    for guideline in template_scanner.get_security_guidelines():
        template_branch.add(guideline)
    
    # General security
    general_branch = guidelines_tree.add("🔒 General Security")
    general_recommendations = [
        "Keep BlastDock and dependencies updated",
        "Use strong passwords and enable encryption",
        "Regularly scan for security vulnerabilities",
        "Monitor logs for suspicious activities",
        "Use principle of least privilege",
        "Enable audit logging for sensitive operations",
        "Backup configurations securely",
        "Test security configurations regularly"
    ]
    
    for rec in general_recommendations:
        general_branch.add(rec)
    
    console.print(guidelines_tree)
    
    # Security report
    security_report = validator.get_security_report()
    
    console.print("\\n[bold]🔍 Security Validator Info:[/bold]")
    console.print(f"  • Version: {security_report['validator_version']}")
    console.print(f"  • Dangerous patterns detected: {security_report['dangerous_patterns_count']}")
    console.print(f"  • Allowed extensions: {len(security_report['allowed_extensions'])}")
    console.print(f"  • Blocked extensions: {len(security_report['blocked_extensions'])}")


def _display_security_scan_results(results: dict, detailed: bool):
    """Display comprehensive security scan results"""
    
    # Overall score
    score = results.get('overall_score', 0)
    if score >= 80:
        score_color = "green"
        score_icon = "🟢"
    elif score >= 60:
        score_color = "yellow"
        score_icon = "🟡"
    else:
        score_color = "red"
        score_icon = "🔴"
    
    console.print(f"[bold]Overall Security Score: [{score_color}]{score_icon} {score}/100[/{score_color}][/bold]\\n")
    
    # Docker security
    docker_results = results.get('docker_security', {})
    if docker_results.get('accessible'):
        docker_score = docker_results.get('security_score', 0)
        console.print(f"[bold]🐳 Docker Security: {docker_score}/100[/bold]")
        
        if docker_results.get('security_issues'):
            for issue in docker_results['security_issues'][:3]:  # Show top 3
                severity = issue.get('severity', 'unknown')
                console.print(f"  • [{severity.upper()}] {issue.get('issue', 'Unknown issue')}")
        else:
            console.print("  ✅ No Docker security issues found")
        console.print()
    
    # Template security
    template_results = results.get('template_security', {})
    if template_results.get('accessible'):
        template_score = template_results.get('average_security_score', 0)
        templates_count = template_results.get('templates_scanned', 0)
        console.print(f"[bold]📄 Template Security: {template_score}/100 ({templates_count} templates)[/bold]")
        
        issues_by_severity = template_results.get('issues_by_severity', {})
        if any(issues_by_severity.values()):
            console.print(f"  • Critical: {issues_by_severity.get('critical', 0)}")
            console.print(f"  • High: {issues_by_severity.get('high', 0)}")
            console.print(f"  • Medium: {issues_by_severity.get('medium', 0)}")
            console.print(f"  • Low: {issues_by_severity.get('low', 0)}")
        else:
            console.print("  ✅ No template security issues found")
        console.print()
    
    # Configuration security
    config_results = results.get('configuration_security', {})
    console.print("[bold]⚙️ Configuration Security:[/bold]")
    console.print(f"  • Encryption: {'✅ Enabled' if config_results.get('encryption_enabled') else '❌ Disabled'}")
    console.print(f"  • Key Management: {'✅ Configured' if config_results.get('key_file_exists') else '❌ Not configured'}")


def _display_template_scan_results(result: dict, detailed: bool):
    """Display template security scan results"""
    
    score = result.get('security_score', 0)
    issues = result.get('security_issues', [])
    
    # Score display
    if score >= 80:
        score_display = f"[green]🟢 {score}/100[/green]"
    elif score >= 60:
        score_display = f"[yellow]🟡 {score}/100[/yellow]"
    else:
        score_display = f"[red]🔴 {score}/100[/red]"
    
    console.print(f"[bold]Security Score: {score_display}[/bold]")
    console.print(f"[bold]Issues Found: {len(issues)}[/bold]\\n")
    
    if not issues:
        console.print("[green]✅ No security issues found in template[/green]")
        return
    
    # Group issues by severity
    issues_by_severity = {}
    for issue in issues:
        severity = issue.get('severity', 'unknown')
        if severity not in issues_by_severity:
            issues_by_severity[severity] = []
        issues_by_severity[severity].append(issue)
    
    # Display issues
    severity_order = ['critical', 'high', 'medium', 'low']
    for severity in severity_order:
        if severity in issues_by_severity:
            severity_issues = issues_by_severity[severity]
            severity_color = {
                'critical': 'red',
                'high': 'red',
                'medium': 'yellow',
                'low': 'blue'
            }.get(severity, 'white')
            
            console.print(f"\\n[bold {severity_color}]{severity.upper()} ISSUES ({len(severity_issues)}):[/bold {severity_color}]")
            
            for issue in severity_issues:
                console.print(f"  🔸 {issue.get('issue', 'Unknown issue')}")
                if detailed:
                    if issue.get('description'):
                        console.print(f"     [dim]{issue['description']}[/dim]")
                    if issue.get('recommendation'):
                        console.print(f"     [dim]💡 {issue['recommendation']}[/dim]")
                    if issue.get('file'):
                        console.print(f"     [dim]📁 File: {issue['file']}[/dim]")


def _display_container_scan_results(result: dict):
    """Display container security scan results"""
    
    score = result.get('security_score', 0)
    issues = result.get('security_issues', [])
    config = result.get('configuration', {})
    
    # Score display
    if score >= 80:
        score_display = f"[green]🟢 {score}/100[/green]"
    elif score >= 60:
        score_display = f"[yellow]🟡 {score}/100[/yellow]"
    else:
        score_display = f"[red]🔴 {score}/100[/red]"
    
    console.print(f"[bold]Security Score: {score_display}[/bold]")
    console.print(f"[bold]Issues Found: {len(issues)}[/bold]\\n")
    
    # Configuration summary
    config_table = Table(title="Container Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="white")
    
    config_table.add_row("Privileged", "✅ No" if not config.get('privileged') else "❌ Yes")
    config_table.add_row("User", config.get('user', 'unknown'))
    config_table.add_row("Network Mode", config.get('network_mode', 'default'))
    config_table.add_row("Read Only", "✅ Yes" if config.get('read_only') else "❌ No")
    
    console.print(config_table)
    
    # Issues
    if issues:
        console.print("\\n[bold red]🚨 Security Issues:[/bold red]")
        for issue in issues:
            severity = issue.get('severity', 'unknown')
            console.print(f"  • [{severity.upper()}] {issue.get('issue', 'Unknown issue')}")
            if issue.get('recommendation'):
                console.print(f"    💡 {issue['recommendation']}")


def _display_file_scan_results(result: dict, fix_issues: bool):
    """Display file security scan results"""
    
    file_count = result.get('file_count', 0)
    dir_count = result.get('directory_count', 0)
    total_size = result.get('total_size', 0)
    security_issues = result.get('security_issues', [])
    insecure_files = result.get('insecure_files', [])
    
    # Summary
    console.print(f"[bold]📊 Scan Summary:[/bold]")
    console.print(f"  • Files: {file_count}")
    console.print(f"  • Directories: {dir_count}")
    console.print(f"  • Total Size: {total_size / 1024:.1f} KB")
    console.print(f"  • Security Issues: {len(security_issues)}")
    console.print(f"  • Insecure Files: {len(insecure_files)}\\n")
    
    if result.get('is_secure'):
        console.print("[green]✅ No security issues found[/green]")
        return
    
    # Show issues
    console.print("[bold red]🚨 Security Issues:[/bold red]")
    for issue in security_issues[:10]:  # Show first 10
        console.print(f"  • {issue}")
    
    if len(security_issues) > 10:
        console.print(f"  ... and {len(security_issues) - 10} more")
    
    if fix_issues:
        console.print("\\n[yellow]🔧 Attempting to fix issues...[/yellow]")
        file_ops = get_secure_file_operations()
        
        fixed_count = 0
        for file_info in insecure_files:
            file_path = file_info['path']
            success, _ = file_ops.set_secure_permissions(file_path, os.path.isdir(file_path))
            if success:
                fixed_count += 1
        
        console.print(f"[green]✅ Fixed {fixed_count} out of {len(insecure_files)} files[/green]")