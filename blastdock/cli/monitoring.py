"""
CLI commands for monitoring and health checks
"""

import click
import json
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..monitoring import (
    get_health_checker, get_metrics_collector, get_alert_manager, 
    get_monitoring_dashboard, get_log_analyzer
)
from ..monitoring.web_dashboard import WebDashboard
from ..monitoring.health_checker import HealthStatus, ServiceHealthConfig
from ..monitoring.alert_manager import AlertRule, AlertSeverity, NotificationChannel

console = Console()


@click.group()
def monitoring():
    """Advanced monitoring and health check commands"""
    pass


@monitoring.command()
@click.argument('project_name')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.option('--detailed', is_flag=True, help='Show detailed health information')
def health(project_name, output_format, detailed):
    """Check health status of a project"""
    
    health_checker = get_health_checker()
    
    try:
        console.print(f"\n[bold blue]🏥 Health Check: {project_name}[/bold blue]\n")
        
        # Perform health check
        health_data = health_checker.check_project_health(project_name)
        
        if output_format == 'json':
            console.print(json.dumps(health_data, indent=2, default=str))
            return
        
        # Display results in table format
        overall_status = health_data.get('overall_status', 'unknown')
        overall_message = health_data.get('message', 'No status available')
        duration = health_data.get('duration_ms', 0)
        
        # Overall status panel
        if overall_status == HealthStatus.HEALTHY.value:
            status_color = "green"
            status_icon = "✅"
        elif overall_status == HealthStatus.DEGRADED.value:
            status_color = "yellow"
            status_icon = "⚠️"
        elif overall_status == HealthStatus.UNHEALTHY.value:
            status_color = "red"
            status_icon = "❌"
        else:
            status_color = "white"
            status_icon = "❓"
        
        status_text = Text()
        status_text.append(f"{status_icon} {overall_status.upper()}\n", style=f"bold {status_color}")
        status_text.append(f"{overall_message}\n", style=status_color)
        status_text.append(f"Response time: {duration:.1f}ms", style="dim")
        
        console.print(Panel(status_text, title="Overall Health", border_style=status_color))
        
        # Service details
        services = health_data.get('services', {})
        if services:
            console.print(f"\n[bold]Service Health Details:[/bold]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Service", style="cyan")
            table.add_column("Status", style="white")
            table.add_column("Message", style="blue")
            table.add_column("Response Time", style="green")
            
            for service_name, service_info in services.items():
                status = service_info.get('status', 'unknown')
                message = service_info.get('message', 'No message')
                response_time = service_info.get('response_time_ms', 0)
                
                # Status with emoji
                if status == HealthStatus.HEALTHY.value:
                    status_display = "✅ Healthy"
                elif status == HealthStatus.DEGRADED.value:
                    status_display = "⚠️ Degraded"
                elif status == HealthStatus.UNHEALTHY.value:
                    status_display = "❌ Unhealthy"
                else:
                    status_display = "❓ Unknown"
                
                table.add_row(
                    service_name,
                    status_display,
                    message[:50] + "..." if len(message) > 50 else message,
                    f"{response_time:.1f}ms"
                )
            
            console.print(table)
            
            # Detailed information
            if detailed:
                console.print(f"\n[bold]Detailed Service Information:[/bold]")
                for service_name, service_info in services.items():
                    details = service_info.get('details', {})
                    suggestions = service_info.get('suggestions', [])
                    container_info = service_info.get('container_info', {})
                    
                    detail_text = Text()
                    detail_text.append(f"Container: {container_info.get('name', 'unknown')}\n", style="cyan")
                    detail_text.append(f"Image: {container_info.get('image', 'unknown')}\n", style="blue")
                    detail_text.append(f"Status: {container_info.get('status', 'unknown')}\n", style="white")
                    
                    if details:
                        detail_text.append("\nDetails:\n", style="bold")
                        for key, value in details.items():
                            detail_text.append(f"  {key}: {value}\n", style="dim")
                    
                    if suggestions:
                        detail_text.append("\nSuggestions:\n", style="bold yellow")
                        for suggestion in suggestions:
                            detail_text.append(f"  • {suggestion}\n", style="yellow")
                    
                    console.print(Panel(detail_text, title=f"Service: {service_name}", border_style="blue"))
        
        console.print(f"\n[green]✅ Health check completed in {duration:.1f}ms[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Health check failed: {e}[/red]")


