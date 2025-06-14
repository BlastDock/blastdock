# Core API Reference

The Core API provides the main functionality for template deployment, project management, and application monitoring.

## Classes Overview

- **[DeploymentManager](#deploymentmanager)** - Manages application deployments
- **[TemplateManager](#templatemanager)** - Handles template operations
- **[Monitor](#monitor)** - Application monitoring and health checks
- **[ProjectManager](#projectmanager)** - Project lifecycle management

## DeploymentManager

The `DeploymentManager` class is the primary interface for deploying and managing applications.

### Class Definition

```python
from blastdock.core.deployment_manager import DeploymentManager
from blastdock.types import DeploymentResult, DeploymentConfig

class DeploymentManager:
    def __init__(self, config_profile: str = "default"):
        """Initialize deployment manager with configuration profile."""
```

### Methods

#### deploy_template()

Deploy an application from a template.

```python
def deploy_template(
    self,
    template_name: str,
    project_name: str,
    domain: Optional[str] = None,
    variables: Optional[Dict[str, Any]] = None,
    traefik_enabled: bool = True,
    ssl_enabled: bool = True,
    **kwargs
) -> DeploymentResult:
    """
    Deploy an application from a template.
    
    Args:
        template_name: Name of the template to deploy
        project_name: Unique name for the project
        domain: Domain name for the application
        variables: Template variables and configuration
        traefik_enabled: Enable Traefik reverse proxy
        ssl_enabled: Enable SSL/TLS certificates
        **kwargs: Additional deployment options
    
    Returns:
        DeploymentResult: Result of the deployment operation
    
    Raises:
        DeploymentError: If deployment fails
        ValidationError: If parameters are invalid
    """
```

**Example Usage:**

```python
from blastdock.core import DeploymentManager

manager = DeploymentManager()

# Deploy WordPress with custom configuration
result = manager.deploy_template(
    template_name="wordpress",
    project_name="my-blog",
    domain="blog.example.com",
    variables={
        "mysql_password": "secure_password_123",
        "admin_email": "admin@example.com",
        "wordpress_title": "My Amazing Blog",
        "mysql_database": "wordpress_db"
    },
    traefik_enabled=True,
    ssl_enabled=True
)

if result.success:
    print(f"✅ Deployment successful!")
    print(f"📁 Project path: {result.project_path}")
    print(f"🌐 URL: {result.url}")
    print(f"⏱️  Duration: {result.duration:.1f}s")
else:
    print(f"❌ Deployment failed: {result.error}")
    for warning in result.warnings:
        print(f"⚠️  Warning: {warning}")
```

#### update_deployment()

Update an existing deployment.

```python
def update_deployment(
    self,
    project_name: str,
    variables: Optional[Dict[str, Any]] = None,
    restart_services: bool = False,
    update_images: bool = False
) -> DeploymentResult:
    """
    Update an existing deployment.
    
    Args:
        project_name: Name of the project to update
        variables: New template variables
        restart_services: Restart all services after update
        update_images: Pull latest container images
    
    Returns:
        DeploymentResult: Result of the update operation
    """
```

**Example Usage:**

```python
# Update deployment with new variables
result = manager.update_deployment(
    project_name="my-blog",
    variables={
        "wordpress_title": "My Updated Blog Title",
        "admin_email": "newemail@example.com"
    },
    restart_services=True,
    update_images=True
)

if result.success:
    print(f"✅ Update successful in {result.duration:.1f}s")
else:
    print(f"❌ Update failed: {result.error}")
```

#### remove_deployment()

Remove a deployment and clean up resources.

```python
def remove_deployment(
    self,
    project_name: str,
    remove_volumes: bool = False,
    remove_networks: bool = False,
    backup_data: bool = True
) -> DeploymentResult:
    """
    Remove a deployment and clean up resources.
    
    Args:
        project_name: Name of the project to remove
        remove_volumes: Remove associated volumes
        remove_networks: Remove custom networks
        backup_data: Create backup before removal
    
    Returns:
        DeploymentResult: Result of the removal operation
    """
```

**Example Usage:**

```python
# Remove deployment with backup
result = manager.remove_deployment(
    project_name="my-blog",
    remove_volumes=True,
    remove_networks=True,
    backup_data=True
)

if result.success:
    print(f"✅ Deployment removed successfully")
    if result.metadata.get('backup_path'):
        print(f"💾 Backup saved to: {result.metadata['backup_path']}")
else:
    print(f"❌ Removal failed: {result.error}")
```

#### list_deployments()

List all active deployments.

```python
def list_deployments(
    self,
    status_filter: Optional[str] = None,
    template_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all active deployments.
    
    Args:
        status_filter: Filter by deployment status
        template_filter: Filter by template name
    
    Returns:
        List of deployment information dictionaries
    """
```

**Example Usage:**

```python
# List all deployments
deployments = manager.list_deployments()

for deployment in deployments:
    print(f"📦 {deployment['name']} ({deployment['template']})")
    print(f"   Status: {deployment['status']}")
    print(f"   URL: {deployment['url']}")
    print(f"   Created: {deployment['created_at']}")

# List only WordPress deployments
wordpress_deployments = manager.list_deployments(template_filter="wordpress")
```

#### get_deployment_status()

Get detailed status of a deployment.

```python
def get_deployment_status(self, project_name: str) -> Dict[str, Any]:
    """
    Get detailed status of a deployment.
    
    Args:
        project_name: Name of the project
    
    Returns:
        Detailed status information
    """
```

**Example Usage:**

```python
status = manager.get_deployment_status("my-blog")

print(f"📊 Deployment Status for {status['name']}")
print(f"   Overall: {status['overall_status']}")
print(f"   Services: {len(status['services'])}")

for service in status['services']:
    print(f"   🔧 {service['name']}: {service['status']}")
    if service['status'] != 'running':
        print(f"      Error: {service.get('error', 'Unknown')}")
```

### Configuration

The DeploymentManager can be configured with various options:

```python
from blastdock.core import DeploymentManager
from blastdock.config import get_config_manager

# Use custom configuration profile
manager = DeploymentManager(config_profile="production")

# Access configuration
config = manager.config
print(f"Docker timeout: {config.docker.timeout}")
print(f"Default ports: {config.default_ports.dict()}")

# Update configuration
config_manager = get_config_manager("production")
config_manager.set_setting("docker.timeout", 60)
```

## TemplateManager

The `TemplateManager` class handles template discovery, validation, and management.

### Class Definition

```python
from blastdock.core.template_manager import TemplateManager

class TemplateManager:
    def __init__(self, config_profile: str = "default"):
        """Initialize template manager."""
```

### Methods

#### list_templates()

List available templates with filtering and search.

```python
def list_templates(
    self,
    category: Optional[str] = None,
    search: Optional[str] = None,
    include_custom: bool = True
) -> List[Dict[str, Any]]:
    """
    List available templates.
    
    Args:
        category: Filter by template category
        search: Search in template names and descriptions
        include_custom: Include custom user templates
    
    Returns:
        List of template information
    """
```

**Example Usage:**

```python
from blastdock.core import TemplateManager

manager = TemplateManager()

# List all templates
templates = manager.list_templates()

for template in templates:
    print(f"📄 {template['name']} v{template['version']}")
    print(f"   {template['description']}")
    print(f"   Category: {template['category']}")
    print(f"   Services: {', '.join(template['services'])}")

# Search for web application templates
web_templates = manager.list_templates(category="web", search="php")
```

#### get_template_info()

Get detailed information about a specific template.

```python
def get_template_info(self, template_name: str) -> Dict[str, Any]:
    """
    Get detailed template information.
    
    Args:
        template_name: Name of the template
    
    Returns:
        Detailed template information
    """
```

**Example Usage:**

```python
# Get WordPress template details
template_info = manager.get_template_info("wordpress")

print(f"📄 Template: {template_info['name']}")
print(f"📝 Description: {template_info['description']}")
print(f"🏷️  Version: {template_info['version']}")
print(f"👤 Author: {template_info['author']}")

print("\n📋 Required Variables:")
for var in template_info['variables']:
    required = "✓" if var['required'] else "○"
    print(f"   {required} {var['name']}: {var['description']}")
    if var.get('default'):
        print(f"      Default: {var['default']}")

print(f"\n🔧 Services:")
for service in template_info['services']:
    print(f"   • {service['name']} ({service['image']})")
    if service.get('ports'):
        print(f"     Ports: {', '.join(map(str, service['ports']))}")
```

#### validate_template()

Validate a template for correctness and security.

```python
def validate_template(
    self, 
    template_path: str,
    strict: bool = False
) -> Dict[str, Any]:
    """
    Validate a template.
    
    Args:
        template_path: Path to template directory
        strict: Enable strict validation mode
    
    Returns:
        Validation results with issues and suggestions
    """
```

**Example Usage:**

```python
# Validate a custom template
validation = manager.validate_template(
    template_path="/path/to/my-template",
    strict=True
)

if validation['valid']:
    print("✅ Template is valid!")
else:
    print("❌ Template validation failed:")
    for error in validation['errors']:
        print(f"   • {error}")

if validation['warnings']:
    print("\n⚠️  Warnings:")
    for warning in validation['warnings']:
        print(f"   • {warning}")

if validation['suggestions']:
    print("\n💡 Suggestions:")
    for suggestion in validation['suggestions']:
        print(f"   • {suggestion}")
```

## Monitor

The `Monitor` class provides application monitoring and health checking capabilities.

### Class Definition

```python
from blastdock.core.monitor import Monitor

class Monitor:
    def __init__(self, config_profile: str = "default"):
        """Initialize monitoring system."""
```

### Methods

#### check_project_health()

Perform comprehensive health check on a project.

```python
def check_project_health(
    self,
    project_name: str,
    deep_check: bool = False
) -> Dict[str, Any]:
    """
    Check health of a project.
    
    Args:
        project_name: Name of the project to check
        deep_check: Perform detailed health checks
    
    Returns:
        Health check results
    """
```

**Example Usage:**

```python
from blastdock.core import Monitor

monitor = Monitor()

# Basic health check
health = monitor.check_project_health("my-blog")

print(f"🏥 Health Check: {health['project_name']}")
print(f"   Overall: {'✅ Healthy' if health['healthy'] else '❌ Unhealthy'}")
print(f"   Score: {health['health_score']}/100")

for service in health['services']:
    status = "✅" if service['healthy'] else "❌"
    print(f"   {status} {service['name']}: {service['status']}")
    
    if not service['healthy'] and service.get('issues'):
        for issue in service['issues']:
            print(f"      • {issue}")

# Deep health check with performance metrics
deep_health = monitor.check_project_health("my-blog", deep_check=True)

if 'performance' in deep_health:
    perf = deep_health['performance']
    print(f"\n📊 Performance Metrics:")
    print(f"   CPU Usage: {perf['cpu_usage']:.1f}%")
    print(f"   Memory Usage: {perf['memory_usage']:.1f}%")
    print(f"   Response Time: {perf['response_time']:.0f}ms")
```

#### get_project_metrics()

Get detailed metrics for a project.

```python
def get_project_metrics(
    self,
    project_name: str,
    time_range: str = "1h"
) -> Dict[str, Any]:
    """
    Get project metrics over time.
    
    Args:
        project_name: Name of the project
        time_range: Time range for metrics (1h, 24h, 7d, 30d)
    
    Returns:
        Metrics data
    """
```

**Example Usage:**

```python
# Get 24-hour metrics
metrics = monitor.get_project_metrics("my-blog", time_range="24h")

print(f"📈 Metrics for {metrics['project_name']} (24h)")
print(f"   Uptime: {metrics['uptime_percentage']:.1f}%")
print(f"   Avg Response Time: {metrics['avg_response_time']:.0f}ms")
print(f"   Total Requests: {metrics['total_requests']:,}")
print(f"   Error Rate: {metrics['error_rate']:.2f}%")

# Plot CPU usage over time
import matplotlib.pyplot as plt

timestamps = metrics['cpu_usage']['timestamps']
values = metrics['cpu_usage']['values']

plt.figure(figsize=(12, 6))
plt.plot(timestamps, values)
plt.title('CPU Usage Over Time')
plt.ylabel('CPU %')
plt.xlabel('Time')
plt.grid(True)
plt.show()
```

## Advanced Usage Examples

### Batch Deployment

```python
from blastdock.core import DeploymentManager
import asyncio

async def deploy_multiple_sites():
    manager = DeploymentManager()
    
    sites = [
        {
            "template": "wordpress",
            "name": "blog",
            "domain": "blog.example.com",
            "variables": {"mysql_password": "blog_pass_123"}
        },
        {
            "template": "nextcloud",
            "name": "cloud", 
            "domain": "cloud.example.com",
            "variables": {"admin_password": "cloud_pass_123"}
        }
    ]
    
    results = []
    for site in sites:
        print(f"🚀 Deploying {site['name']}...")
        result = manager.deploy_template(**site)
        results.append(result)
        
        if result.success:
            print(f"✅ {site['name']} deployed successfully")
        else:
            print(f"❌ {site['name']} failed: {result.error}")
    
    return results

# Run batch deployment
results = asyncio.run(deploy_multiple_sites())
```

### Custom Template Development

```python
from blastdock.core import TemplateManager
from pathlib import Path

def create_custom_template():
    manager = TemplateManager()
    
    # Template structure
    template_dir = Path("./my-custom-app")
    template_dir.mkdir(exist_ok=True)
    
    # Create template.yml
    template_config = {
        "name": "my-custom-app",
        "version": "1.0.0",
        "description": "My custom application template",
        "author": "Your Name",
        "category": "web",
        "variables": [
            {
                "name": "app_name",
                "description": "Application name",
                "required": True,
                "type": "string"
            },
            {
                "name": "database_password",
                "description": "Database password",
                "required": True,
                "type": "password"
            }
        ],
        "services": [
            {
                "name": "app",
                "image": "node:18-alpine",
                "ports": [3000]
            },
            {
                "name": "database",
                "image": "postgres:15",
                "environment": ["POSTGRES_PASSWORD={{database_password}}"]
            }
        ]
    }
    
    import yaml
    with open(template_dir / "template.yml", "w") as f:
        yaml.dump(template_config, f, default_flow_style=False)
    
    # Validate the template
    validation = manager.validate_template(str(template_dir))
    
    if validation['valid']:
        print("✅ Custom template created and validated!")
        return str(template_dir)
    else:
        print("❌ Template validation failed:")
        for error in validation['errors']:
            print(f"   • {error}")
        return None

# Create and validate custom template
template_path = create_custom_template()
```

### Monitoring Dashboard

```python
from blastdock.core import Monitor
from rich.console import Console
from rich.table import Table
from rich.live import Live
import time

def create_monitoring_dashboard():
    monitor = Monitor()
    console = Console()
    
    def generate_table():
        table = Table(title="BlastDock Deployment Status")
        table.add_column("Project", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Health", style="yellow")
        table.add_column("CPU", style="blue")
        table.add_column("Memory", style="magenta")
        table.add_column("Response", style="red")
        
        # Get list of deployments
        from blastdock.core import DeploymentManager
        deployment_manager = DeploymentManager()
        deployments = deployment_manager.list_deployments()
        
        for deployment in deployments:
            health = monitor.check_project_health(deployment['name'])
            metrics = monitor.get_project_metrics(deployment['name'], "1h")
            
            status_icon = "🟢" if deployment['status'] == 'running' else "🔴"
            health_score = health.get('health_score', 0)
            cpu_usage = metrics.get('current_cpu', 0)
            memory_usage = metrics.get('current_memory', 0)
            response_time = metrics.get('avg_response_time', 0)
            
            table.add_row(
                deployment['name'],
                f"{status_icon} {deployment['status']}",
                f"{health_score}/100",
                f"{cpu_usage:.1f}%",
                f"{memory_usage:.1f}%",
                f"{response_time:.0f}ms"
            )
        
        return table
    
    # Live updating dashboard
    with Live(generate_table(), refresh_per_second=0.5) as live:
        for _ in range(60):  # Run for 1 minute
            time.sleep(2)
            live.update(generate_table())

# Run monitoring dashboard
create_monitoring_dashboard()
```

## Error Handling Best Practices

```python
from blastdock.core import DeploymentManager
from blastdock.exceptions import DeploymentError, ValidationError
import logging

def robust_deployment(template_name, project_name, **kwargs):
    """Example of robust deployment with comprehensive error handling."""
    
    logger = logging.getLogger(__name__)
    manager = DeploymentManager()
    
    try:
        # Pre-deployment validation
        logger.info(f"Starting deployment: {project_name}")
        
        # Check if project already exists
        existing_deployments = manager.list_deployments()
        if any(d['name'] == project_name for d in existing_deployments):
            raise ValidationError(f"Project '{project_name}' already exists")
        
        # Deploy the template
        result = manager.deploy_template(
            template_name=template_name,
            project_name=project_name,
            **kwargs
        )
        
        if result.success:
            logger.info(f"Deployment successful: {project_name}")
            return result
        else:
            logger.error(f"Deployment failed: {result.error}")
            raise DeploymentError(result.error)
            
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return {"success": False, "error": str(e), "type": "validation"}
        
    except DeploymentError as e:
        logger.error(f"Deployment error: {e}")
        
        # Attempt cleanup on failure
        try:
            logger.info("Attempting cleanup after failed deployment")
            cleanup_result = manager.remove_deployment(
                project_name=project_name,
                remove_volumes=True,
                backup_data=False
            )
            if cleanup_result.success:
                logger.info("Cleanup successful")
            else:
                logger.warning(f"Cleanup failed: {cleanup_result.error}")
        except Exception as cleanup_error:
            logger.error(f"Cleanup error: {cleanup_error}")
        
        return {"success": False, "error": str(e), "type": "deployment"}
        
    except Exception as e:
        logger.exception("Unexpected error during deployment")
        return {"success": False, "error": str(e), "type": "unexpected"}

# Example usage with error handling
result = robust_deployment(
    template_name="wordpress",
    project_name="production-blog",
    domain="blog.company.com",
    variables={
        "mysql_password": "ultra_secure_password_123",
        "admin_email": "admin@company.com"
    }
)

if result["success"]:
    print("✅ Deployment completed successfully!")
else:
    print(f"❌ Deployment failed ({result['type']}): {result['error']}")
```

## Next Steps

- 📖 **[Configuration API](../config/)** - Learn about configuration management
- 🐳 **[Docker Integration](../docker/)** - Advanced Docker operations
- 🔒 **[Security API](../security/)** - Security and validation features
- 📊 **[Monitoring API](../monitoring/)** - Advanced monitoring capabilities