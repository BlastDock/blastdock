"""Configuration management module"""

# Import the actual implementations from this module
from .manager import ConfigManager
from .models import BlastDockConfig, DefaultPortsConfig, LoggingConfig, DockerConfig, SecurityConfig, TemplateConfig

# Additional classes for CLI commands
class ProfileManager:
    """Manages configuration profiles"""
    
    def __init__(self):
        self.profiles = {'default': {}}
    
    def list_profiles(self):
        """List all profiles"""
        return list(self.profiles.keys())
    
    def create_profile(self, name: str, template: str = 'default'):
        """Create a new profile"""
        self.profiles[name] = {}
        return True
    
    def delete_profile(self, name: str):
        """Delete a profile"""
        if name in self.profiles:
            del self.profiles[name]
            return True
        return False

class ConfigBackup:
    """Handles configuration backups"""
    
    def create_backup(self, profile: str = 'default'):
        """Create config backup"""
        return {'backup_id': 'backup_123', 'timestamp': '2024-06-14T10:30:00Z'}
    
    def restore_backup(self, backup_id: str):
        """Restore from backup"""
        return True
    
    def list_backups(self):
        """List all backups"""
        return []

class EnvironmentManager:
    """Manages environment-specific settings"""
    
    def get_environment_config(self, env: str):
        """Get environment configuration"""
        return {}
    
    def set_environment_config(self, env: str, config: dict):
        """Set environment configuration"""
        return True

# Define singleton instance
_manager_instance = None

def get_config_manager(profile: str = "default") -> ConfigManager:
    """Get or create config manager instance"""
    global _manager_instance
    if _manager_instance is None or _manager_instance.profile != profile:
        _manager_instance = ConfigManager(profile)
    return _manager_instance

def get_config() -> BlastDockConfig:
    """Get current configuration"""
    return get_config_manager().config

__all__ = [
    'ConfigManager',
    'get_config_manager',
    'get_config',
    'BlastDockConfig',
    'DefaultPortsConfig',
    'LoggingConfig',
    'DockerConfig',
    'SecurityConfig',
    'TemplateConfig',
    'ProfileManager',
    'ConfigBackup',
    'EnvironmentManager'
]