@monitoring.command()
@click.argument('project_name')
@click.option('--window', default=24, help='Time window in hours')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
def metrics(project_name, window, output_format):
    """Show metrics for a project"""
    
    metrics_collector = get_metrics_collector()
    
    try:
        console.print(f"\n[bold blue]📊 Metrics: {project_name} (last {window}h)[/bold blue]\n")
        
        # Get dashboard data
        dashboard_data = metrics_collector.get_project_dashboard_data(project_name, window)
        
        if output_format == 'json':
            console.print(json.dumps(dashboard_data, indent=2, default=str))
            return
        
        if 'error' in dashboard_data:
            console.print(f"[red]❌ Metrics error: {dashboard_data['error']}[/red]")
            return
        
        # Project metrics overview
        metrics_data = dashboard_data.get('metrics', {})
        
        overview_table = Table(title="Project Metrics Overview", show_header=True, header_style="bold magenta")
        overview_table.add_column("Metric", style="cyan")
        overview_table.add_column("Current", style="white")
        overview_table.add_column("Average", style="blue")
        overview_table.add_column("Maximum", style="red")
        overview_table.add_column("Minimum", style="green")
        
        key_metrics = [
            ('project_container_count', 'Container Count'),
            ('project_running_containers', 'Running Containers'),
            ('project_cpu_total_percent', 'Total CPU %'),
            ('project_memory_total_mb', 'Total Memory (MB)')
        ]
        
        for metric_name, display_name in key_metrics:
            if metric_name in metrics_data:
                summary = metrics_data[metric_name].get('summary', {})
                recent = metrics_data[metric_name].get('recent_values', [])
                
                current = recent[-1]['value'] if recent else 0
                avg = summary.get('avg', 0)
                max_val = summary.get('max', 0)
                min_val = summary.get('min', 0)
                
                # Format based on metric type
                if 'percent' in metric_name:
                    current_str = f"{current:.1f}%"
                    avg_str = f"{avg:.1f}%"
                    max_str = f"{max_val:.1f}%"
                    min_str = f"{min_val:.1f}%"
                elif 'mb' in metric_name:
                    current_str = f"{current:.0f}"
                    avg_str = f"{avg:.0f}"
                    max_str = f"{max_val:.0f}"
                    min_str = f"{min_val:.0f}"
                else:
                    current_str = f"{current:.0f}"
                    avg_str = f"{avg:.0f}"
                    max_str = f"{max_val:.0f}"
                    min_str = f"{min_val:.0f}"
                
                overview_table.add_row(display_name, current_str, avg_str, max_str, min_str)
        
        console.print(overview_table)
        
        # Container-specific metrics
        containers = dashboard_data.get('containers', {})
        if containers:
            console.print(f"\n[bold]Container Metrics:[/bold]")
            
            container_table = Table(show_header=True, header_style="bold magenta")
            container_table.add_column("Container", style="cyan")
            container_table.add_column("Avg CPU %", style="blue")
            container_table.add_column("Avg Memory", style="green")
            container_table.add_column("Uptime", style="yellow")
            
            for container_name, container_metrics in containers.items():
                cpu_avg = container_metrics.get('cpu', {}).get('avg', 0)
                memory_avg = container_metrics.get('memory', {}).get('avg', 0)
                uptime_avg = container_metrics.get('uptime', {}).get('avg', 0)
                
                # Format uptime
                if uptime_avg > 3600:
                    uptime_str = f"{uptime_avg / 3600:.1f}h"
                elif uptime_avg > 60:
                    uptime_str = f"{uptime_avg / 60:.1f}m"
                else:
                    uptime_str = f"{uptime_avg:.0f}s"
                
                container_table.add_row(
                    container_name,
                    f"{cpu_avg:.1f}%",
                    f"{memory_avg:.0f}MB",
                    uptime_str
                )
            
            console.print(container_table)
        
        console.print(f"\n[green]✅ Metrics retrieved successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Metrics retrieval failed: {e}[/red]")


