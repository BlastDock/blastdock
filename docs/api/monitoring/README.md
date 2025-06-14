# Monitoring API Reference

The Monitoring API provides comprehensive monitoring, metrics collection, health checking, and alerting capabilities for BlastDock deployments.

## Classes Overview

- **[HealthChecker](#healthchecker)** - Service health monitoring and validation
- **[MetricsCollector](#metricscollector)** - Performance metrics collection and analysis
- **[AlertManager](#alertmanager)** - Alert management and notification system
- **[LogAnalyzer](#loganalyzer)** - Log analysis and pattern detection
- **[MonitoringDashboard](#monitoringdashboard)** - Real-time monitoring dashboard

## HealthChecker

The `HealthChecker` class provides comprehensive health monitoring for services and infrastructure.

### Class Definition

```python
from blastdock.monitoring import HealthChecker

health_checker = HealthChecker(
    check_interval=30,  # seconds
    timeout=10,        # seconds
    retry_attempts=3
)
```

### Methods

#### check_service_health()

Perform comprehensive health check on a service.

```python
def check_service_health(
    self,
    service_name: str,
    project_name: str,
    deep_check: bool = False
) -> Dict[str, Any]:
    """
    Check health of a specific service.
    
    Args:
        service_name: Name of service to check
        project_name: Project containing the service
        deep_check: Perform detailed health analysis
    
    Returns:
        Service health status and metrics
    """
```

**Example Usage:**

```python
from blastdock.monitoring import HealthChecker

health_checker = HealthChecker()

# Basic health check
health = health_checker.check_service_health(
    service_name="wordpress",
    project_name="my-blog"
)

print(f"🏥 Health Check: {health['service_name']}")
print(f"   Status: {'✅ Healthy' if health['healthy'] else '❌ Unhealthy'}")
print(f"   Response Time: {health['response_time']:.0f}ms")
print(f"   Uptime: {health['uptime_percentage']:.1f}%")

if not health['healthy']:
    print("❌ Issues Found:")
    for issue in health['issues']:
        print(f"   • {issue['type']}: {issue['description']}")

# Deep health check with detailed metrics
deep_health = health_checker.check_service_health(
    service_name="wordpress",
    project_name="my-blog",
    deep_check=True
)

if 'performance_metrics' in deep_health:
    metrics = deep_health['performance_metrics']
    print(f"\n📊 Performance Metrics:")
    print(f"   CPU Usage: {metrics['cpu_usage']:.1f}%")
    print(f"   Memory Usage: {metrics['memory_usage']:.1f}%")
    print(f"   Disk I/O: {metrics['disk_io']:.1f} MB/s")
    print(f"   Network I/O: {metrics['network_io']:.1f} MB/s")

# Health trend analysis
if 'trend_analysis' in deep_health:
    trend = deep_health['trend_analysis']
    print(f"\n📈 Health Trends (24h):")
    print(f"   Availability: {trend['availability_trend']}")
    print(f"   Performance: {trend['performance_trend']}")
    print(f"   Error Rate: {trend['error_rate_trend']}")
```

#### check_project_health()

Perform comprehensive health check on entire project.

```python
def check_project_health(
    self,
    project_name: str,
    include_dependencies: bool = True
) -> Dict[str, Any]:
    """
    Check health of entire project.
    
    Args:
        project_name: Name of project to check
        include_dependencies: Include dependency health checks
    
    Returns:
        Project health status and service breakdown
    """
```

**Example Usage:**

```python
# Project-wide health check
project_health = health_checker.check_project_health(
    project_name="production-ecommerce",
    include_dependencies=True
)

print(f"🏥 Project Health: {project_health['project_name']}")
print(f"   Overall Score: {project_health['health_score']}/100")
print(f"   Status: {project_health['overall_status']}")
print(f"   Services: {len(project_health['services'])} total")

# Service breakdown
healthy_services = [s for s in project_health['services'] if s['healthy']]
unhealthy_services = [s for s in project_health['services'] if not s['healthy']]

print(f"   ✅ Healthy: {len(healthy_services)}")
print(f"   ❌ Unhealthy: {len(unhealthy_services)}")

# Show unhealthy services details
if unhealthy_services:
    print("\n🚨 Unhealthy Services:")
    for service in unhealthy_services:
        print(f"   📦 {service['name']}")
        print(f"      Status: {service['status']}")
        print(f"      Issues: {len(service['issues'])}")
        for issue in service['issues'][:2]:  # Show first 2 issues
            print(f"        • {issue}")

# Dependency analysis
if 'dependencies' in project_health:
    deps = project_health['dependencies']
    print(f"\n🔗 Dependencies:")
    for dep_name, dep_status in deps.items():
        status_icon = "✅" if dep_status['available'] else "❌"
        print(f"   {status_icon} {dep_name}: {dep_status['status']}")
```

#### start_continuous_monitoring()

Start continuous health monitoring with automatic alerting.

```python
def start_continuous_monitoring(
    self,
    projects: List[str],
    alert_callback: Optional[Callable] = None,
    monitoring_config: Optional[Dict] = None
) -> str:
    """
    Start continuous health monitoring.
    
    Args:
        projects: List of project names to monitor
        alert_callback: Function to call when alerts are triggered
        monitoring_config: Custom monitoring configuration
    
    Returns:
        Monitoring session ID
    """
```

**Example Usage:**

```python
def custom_alert_handler(alert_data):
    """Custom alert handler function."""
    severity = alert_data['severity']
    project = alert_data['project']
    service = alert_data['service']
    message = alert_data['message']
    
    print(f"🚨 ALERT [{severity}] {project}/{service}: {message}")
    
    # Send to Slack, email, etc.
    if severity in ['critical', 'high']:
        send_slack_alert(alert_data)
        send_email_alert(alert_data)

# Start monitoring multiple projects
monitoring_config = {
    "check_interval": 60,  # Check every minute
    "alert_thresholds": {
        "response_time": 5000,  # 5 seconds
        "cpu_usage": 80,        # 80%
        "memory_usage": 85,     # 85%
        "error_rate": 5         # 5%
    },
    "escalation_rules": {
        "critical": {"immediate": True, "retry_interval": 300},
        "high": {"delay": 60, "retry_interval": 600},
        "medium": {"delay": 300, "retry_interval": 1800}
    }
}

session_id = health_checker.start_continuous_monitoring(
    projects=["production-web", "production-api", "production-db"],
    alert_callback=custom_alert_handler,
    monitoring_config=monitoring_config
)

print(f"📊 Continuous monitoring started: {session_id}")

# Monitor for some time
try:
    import time
    print("Monitoring active... Press Ctrl+C to stop")
    while True:
        time.sleep(10)
        
        # Get current monitoring status
        status = health_checker.get_monitoring_status(session_id)
        print(f"📊 Monitoring: {status['checked_services']} services, "
              f"{status['active_alerts']} active alerts")
        
except KeyboardInterrupt:
    print("\n🛑 Stopping monitoring...")
    health_checker.stop_monitoring(session_id)
```

## MetricsCollector

The `MetricsCollector` class handles collection and analysis of performance metrics.

### Class Definition

```python
from blastdock.monitoring import MetricsCollector

metrics_collector = MetricsCollector(
    collection_interval=30,  # seconds
    retention_period="30d",  # 30 days
    aggregation_window="5m"  # 5 minutes
)
```

### Methods

#### collect_system_metrics()

Collect comprehensive system metrics.

```python
def collect_system_metrics(
    self,
    project_name: str,
    services: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Collect system metrics for project services.
    
    Args:
        project_name: Name of project
        services: Specific services to collect metrics for
    
    Returns:
        Collected metrics data
    """
```

**Example Usage:**

```python
from blastdock.monitoring import MetricsCollector

metrics_collector = MetricsCollector()

# Collect metrics for entire project
metrics = metrics_collector.collect_system_metrics(
    project_name="production-app"
)

print(f"📊 System Metrics: {metrics['project_name']}")
print(f"   Collection Time: {metrics['timestamp']}")
print(f"   Services Monitored: {len(metrics['services'])}")

# Overall resource utilization
overall = metrics['overall_metrics']
print(f"\n🔄 Overall Resource Utilization:")
print(f"   CPU Usage: {overall['cpu_usage']:.1f}%")
print(f"   Memory Usage: {overall['memory_usage']:.1f}%")
print(f"   Disk Usage: {overall['disk_usage']:.1f}%")
print(f"   Network I/O: {overall['network_io']:.1f} MB/s")

# Service-specific metrics
for service_name, service_metrics in metrics['services'].items():
    print(f"\n📦 {service_name}:")
    print(f"   CPU: {service_metrics['cpu_percent']:.1f}%")
    print(f"   Memory: {service_metrics['memory_usage']:.1f} MB")
    print(f"   Connections: {service_metrics.get('connections', 'N/A')}")
    
    # Application-specific metrics
    if 'app_metrics' in service_metrics:
        app_metrics = service_metrics['app_metrics']
        if 'requests_per_second' in app_metrics:
            print(f"   Requests/sec: {app_metrics['requests_per_second']:.1f}")
        if 'response_time' in app_metrics:
            print(f"   Avg Response: {app_metrics['response_time']:.0f}ms")
```

#### get_performance_trends()

Get performance trends and analysis over time.

```python
def get_performance_trends(
    self,
    project_name: str,
    time_range: str = "24h",
    metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get performance trends over specified time range.
    
    Args:
        project_name: Name of project
        time_range: Time range (1h, 6h, 24h, 7d, 30d)
        metrics: Specific metrics to analyze
    
    Returns:
        Trend analysis data
    """
```

**Example Usage:**

```python
# Get 24-hour performance trends
trends = metrics_collector.get_performance_trends(
    project_name="production-app",
    time_range="24h",
    metrics=["cpu_usage", "memory_usage", "response_time", "error_rate"]
)

print(f"📈 Performance Trends (24h): {trends['project_name']}")
print(f"   Data Points: {trends['data_points']}")
print(f"   Analysis Period: {trends['start_time']} to {trends['end_time']}")

# Trend analysis for each metric
for metric_name, metric_data in trends['metrics'].items():
    trend_direction = metric_data['trend']  # increasing/decreasing/stable
    
    trend_icon = {
        'increasing': '📈',
        'decreasing': '📉',
        'stable': '➡️'
    }.get(trend_direction, '❓')
    
    print(f"\n{trend_icon} {metric_name.title()}:")
    print(f"   Current: {metric_data['current_value']}")
    print(f"   Average: {metric_data['average_value']:.1f}")
    print(f"   Peak: {metric_data['peak_value']}")
    print(f"   Trend: {trend_direction} ({metric_data['trend_percentage']:+.1f}%)")
    
    # Anomaly detection
    if metric_data.get('anomalies'):
        print(f"   🚨 Anomalies: {len(metric_data['anomalies'])} detected")
        for anomaly in metric_data['anomalies'][:2]:
            print(f"      • {anomaly['timestamp']}: {anomaly['description']}")

# Performance predictions
if 'predictions' in trends:
    print(f"\n🔮 Performance Predictions:")
    for metric, prediction in trends['predictions'].items():
        print(f"   {metric}: {prediction['next_hour']} (confidence: {prediction['confidence']:.0f}%)")
```

#### create_custom_dashboard()

Create custom monitoring dashboard with specific metrics.

```python
def create_custom_dashboard(
    self,
    dashboard_config: Dict[str, Any],
    projects: List[str]
) -> str:
    """
    Create custom monitoring dashboard.
    
    Args:
        dashboard_config: Dashboard configuration
        projects: Projects to include in dashboard
    
    Returns:
        Dashboard URL or file path
    """
```

**Example Usage:**

```python
# Define custom dashboard configuration
dashboard_config = {
    "name": "Production Overview",
    "refresh_interval": 30,  # seconds
    "layout": "grid",
    "widgets": [
        {
            "type": "metric_chart",
            "title": "CPU Usage",
            "metrics": ["cpu_usage"],
            "chart_type": "line",
            "time_range": "1h",
            "size": "medium"
        },
        {
            "type": "metric_gauge",
            "title": "Memory Usage",
            "metrics": ["memory_usage"],
            "thresholds": {"warning": 70, "critical": 85},
            "size": "small"
        },
        {
            "type": "service_status",
            "title": "Service Health",
            "show_all_services": True,
            "size": "large"
        },
        {
            "type": "alert_feed",
            "title": "Recent Alerts",
            "max_alerts": 10,
            "severity_filter": ["high", "critical"],
            "size": "medium"
        },
        {
            "type": "performance_summary",
            "title": "Performance KPIs",
            "metrics": ["response_time", "throughput", "error_rate"],
            "time_range": "24h",
            "size": "large"
        }
    ],
    "alerting": {
        "enabled": True,
        "notification_channels": ["slack", "email"]
    }
}

# Create dashboard
dashboard_url = metrics_collector.create_custom_dashboard(
    dashboard_config=dashboard_config,
    projects=["production-web", "production-api", "production-db"]
)

print(f"📊 Custom dashboard created: {dashboard_url}")

# Export dashboard for sharing
export_config = metrics_collector.export_dashboard_config(dashboard_url)
print(f"💾 Dashboard config exported for sharing")
```

## AlertManager

The `AlertManager` class handles alert configuration, triggering, and notification routing.

### Class Definition

```python
from blastdock.monitoring import AlertManager

alert_manager = AlertManager(
    notification_channels=["email", "slack", "webhook"],
    escalation_enabled=True,
    alert_grouping=True
)
```

### Methods

#### create_alert_rule()

Create custom alert rules with conditions and actions.

```python
def create_alert_rule(
    self,
    rule_name: str,
    conditions: List[Dict[str, Any]],
    actions: List[Dict[str, Any]],
    severity: str = "medium"
) -> str:
    """
    Create custom alert rule.
    
    Args:
        rule_name: Name of the alert rule
        conditions: List of conditions that trigger the alert
        actions: Actions to take when alert is triggered
        severity: Alert severity level
    
    Returns:
        Alert rule ID
    """
```

**Example Usage:**

```python
from blastdock.monitoring import AlertManager

alert_manager = AlertManager()

# Create high CPU usage alert
high_cpu_rule = alert_manager.create_alert_rule(
    rule_name="High CPU Usage",
    conditions=[
        {
            "metric": "cpu_usage",
            "operator": "greater_than",
            "value": 80,
            "duration": "5m"  # Sustained for 5 minutes
        }
    ],
    actions=[
        {
            "type": "notification",
            "channels": ["slack", "email"],
            "message": "🚨 High CPU usage detected: {{value}}% on {{service}}"
        },
        {
            "type": "auto_scale",
            "enabled": True,
            "scale_factor": 1.5
        }
    ],
    severity="high"
)

# Create disk space alert
disk_space_rule = alert_manager.create_alert_rule(
    rule_name="Low Disk Space",
    conditions=[
        {
            "metric": "disk_usage",
            "operator": "greater_than",
            "value": 90,
            "duration": "1m"
        }
    ],
    actions=[
        {
            "type": "notification",
            "channels": ["slack", "pagerduty"],
            "message": "💽 Critical: Disk usage {{value}}% on {{service}}"
        },
        {
            "type": "log_cleanup",
            "enabled": True,
            "retention_days": 7
        }
    ],
    severity="critical"
)

# Create composite alert (multiple conditions)
service_health_rule = alert_manager.create_alert_rule(
    rule_name="Service Degradation",
    conditions=[
        {
            "metric": "response_time",
            "operator": "greater_than",
            "value": 5000,  # 5 seconds
            "duration": "3m"
        },
        {
            "metric": "error_rate",
            "operator": "greater_than",
            "value": 5,  # 5%
            "duration": "2m"
        }
    ],
    actions=[
        {
            "type": "notification",
            "channels": ["slack"],
            "message": "⚠️ Service degradation detected on {{service}}"
        },
        {
            "type": "health_check",
            "enabled": True,
            "deep_check": True
        }
    ],
    severity="medium"
)

print(f"✅ Alert rules created:")
print(f"   • High CPU: {high_cpu_rule}")
print(f"   • Disk Space: {disk_space_rule}")
print(f"   • Service Health: {service_health_rule}")
```

#### configure_notification_channels()

Configure notification channels for alerts.

```python
def configure_notification_channels(
    self,
    channels: Dict[str, Dict[str, Any]]
) -> None:
    """
    Configure notification channels.
    
    Args:
        channels: Channel configurations
    """
```

**Example Usage:**

```python
# Configure notification channels
notification_config = {
    "slack": {
        "webhook_url": "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK",
        "channel": "#alerts",
        "username": "BlastDock Monitor",
        "icon_emoji": ":warning:",
        "severity_mapping": {
            "critical": "@channel",
            "high": "@here",
            "medium": "",
            "low": ""
        }
    },
    "email": {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "username": "alerts@company.com",
        "password": "app_password",
        "to_addresses": {
            "critical": ["oncall@company.com", "cto@company.com"],
            "high": ["devops@company.com"],
            "medium": ["team@company.com"],
            "low": ["logs@company.com"]
        },
        "from_address": "BlastDock Monitor <alerts@company.com>"
    },
    "webhook": {
        "url": "https://api.company.com/alerts",
        "headers": {
            "Authorization": "Bearer YOUR_API_TOKEN",
            "Content-Type": "application/json"
        },
        "payload_template": {
            "alert_id": "{{alert_id}}",
            "severity": "{{severity}}",
            "service": "{{service}}",
            "message": "{{message}}",
            "timestamp": "{{timestamp}}",
            "project": "{{project}}"
        }
    },
    "pagerduty": {
        "integration_key": "YOUR_PAGERDUTY_INTEGRATION_KEY",
        "severity_mapping": {
            "critical": "critical",
            "high": "error",
            "medium": "warning",
            "low": "info"
        }
    }
}

alert_manager.configure_notification_channels(notification_config)
print("📢 Notification channels configured successfully")

# Test notification channels
test_alert = {
    "rule_name": "Test Alert",
    "severity": "medium",
    "message": "This is a test alert to verify notification channels",
    "service": "test-service",
    "project": "test-project"
}

alert_manager.send_test_notification(test_alert, channels=["slack"])
print("📧 Test notification sent")
```

#### get_alert_history()

Get alert history and statistics.

```python
def get_alert_history(
    self,
    time_range: str = "24h",
    severity_filter: Optional[List[str]] = None,
    project_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get alert history and statistics.
    
    Args:
        time_range: Time range to query
        severity_filter: Filter by severity levels
        project_filter: Filter by project name
    
    Returns:
        Alert history and statistics
    """
```

**Example Usage:**

```python
# Get alert history for last 24 hours
alert_history = alert_manager.get_alert_history(
    time_range="24h",
    severity_filter=["critical", "high"],
    project_filter="production-app"
)

print(f"📊 Alert History (24h): {alert_history['project']}")
print(f"   Total Alerts: {alert_history['total_alerts']}")
print(f"   By Severity:")
for severity, count in alert_history['by_severity'].items():
    severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    icon = severity_icon.get(severity, "⚪")
    print(f"     {icon} {severity.title()}: {count}")

# Alert trends
trends = alert_history['trends']
print(f"\n📈 Alert Trends:")
print(f"   Frequency: {trends['frequency_trend']}")  # increasing/decreasing
print(f"   Most Common: {trends['most_common_alert']}")
print(f"   Avg Resolution Time: {trends['avg_resolution_time']}")

# Recent critical alerts
if alert_history['recent_critical']:
    print(f"\n🚨 Recent Critical Alerts:")
    for alert in alert_history['recent_critical'][:3]:
        print(f"   • {alert['timestamp']}: {alert['rule_name']}")
        print(f"     Service: {alert['service']}")
        print(f"     Status: {alert['status']}")

# Alert patterns
if 'patterns' in alert_history:
    patterns = alert_history['patterns']
    print(f"\n🔍 Alert Patterns:")
    for pattern in patterns:
        print(f"   • {pattern['description']} (confidence: {pattern['confidence']:.0f}%)")
```

## Advanced Monitoring Examples

### Comprehensive Monitoring Setup

```python
from blastdock.monitoring import HealthChecker, MetricsCollector, AlertManager
import threading
import time

def setup_comprehensive_monitoring():
    """Setup comprehensive monitoring for production environment."""
    
    # Initialize monitoring components
    health_checker = HealthChecker()
    metrics_collector = MetricsCollector()
    alert_manager = AlertManager()
    
    # Production projects to monitor
    projects = ["production-web", "production-api", "production-db"]
    
    print("🚀 Setting up comprehensive monitoring...")
    
    # 1. Configure alert rules
    print("1️⃣ Configuring alert rules...")
    
    # Critical infrastructure alerts
    critical_rules = [
        {
            "name": "Service Down",
            "conditions": [{"metric": "service_availability", "operator": "less_than", "value": 100}],
            "actions": [{"type": "notification", "channels": ["pagerduty", "slack"]}],
            "severity": "critical"
        },
        {
            "name": "High Error Rate",
            "conditions": [{"metric": "error_rate", "operator": "greater_than", "value": 10, "duration": "2m"}],
            "actions": [{"type": "notification", "channels": ["slack", "email"]}],
            "severity": "high"
        },
        {
            "name": "Resource Exhaustion",
            "conditions": [
                {"metric": "cpu_usage", "operator": "greater_than", "value": 90, "duration": "5m"},
                {"metric": "memory_usage", "operator": "greater_than", "value": 95, "duration": "3m"}
            ],
            "actions": [
                {"type": "notification", "channels": ["slack"]},
                {"type": "auto_scale", "enabled": True}
            ],
            "severity": "high"
        }
    ]
    
    for rule in critical_rules:
        rule_id = alert_manager.create_alert_rule(**rule)
        print(f"   ✅ {rule['name']}: {rule_id}")
    
    # 2. Start continuous health monitoring
    print("2️⃣ Starting health monitoring...")
    
    def health_monitor_worker():
        while True:
            for project in projects:
                try:
                    health = health_checker.check_project_health(project)
                    
                    # Log health status
                    if health['health_score'] < 80:
                        print(f"⚠️ {project} health score: {health['health_score']}/100")
                    
                    # Check for unhealthy services
                    unhealthy = [s for s in health['services'] if not s['healthy']]
                    if unhealthy:
                        for service in unhealthy:
                            alert_manager.trigger_alert({
                                "rule_name": "Service Health Check Failed",
                                "severity": "medium",
                                "project": project,
                                "service": service['name'],
                                "message": f"Service {service['name']} is unhealthy"
                            })
                    
                except Exception as e:
                    print(f"❌ Health check error for {project}: {e}")
            
            time.sleep(60)  # Check every minute
    
    # 3. Start metrics collection
    print("3️⃣ Starting metrics collection...")
    
    def metrics_worker():
        while True:
            for project in projects:
                try:
                    metrics = metrics_collector.collect_system_metrics(project)
                    
                    # Check metric thresholds
                    overall = metrics['overall_metrics']
                    
                    if overall['cpu_usage'] > 80:
                        alert_manager.trigger_alert({
                            "rule_name": "High CPU Usage",
                            "severity": "high",
                            "project": project,
                            "message": f"CPU usage: {overall['cpu_usage']:.1f}%"
                        })
                    
                    if overall['memory_usage'] > 85:
                        alert_manager.trigger_alert({
                            "rule_name": "High Memory Usage",
                            "severity": "high",
                            "project": project,
                            "message": f"Memory usage: {overall['memory_usage']:.1f}%"
                        })
                    
                except Exception as e:
                    print(f"❌ Metrics collection error for {project}: {e}")
            
            time.sleep(30)  # Collect every 30 seconds
    
    # Start monitoring threads
    health_thread = threading.Thread(target=health_monitor_worker, daemon=True)
    metrics_thread = threading.Thread(target=metrics_worker, daemon=True)
    
    health_thread.start()
    metrics_thread.start()
    
    print("✅ Comprehensive monitoring active!")
    print("📊 Monitor dashboard: http://localhost:8080/dashboard")
    
    return {
        "health_checker": health_checker,
        "metrics_collector": metrics_collector,
        "alert_manager": alert_manager,
        "threads": [health_thread, metrics_thread]
    }

# Setup and run monitoring
monitoring_setup = setup_comprehensive_monitoring()

# Keep monitoring running
try:
    while True:
        time.sleep(10)
        # Print status update
        print("📊 Monitoring active... (Ctrl+C to stop)")
except KeyboardInterrupt:
    print("\n🛑 Stopping monitoring...")
```

### Real-time Monitoring Dashboard

```python
from blastdock.monitoring import MonitoringDashboard
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
import time

def create_realtime_dashboard():
    """Create real-time monitoring dashboard with Rich UI."""
    
    console = Console()
    dashboard = MonitoringDashboard()
    
    def make_layout():
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="services"),
            Layout(name="metrics")
        )
        
        layout["right"].split_column(
            Layout(name="alerts"),
            Layout(name="logs")
        )
        
        return layout
    
    def update_dashboard():
        layout = make_layout()
        
        # Header
        header = Panel(
            "🔒 BlastDock Production Monitoring Dashboard",
            style="bold blue"
        )
        layout["header"].update(header)
        
        # Services status
        services_table = Table(title="🔧 Services Status")
        services_table.add_column("Service", style="cyan")
        services_table.add_column("Status", style="green")
        services_table.add_column("Health", style="yellow")
        services_table.add_column("Response", style="blue")
        
        # Get service data
        services_data = dashboard.get_services_status()
        for service in services_data:
            status_icon = "🟢" if service['healthy'] else "🔴"
            services_table.add_row(
                service['name'],
                f"{status_icon} {service['status']}",
                f"{service['health_score']}/100",
                f"{service['response_time']:.0f}ms"
            )
        
        layout["services"].update(Panel(services_table))
        
        # Metrics
        metrics_data = dashboard.get_current_metrics()
        metrics_content = f"""
📊 System Metrics:
   CPU Usage: {metrics_data['cpu_usage']:.1f}%
   Memory Usage: {metrics_data['memory_usage']:.1f}%
   Disk Usage: {metrics_data['disk_usage']:.1f}%
   Network I/O: {metrics_data['network_io']:.1f} MB/s

📈 Performance:
   Avg Response Time: {metrics_data['avg_response_time']:.0f}ms
   Requests/sec: {metrics_data['requests_per_second']:.1f}
   Error Rate: {metrics_data['error_rate']:.2f}%
   Uptime: {metrics_data['uptime_percentage']:.1f}%
        """.strip()
        
        layout["metrics"].update(Panel(metrics_content, title="📊 Metrics"))
        
        # Active alerts
        alerts_table = Table(title="🚨 Active Alerts")
        alerts_table.add_column("Time", style="yellow")
        alerts_table.add_column("Severity", style="red")
        alerts_table.add_column("Message", style="white")
        
        alerts_data = dashboard.get_active_alerts()
        for alert in alerts_data[-10:]:  # Last 10 alerts
            severity_color = {
                "critical": "bold red",
                "high": "red",
                "medium": "yellow",
                "low": "green"
            }.get(alert['severity'], "white")
            
            alerts_table.add_row(
                alert['timestamp'].strftime("%H:%M:%S"),
                f"[{severity_color}]{alert['severity'].upper()}[/{severity_color}]",
                alert['message']
            )
        
        layout["alerts"].update(Panel(alerts_table))
        
        # Recent logs
        logs_data = dashboard.get_recent_logs(limit=8)
        logs_content = "\n".join([
            f"{log['timestamp'].strftime('%H:%M:%S')} [{log['level']}] {log['message'][:50]}..."
            for log in logs_data
        ])
        
        layout["logs"].update(Panel(logs_content, title="📝 Recent Logs"))
        
        # Footer
        footer_text = f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')} | Press Ctrl+C to exit"
        layout["footer"].update(Panel(footer_text, style="dim"))
        
        return layout
    
    # Run live dashboard
    with Live(update_dashboard(), refresh_per_second=1) as live:
        try:
            while True:
                time.sleep(1)
                live.update(update_dashboard())
        except KeyboardInterrupt:
            console.print("\n👋 Dashboard stopped")

# Run the dashboard
create_realtime_dashboard()
```

## Next Steps

- 🎯 **[Performance API](../performance/)** - Performance optimization capabilities
- 🏗️ **[Templates API](../templates/)** - Template system and validation
- 💻 **[CLI API](../cli/)** - Command-line interface components
- 🔧 **[Utils API](../utils/)** - Utility functions and helpers