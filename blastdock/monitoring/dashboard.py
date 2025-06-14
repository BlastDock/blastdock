"""
Monitoring dashboard for BlastDock
"""

import time
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.live import Live
from rich.layout import Layout

from ..utils.logging import get_logger
from .health_checker import get_health_checker, HealthStatus
from .metrics_collector import get_metrics_collector
from .alert_manager import get_alert_manager, AlertStatus

logger = get_logger(__name__)


class MonitoringDashboard:
    """Interactive monitoring dashboard"""
    
    def __init__(self):
        """Initialize monitoring dashboard"""
        self.logger = get_logger(__name__)
        self.console = Console()
        self.health_checker = get_health_checker()
        self.metrics_collector = get_metrics_collector()
        self.alert_manager = get_alert_manager()
    
    def show_project_overview(self, project_name: str) -> None:
        """Show comprehensive project overview"""
        try:
            # Get health status
            health_data = self.health_checker.check_project_health(project_name)
            
            # Get metrics dashboard data
            metrics_data = self.metrics_collector.get_project_dashboard_data(project_name)
            
            # Get active alerts
            active_alerts = [
                alert for alert in self.alert_manager.get_active_alerts()
                if project_name in str(alert.labels)
            ]
            
            # Create layout
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=3)
            )
            
            layout["body"].split_row(
                Layout(name="left"),
                Layout(name="right")
            )
            
            layout["left"].split_column(
                Layout(name="health", ratio=1),
                Layout(name="metrics", ratio=2)
            )
            
            layout["right"].split_column(
                Layout(name="alerts", ratio=1),
                Layout(name="containers", ratio=2)
            )
            
            # Header
            header_text = Text(f"BlastDock Monitoring Dashboard - {project_name}", style="bold blue")
            layout["header"].update(Panel(header_text, style="blue"))
            
            # Health status
            health_panel = self._create_health_panel(health_data)
            layout["health"].update(health_panel)
            
            # Metrics overview
            metrics_panel = self._create_metrics_panel(metrics_data)
            layout["metrics"].update(metrics_panel)
            
            # Alerts
            alerts_panel = self._create_alerts_panel(active_alerts)
            layout["alerts"].update(alerts_panel)
            
            # Container details
            containers_panel = self._create_containers_panel(health_data.get('services', {}))
            layout["containers"].update(containers_panel)
            
            # Footer
            footer_text = Text(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
            layout["footer"].update(Panel(footer_text, style="dim"))
            
            self.console.print(layout)
            
        except Exception as e:
            self.logger.error(f"Error creating project overview: {e}")
            self.console.print(f"[red]Error creating dashboard: {e}[/red]")
    
    def _create_health_panel(self, health_data: Dict[str, Any]) -> Panel:
        """Create health status panel"""
        status = health_data.get('overall_status', 'unknown')
        message = health_data.get('message', 'No status available')
        
        # Color based on status
        if status == HealthStatus.HEALTHY.value:
            color = "green"
            icon = "✓"
        elif status == HealthStatus.DEGRADED.value:
            color = "yellow" 
            icon = "⚠"
        elif status == HealthStatus.UNHEALTHY.value:
            color = "red"
            icon = "✗"
        else:
            color = "white"
            icon = "?"
        
        content = Text()
        content.append(f"{icon} {status.upper()}\n", style=f"bold {color}")
        content.append(f"{message}\n\n", style=color)
        content.append(f"Response: {health_data.get('duration_ms', 0):.1f}ms", style="dim")
        
        return Panel(content, title="Health Status", border_style=color)
    
    def _create_metrics_panel(self, metrics_data: Dict[str, Any]) -> Panel:
        """Create metrics overview panel"""
        if 'error' in metrics_data:
            return Panel(f"Error: {metrics_data['error']}", title="Metrics", border_style="red")
        
        metrics = metrics_data.get('metrics', {})
        
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Current", style="white")
        table.add_column("Avg", style="blue")
        table.add_column("Max", style="red")
        
        # Key metrics to display
        key_metrics = [
            ('project_container_count', 'Containers'),
            ('project_running_containers', 'Running'),
            ('project_cpu_total_percent', 'CPU %'),
            ('project_memory_total_mb', 'Memory MB')
        ]
        
        for metric_name, display_name in key_metrics:
            if metric_name in metrics:
                summary = metrics[metric_name].get('summary', {})
                recent = metrics[metric_name].get('recent_values', [])
                
                current = recent[-1]['value'] if recent else 0
                avg = summary.get('avg', 0)
                max_val = summary.get('max', 0)
                
                # Format values
                if 'percent' in metric_name:
                    current_str = f"{current:.1f}%"
                    avg_str = f"{avg:.1f}%"
                    max_str = f"{max_val:.1f}%"
                elif 'mb' in metric_name:
                    current_str = f"{current:.0f}MB"
                    avg_str = f"{avg:.0f}MB"
                    max_str = f"{max_val:.0f}MB"
                else:
                    current_str = f"{current:.0f}"
                    avg_str = f"{avg:.0f}"
                    max_str = f"{max_val:.0f}"
                
                table.add_row(display_name, current_str, avg_str, max_str)
        
        return Panel(table, title="Metrics Overview", border_style="blue")
    
    def _create_alerts_panel(self, alerts: List[Any]) -> Panel:
        """Create alerts panel"""
        if not alerts:
            content = Text("No active alerts", style="green")
            return Panel(content, title="Alerts", border_style="green")
        
        content = Text()
        for alert in alerts[:5]:  # Show first 5 alerts
            severity = alert.severity.value
            if severity == "critical":
                style = "bold red"
                icon = "🔴"
            elif severity == "warning":
                style = "yellow"
                icon = "🟡"
            else:
                style = "blue"
                icon = "🔵"
            
            content.append(f"{icon} ", style=style)
            content.append(f"{alert.rule_name}\n", style=style)
            content.append(f"  {alert.message}\n", style="dim")
        
        if len(alerts) > 5:
            content.append(f"\n... and {len(alerts) - 5} more alerts", style="dim")
        
        return Panel(content, title="Active Alerts", border_style="red" if alerts else "green")
    
    def _create_containers_panel(self, services: Dict[str, Any]) -> Panel:
        """Create containers panel"""
        if not services:
            content = Text("No containers found", style="yellow")
            return Panel(content, title="Containers", border_style="yellow")
        
        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Container", style="cyan")
        table.add_column("Status", style="white")
        table.add_column("CPU %", style="blue")
        table.add_column("Memory", style="green")
        
        for service_name, service_info in services.items():
            status = service_info.get('status', 'unknown')
            details = service_info.get('details', {})
            
            # Status with color
            if status == 'healthy':
                status_text = Text("✓ Healthy", style="green")
            elif status == 'degraded':
                status_text = Text("⚠ Degraded", style="yellow")
            elif status == 'unhealthy':
                status_text = Text("✗ Unhealthy", style="red")
            else:
                status_text = Text("? Unknown", style="white")
            
            # Resource usage
            cpu_percent = details.get('cpu_percent', 0)
            memory_percent = details.get('memory_percent', 0)
            
            cpu_str = f"{cpu_percent:.1f}%" if cpu_percent > 0 else "-"
            memory_str = f"{memory_percent:.1f}%" if memory_percent > 0 else "-"
            
            table.add_row(
                service_name,
                status_text,
                cpu_str,
                memory_str
            )
        
        return Panel(table, title="Container Status", border_style="blue")
    
    def show_system_overview(self) -> None:
        """Show system-wide overview"""
        try:
            # Get system metrics
            system_metrics = self.metrics_collector.get_all_metrics()
            
            # Get all active alerts
            active_alerts = self.alert_manager.get_active_alerts()
            
            # Get alert statistics
            alert_stats = self.alert_manager.get_statistics()
            
            # Create main layout
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=3)
            )
            
            layout["body"].split_row(
                Layout(name="metrics"),
                Layout(name="alerts")
            )
            
            # Header
            header = Text("BlastDock System Overview", style="bold blue")
            layout["header"].update(Panel(header, style="blue"))
            
            # System metrics
            metrics_panel = self._create_system_metrics_panel(system_metrics)
            layout["metrics"].update(metrics_panel)
            
            # System alerts
            alerts_panel = self._create_system_alerts_panel(active_alerts, alert_stats)
            layout["alerts"].update(alerts_panel)
            
            # Footer
            footer = Text(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
            layout["footer"].update(Panel(footer, style="dim"))
            
            self.console.print(layout)
            
        except Exception as e:
            self.logger.error(f"Error creating system overview: {e}")
            self.console.print(f"[red]Error creating system dashboard: {e}[/red]")
    
    def _create_system_metrics_panel(self, metrics: Dict[str, Any]) -> Panel:
        """Create system metrics panel"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="white")
        table.add_column("Description", style="blue")
        
        system_metrics = [
            ('system_containers_total', 'Total Containers'),
            ('system_images_total', 'Total Images'),
            ('system_volumes_total', 'Total Volumes'),
            ('system_networks_total', 'Total Networks')
        ]
        
        for metric_name, description in system_metrics:
            if metric_name in metrics:
                metric_info = metrics[metric_name]
                count = metric_info.get('point_count', 0)
                table.add_row(description, str(count), metric_info.get('description', ''))
        
        return Panel(table, title="System Metrics", border_style="blue")
    
    def _create_system_alerts_panel(self, alerts: List[Any], stats: Dict[str, Any]) -> Panel:
        """Create system alerts panel"""
        content = Text()
        
        # Alert statistics
        content.append("Alert Statistics:\n", style="bold")
        content.append(f"  Active: {stats.get('active_alerts_current', 0)}\n", style="red")
        content.append(f"  Total: {stats.get('total_alerts', 0)}\n", style="blue")
        content.append(f"  Resolved: {stats.get('resolved_alerts', 0)}\n", style="green")
        content.append(f"  Rules: {stats.get('enabled_rules', 0)}/{stats.get('rules_count', 0)}\n\n", style="yellow")
        
        # Recent alerts
        if alerts:
            content.append("Recent Alerts:\n", style="bold")
            for alert in alerts[:3]:  # Show first 3
                severity_color = {
                    'critical': 'red',
                    'warning': 'yellow',
                    'info': 'blue'
                }.get(alert.severity.value, 'white')
                
                content.append(f"  • {alert.rule_name}\n", style=severity_color)
                content.append(f"    {alert.message}\n", style="dim")
        else:
            content.append("No active alerts\n", style="green")
        
        return Panel(content, title="Alert Status", border_style="red" if alerts else "green")
    
    def show_live_monitoring(self, project_name: str, refresh_interval: float = 5.0):
        """Show live monitoring dashboard with auto-refresh"""
        try:
            with Live(console=self.console, refresh_per_second=1/refresh_interval) as live:
                while True:
                    # Create fresh dashboard
                    self.show_project_overview(project_name)
                    time.sleep(refresh_interval)
        except KeyboardInterrupt:
            self.console.print("\n[dim]Live monitoring stopped[/dim]")
        except Exception as e:
            self.logger.error(f"Error in live monitoring: {e}")
            self.console.print(f"[red]Live monitoring error: {e}[/red]")
    
    def export_dashboard_data(self, project_name: str = None) -> Dict[str, Any]:
        """Export dashboard data for external use"""
        try:
            export_data = {
                'timestamp': time.time(),
                'export_time': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if project_name:
                # Project-specific export
                export_data['project'] = project_name
                export_data['health'] = self.health_checker.check_project_health(project_name)
                export_data['metrics'] = self.metrics_collector.get_project_dashboard_data(project_name)
                export_data['alerts'] = [
                    {
                        'rule_name': alert.rule_name,
                        'severity': alert.severity.value,
                        'message': alert.message,
                        'status': alert.status.value,
                        'fired_at': alert.fired_at
                    }
                    for alert in self.alert_manager.get_active_alerts()
                    if project_name in str(alert.labels)
                ]
            else:
                # System-wide export
                export_data['system_metrics'] = self.metrics_collector.get_all_metrics()
                export_data['alert_stats'] = self.alert_manager.get_statistics()
                export_data['active_alerts'] = [
                    {
                        'rule_name': alert.rule_name,
                        'severity': alert.severity.value,
                        'message': alert.message,
                        'status': alert.status.value,
                        'fired_at': alert.fired_at,
                        'labels': alert.labels
                    }
                    for alert in self.alert_manager.get_active_alerts()
                ]
            
            return export_data
            
        except Exception as e:
            self.logger.error(f"Error exporting dashboard data: {e}")
            return {'error': str(e), 'timestamp': time.time()}


# Global dashboard instance
_monitoring_dashboard = None


def get_monitoring_dashboard() -> MonitoringDashboard:
    """Get global monitoring dashboard instance"""
    global _monitoring_dashboard
    if _monitoring_dashboard is None:
        _monitoring_dashboard = MonitoringDashboard()
    return _monitoring_dashboard