@monitoring.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.option('--active-only', is_flag=True, help='Show only active alerts')
def alerts(output_format, active_only):
    """Show active alerts and alert status"""
    
    alert_manager = get_alert_manager()
    
    try:
        console.print(f"\n[bold blue]🚨 Alert Status[/bold blue]\n")
        
        # Get alerts
        if active_only:
            alert_list = alert_manager.get_active_alerts()
            title = "Active Alerts"
        else:
            alert_list = alert_manager.get_alert_history(50)
            title = "Recent Alerts"
        
        # Get statistics
        stats = alert_manager.get_statistics()
        
        if output_format == 'json':
            output_data = {
                'statistics': stats,
                'alerts': [
                    {
                        'rule_name': alert.rule_name,
                        'severity': alert.severity.value,
                        'message': alert.message,
                        'status': alert.status.value,
                        'fired_at': alert.fired_at,
                        'resolved_at': alert.resolved_at,
                        'labels': alert.labels
                    }
                    for alert in alert_list
                ]
            }
            console.print(json.dumps(output_data, indent=2, default=str))
            return
        
        # Display statistics
        stats_text = Text()
        stats_text.append(f"Total Alerts: {stats['total_alerts']}\n", style="blue")
        stats_text.append(f"Active: {stats['active_alerts_current']}\n", style="red")
        stats_text.append(f"Resolved: {stats['resolved_alerts']}\n", style="green")
        stats_text.append(f"Rules: {stats['enabled_rules']}/{stats['rules_count']}\n", style="yellow")
        stats_text.append(f"Notifications Sent: {stats['notifications_sent']}", style="cyan")
        
        console.print(Panel(stats_text, title="Alert Statistics", border_style="blue"))
        
        # Display alerts
        if not alert_list:
            console.print(f"\n[green]✅ No {'active' if active_only else 'recent'} alerts[/green]")
            return
        
        console.print(f"\n[bold]{title}:[/bold]")
        
        alerts_table = Table(show_header=True, header_style="bold magenta")
        alerts_table.add_column("Rule", style="cyan")
        alerts_table.add_column("Severity", style="white")
        alerts_table.add_column("Status", style="blue")
        alerts_table.add_column("Message", style="green")
        alerts_table.add_column("Fired At", style="yellow")
        
        for alert in alert_list:
            # Severity with color
            severity = alert.severity.value
            if severity == "critical":
                severity_display = Text("🔴 Critical", style="bold red")
            elif severity == "warning":
                severity_display = Text("🟡 Warning", style="yellow")
            else:
                severity_display = Text("🔵 Info", style="blue")
            
            # Status with color
            status = alert.status.value
            if status == "firing":
                status_display = Text("🔥 Firing", style="red")
            elif status == "resolved":
                status_display = Text("✅ Resolved", style="green")
            else:
                status_display = Text("🔇 Silenced", style="yellow")
            
            fired_time = time.strftime('%H:%M:%S', time.localtime(alert.fired_at))
            
            alerts_table.add_row(
                alert.rule_name,
                severity_display,
                status_display,
                alert.message[:50] + "..." if len(alert.message) > 50 else alert.message,
                fired_time
            )
        
        console.print(alerts_table)
        
    except Exception as e:
        console.print(f"[red]❌ Alert retrieval failed: {e}[/red]")


@monitoring.command()
@click.argument('project_name')
@click.option('--tail', default=1000, help='Number of log lines to analyze')
@click.option('--window', default=24, help='Time window in hours')
@click.option('--format', 'output_format', type=click.Choice(['table', 'summary', 'json']), 
              default='summary', help='Output format')
