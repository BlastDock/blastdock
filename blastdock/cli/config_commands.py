"""
CLI commands for configuration management
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.tree import Tree

from ..config import (
    get_config_manager, ConfigManager, BlastDockConfig,
    ProfileManager, ConfigBackup, EnvironmentManager
)
from ..exceptions import ConfigurationError
from ..utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


@click.group(name='config')
def config_group():
    """Configuration management commands"""
    pass


@config_group.command('show')
@click.option('--profile', default='default', help='Configuration profile to show')
@click.option('--section', help='Show specific configuration section')
@click.option('--format', 'output_format', default='table', 
              type=click.Choice(['table', 'json', 'yaml']), 
              help='Output format')
@click.option('--no-sensitive', is_flag=True, help='Hide sensitive information')
def show_config(profile: str, section: Optional[str], output_format: str, no_sensitive: bool):
    """Show current configuration"""
    try:
        config_manager = get_config_manager(profile)
        config = config_manager.config
        
        if section:
            config_data = config.get_setting(section)
            if config_data is None:
                console.print(f"[red]Configuration section '{section}' not found[/red]")
                sys.exit(1)
        else:
            config_data = config.dict()
        
        # Hide sensitive data if requested
        if no_sensitive:
            config_data = _sanitize_config(config_data)
        
        if output_format == 'json':
            console.print(json.dumps(config_data, indent=2))
        elif output_format == 'yaml':
            import yaml
            console.print(yaml.dump(config_data, default_flow_style=False))
        else:
            _display_config_table(config_data, section or 'Configuration')
            
    except Exception as e:
        console.print(f"[red]Error showing configuration: {e}[/red]")
        sys.exit(1)


@config_group.command('set')
@click.argument('key')
@click.argument('value')
@click.option('--profile', default='default', help='Configuration profile')
@click.option('--type', 'value_type', default='auto',
              type=click.Choice(['auto', 'string', 'int', 'float', 'bool']),
              help='Value type')
def set_config(key: str, value: str, profile: str, value_type: str):
    """Set configuration value"""
    try:
        config_manager = get_config_manager(profile)
        
        # Parse value based on type
        parsed_value = _parse_config_value(value, value_type)
        
        # Set the configuration
        config_manager.set_setting(key, parsed_value)
        
        console.print(f"[green]Set {key} = {parsed_value} in profile '{profile}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error setting configuration: {e}[/red]")
        sys.exit(1)


@config_group.command('get')
@click.argument('key')
@click.option('--profile', default='default', help='Configuration profile')
@click.option('--default', help='Default value if key not found')
def get_config(key: str, profile: str, default: Optional[str]):
    """Get configuration value"""
    try:
        config_manager = get_config_manager(profile)
        value = config_manager.get_setting(key, default)
        
        if value is None and default is None:
            console.print(f"[yellow]Configuration key '{key}' not found[/yellow]")
            sys.exit(1)
        
        console.print(str(value))
        
    except Exception as e:
        console.print(f"[red]Error getting configuration: {e}[/red]")
        sys.exit(1)


@config_group.command('reset')
@click.option('--profile', default='default', help='Configuration profile')
@click.option('--section', help='Reset specific section only')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
def reset_config(profile: str, section: Optional[str], confirm: bool):
    """Reset configuration to defaults"""
    try:
        if not confirm:
            sections_text = f"section '{section}'" if section else "entire configuration"
            if not click.confirm(f"Reset {sections_text} for profile '{profile}' to defaults?"):
                console.print("[yellow]Reset cancelled[/yellow]")
                return
        
        config_manager = get_config_manager(profile)
        
        if section:
            config_manager.reset_to_defaults(sections=[section])
            console.print(f"[green]Reset section '{section}' to defaults[/green]")
        else:
            config_manager.reset_to_defaults()
            console.print(f"[green]Reset configuration to defaults[/green]")
            
    except Exception as e:
        console.print(f"[red]Error resetting configuration: {e}[/red]")
        sys.exit(1)


@config_group.command('validate')
@click.option('--profile', default='default', help='Configuration profile')
@click.option('--section', help='Validate specific section only')
@click.option('--suggestions', is_flag=True, help='Show improvement suggestions')
def validate_config(profile: str, section: Optional[str], suggestions: bool):
    """Validate configuration"""
    try:
        config_manager = get_config_manager(profile)
        
        if section:
            issues = config_manager.validator.validate_section(config_manager.config.dict(), section)
        else:
            issues = config_manager.validate_current_config()
        
        if not issues:
            console.print(f"[green]✓ Configuration is valid[/green]")
        else:
            console.print(f"[red]Found {len(issues)} validation issues:[/red]")
            for i, issue in enumerate(issues, 1):
                console.print(f"  {i}. {issue}")
        
        if suggestions:
            suggestions_list = config_manager.validator.get_validation_suggestions(config_manager.config.dict())
            if suggestions_list:
                console.print("\n[blue]Suggestions for improvement:[/blue]")
                for i, suggestion in enumerate(suggestions_list, 1):
                    console.print(f"  {i}. {suggestion}")
            
    except Exception as e:
        console.print(f"[red]Error validating configuration: {e}[/red]")
        sys.exit(1)


@config_group.command('export')
@click.argument('export_path')
@click.option('--profile', default='default', help='Configuration profile')
@click.option('--format', 'export_format', default='yaml',
              type=click.Choice(['yaml', 'json']),
              help='Export format')
@click.option('--include-secrets', is_flag=True, help='Include sensitive information')
def export_config(export_path: str, profile: str, export_format: str, include_secrets: bool):
    """Export configuration to file"""
    try:
        config_manager = get_config_manager(profile)
        config_manager.export_config(export_path, export_format, include_secrets)
        
        console.print(f"[green]Exported configuration to {export_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error exporting configuration: {e}[/red]")
        sys.exit(1)


@config_group.command('import')
@click.argument('import_path')
@click.option('--profile', default='default', help='Configuration profile')
@click.option('--merge', is_flag=True, help='Merge with existing configuration')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
def import_config(import_path: str, profile: str, merge: bool, confirm: bool):
    """Import configuration from file"""
    try:
        if not Path(import_path).exists():
            console.print(f"[red]Import file not found: {import_path}[/red]")
            sys.exit(1)
        
        if not confirm:
            action = "merge with" if merge else "replace"
            if not click.confirm(f"Import configuration will {action} existing configuration. Continue?"):
                console.print("[yellow]Import cancelled[/yellow]")
                return
        
        config_manager = get_config_manager(profile)
        config_manager.import_config(import_path, merge)
        
        action = "merged with" if merge else "imported to replace"
        console.print(f"[green]Configuration {action} profile '{profile}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error importing configuration: {e}[/red]")
        sys.exit(1)


@config_group.group('profile')
def profile_group():
    """Configuration profile management"""
    pass


@profile_group.command('list')
def list_profiles():
    """List available configuration profiles"""
    try:
        profile_manager = ProfileManager()
        profiles = profile_manager.list_profiles()
        
        if not profiles:
            console.print("[yellow]No configuration profiles found[/yellow]")
            return
        
        table = Table(title="Configuration Profiles")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="green")
        table.add_column("Created", style="blue")
        table.add_column("Size", style="yellow")
        table.add_column("Version", style="magenta")
        
        for profile in profiles:
            size_str = f"{profile.size:,} bytes" if profile.size > 0 else "0 bytes"
            created_str = profile.created_at.strftime("%Y-%m-%d %H:%M")
            
            table.add_row(
                profile.name,
                profile.description or "No description",
                created_str,
                size_str,
                profile.config_version
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error listing profiles: {e}[/red]")
        sys.exit(1)


@profile_group.command('create')
@click.argument('profile_name')
@click.option('--description', help='Profile description')
@click.option('--base', default='default', help='Base profile to copy from')
def create_profile(profile_name: str, description: Optional[str], base: str):
    """Create new configuration profile"""
    try:
        profile_manager = ProfileManager()
        profile_manager.create_profile(profile_name, description, base)
        
        console.print(f"[green]Created profile '{profile_name}' based on '{base}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error creating profile: {e}[/red]")
        sys.exit(1)


@profile_group.command('delete')
@click.argument('profile_name')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
def delete_profile(profile_name: str, confirm: bool):
    """Delete configuration profile"""
    try:
        if profile_name == 'default':
            console.print("[red]Cannot delete default profile[/red]")
            sys.exit(1)
        
        if not confirm:
            if not click.confirm(f"Delete profile '{profile_name}'? This cannot be undone."):
                console.print("[yellow]Delete cancelled[/yellow]")
                return
        
        profile_manager = ProfileManager()
        profile_manager.delete_profile(profile_name, confirm=True)
        
        console.print(f"[green]Deleted profile '{profile_name}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error deleting profile: {e}[/red]")
        sys.exit(1)


@profile_group.command('copy')
@click.argument('source_profile')
@click.argument('target_profile')
@click.option('--description', help='Target profile description')
def copy_profile(source_profile: str, target_profile: str, description: Optional[str]):
    """Copy configuration profile"""
    try:
        profile_manager = ProfileManager()
        profile_manager.copy_profile(source_profile, target_profile, description)
        
        console.print(f"[green]Copied profile '{source_profile}' to '{target_profile}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error copying profile: {e}[/red]")
        sys.exit(1)


@config_group.group('backup')
def backup_group():
    """Configuration backup management"""
    pass


@backup_group.command('create')
@click.option('--profile', default='default', help='Configuration profile')
@click.option('--description', help='Backup description')
@click.option('--compress', is_flag=True, help='Create compressed backup')
def create_backup(profile: str, description: Optional[str], compress: bool):
    """Create configuration backup"""
    try:
        config_manager = get_config_manager(profile)
        backup_manager = ConfigBackup()
        
        config_data = config_manager.config.dict()
        backup_file = backup_manager.create_backup(config_data, profile, description, compress)
        
        console.print(f"[green]Created backup: {backup_file}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error creating backup: {e}[/red]")
        sys.exit(1)


@backup_group.command('list')
@click.option('--profile', help='Filter by profile')
def list_backups(profile: Optional[str]):
    """List configuration backups"""
    try:
        backup_manager = ConfigBackup()
        backups = backup_manager.list_backups(profile)
        
        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            return
        
        table = Table(title="Configuration Backups")
        table.add_column("Filename", style="cyan")
        table.add_column("Profile", style="green")
        table.add_column("Created", style="blue")
        table.add_column("Size", style="yellow")
        table.add_column("Description", style="white")
        
        for backup in backups:
            size_str = f"{backup.size:,} bytes"
            created_str = backup.timestamp.strftime("%Y-%m-%d %H:%M")
            
            table.add_row(
                backup.filename,
                backup.profile,
                created_str,
                size_str,
                backup.description or "No description"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error listing backups: {e}[/red]")
        sys.exit(1)


@backup_group.command('restore')
@click.argument('backup_file')
@click.option('--profile', default='default', help='Target profile')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompt')
def restore_backup(backup_file: str, profile: str, confirm: bool):
    """Restore configuration from backup"""
    try:
        if not confirm:
            if not click.confirm(f"Restore backup '{backup_file}' to profile '{profile}'? This will overwrite current configuration."):
                console.print("[yellow]Restore cancelled[/yellow]")
                return
        
        backup_manager = ConfigBackup()
        config_data = backup_manager.restore_backup(backup_file)
        
        config_manager = get_config_manager(profile)
        config_manager._config = BlastDockConfig(**config_data)
        config_manager.save_config()
        
        console.print(f"[green]Restored backup '{backup_file}' to profile '{profile}'[/green]")
        
    except Exception as e:
        console.print(f"[red]Error restoring backup: {e}[/red]")
        sys.exit(1)


@config_group.command('info')
@click.option('--profile', default='default', help='Configuration profile')
def config_info(profile: str):
    """Show configuration information"""
    try:
        config_manager = get_config_manager(profile)
        info = config_manager.get_config_info()
        
        table = Table(title=f"Configuration Information - Profile: {profile}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in info.items():
            if isinstance(value, bool):
                value_str = "✓" if value else "✗"
            else:
                value_str = str(value) if value is not None else "Not set"
            
            table.add_row(key.replace('_', ' ').title(), value_str)
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting configuration info: {e}[/red]")
        sys.exit(1)


def _parse_config_value(value: str, value_type: str) -> Any:
    """Parse configuration value based on type"""
    if value_type == 'auto':
        # Try to automatically detect type
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value
    elif value_type == 'bool':
        return value.lower() in ('true', '1', 'yes', 'on')
    elif value_type == 'int':
        return int(value)
    elif value_type == 'float':
        return float(value)
    else:
        return value


def _sanitize_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from configuration"""
    sensitive_keys = ['password', 'secret', 'key', 'token', 'auth']
    
    def sanitize_dict(d):
        if isinstance(d, dict):
            result = {}
            for k, v in d.items():
                if any(sensitive in k.lower() for sensitive in sensitive_keys):
                    result[k] = "***HIDDEN***"
                else:
                    result[k] = sanitize_dict(v)
            return result
        elif isinstance(d, list):
            return [sanitize_dict(item) for item in d]
        else:
            return d
    
    return sanitize_dict(config_data)


def _display_config_table(config_data: Any, title: str = "Configuration"):
    """Display configuration data as a rich table"""
    if isinstance(config_data, dict):
        table = Table(title=title)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in config_data.items():
            if isinstance(value, dict):
                # For nested dictionaries, show a summary
                value_str = f"({len(value)} items)"
            elif isinstance(value, list):
                value_str = f"[{len(value)} items]"
            else:
                value_str = str(value)
            
            table.add_row(key, value_str)
        
        console.print(table)
    else:
        console.print(f"{title}: {config_data}")


# Register all config commands
config_commands = [
    config_group,
    show_config,
    set_config,
    get_config,
    reset_config,
    validate_config,
    export_config,
    import_config,
    config_info,
    profile_group,
    list_profiles,
    create_profile,
    delete_profile,
    copy_profile,
    backup_group,
    create_backup,
    list_backups,
    restore_backup
]