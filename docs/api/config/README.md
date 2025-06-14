# Configuration API Reference

The Configuration API provides comprehensive configuration management with profiles, persistence, validation, and environment variable support.

## Classes Overview

- **[ConfigManager](#configmanager)** - Main configuration management
- **[ProfileManager](#profilemanager)** - Configuration profile management
- **[ConfigBackup](#configbackup)** - Configuration backup and restore
- **[EnvironmentManager](#environmentmanager)** - Environment variable integration
- **[ConfigValidator](#configvalidator)** - Configuration validation

## ConfigManager

The `ConfigManager` class is the primary interface for managing BlastDock configuration.

### Class Definition

```python
from blastdock.config import ConfigManager, get_config_manager

# Create manager instance
manager = ConfigManager(
    profile="default",
    auto_save=True,
    watch_changes=False
)

# Or use the global manager
manager = get_config_manager("production")
```

### Configuration Structure

BlastDock configuration is organized into logical sections:

```python
from blastdock.config import BlastDockConfig

# Access configuration sections
config = manager.config

# Default ports for services
wordpress_port = config.default_ports.wordpress  # 8080
mysql_port = config.default_ports.mysql          # 3306

# Logging configuration
log_level = config.logging.level                 # "INFO"
log_to_file = config.logging.log_to_file        # True

# Docker settings
compose_version = config.docker.compose_version  # "3.8"
timeout = config.docker.timeout                 # 30

# Security settings
auto_passwords = config.security.auto_generate_passwords  # True
password_length = config.security.password_length         # 16

# Performance settings
cache_strategy = config.performance.cache_strategy        # "hybrid"
parallel_ops = config.performance.parallel_operations     # 4
```

### Methods

#### get_setting()

Retrieve configuration values using dot notation.

```python
def get_setting(self, key: str, default: Any = None) -> Any:
    """
    Get configuration value using dot notation.
    
    Args:
        key: Configuration key (e.g., 'logging.level')
        default: Default value if key not found
    
    Returns:
        Configuration value or default
    """
```

**Example Usage:**

```python
# Get individual settings
log_level = manager.get_setting("logging.level")
wordpress_port = manager.get_setting("default_ports.wordpress")
docker_timeout = manager.get_setting("docker.timeout", 30)

# Get entire sections
logging_config = manager.get_setting("logging")
security_config = manager.get_setting("security")

# Handle missing keys gracefully
custom_setting = manager.get_setting("custom.non_existent", "default_value")
```

#### set_setting()

Update configuration values using dot notation.

```python
def set_setting(self, key: str, value: Any, save: Optional[bool] = None) -> None:
    """
    Set configuration value using dot notation.
    
    Args:
        key: Configuration key (e.g., 'logging.level')
        value: New value to set
        save: Whether to save immediately (None = use auto_save setting)
    
    Raises:
        ConfigurationError: If key is invalid or value doesn't validate
    """
```

**Example Usage:**

```python
# Set individual values
manager.set_setting("logging.level", "DEBUG")
manager.set_setting("default_ports.wordpress", 9080)
manager.set_setting("docker.timeout", 60)

# Set nested values
manager.set_setting("security.password_length", 20)
manager.set_setting("performance.parallel_operations", 8)

# Batch updates
settings = {
    "logging.level": "INFO",
    "docker.timeout": 45,
    "security.auto_generate_passwords": True
}
manager.update_settings(settings)
```

#### load_config()

Load configuration from file with validation.

```python
def load_config(self) -> BlastDockConfig:
    """
    Load configuration with environment overrides and validation.
    
    Returns:
        Validated configuration object
    
    Raises:
        ConfigurationError: If configuration is invalid
    """
```

**Example Usage:**

```python
# Reload configuration from disk
config = manager.load_config()

# Force reload (useful after external changes)
manager._config = None
fresh_config = manager.config  # Triggers reload

# Handle configuration errors
try:
    config = manager.load_config()
    print("✅ Configuration loaded successfully")
except ConfigurationError as e:
    print(f"❌ Configuration error: {e}")
    # Fall back to defaults
    manager.reset_to_defaults()
```

#### save_config()

Save configuration to file.

```python
def save_config(self, config: Optional[BlastDockConfig] = None) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save (None = current config)
    
    Raises:
        ConfigurationError: If save operation fails
    """
```

**Example Usage:**

```python
# Save current configuration
manager.save_config()

# Save specific configuration
custom_config = BlastDockConfig(
    version="1.1.0",
    logging={"level": "DEBUG"},
    docker={"timeout": 60}
)
manager.save_config(custom_config)

# Auto-save is enabled by default
manager.set_setting("logging.level", "WARNING")  # Automatically saved
```

#### reset_to_defaults()

Reset configuration to default values.

```python
def reset_to_defaults(self, sections: Optional[List[str]] = None) -> None:
    """
    Reset configuration to defaults.
    
    Args:
        sections: Specific sections to reset (None = reset all)
    """
```

**Example Usage:**

```python
# Reset entire configuration
manager.reset_to_defaults()

# Reset specific sections
manager.reset_to_defaults(sections=["logging", "docker"])

# Reset with confirmation
import click
if click.confirm("Reset configuration to defaults?"):
    manager.reset_to_defaults()
    print("✅ Configuration reset to defaults")
```

#### temporary_config()

Context manager for temporary configuration changes.

```python
@contextmanager
def temporary_config(self, **overrides):
    """
    Context manager for temporary configuration changes.
    
    Args:
        **overrides: Temporary configuration overrides
    
    Yields:
        Temporarily modified configuration
    """
```

**Example Usage:**

```python
# Temporary configuration for testing
with manager.temporary_config(
    logging={"level": "DEBUG"},
    docker={"timeout": 120}
):
    # Configuration is temporarily modified
    print(f"Log level: {manager.get_setting('logging.level')}")  # DEBUG
    # Perform operations with modified config
    
# Configuration is automatically restored
print(f"Log level: {manager.get_setting('logging.level')}")  # Original value
```

#### validate_current_config()

Validate current configuration.

```python
def validate_current_config(self) -> List[str]:
    """
    Validate current configuration.
    
    Returns:
        List of validation issues (empty if valid)
    """
```

**Example Usage:**

```python
# Validate configuration
issues = manager.validate_current_config()

if not issues:
    print("✅ Configuration is valid")
else:
    print("❌ Configuration validation failed:")
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    # Get suggestions for improvement
    suggestions = manager.validator.get_validation_suggestions(
        manager.config.dict()
    )
    
    if suggestions:
        print("\n💡 Suggestions:")
        for suggestion in suggestions:
            print(f"   • {suggestion}")
```

#### export_config() / import_config()

Export and import configuration with metadata.

```python
def export_config(
    self, 
    export_path: str, 
    format: str = 'yaml',
    include_secrets: bool = False
) -> None:
    """Export configuration to file."""

def import_config(
    self, 
    import_path: str, 
    merge: bool = False
) -> None:
    """Import configuration from file."""
```

**Example Usage:**

```python
# Export configuration
manager.export_config(
    export_path="./my_config_backup.yml",
    format="yaml",
    include_secrets=False  # Sanitize sensitive data
)

# Import configuration
try:
    manager.import_config(
        import_path="./my_config_backup.yml",
        merge=True  # Merge with existing config
    )
    print("✅ Configuration imported successfully")
except ConfigurationError as e:
    print(f"❌ Import failed: {e}")
```

## ProfileManager

The `ProfileManager` class handles multiple configuration profiles for different environments.

### Class Definition

```python
from blastdock.config import ProfileManager

profile_manager = ProfileManager()
```

### Methods

#### create_profile()

Create a new configuration profile.

```python
def create_profile(
    self,
    profile_name: str,
    description: Optional[str] = None,
    base_profile: str = 'default',
    copy_settings: bool = True
) -> None:
    """
    Create a new configuration profile.
    
    Args:
        profile_name: Name of the new profile
        description: Profile description
        base_profile: Profile to copy from
        copy_settings: Whether to copy settings from base
    
    Raises:
        ConfigurationError: If profile already exists or creation fails
    """
```

**Example Usage:**

```python
# Create development profile
profile_manager.create_profile(
    profile_name="development",
    description="Development environment settings",
    base_profile="default",
    copy_settings=True
)

# Create production profile with custom settings
profile_manager.create_profile(
    profile_name="production",
    description="Production environment with enhanced security"
)

# Switch to production profile and customize
prod_manager = ConfigManager(profile="production")
prod_manager.set_setting("logging.level", "WARNING")
prod_manager.set_setting("security.password_length", 32)
prod_manager.set_setting("performance.cache_strategy", "memory")
```

#### list_profiles()

List all available configuration profiles.

```python
def list_profiles(self, refresh: bool = True) -> List[ProfileInfo]:
    """
    List all available profiles.
    
    Args:
        refresh: Whether to refresh profile cache
    
    Returns:
        List of ProfileInfo objects
    """
```

**Example Usage:**

```python
# List all profiles
profiles = profile_manager.list_profiles()

print("📋 Available Configuration Profiles:")
for profile in profiles:
    print(f"   📁 {profile.name}")
    print(f"      Description: {profile.description}")
    print(f"      Created: {profile.created_at.strftime('%Y-%m-%d %H:%M')}")
    print(f"      Version: {profile.config_version}")
    print(f"      Size: {profile.size:,} bytes")
    print()

# Filter profiles by creation date
from datetime import datetime, timedelta
recent_profiles = [
    p for p in profiles 
    if p.created_at > datetime.now() - timedelta(days=7)
]
```

#### copy_profile()

Copy an existing profile to create a new one.

```python
def copy_profile(
    self,
    source_profile: str,
    target_profile: str,
    description: Optional[str] = None
) -> None:
    """
    Copy an existing profile.
    
    Args:
        source_profile: Name of profile to copy
        target_profile: Name of new profile
        description: Description for new profile
    """
```

**Example Usage:**

```python
# Copy production to staging
profile_manager.copy_profile(
    source_profile="production",
    target_profile="staging",
    description="Staging environment based on production"
)

# Modify staging profile
staging_manager = ConfigManager(profile="staging")
staging_manager.set_setting("logging.level", "DEBUG")
staging_manager.set_setting("docker.timeout", 120)
```

#### delete_profile()

Delete a configuration profile.

```python
def delete_profile(self, profile_name: str, confirm: bool = False) -> None:
    """
    Delete a configuration profile.
    
    Args:
        profile_name: Name of profile to delete
        confirm: Confirmation flag (required for safety)
    
    Raises:
        ConfigurationError: If profile is default or doesn't exist
    """
```

**Example Usage:**

```python
# Delete profile with confirmation
try:
    profile_manager.delete_profile("old_profile", confirm=True)
    print("✅ Profile deleted successfully")
except ConfigurationError as e:
    print(f"❌ Cannot delete profile: {e}")

# Interactive deletion with prompt
import click
profile_name = "development"
if click.confirm(f"Delete profile '{profile_name}'? This cannot be undone."):
    profile_manager.delete_profile(profile_name, confirm=True)
```

## ConfigBackup

The `ConfigBackup` class provides configuration backup and restore functionality.

### Class Definition

```python
from blastdock.config import ConfigBackup

backup_manager = ConfigBackup()
```

### Methods

#### create_backup()

Create a configuration backup.

```python
def create_backup(
    self,
    config: Dict[str, Any],
    profile: str = 'default',
    description: Optional[str] = None,
    compression: bool = True
) -> str:
    """
    Create a configuration backup.
    
    Args:
        config: Configuration data to backup
        profile: Profile name for backup
        description: Backup description
        compression: Whether to compress backup
    
    Returns:
        Backup filename
    """
```

**Example Usage:**

```python
# Create compressed backup
config_manager = ConfigManager()
config_data = config_manager.config.dict()

backup_file = backup_manager.create_backup(
    config=config_data,
    profile="production",
    description="Pre-upgrade backup",
    compression=True
)

print(f"💾 Backup created: {backup_file}")

# Create daily backup routine
from datetime import datetime

def daily_backup():
    timestamp = datetime.now().strftime("%Y-%m-%d")
    description = f"Daily backup - {timestamp}"
    
    for profile in ["default", "production", "staging"]:
        try:
            manager = ConfigManager(profile=profile)
            config_data = manager.config.dict()
            
            backup_file = backup_manager.create_backup(
                config=config_data,
                profile=profile,
                description=description,
                compression=True
            )
            print(f"✅ {profile}: {backup_file}")
            
        except Exception as e:
            print(f"❌ Failed to backup {profile}: {e}")

# Run daily backup
daily_backup()
```

#### list_backups()

List available configuration backups.

```python
def list_backups(self, profile: Optional[str] = None) -> List[ConfigBackupInfo]:
    """
    List available backups.
    
    Args:
        profile: Filter by profile name
    
    Returns:
        List of backup information
    """
```

**Example Usage:**

```python
# List all backups
backups = backup_manager.list_backups()

print("📦 Configuration Backups:")
for backup in backups:
    print(f"   📄 {backup.filename}")
    print(f"      Profile: {backup.profile}")
    print(f"      Created: {backup.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"      Size: {backup.size:,} bytes")
    print(f"      Description: {backup.description or 'No description'}")
    print()

# List backups for specific profile
prod_backups = backup_manager.list_backups(profile="production")

# Find recent backups
from datetime import datetime, timedelta
recent_backups = [
    b for b in backups 
    if b.timestamp > datetime.now() - timedelta(days=7)
]
```

#### restore_backup()

Restore configuration from backup.

```python
def restore_backup(self, backup_file: str) -> Dict[str, Any]:
    """
    Restore configuration from backup.
    
    Args:
        backup_file: Backup filename to restore
    
    Returns:
        Restored configuration data
    
    Raises:
        ConfigurationError: If backup doesn't exist or is corrupt
    """
```

**Example Usage:**

```python
# Restore from backup
backup_file = "config_production_20240613_140000.tar.gz"

try:
    restored_config = backup_manager.restore_backup(backup_file)
    
    # Apply restored configuration
    config_manager = ConfigManager(profile="production")
    config_manager._config = BlastDockConfig(**restored_config)
    config_manager.save_config()
    
    print("✅ Configuration restored successfully")
    
except ConfigurationError as e:
    print(f"❌ Restore failed: {e}")

# Interactive restore with selection
def interactive_restore():
    backups = backup_manager.list_backups()
    
    if not backups:
        print("No backups found")
        return
    
    print("Available backups:")
    for i, backup in enumerate(backups, 1):
        print(f"   {i}. {backup.filename} ({backup.profile})")
        print(f"      {backup.timestamp.strftime('%Y-%m-%d %H:%M')}")
    
    try:
        choice = int(input("Select backup to restore (number): ")) - 1
        selected_backup = backups[choice]
        
        if click.confirm(f"Restore {selected_backup.filename}?"):
            restored_config = backup_manager.restore_backup(selected_backup.filename)
            print("✅ Configuration restored")
            
    except (ValueError, IndexError):
        print("Invalid selection")

# Run interactive restore
interactive_restore()
```

## EnvironmentManager

The `EnvironmentManager` class handles environment variable integration.

### Class Definition

```python
from blastdock.config import EnvironmentManager

env_manager = EnvironmentManager(prefix="BLASTDOCK_")
```

### Methods

#### get_env_config()

Extract configuration from environment variables.

```python
def get_env_config(self) -> Dict[str, Any]:
    """
    Extract BlastDock configuration from environment variables.
    
    Returns:
        Configuration dictionary from environment
    """
```

**Example Usage:**

```python
import os

# Set environment variables
os.environ["BLASTDOCK_LOGGING_LEVEL"] = "DEBUG"
os.environ["BLASTDOCK_DOCKER_TIMEOUT"] = "60"
os.environ["BLASTDOCK_SECURITY_PASSWORD_LENGTH"] = "20"

# Extract configuration
env_config = env_manager.get_env_config()

print("🌍 Environment Configuration:")
print(f"   Logging Level: {env_config['logging']['level']}")
print(f"   Docker Timeout: {env_config['docker']['timeout']}")
print(f"   Password Length: {env_config['security']['password_length']}")

# Apply environment overrides to configuration manager
config_manager = ConfigManager()
overridden_config = env_manager.apply_env_overrides(
    config_manager.config.dict()
)

# Create new config with environment overrides
from blastdock.config import BlastDockConfig
final_config = BlastDockConfig(**overridden_config)
```

#### export_to_env_file()

Export configuration to .env file.

```python
def export_to_env_file(self, file_path: str, config: Dict[str, Any]) -> None:
    """
    Export configuration to .env file.
    
    Args:
        file_path: Path to .env file
        config: Configuration to export
    """
```

**Example Usage:**

```python
# Export current configuration to .env file
config_manager = ConfigManager()
config_data = config_manager.config.dict()

env_manager.export_to_env_file(
    file_path="./.env.blastdock",
    config=config_data
)

print("📄 Configuration exported to .env.blastdock")

# The .env file will contain:
# BLASTDOCK_VERSION=1.1.0
# BLASTDOCK_LOGGING_LEVEL=INFO
# BLASTDOCK_DOCKER_TIMEOUT=30
# BLASTDOCK_SECURITY_AUTO_GENERATE_PASSWORDS=true
# ... etc
```

#### load_from_env_file()

Load environment variables from .env file.

```python
def load_from_env_file(self, file_path: str, override: bool = False) -> None:
    """
    Load environment variables from .env file.
    
    Args:
        file_path: Path to .env file
        override: Whether to override existing environment variables
    """
```

**Example Usage:**

```python
# Load .env file
env_manager.load_from_env_file(
    file_path="./.env.production",
    override=True
)

print("🔄 Environment variables loaded from .env.production")

# Use with Docker Compose
env_manager.create_docker_env_file(
    config=config_manager.config.dict(),
    output_path="./docker-compose.env"
)

# docker-compose.yml can then use:
# env_file:
#   - docker-compose.env
```

## Advanced Configuration Examples

### Multi-Environment Setup

```python
from blastdock.config import ConfigManager, ProfileManager

def setup_environments():
    """Setup development, staging, and production environments."""
    
    profile_manager = ProfileManager()
    
    environments = {
        "development": {
            "description": "Development environment",
            "settings": {
                "logging.level": "DEBUG",
                "logging.log_to_console": True,
                "docker.timeout": 120,
                "security.auto_generate_passwords": True,
                "performance.cache_strategy": "memory"
            }
        },
        "staging": {
            "description": "Staging environment",
            "settings": {
                "logging.level": "INFO",
                "logging.log_to_file": True,
                "docker.timeout": 60,
                "security.password_length": 20,
                "performance.cache_strategy": "hybrid"
            }
        },
        "production": {
            "description": "Production environment",
            "settings": {
                "logging.level": "WARNING",
                "logging.log_to_file": True,
                "logging.json_format": True,
                "docker.timeout": 30,
                "security.password_length": 32,
                "security.enable_secrets_encryption": True,
                "performance.cache_strategy": "disk",
                "monitoring.enable_metrics": True,
                "backup.enable_auto_backup": True
            }
        }
    }
    
    for env_name, env_config in environments.items():
        try:
            # Create profile
            profile_manager.create_profile(
                profile_name=env_name,
                description=env_config["description"]
            )
            
            # Configure settings
            manager = ConfigManager(profile=env_name)
            for key, value in env_config["settings"].items():
                manager.set_setting(key, value)
            
            print(f"✅ {env_name} environment configured")
            
        except Exception as e:
            print(f"❌ Failed to setup {env_name}: {e}")

# Setup all environments
setup_environments()
```

### Configuration Validation Pipeline

```python
from blastdock.config import ConfigManager, ConfigValidator

def validate_all_profiles():
    """Validate all configuration profiles."""
    
    profile_manager = ProfileManager()
    validator = ConfigValidator()
    
    profiles = profile_manager.list_profiles()
    results = {}
    
    for profile in profiles:
        print(f"🔍 Validating profile: {profile.name}")
        
        try:
            manager = ConfigManager(profile=profile.name)
            config_data = manager.config.dict()
            
            # Run validation
            issues = validator.validate_config(config_data)
            suggestions = validator.get_validation_suggestions(config_data)
            
            results[profile.name] = {
                "valid": len(issues) == 0,
                "issues": issues,
                "suggestions": suggestions
            }
            
            if issues:
                print(f"   ❌ {len(issues)} issues found")
                for issue in issues:
                    print(f"      • {issue}")
            else:
                print("   ✅ Valid")
                
            if suggestions:
                print(f"   💡 {len(suggestions)} suggestions")
                for suggestion in suggestions:
                    print(f"      • {suggestion}")
                    
        except Exception as e:
            results[profile.name] = {
                "valid": False,
                "error": str(e)
            }
            print(f"   ❌ Validation failed: {e}")
        
        print()
    
    return results

# Run validation pipeline
validation_results = validate_all_profiles()

# Generate validation report
def generate_validation_report(results):
    valid_profiles = [name for name, result in results.items() if result["valid"]]
    invalid_profiles = [name for name, result in results.items() if not result["valid"]]
    
    print("📊 Validation Report Summary:")
    print(f"   ✅ Valid profiles: {len(valid_profiles)}")
    print(f"   ❌ Invalid profiles: {len(invalid_profiles)}")
    
    if invalid_profiles:
        print("\n🚨 Profiles requiring attention:")
        for profile in invalid_profiles:
            print(f"   • {profile}")

generate_validation_report(validation_results)
```

### Configuration Monitoring

```python
from blastdock.config import ConfigWatcher, ConfigChangeLogger
from pathlib import Path

def setup_config_monitoring():
    """Setup configuration file monitoring with change logging."""
    
    # Setup change logger
    change_logger = ConfigChangeLogger(
        log_file=Path("./config_changes.log")
    )
    
    # Setup file watcher
    config_file = Path("~/.config/blastdock/config.yml").expanduser()
    watcher = ConfigWatcher(config_file, check_interval=1.0)
    
    def on_config_change(file_path):
        """Handle configuration file changes."""
        change_logger.log_change(
            config_name="default",
            file_path=file_path,
            change_type="modified"
        )
        
        print(f"🔄 Configuration changed: {file_path}")
        
        # Reload configuration
        try:
            manager = ConfigManager()
            manager._config = None  # Force reload
            new_config = manager.config
            
            # Validate new configuration
            issues = manager.validate_current_config()
            if issues:
                print(f"⚠️  Configuration issues detected:")
                for issue in issues:
                    print(f"   • {issue}")
            else:
                print("✅ Configuration reloaded successfully")
                
        except Exception as e:
            print(f"❌ Configuration reload failed: {e}")
    
    # Add callback and start watching
    watcher.add_callback(on_config_change)
    watcher.start()
    
    print(f"👀 Monitoring configuration file: {config_file}")
    return watcher, change_logger

# Setup monitoring
watcher, change_logger = setup_config_monitoring()

# Keep monitoring running
try:
    import time
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n🛑 Stopping configuration monitoring")
    watcher.stop()
```

## Next Steps

- 🐳 **[Docker Integration API](../docker/)** - Advanced Docker operations
- 🔒 **[Security API](../security/)** - Security validation features
- 📊 **[Monitoring API](../monitoring/)** - Monitoring and metrics
- 🎯 **[Performance API](../performance/)** - Performance optimization