def logs(project_name, tail, window, output_format):
    """Analyze logs for a project"""
    
    log_analyzer = get_log_analyzer()
    
    try:
        console.print(f"\n[bold blue]📋 Log Analysis: {project_name}[/bold blue]\n")
        
        with console.status("[bold green]Analyzing logs..."):
            analysis_result = log_analyzer.analyze_project_logs(project_name, tail, window)
        
        if output_format == 'json':
            console.print(log_analyzer.export_analysis(analysis_result, 'json'))
            return
        
        # Summary information
        summary_text = Text()
        summary_text.append(f"Total Lines: {analysis_result.total_lines}\n", style="blue")
        summary_text.append(f"Parsed Lines: {analysis_result.parsed_lines}\n", style="cyan")
        summary_text.append(f"Errors: {analysis_result.error_count}\n", style="red")
        summary_text.append(f"Warnings: {analysis_result.warning_count}\n", style="yellow")
        summary_text.append(f"Analysis Time: {time.strftime('%H:%M:%S', time.localtime(analysis_result.analysis_time))}", style="dim")
        
        console.print(Panel(summary_text, title="Log Analysis Summary", border_style="blue"))
        
        # Patterns found
        if analysis_result.patterns_found:
            console.print(f"\n[bold]Patterns Detected:[/bold]")
            
            patterns_table = Table(show_header=True, header_style="bold magenta")
            patterns_table.add_column("Pattern", style="cyan")
            patterns_table.add_column("Count", style="red")
            patterns_table.add_column("Description", style="blue")
            
            for pattern_name, count in sorted(analysis_result.patterns_found.items(), 
                                            key=lambda x: x[1], reverse=True):
                # Find pattern description
                description = "Custom pattern"
                for pattern in log_analyzer._patterns:
                    if pattern.name == pattern_name:
                        description = pattern.description
                        break
                
                patterns_table.add_row(
                    pattern_name.replace('_', ' ').title(),
                    str(count),
                    description
                )
            
            console.print(patterns_table)
        
        # Top errors
        if analysis_result.top_errors:
            console.print(f"\n[bold]Top Errors:[/bold]")
            
            for i, error in enumerate(analysis_result.top_errors[:5], 1):
                error_text = Text()
                error_text.append(f"{i}. ", style="bold")
                error_text.append(f"({error['count']} times, {error['percentage']:.1f}%)\n", style="red")
                error_text.append(f"   {error['message']}", style="white")
                console.print(error_text)
        
        # Recommendations
        if analysis_result.recommendations:
            console.print(f"\n[bold yellow]🔧 Recommendations:[/bold yellow]")
            for i, rec in enumerate(analysis_result.recommendations, 1):
                console.print(f"  {i}. {rec}", style="yellow")
        
        # Timeline (if table format)
        if output_format == 'table' and analysis_result.timeline:
            console.print(f"\n[bold]Timeline (Last 24h):[/bold]")
            
            timeline_table = Table(show_header=True, header_style="bold magenta")
            timeline_table.add_column("Hour", style="cyan")
            timeline_table.add_column("Errors", style="red")
            timeline_table.add_column("Warnings", style="yellow")
            timeline_table.add_column("Events", style="blue")
            
            for entry in analysis_result.timeline[-12:]:  # Last 12 hours
                significant_events = len(entry.get('significant_events', []))
                timeline_table.add_row(
                    f"{entry['date']} {entry['hour']}",
                    str(entry['errors']),
                    str(entry['warnings']),
                    str(significant_events)
                )
            
            console.print(timeline_table)
        
        console.print(f"\n[green]✅ Log analysis completed[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Log analysis failed: {e}[/red]")


@monitoring.command()
@click.argument('project_name')
@click.option('--refresh', default=5, help='Refresh interval in seconds')
def dashboard(project_name, refresh):
    """Show live monitoring dashboard for a project"""
    
    dashboard = get_monitoring_dashboard()
    
    try:
        console.print(f"\n[bold blue]🖥️ Starting live dashboard for {project_name}[/bold blue]")
        console.print(f"[dim]Refresh interval: {refresh}s (Press Ctrl+C to exit)[/dim]\n")
        
        dashboard.show_live_monitoring(project_name, refresh)
        
    except KeyboardInterrupt:
        console.print("\n[dim]Dashboard stopped[/dim]")
    except Exception as e:
        console.print(f"[red]❌ Dashboard error: {e}[/red]")


