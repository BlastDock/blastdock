"""
Enhanced configuration management system with validation
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator

from ..utils.helpers import load_yaml, save_yaml
from ..utils.filesystem import paths
from ..utils.logging import get_logger
from ..exceptions import ConfigurationError

logger = get_logger(__name__)


class DefaultPortsConfig(BaseModel):
    """Default ports configuration"""
    wordpress: int = Field(default=8080, ge=1, le=65535)
    mysql: int = Field(default=3306, ge=1, le=65535)
    postgresql: int = Field(default=5432, ge=1, le=65535)
    n8n: int = Field(default=5678, ge=1, le=65535)
    nginx: int = Field(default=80, ge=1, le=65535)
    redis: int = Field(default=6379, ge=1, le=65535)
    grafana: int = Field(default=3000, ge=1, le=65535)
    prometheus: int = Field(default=9090, ge=1, le=65535)
    
    class Config:
        extra = "allow"  # Allow additional ports


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO")
    log_to_file: bool = Field(default=True)
    log_to_console: bool = Field(default=True)
    json_format: bool = Field(default=False)
    max_log_size: int = Field(default=10 * 1024 * 1024)  # 10MB
    backup_count: int = Field(default=5)
    
    @validator('level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()


class DockerConfig(BaseModel):
    """Docker configuration"""
    compose_version: str = Field(default="3.8")
    default_restart_policy: str = Field(default="unless-stopped")
    timeout: int = Field(default=30, ge=5, le=300)
    
    @validator('compose_version')
    def validate_compose_version(cls, v):
        valid_versions = ['3.0', '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9']
        if v not in valid_versions:
            raise ValueError(f'Compose version must be one of: {valid_versions}')
        return v
    
    @validator('default_restart_policy')
    def validate_restart_policy(cls, v):
        valid_policies = ['no', 'always', 'on-failure', 'unless-stopped']
        if v not in valid_policies:
            raise ValueError(f'Restart policy must be one of: {valid_policies}')
        return v


class SecurityConfig(BaseModel):
    """Security configuration"""
    auto_generate_passwords: bool = Field(default=True)
    password_length: int = Field(default=16, ge=8, le=64)
    confirm_destructive_operations: bool = Field(default=True)
    require_port_confirmation: bool = Field(default=True)
    
    @validator('password_length')
    def validate_password_length(cls, v):
        if v < 8:
            raise ValueError('Password length must be at least 8 characters')
        if v > 64:
            raise ValueError('Password length must not exceed 64 characters')
        return v


class TemplateConfig(BaseModel):
    """Template configuration"""
    auto_update: bool = Field(default=False)
    update_check_interval: int = Field(default=86400, ge=3600)  # 24 hours, min 1 hour
    custom_template_dirs: List[str] = Field(default_factory=list)
    
    @validator('custom_template_dirs')
    def validate_template_dirs(cls, v):
        for dir_path in v:
            if not os.path.isabs(dir_path):
                raise ValueError(f'Template directory must be absolute path: {dir_path}')
            if not os.path.isdir(dir_path):
                logger.warning(f'Template directory does not exist: {dir_path}')
        return v


class BlastDockConfig(BaseModel):
    """Main BlastDock configuration"""
    version: str = Field(default="1.0.0")
    default_ports: DefaultPortsConfig = Field(default_factory=DefaultPortsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
    
    # Global settings
    editor: Optional[str] = Field(default=None)
    browser: Optional[str] = Field(default=None)
    timezone: str = Field(default="UTC")
    
    class Config:
        extra = "allow"  # Allow additional configuration keys


class ConfigManager:
    """Enhanced configuration manager with validation and profiles"""
    
    CONFIG_VERSION = "1.0.0"
    
    def __init__(self, profile: str = "default"):
        self.profile = profile
        self.config_file = paths.config_dir / f"config-{profile}.yml"
        self.global_config_file = paths.config_file
        self._config: Optional[BlastDockConfig] = None
        
        # Ensure config directory exists
        paths.ensure_directories()
    
    @property
    def config(self) -> BlastDockConfig:
        """Get the current configuration"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def load_config(self) -> BlastDockConfig:
        """Load configuration with validation"""
        try:
            # Try to load profile-specific config first
            if self.config_file.exists():
                config_data = load_yaml(str(self.config_file))
            # Fallback to global config
            elif self.global_config_file.exists():
                config_data = load_yaml(str(self.global_config_file))
            else:
                config_data = {}
            
            # Validate and return config
            return BlastDockConfig(**config_data)
            
        except Exception as e:
            logger.warning(f"Failed to load configuration: {e}. Using defaults.")
            return BlastDockConfig()
    
    def save_config(self, config: BlastDockConfig = None) -> None:
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        try:
            # Save to profile-specific file if not default profile
            target_file = self.config_file if self.profile != "default" else self.global_config_file
            
            # Convert to dict and save
            config_dict = config.dict()
            save_yaml(config_dict, str(target_file))
            
            logger.info(f"Configuration saved to {target_file}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting using dot notation"""
        try:
            value = self.config
            for part in key.split('.'):
                if hasattr(value, part):
                    value = getattr(value, part)
                elif isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        except Exception:
            return default
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a configuration setting using dot notation"""
        try:
            # Reload config to get latest values
            self._config = self.load_config()
            
            # Navigate to the setting and update it
            config_dict = self.config.dict()
            keys = key.split('.')
            target = config_dict
            
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            
            target[keys[-1]] = value
            
            # Validate and save
            new_config = BlastDockConfig(**config_dict)
            self._config = new_config
            self.save_config(new_config)
            
        except Exception as e:
            raise ConfigurationError(f"Failed to set configuration key '{key}': {e}")
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._config = BlastDockConfig()
        self.save_config()
        logger.info("Configuration reset to defaults")
    
    def migrate_config(self) -> None:
        """Migrate configuration from older versions"""
        # Check if old config exists
        old_config_file = paths.config_dir.parent / '.blastdock' / 'config.yml'
        
        if old_config_file.exists() and not self.global_config_file.exists():
            try:
                logger.info("Migrating configuration from old format")
                old_config = load_yaml(str(old_config_file))
                
                # Map old config structure to new
                migrated_config = self._migrate_old_config(old_config)
                
                # Validate and save
                new_config = BlastDockConfig(**migrated_config)
                self._config = new_config
                self.save_config()
                
                logger.info("Configuration migration completed")
                
            except Exception as e:
                logger.error(f"Configuration migration failed: {e}")
    
    def _migrate_old_config(self, old_config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate old configuration format to new format"""
        migrated = {}
        
        # Migrate default ports
        if 'default_ports' in old_config:
            migrated['default_ports'] = old_config['default_ports']
        
        # Migrate security settings
        security_settings = {}
        if 'auto_generate_passwords' in old_config:
            security_settings['auto_generate_passwords'] = old_config['auto_generate_passwords']
        if 'confirm_destructive_operations' in old_config:
            security_settings['confirm_destructive_operations'] = old_config['confirm_destructive_operations']
        
        if security_settings:
            migrated['security'] = security_settings
        
        # Migrate logging settings
        if 'log_level' in old_config:
            migrated['logging'] = {'level': old_config['log_level']}
        
        # Migrate Docker settings
        if 'docker_compose_version' in old_config:
            migrated['docker'] = {'compose_version': old_config['docker_compose_version']}
        
        return migrated
    
    def list_profiles(self) -> List[str]:
        """List available configuration profiles"""
        profiles = []
        
        # Add default profile if global config exists
        if self.global_config_file.exists():
            profiles.append("default")
        
        # Add profile-specific configs
        for config_file in paths.config_dir.glob("config-*.yml"):
            profile_name = config_file.stem.replace("config-", "")
            if profile_name != "default":
                profiles.append(profile_name)
        
        return sorted(profiles)
    
    def create_profile(self, profile_name: str, base_profile: str = "default") -> None:
        """Create a new configuration profile"""
        if not profile_name or profile_name == "default":
            raise ConfigurationError("Invalid profile name")
        
        new_profile_file = paths.config_dir / f"config-{profile_name}.yml"
        
        if new_profile_file.exists():
            raise ConfigurationError(f"Profile '{profile_name}' already exists")
        
        # Load base profile
        if base_profile == "default":
            base_config = BlastDockConfig()
        else:
            base_manager = ConfigManager(base_profile)
            base_config = base_manager.config
        
        # Save as new profile
        save_yaml(base_config.dict(), str(new_profile_file))
        logger.info(f"Created new profile '{profile_name}' based on '{base_profile}'")
    
    def delete_profile(self, profile_name: str) -> None:
        """Delete a configuration profile"""
        if profile_name == "default":
            raise ConfigurationError("Cannot delete default profile")
        
        profile_file = paths.config_dir / f"config-{profile_name}.yml"
        
        if not profile_file.exists():
            raise ConfigurationError(f"Profile '{profile_name}' does not exist")
        
        profile_file.unlink()
        logger.info(f"Deleted profile '{profile_name}'")
    
    # Convenience methods for common settings
    def get_default_port(self, service: str) -> Optional[int]:
        """Get default port for a service"""
        ports = self.config.default_ports
        return getattr(ports, service, None) if hasattr(ports, service) else None
    
    def should_auto_generate_passwords(self) -> bool:
        """Check if passwords should be auto-generated"""
        return self.config.security.auto_generate_passwords
    
    def should_confirm_destructive_operations(self) -> bool:
        """Check if destructive operations should be confirmed"""
        return self.config.security.confirm_destructive_operations
    
    def get_password_length(self) -> int:
        """Get configured password length"""
        return self.config.security.password_length
    
    def get_docker_compose_version(self) -> str:
        """Get Docker Compose version"""
        return self.config.docker.compose_version
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration"""
        return self.config.logging


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(profile: str = "default") -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None or _config_manager.profile != profile:
        _config_manager = ConfigManager(profile)
        # Run migration on first load
        _config_manager.migrate_config()
    return _config_manager


def get_config(profile: str = "default") -> BlastDockConfig:
    """Get the current configuration"""
    return get_config_manager(profile).config