"""
Enhanced configuration manager with advanced features
"""

import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Union
from contextlib import contextmanager

try:
    from .models import BlastDockConfig, LoggingConfig
except Exception:
    # Fallback to simple models for compatibility
    from .simple_models import BlastDockConfig, LoggingConfig
from .persistence import ConfigPersistence, ConfigBackup
from .environment import EnvironmentManager
from .profiles import ProfileManager
from .schema import ConfigValidator
from .watchers import ConfigWatcher

from ..utils.helpers import load_yaml, save_yaml
from ..utils.filesystem import paths
from ..utils.logging import get_logger
from ..exceptions import ConfigurationError

logger = get_logger(__name__)


class ConfigManager:
    """Enhanced configuration manager with comprehensive features"""
    
    CONFIG_VERSION = "1.1.0"
    
    def __init__(self, profile: str = "default", auto_save: bool = True, watch_changes: bool = False):
        self.profile = profile
        self.auto_save = auto_save
        self.watch_changes = watch_changes
        
        # Core components
        self.persistence = ConfigPersistence()
        self.environment = EnvironmentManager()
        self.backup_manager = ConfigBackup()
        self.profile_manager = ProfileManager()
        self.validator = ConfigValidator()
        
        # Configuration state
        self._config: Optional[BlastDockConfig] = None
        self._config_lock = threading.RLock()
        self._change_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._last_modified: Optional[datetime] = None
        
        # File watching
        self._watcher: Optional[ConfigWatcher] = None
        if self.watch_changes:
            self._setup_file_watcher()
        
        # Ensure directories exist
        paths.ensure_directories()
        
        # Initialize configuration
        self.load_config()
    
    @property
    def config(self) -> BlastDockConfig:
        """Get the current configuration"""
        with self._config_lock:
            if self._config is None:
                self._config = self.load_config()
            return self._config
    
    @property
    def config_file_path(self) -> Path:
        """Get the configuration file path for current profile"""
        if self.profile == "default":
            return paths.config_file
        else:
            return paths.config_dir / f"config-{self.profile}.yml"
    
    def load_config(self) -> BlastDockConfig:
        """Load configuration with environment overrides and validation"""
        try:
            with self._config_lock:
                # Load base configuration
                base_config = self._load_base_config()
                
                # Apply environment overrides
                env_overrides = self.environment.apply_env_overrides(base_config)
                
                # Validate configuration
                validation_errors = self.validator.validate_config(env_overrides)
                if validation_errors:
                    logger.warning(f"Configuration validation issues: {validation_errors}")
                
                # Create and cache configuration object
                config_obj = BlastDockConfig(**env_overrides)
                self._config = config_obj
                self._last_modified = datetime.now()
                
                # Trigger callbacks
                self._trigger_change_callbacks(env_overrides)
                
                return config_obj
                
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Return default configuration as fallback
            default_config = BlastDockConfig()
            self._config = default_config
            return default_config
    
    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration from file"""
        config_file = self.config_file_path
        
        if config_file.exists():
            config_data = self.persistence.load_config(config_file.name)
        else:
            # Check for legacy config
            legacy_config = self._check_legacy_config()
            if legacy_config:
                config_data = legacy_config
                # Save in new format
                self.persistence.save_config(config_data, config_file.name)
            else:
                config_data = {}
        
        # Ensure version is set
        if 'version' not in config_data:
            config_data['version'] = self.CONFIG_VERSION
        
        return config_data
    
    def _check_legacy_config(self) -> Optional[Dict[str, Any]]:
        """Check for and migrate legacy configuration"""
        # Check old BlastDock config locations
        legacy_paths = [
            Path.home() / '.blastdock' / 'config.yml',
            Path.home() / '.config' / 'blastdock' / 'config.yml',
            paths.config_dir.parent / '.blastdock' / 'config.yml'
        ]
        
        for legacy_path in legacy_paths:
            if legacy_path.exists():
                logger.info(f"Migrating legacy configuration from {legacy_path}")
                try:
                    legacy_config = load_yaml(str(legacy_path))
                    migrated_config = self._migrate_legacy_config(legacy_config)
                    
                    # Create backup of legacy config
                    backup_name = f"legacy_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    self.backup_manager.create_backup(legacy_config, description=f"Legacy config from {legacy_path}")
                    
                    return migrated_config
                except Exception as e:
                    logger.error(f"Failed to migrate legacy config from {legacy_path}: {e}")
        
        return None
    
    def _migrate_legacy_config(self, legacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate legacy configuration to new format"""
        migrated = {'version': self.CONFIG_VERSION}
        
        # Map old configuration keys to new structure
        key_mappings = {
            'default_ports': 'default_ports',
            'log_level': 'logging.level',
            'auto_generate_passwords': 'security.auto_generate_passwords',
            'confirm_destructive_operations': 'security.confirm_destructive_operations',
            'docker_compose_version': 'docker.compose_version',
            'docker_timeout': 'docker.timeout'
        }
        
        for old_key, new_key in key_mappings.items():
            if old_key in legacy_config:
                self._set_nested_config_value(migrated, new_key, legacy_config[old_key])
        
        # Copy any other configuration that doesn't need mapping
        for key, value in legacy_config.items():
            if key not in key_mappings and key != 'version':
                migrated[key] = value
        
        return migrated
    
    def _set_nested_config_value(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """Set nested configuration value using dot notation"""
        parts = key.split('.')
        current = config
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def save_config(self, config: Optional[BlastDockConfig] = None) -> None:
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        try:
            with self._config_lock:
                # Create backup before saving
                if self.config_file_path.exists():
                    current_config = self.persistence.load_config(self.config_file_path.name)
                    self.backup_manager.create_backup(
                        current_config, 
                        self.profile,
                        description="Auto-backup before save"
                    )
                
                # Save configuration
                config_dict = config.dict()
                self.persistence.save_config(config_dict, self.config_file_path.name)
                
                # Update cached config
                self._config = config
                self._last_modified = datetime.now()
                
                logger.info(f"Configuration saved for profile '{self.profile}'")
                
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting using dot notation"""
        return self.config.get_setting(key, default)
    
    def set_setting(self, key: str, value: Any, save: Optional[bool] = None) -> None:
        """Set a configuration setting using dot notation"""
        try:
            with self._config_lock:
                # Update the configuration object
                self.config.set_setting(key, value)
                
                # Save if auto_save is enabled or explicitly requested
                if save is True or (save is None and self.auto_save):
                    self.save_config()
                
                logger.debug(f"Set configuration setting: {key} = {value}")
                
        except Exception as e:
            raise ConfigurationError(f"Failed to set configuration key '{key}': {e}")
    
    def update_settings(self, settings: Dict[str, Any], save: Optional[bool] = None) -> None:
        """Update multiple configuration settings"""
        try:
            with self._config_lock:
                for key, value in settings.items():
                    self.config.set_setting(key, value)
                
                # Save if auto_save is enabled or explicitly requested
                if save is True or (save is None and self.auto_save):
                    self.save_config()
                
                logger.debug(f"Updated {len(settings)} configuration settings")
                
        except Exception as e:
            raise ConfigurationError(f"Failed to update configuration settings: {e}")
    
    def reset_to_defaults(self, sections: Optional[List[str]] = None) -> None:
        """Reset configuration to defaults (optionally only specific sections)"""
        try:
            with self._config_lock:
                if sections is None:
                    # Reset entire configuration
                    self._config = BlastDockConfig()
                else:
                    # Reset specific sections
                    default_config = BlastDockConfig()
                    current_dict = self.config.dict()
                    
                    for section in sections:
                        if hasattr(default_config, section):
                            current_dict[section] = getattr(default_config, section).dict()
                    
                    self._config = BlastDockConfig(**current_dict)
                
                if self.auto_save:
                    self.save_config()
                
                logger.info(f"Reset configuration to defaults: {sections or 'all sections'}")
                
        except Exception as e:
            raise ConfigurationError(f"Failed to reset configuration: {e}")
    
    @contextmanager
    def temporary_config(self, **overrides):
        """Context manager for temporary configuration changes"""
        original_config = self.config.dict()
        
        try:
            # Apply temporary overrides
            temp_config_dict = original_config.copy()
            for key, value in overrides.items():
                self._set_nested_config_value(temp_config_dict, key, value)
            
            with self._config_lock:
                self._config = BlastDockConfig(**temp_config_dict)
            
            yield self._config
            
        finally:
            # Restore original configuration
            with self._config_lock:
                self._config = BlastDockConfig(**original_config)
    
    def switch_profile(self, profile_name: str) -> None:
        """Switch to a different configuration profile"""
        if profile_name == self.profile:
            return
        
        # Save current profile if auto_save is enabled
        if self.auto_save and self._config is not None:
            self.save_config()
        
        # Switch to new profile
        old_profile = self.profile
        self.profile = profile_name
        self._config = None  # Force reload
        
        # Load new profile configuration
        self.load_config()
        
        logger.info(f"Switched from profile '{old_profile}' to '{profile_name}'")
    
    def export_config(self, export_path: str, format: str = 'yaml', 
                     include_secrets: bool = False) -> None:
        """Export configuration to file"""
        config_dict = self.config.dict()
        
        # Remove secrets if not requested
        if not include_secrets:
            config_dict = self._sanitize_config_for_export(config_dict)
        
        self.persistence.export_config(config_dict, export_path, format)
        logger.info(f"Exported configuration to {export_path}")
    
    def import_config(self, import_path: str, merge: bool = False) -> None:
        """Import configuration from file"""
        imported_config = self.persistence.import_config(import_path)
        
        if merge:
            # Merge with current configuration
            current_dict = self.config.dict()
            merged_dict = self._deep_merge_configs(current_dict, imported_config)
            new_config = BlastDockConfig(**merged_dict)
        else:
            # Replace current configuration
            new_config = BlastDockConfig(**imported_config)
        
        with self._config_lock:
            self._config = new_config
        
        if self.auto_save:
            self.save_config()
        
        logger.info(f"Imported configuration from {import_path}")
    
    def _sanitize_config_for_export(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from configuration for export"""
        sanitized = config.copy()
        
        # Remove environment variables that might contain secrets
        if 'environment_variables' in sanitized:
            env_vars = sanitized['environment_variables'].copy()
            secret_patterns = ['password', 'secret', 'key', 'token', 'auth']
            
            for key in list(env_vars.keys()):
                if any(pattern in key.lower() for pattern in secret_patterns):
                    env_vars[key] = "***REDACTED***"
            
            sanitized['environment_variables'] = env_vars
        
        return sanitized
    
    def _deep_merge_configs(self, config1: Dict[str, Any], config2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries"""
        result = config1.copy()
        
        for key, value in config2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def add_change_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add callback for configuration changes"""
        self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Remove configuration change callback"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
    
    def _trigger_change_callbacks(self, config: Dict[str, Any]) -> None:
        """Trigger all configuration change callbacks"""
        for callback in self._change_callbacks:
            try:
                callback(config)
            except Exception as e:
                logger.error(f"Configuration change callback failed: {e}")
    
    def _setup_file_watcher(self) -> None:
        """Setup file system watcher for configuration changes"""
        try:
            self._watcher = ConfigWatcher(self.config_file_path)
            self._watcher.add_callback(self._on_config_file_changed)
            self._watcher.start()
            logger.debug("Configuration file watcher started")
        except Exception as e:
            logger.warning(f"Failed to setup configuration file watcher: {e}")
    
    def _on_config_file_changed(self, file_path: Path) -> None:
        """Handle configuration file changes"""
        try:
            with self._config_lock:
                # Reload configuration
                self.load_config()
                logger.info("Configuration reloaded due to file change")
        except Exception as e:
            logger.error(f"Failed to reload configuration after file change: {e}")
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about current configuration"""
        config_file = self.config_file_path
        
        info = {
            'profile': self.profile,
            'config_file': str(config_file),
            'exists': config_file.exists(),
            'version': self.config.version,
            'last_modified': self._last_modified.isoformat() if self._last_modified else None,
            'auto_save': self.auto_save,
            'watch_changes': self.watch_changes
        }
        
        if config_file.exists():
            stat = config_file.stat()
            info.update({
                'file_size': stat.st_size,
                'file_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return info
    
    def validate_current_config(self) -> List[str]:
        """Validate current configuration and return any issues"""
        config_dict = self.config.dict()
        return self.validator.validate_config(config_dict)
    
    def cleanup_old_backups(self, max_age_days: int = 30, max_count: int = 10) -> int:
        """Clean up old configuration backups"""
        return self.backup_manager.cleanup_old_backups(max_age_days, max_count)
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.auto_save and self._config is not None:
            try:
                self.save_config()
            except Exception as e:
                logger.error(f"Failed to save configuration on exit: {e}")
        
        if self._watcher:
            self._watcher.stop()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None
_manager_lock = threading.Lock()


def get_config_manager(profile: str = "default", 
                      auto_save: bool = True, 
                      watch_changes: bool = False) -> ConfigManager:
    """Get the global configuration manager instance"""
    global _config_manager
    
    with _manager_lock:
        if (_config_manager is None or 
            _config_manager.profile != profile or
            _config_manager.auto_save != auto_save or
            _config_manager.watch_changes != watch_changes):
            
            _config_manager = ConfigManager(profile, auto_save, watch_changes)
    
    return _config_manager


def get_config(profile: str = "default") -> BlastDockConfig:
    """Get the current configuration"""
    return get_config_manager(profile).config