@monitoring.command()
@click.option('--start', is_flag=True, help='Start background monitoring')
@click.option('--stop', is_flag=True, help='Stop background monitoring')
@click.option('--status', is_flag=True, help='Show monitoring status')
@click.option('--interval', default=30, help='Monitoring interval in seconds')
def background(start, stop, status, interval):
    """Control background monitoring services"""
    
    health_checker = get_health_checker()
    metrics_collector = get_metrics_collector()
    alert_manager = get_alert_manager()
    
    try:
        if start:
            console.print(f"\n[bold blue]🚀 Starting background monitoring[/bold blue]\n")
            
            # Start all monitoring services
            health_checker.start_background_monitoring(interval)
            metrics_collector.start_collection(interval)
            alert_manager.start_evaluation(interval)
            
            console.print(f"[green]✅ Background monitoring started (interval: {interval}s)[/green]")
            console.print("[dim]Use 'monitoring background --status' to check status[/dim]")
            
        elif stop:
            console.print(f"\n[bold blue]⏹️ Stopping background monitoring[/bold blue]\n")
            
            # Stop all monitoring services
            health_checker.stop_background_monitoring()
            metrics_collector.stop_collection()
            alert_manager.stop_evaluation()
            
            console.print(f"[green]✅ Background monitoring stopped[/green]")
            
        elif status:
            console.print(f"\n[bold blue]📊 Background Monitoring Status[/bold blue]\n")
            
            # Get status from each service
            health_stats = health_checker.get_health_statistics()
            metrics_info = metrics_collector.get_all_metrics()
            alert_stats = alert_manager.get_statistics()
            
            status_table = Table(show_header=True, header_style="bold magenta")
            status_table.add_column("Service", style="cyan")
            status_table.add_column("Status", style="white")
            status_table.add_column("Metrics", style="blue")
            
            # Health checker status
            health_checks = health_stats.get('total_checks', 0)
            health_status = "🟢 Active" if health_checks > 0 else "🔴 Inactive"
            status_table.add_row(
                "Health Checker",
                health_status,
                f"{health_checks} checks performed"
            )
            
            # Metrics collector status
            metric_count = len(metrics_info)
            metrics_status = "🟢 Active" if metric_count > 0 else "🔴 Inactive"
            status_table.add_row(
                "Metrics Collector",
                metrics_status,
                f"{metric_count} metrics tracked"
            )
            
            # Alert manager status
            rules_count = alert_stats.get('enabled_rules', 0)
            alerts_status = "🟢 Active" if rules_count > 0 else "🔴 Inactive"
            status_table.add_row(
                "Alert Manager",
                alerts_status,
                f"{rules_count} rules enabled"
            )
            
            console.print(status_table)
            
        else:
            console.print("[yellow]Use --start, --stop, or --status[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Background monitoring error: {e}[/red]")


@monitoring.command()
@click.argument('project_name')
@click.option('--output', help='Output file path')
def export(project_name, output):
    """Export monitoring data for a project"""
    
    dashboard = get_monitoring_dashboard()
    
    try:
        console.print(f"\n[bold blue]📤 Exporting monitoring data for {project_name}[/bold blue]\n")
        
        # Export dashboard data
        export_data = dashboard.export_dashboard_data(project_name)
        
        if output:
            with open(output, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            console.print(f"[green]✅ Data exported to: {output}[/green]")
        else:
            console.print(json.dumps(export_data, indent=2, default=str))
        
    except Exception as e:
        console.print(f"[red]❌ Export failed: {e}[/red]")


@monitoring.command()
@click.option('--host', default='0.0.0.0', help='Web dashboard host')
@click.option('--port', default=8888, type=int, help='Web dashboard port')
@click.option('--browser', is_flag=True, help='Open browser automatically')
@click.pass_context
def web(ctx, host, port, browser):
    """Launch web-based monitoring dashboard"""
    console.print(f"\n[bold blue]🌐 Starting BlastDock Web Dashboard...[/bold blue]\n")
    console.print(f"   Host: {host}")
    console.print(f"   Port: {port}")
    
    # Create web dashboard
    web_dashboard = WebDashboard(host=host, port=port)
    
    # Open browser if requested
    if browser:
        import webbrowser
        import threading
        import time
        
        def open_browser():
            time.sleep(1.5)  # Wait for server to start
            webbrowser.open(f"http://localhost:{port}")
        
        threading.Thread(target=open_browser, daemon=True).start()
    
    console.print(f"\n[green]✅ Dashboard available at: http://{host}:{port}[/green]")
    console.print("[dim]Press Ctrl+C to stop the server[/dim]\n")
    
    try:
        # Run the web server
        web_dashboard.run()
    except KeyboardInterrupt:
        console.print("\n\n[dim]Web dashboard stopped.[/dim]")