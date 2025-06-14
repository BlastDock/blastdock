# CLI API Reference

The CLI API provides the command-line interface components, utilities, and extensibility features for BlastDock.

## Classes Overview

- **[CLICommand](#clicommand)** - Base class for CLI commands
- **[ProgressManager](#progressmanager)** - Progress bars and status indicators
- **[InteractivePrompt](#interactiveprompt)** - Interactive user prompts and wizards
- **[OutputFormatter](#outputformatter)** - Output formatting and display utilities
- **[CLIContext](#clicontext)** - CLI context and state management

## CLICommand

The `CLICommand` base class provides foundation for creating custom CLI commands.

### Class Definition

```python
from blastdock.cli import CLICommand
import click

class MyCommand(CLICommand):
    """Custom CLI command implementation."""
    
    def __init__(self):
        super().__init__(
            name="mycommand",
            help="Description of my command",
            requires_project=False
        )
```

### Creating Custom Commands

#### Basic Command Structure

```python
from blastdock.cli import CLICommand
from blastdock.cli.decorators import with_progress, handle_errors
import click

class DeployCommand(CLICommand):
    """Deploy applications from templates."""
    
    def __init__(self):
        super().__init__(
            name="deploy",
            help="Deploy application from template",
            requires_project=False
        )
    
    def get_command(self):
        """Get Click command object."""
        
        @click.command(name=self.name, help=self.help)
        @click.argument('template')
        @click.argument('project_name')
        @click.option('--domain', '-d', help='Domain name for the application')
        @click.option('--env-file', '-e', type=click.Path(exists=True), help='Environment file')
        @click.option('--no-start', is_flag=True, help='Do not start services after deployment')
        @click.pass_context
        @handle_errors
        @with_progress
        def command(ctx, template, project_name, domain, env_file, no_start, progress):
            """Deploy application from template."""
            
            # Access CLI context
            cli_context = self.get_context(ctx)
            
            # Show deployment progress
            with progress.task("Validating template") as task:
                # Validation logic
                task.update("Template validated")
            
            with progress.task("Creating project structure") as task:
                # Project creation logic
                task.update(f"Project {project_name} created")
            
            with progress.task("Deploying services") as task:
                # Deployment logic
                result = self.deploy_template(
                    template=template,
                    project_name=project_name,
                    domain=domain,
                    env_file=env_file
                )
                task.update("Services deployed")
            
            # Format output
            self.success(f"Application deployed successfully!")
            self.info(f"Project: {project_name}")
            self.info(f"URL: https://{domain or 'localhost'}")
            
            if not no_start:
                with progress.task("Starting services") as task:
                    # Start services
                    task.update("Services started")
            
            return result
        
        return command
    
    def deploy_template(self, template, project_name, domain, env_file):
        """Actual deployment logic."""
        from blastdock.core import DeploymentManager
        
        manager = DeploymentManager()
        
        # Load environment variables if provided
        variables = {}
        if env_file:
            variables = self.load_env_file(env_file)
        
        # Deploy template
        result = manager.deploy_template(
            template_name=template,
            project_name=project_name,
            domain=domain,
            variables=variables
        )
        
        return result

# Register command
deploy_cmd = DeployCommand()
```

#### Command with Subcommands

```python
class ConfigCommand(CLICommand):
    """Configuration management command group."""
    
    def __init__(self):
        super().__init__(
            name="config",
            help="Configuration management commands",
            is_group=True
        )
    
    def get_command(self):
        """Get Click command group."""
        
        @click.group(name=self.name, help=self.help)
        @click.pass_context
        def group(ctx):
            """Configuration management."""
            pass
        
        # Add subcommands
        group.add_command(self.get_show_command())
        group.add_command(self.get_set_command())
        group.add_command(self.get_validate_command())
        
        return group
    
    def get_show_command(self):
        """Show configuration subcommand."""
        
        @click.command(name="show")
        @click.option('--format', '-f', type=click.Choice(['yaml', 'json', 'table']), default='yaml')
        @click.option('--section', '-s', help='Show specific section only')
        @click.pass_context
        @handle_errors
        def show(ctx, format, section):
            """Show current configuration."""
            
            from blastdock.config import get_config_manager
            config_manager = get_config_manager()
            
            if section:
                config_data = config_manager.get_setting(section)
            else:
                config_data = config_manager.config.dict()
            
            # Format output
            if format == 'yaml':
                import yaml
                output = yaml.dump(config_data, default_flow_style=False)
            elif format == 'json':
                import json
                output = json.dumps(config_data, indent=2)
            else:  # table
                output = self.format_as_table(config_data)
            
            click.echo(output)
        
        return show
    
    def get_set_command(self):
        """Set configuration subcommand."""
        
        @click.command(name="set")
        @click.argument('key')
        @click.argument('value')
        @click.option('--profile', '-p', help='Configuration profile')
        @click.pass_context
        @handle_errors
        def set_config(ctx, key, value, profile):
            """Set configuration value."""
            
            from blastdock.config import get_config_manager
            
            config_manager = get_config_manager(profile or "default")
            
            # Convert value to appropriate type
            parsed_value = self.parse_value(value)
            
            # Set configuration
            config_manager.set_setting(key, parsed_value)
            
            self.success(f"Configuration updated: {key} = {parsed_value}")
            
            # Show current value
            current = config_manager.get_setting(key)
            self.info(f"Current value: {current}")
        
        return set_config
```

## ProgressManager

The `ProgressManager` class provides rich progress bars and status indicators.

### Class Definition

```python
from blastdock.cli import ProgressManager

progress_manager = ProgressManager(
    show_spinner=True,
    show_percentage=True,
    show_time=True
)
```

### Methods

#### create_progress_bar()

Create a progress bar for tracking operations.

```python
def create_progress_bar(
    self,
    total: int,
    description: str,
    unit: str = "items"
) -> ProgressBar:
    """
    Create a progress bar.
    
    Args:
        total: Total number of items
        description: Progress bar description
        unit: Unit of measurement
    
    Returns:
        ProgressBar instance
    """
```

**Example Usage:**

```python
from blastdock.cli import ProgressManager

progress_manager = ProgressManager()

# Simple progress bar
with progress_manager.create_progress_bar(
    total=100,
    description="Processing files",
    unit="files"
) as progress:
    for i in range(100):
        # Process file
        time.sleep(0.1)
        progress.update(1, message=f"Processing file_{i}.txt")

# Multiple progress bars
with progress_manager.create_multi_progress() as multi_progress:
    # Download progress
    download_bar = multi_progress.add_task(
        "Downloading images",
        total=50,
        unit="images"
    )
    
    # Processing progress
    process_bar = multi_progress.add_task(
        "Processing images",
        total=50,
        unit="images"
    )
    
    # Simulate work
    for i in range(50):
        time.sleep(0.1)
        multi_progress.update(download_bar, advance=1)
        
        if i > 10:  # Start processing after some downloads
            multi_progress.update(process_bar, advance=1)

# Indeterminate progress (spinner)
with progress_manager.create_spinner(
    description="Connecting to server"
) as spinner:
    # Long running operation
    time.sleep(3)
    spinner.update("Connection established")
```

#### create_status_table()

Create a live updating status table.

```python
def create_status_table(
    self,
    title: str,
    columns: List[str],
    auto_refresh: bool = True
) -> StatusTable:
    """
    Create a status table.
    
    Args:
        title: Table title
        columns: Column names
        auto_refresh: Enable auto-refresh
    
    Returns:
        StatusTable instance
    """
```

**Example Usage:**

```python
# Service status table
with progress_manager.create_status_table(
    title="Service Status",
    columns=["Service", "Status", "Health", "CPU", "Memory"]
) as status_table:
    
    services = ["web", "api", "database", "cache"]
    
    while True:
        rows = []
        for service in services:
            # Get service status (mock data)
            status = "running" if random.random() > 0.1 else "error"
            health = f"{random.randint(80, 100)}%" if status == "running" else "N/A"
            cpu = f"{random.uniform(10, 80):.1f}%"
            memory = f"{random.uniform(100, 500):.0f}MB"
            
            # Status with color
            if status == "running":
                status_display = f"[green]● {status}[/green]"
            else:
                status_display = f"[red]● {status}[/red]"
            
            rows.append([service, status_display, health, cpu, memory])
        
        status_table.update(rows)
        time.sleep(1)
```

#### create_tree_view()

Create a tree view for hierarchical data.

```python
def create_tree_view(
    self,
    title: str,
    data: Dict[str, Any],
    expanded: bool = True
) -> TreeView:
    """
    Create a tree view.
    
    Args:
        title: Tree view title
        data: Hierarchical data
        expanded: Show expanded by default
    
    Returns:
        TreeView instance
    """
```

**Example Usage:**

```python
# Project structure tree
project_structure = {
    "my-wordpress": {
        "docker-compose.yml": "file",
        "env": {
            ".env": "file",
            ".env.example": "file"
        },
        "config": {
            "nginx": {
                "nginx.conf": "file",
                "ssl": {
                    "cert.pem": "file",
                    "key.pem": "file"
                }
            },
            "php": {
                "php.ini": "file"
            }
        },
        "data": {
            "wordpress": "directory",
            "mysql": "directory"
        }
    }
}

tree = progress_manager.create_tree_view(
    title="Project Structure",
    data=project_structure,
    expanded=True
)

tree.display()

# Deployment progress tree
deployment_tree = progress_manager.create_tree_view(
    title="Deployment Progress",
    data={
        "Deployment": {
            "✅ Template Validation": {},
            "✅ Network Creation": {},
            "🔄 Service Deployment": {
                "✅ Database": {},
                "✅ Cache": {},
                "🔄 Web Server": {},
                "⏳ Load Balancer": {}
            },
            "⏳ Health Checks": {},
            "⏳ SSL Configuration": {}
        }
    }
)

tree.display()
```

## InteractivePrompt

The `InteractivePrompt` class provides interactive user prompts and wizards.

### Class Definition

```python
from blastdock.cli import InteractivePrompt

prompt = InteractivePrompt(
    theme="default",
    show_help=True,
    validation_enabled=True
)
```

### Methods

#### prompt_select()

Show a selection prompt.

```python
def prompt_select(
    self,
    message: str,
    choices: List[Union[str, Dict[str, Any]]],
    default: Optional[str] = None,
    multiselect: bool = False
) -> Union[str, List[str]]:
    """
    Show selection prompt.
    
    Args:
        message: Prompt message
        choices: List of choices
        default: Default selection
        multiselect: Allow multiple selections
    
    Returns:
        Selected choice(s)
    """
```

**Example Usage:**

```python
from blastdock.cli import InteractivePrompt

prompt = InteractivePrompt()

# Simple selection
template = prompt.prompt_select(
    message="Select a template",
    choices=["wordpress", "nextcloud", "ghost", "mediawiki"],
    default="wordpress"
)

print(f"Selected template: {template}")

# Selection with descriptions
template_choices = [
    {"name": "wordpress", "value": "wordpress", "description": "Popular blogging platform"},
    {"name": "nextcloud", "value": "nextcloud", "description": "Self-hosted cloud storage"},
    {"name": "ghost", "value": "ghost", "description": "Modern publishing platform"},
    {"name": "custom", "value": "custom", "description": "Create custom template"}
]

template = prompt.prompt_select(
    message="Choose application template",
    choices=template_choices
)

# Multi-select
features = prompt.prompt_select(
    message="Select features to enable",
    choices=[
        "SSL/TLS Encryption",
        "Automated Backups",
        "Monitoring Dashboard",
        "Email Notifications",
        "CDN Integration"
    ],
    multiselect=True
)

print(f"Selected features: {', '.join(features)}")
```

#### prompt_input()

Show an input prompt with validation.

```python
def prompt_input(
    self,
    message: str,
    default: Optional[str] = None,
    validator: Optional[Callable] = None,
    password: bool = False
) -> str:
    """
    Show input prompt.
    
    Args:
        message: Prompt message
        default: Default value
        validator: Validation function
        password: Hide input for passwords
    
    Returns:
        User input
    """
```

**Example Usage:**

```python
# Simple input
project_name = prompt.prompt_input(
    message="Enter project name",
    default="my-app",
    validator=lambda x: len(x) > 0 and x.isalnum()
)

# Password input
password = prompt.prompt_input(
    message="Enter database password",
    password=True,
    validator=lambda x: len(x) >= 8
)

# Email validation
email = prompt.prompt_input(
    message="Enter admin email",
    validator=lambda x: "@" in x and "." in x.split("@")[1]
)

# Numeric input
port = prompt.prompt_input(
    message="Enter port number",
    default="8080",
    validator=lambda x: x.isdigit() and 1 <= int(x) <= 65535
)

# Custom validation with error messages
def validate_domain(value):
    import re
    if not value:
        raise ValueError("Domain cannot be empty")
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$', value):
        raise ValueError("Invalid domain format")
    return True

domain = prompt.prompt_input(
    message="Enter domain name",
    validator=validate_domain
)
```

#### create_wizard()

Create a multi-step configuration wizard.

```python
def create_wizard(
    self,
    title: str,
    steps: List[Dict[str, Any]],
    allow_back: bool = True
) -> Dict[str, Any]:
    """
    Create configuration wizard.
    
    Args:
        title: Wizard title
        steps: List of wizard steps
        allow_back: Allow going back to previous steps
    
    Returns:
        Collected configuration
    """
```

**Example Usage:**

```python
# Deployment wizard
deployment_wizard = prompt.create_wizard(
    title="BlastDock Deployment Wizard",
    steps=[
        {
            "name": "template_selection",
            "title": "Template Selection",
            "prompts": [
                {
                    "type": "select",
                    "name": "template",
                    "message": "Select application template",
                    "choices": ["wordpress", "nextcloud", "ghost", "custom"]
                },
                {
                    "type": "confirm",
                    "name": "use_latest",
                    "message": "Use latest version?",
                    "default": True
                }
            ]
        },
        {
            "name": "project_config",
            "title": "Project Configuration",
            "prompts": [
                {
                    "type": "input",
                    "name": "project_name",
                    "message": "Project name",
                    "validator": lambda x: len(x) > 0 and x.replace("-", "").isalnum()
                },
                {
                    "type": "input",
                    "name": "domain",
                    "message": "Domain name (optional)",
                    "default": ""
                }
            ]
        },
        {
            "name": "security_config",
            "title": "Security Configuration",
            "prompts": [
                {
                    "type": "password",
                    "name": "admin_password",
                    "message": "Admin password",
                    "validator": lambda x: len(x) >= 12
                },
                {
                    "type": "confirm",
                    "name": "enable_ssl",
                    "message": "Enable SSL/TLS?",
                    "default": True
                },
                {
                    "type": "confirm",
                    "name": "auto_updates",
                    "message": "Enable automatic security updates?",
                    "default": True
                }
            ]
        },
        {
            "name": "advanced_options",
            "title": "Advanced Options",
            "prompts": [
                {
                    "type": "select",
                    "name": "backup_schedule",
                    "message": "Backup schedule",
                    "choices": ["hourly", "daily", "weekly", "disabled"],
                    "default": "daily"
                },
                {
                    "type": "multiselect",
                    "name": "monitoring_features",
                    "message": "Select monitoring features",
                    "choices": [
                        "Health Checks",
                        "Performance Metrics",
                        "Log Aggregation",
                        "Alert Notifications"
                    ],
                    "default": ["Health Checks"]
                }
            ]
        }
    ],
    allow_back=True
)

# Run wizard
result = deployment_wizard.run()

print("\n📋 Deployment Configuration:")
print(f"   Template: {result['template']}")
print(f"   Project: {result['project_name']}")
print(f"   Domain: {result['domain'] or 'localhost'}")
print(f"   SSL Enabled: {'Yes' if result['enable_ssl'] else 'No'}")
print(f"   Backup: {result['backup_schedule']}")
print(f"   Monitoring: {', '.join(result['monitoring_features'])}")
```

## OutputFormatter

The `OutputFormatter` class provides utilities for formatting and displaying output.

### Class Definition

```python
from blastdock.cli import OutputFormatter

formatter = OutputFormatter(
    color_enabled=True,
    unicode_enabled=True,
    table_style="rounded"
)
```

### Methods

#### format_table()

Format data as a table.

```python
def format_table(
    self,
    data: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    title: Optional[str] = None
) -> str:
    """
    Format data as table.
    
    Args:
        data: List of dictionaries
        columns: Column names to display
        title: Table title
    
    Returns:
        Formatted table string
    """
```

**Example Usage:**

```python
from blastdock.cli import OutputFormatter

formatter = OutputFormatter()

# Service status table
services = [
    {"name": "web", "status": "running", "cpu": "45%", "memory": "256MB", "uptime": "2d 5h"},
    {"name": "api", "status": "running", "cpu": "32%", "memory": "512MB", "uptime": "2d 5h"},
    {"name": "database", "status": "running", "cpu": "78%", "memory": "1GB", "uptime": "2d 5h"},
    {"name": "cache", "status": "stopped", "cpu": "0%", "memory": "0MB", "uptime": "-"}
]

table = formatter.format_table(
    data=services,
    columns=["name", "status", "cpu", "memory", "uptime"],
    title="Service Status"
)

print(table)

# Deployment history table
deployments = [
    {
        "project": "blog-prod",
        "template": "wordpress",
        "version": "6.3",
        "deployed": "2024-01-15 10:30",
        "status": "active"
    },
    {
        "project": "shop-staging",
        "template": "woocommerce",
        "version": "8.5",
        "deployed": "2024-01-14 15:45",
        "status": "active"
    },
    {
        "project": "docs-dev",
        "template": "mediawiki",
        "version": "1.40",
        "deployed": "2024-01-13 09:00",
        "status": "stopped"
    }
]

table = formatter.format_table(
    data=deployments,
    title="Recent Deployments"
)

print(table)
```

#### format_json()

Format data as colored JSON.

```python
def format_json(
    self,
    data: Any,
    indent: int = 2,
    sort_keys: bool = True
) -> str:
    """
    Format data as colored JSON.
    
    Args:
        data: Data to format
        indent: Indentation level
        sort_keys: Sort dictionary keys
    
    Returns:
        Formatted JSON string
    """
```

**Example Usage:**

```python
# Configuration display
config = {
    "version": "1.1.0",
    "docker": {
        "timeout": 30,
        "compose_version": "2.15.0"
    },
    "security": {
        "auto_generate_passwords": True,
        "password_length": 16,
        "enable_ssl": True
    },
    "monitoring": {
        "enabled": True,
        "interval": 60,
        "alerts": ["email", "slack"]
    }
}

formatted_json = formatter.format_json(config)
print(formatted_json)

# API response display
api_response = {
    "status": "success",
    "data": {
        "deployments": 15,
        "active_services": 42,
        "resource_usage": {
            "cpu": "65%",
            "memory": "4.2GB",
            "storage": "45GB"
        }
    },
    "timestamp": "2024-01-15T10:30:00Z"
}

print(formatter.format_json(api_response))
```

#### format_diff()

Format differences between configurations or files.

```python
def format_diff(
    self,
    old_data: Union[str, Dict],
    new_data: Union[str, Dict],
    context_lines: int = 3
) -> str:
    """
    Format differences between data.
    
    Args:
        old_data: Original data
        new_data: New data
        context_lines: Number of context lines
    
    Returns:
        Formatted diff string
    """
```

**Example Usage:**

```python
# Configuration diff
old_config = {
    "version": "1.0.0",
    "docker": {"timeout": 30},
    "security": {"password_length": 12}
}

new_config = {
    "version": "1.1.0",
    "docker": {"timeout": 60, "retry_attempts": 3},
    "security": {"password_length": 16, "enable_2fa": True}
}

diff = formatter.format_diff(old_config, new_config)
print("Configuration Changes:")
print(diff)

# File diff
old_compose = """version: '3'
services:
  web:
    image: nginx:1.20
    ports:
      - "80:80"
"""

new_compose = """version: '3.8'
services:
  web:
    image: nginx:1.25
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./ssl:/etc/nginx/ssl
"""

diff = formatter.format_diff(old_compose, new_compose)
print("Docker Compose Changes:")
print(diff)
```

## Advanced CLI Examples

### Custom CLI Plugin System

```python
from blastdock.cli import CLICommand, CLIContext
import importlib
import os

class PluginManager:
    """Manage CLI plugins."""
    
    def __init__(self):
        self.plugins = {}
        self.commands = {}
    
    def load_plugins(self, plugin_dir="~/.blastdock/plugins"):
        """Load CLI plugins from directory."""
        plugin_dir = os.path.expanduser(plugin_dir)
        
        if not os.path.exists(plugin_dir):
            return
        
        for filename in os.listdir(plugin_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                plugin_name = filename[:-3]
                
                try:
                    # Import plugin module
                    spec = importlib.util.spec_from_file_location(
                        plugin_name,
                        os.path.join(plugin_dir, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find CLICommand subclasses
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, CLICommand) and 
                            attr != CLICommand):
                            
                            # Instantiate command
                            command = attr()
                            self.register_command(command)
                            
                            print(f"✅ Loaded plugin command: {command.name}")
                    
                except Exception as e:
                    print(f"❌ Failed to load plugin {plugin_name}: {e}")
    
    def register_command(self, command: CLICommand):
        """Register a plugin command."""
        self.commands[command.name] = command
    
    def get_commands(self):
        """Get all plugin commands."""
        return self.commands

# Example plugin: backup_command.py
class BackupCommand(CLICommand):
    """Backup management plugin."""
    
    def __init__(self):
        super().__init__(
            name="backup",
            help="Backup and restore deployments",
            is_group=True
        )
    
    def get_command(self):
        @click.group(name=self.name, help=self.help)
        def backup_group():
            pass
        
        @backup_group.command()
        @click.argument('project_name')
        @click.option('--output', '-o', help='Output directory')
        def create(project_name, output):
            """Create backup of project."""
            from blastdock.core import BackupManager
            
            backup_mgr = BackupManager()
            backup_path = backup_mgr.create_backup(
                project_name=project_name,
                output_dir=output
            )
            
            click.echo(f"✅ Backup created: {backup_path}")
        
        @backup_group.command()
        @click.argument('backup_file')
        @click.option('--project-name', '-p', help='Restore with new name')
        def restore(backup_file, project_name):
            """Restore project from backup."""
            from blastdock.core import BackupManager
            
            backup_mgr = BackupManager()
            result = backup_mgr.restore_backup(
                backup_file=backup_file,
                project_name=project_name
            )
            
            if result['success']:
                click.echo(f"✅ Backup restored: {result['project_name']}")
            else:
                click.echo(f"❌ Restore failed: {result['error']}")
        
        return backup_group

# Usage in main CLI
plugin_manager = PluginManager()
plugin_manager.load_plugins()

# Add plugin commands to main CLI
for command in plugin_manager.get_commands().values():
    cli.add_command(command.get_command())
```

### Interactive CLI Dashboard

```python
from blastdock.cli import InteractivePrompt, OutputFormatter
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
import asyncio

class CLIDashboard:
    """Interactive CLI dashboard."""
    
    def __init__(self):
        self.console = Console()
        self.prompt = InteractivePrompt()
        self.formatter = OutputFormatter()
        self.running = True
    
    async def run(self):
        """Run interactive dashboard."""
        layout = self.create_layout()
        
        with Live(layout, refresh_per_second=1) as live:
            while self.running:
                # Update dashboard sections
                await self.update_dashboard(layout)
                
                # Check for user input (non-blocking)
                if self.console.is_terminal:
                    key = await self.get_key_async()
                    if key:
                        await self.handle_key(key)
                
                await asyncio.sleep(0.1)
    
    def create_layout(self):
        """Create dashboard layout."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        layout["main"].split_row(
            Layout(name="projects", ratio=2),
            Layout(name="stats", ratio=1)
        )
        
        return layout
    
    async def update_dashboard(self, layout):
        """Update dashboard content."""
        # Header
        layout["header"].update(
            Panel("🚀 BlastDock Interactive Dashboard", style="bold blue")
        )
        
        # Projects section
        projects = await self.get_projects()
        projects_table = self.formatter.format_table(
            data=projects,
            title="Active Projects"
        )
        layout["projects"].update(Panel(projects_table))
        
        # Stats section
        stats = await self.get_stats()
        stats_panel = self.format_stats(stats)
        layout["stats"].update(Panel(stats_panel, title="System Stats"))
        
        # Footer
        layout["footer"].update(
            Panel("[Q]uit | [R]efresh | [N]ew Project | [H]elp", style="dim")
        )
    
    async def handle_key(self, key):
        """Handle keyboard input."""
        if key.lower() == 'q':
            self.running = False
        elif key.lower() == 'n':
            await self.new_project_wizard()
        elif key.lower() == 'h':
            await self.show_help()
    
    async def new_project_wizard(self):
        """Launch new project wizard."""
        self.console.clear()
        
        config = self.prompt.create_wizard(
            title="New Project Wizard",
            steps=[
                {
                    "name": "basic",
                    "prompts": [
                        {
                            "type": "input",
                            "name": "project_name",
                            "message": "Project name"
                        },
                        {
                            "type": "select",
                            "name": "template",
                            "message": "Template",
                            "choices": ["wordpress", "nextcloud", "custom"]
                        }
                    ]
                }
            ]
        ).run()
        
        # Deploy project
        from blastdock.core import DeploymentManager
        manager = DeploymentManager()
        
        result = manager.deploy_template(
            template_name=config['template'],
            project_name=config['project_name']
        )
        
        if result.success:
            self.console.print(f"✅ Project deployed: {config['project_name']}")
        else:
            self.console.print(f"❌ Deployment failed: {result.error}")
        
        await asyncio.sleep(2)

# Run dashboard
dashboard = CLIDashboard()
asyncio.run(dashboard.run())
```

## Next Steps

- 🔧 **[Utils API](../utils/)** - Utility functions and helpers
- 📖 **[API Overview](../)** - Return to API documentation overview
- 🏗️ **[Templates API](../templates/)** - Return to template management
- 🔒 **[Security API](../security/)** - Return to security features