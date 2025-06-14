"""
Environment variable management for configuration
"""

import os
from typing import Dict, Any, Optional, Set, List, Union
from pathlib import Path

from ..utils.logging import get_logger
from ..exceptions import ConfigurationError

logger = get_logger(__name__)


class EnvironmentManager:
    """Manage configuration through environment variables"""
    
    PREFIX = "BLASTDOCK_"
    BOOL_TRUE_VALUES = {'true', '1', 'yes', 'on', 'enabled'}
    BOOL_FALSE_VALUES = {'false', '0', 'no', 'off', 'disabled'}
    
    def __init__(self, prefix: str = None):
        self.prefix = prefix or self.PREFIX
        self._env_cache: Dict[str, Any] = {}
        self._watched_vars: Set[str] = set()
    
    def get_env_config(self) -> Dict[str, Any]:
        """Extract BlastDock configuration from environment variables"""
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                config_key = key[len(self.prefix):].lower()
                config_value = self._parse_env_value(value)
                self._set_nested_value(config, config_key, config_value)
        
        return config
    
    def _parse_env_value(self, value: str) -> Union[str, int, float, bool, List[str]]:
        """Parse environment variable value to appropriate type"""
        value = value.strip()
        
        # Boolean values
        if value.lower() in self.BOOL_TRUE_VALUES:
            return True
        elif value.lower() in self.BOOL_FALSE_VALUES:
            return False
        
        # List values (comma-separated)
        if ',' in value:
            return [item.strip() for item in value.split(',') if item.strip()]
        
        # Numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # String value
        return value
    
    def _set_nested_value(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """Set nested configuration value using dot notation"""
        parts = key.split('_')
        current = config
        
        # Navigate to the nested location
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the final value
        current[parts[-1]] = value
    
    def set_env_var(self, key: str, value: Any) -> None:
        """Set environment variable with BlastDock prefix"""
        env_key = f"{self.prefix}{key.upper()}"
        env_value = self._format_env_value(value)
        os.environ[env_key] = env_value
        self._env_cache[env_key] = value
        logger.debug(f"Set environment variable: {env_key}")
    
    def _format_env_value(self, value: Any) -> str:
        """Format value for environment variable storage"""
        if isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, (list, tuple)):
            return ','.join(str(item) for item in value)
        else:
            return str(value)
    
    def get_env_var(self, key: str, default: Any = None) -> Any:
        """Get environment variable with BlastDock prefix"""
        env_key = f"{self.prefix}{key.upper()}"
        
        if env_key in self._env_cache:
            return self._env_cache[env_key]
        
        value = os.environ.get(env_key)
        if value is not None:
            parsed_value = self._parse_env_value(value)
            self._env_cache[env_key] = parsed_value
            return parsed_value
        
        return default
    
    def unset_env_var(self, key: str) -> None:
        """Remove environment variable with BlastDock prefix"""
        env_key = f"{self.prefix}{key.upper()}"
        os.environ.pop(env_key, None)
        self._env_cache.pop(env_key, None)
        logger.debug(f"Unset environment variable: {env_key}")
    
    def list_blastdock_env_vars(self) -> Dict[str, str]:
        """List all BlastDock environment variables"""
        blastdock_vars = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                blastdock_vars[key] = value
        
        return blastdock_vars
    
    def export_to_env_file(self, file_path: str, config: Dict[str, Any]) -> None:
        """Export configuration to .env file"""
        env_vars = self._flatten_config_to_env(config)
        
        with open(file_path, 'w') as f:
            f.write(f"# BlastDock Configuration Environment Variables\n")
            f.write(f"# Generated at: {self._get_timestamp()}\n\n")
            
            for key, value in sorted(env_vars.items()):
                f.write(f"{key}={value}\n")
        
        logger.info(f"Exported configuration to environment file: {file_path}")
    
    def load_from_env_file(self, file_path: str, override: bool = False) -> None:
        """Load environment variables from .env file"""
        if not os.path.exists(file_path):
            raise ConfigurationError(f"Environment file not found: {file_path}")
        
        loaded_vars = []
        
        with open(file_path, 'r') as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value
                if '=' not in line:
                    logger.warning(f"Invalid line {line_no} in {file_path}: {line}")
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Only load BlastDock variables
                if key.startswith(self.prefix):
                    if override or key not in os.environ:
                        os.environ[key] = value
                        loaded_vars.append(key)
        
        logger.info(f"Loaded {len(loaded_vars)} environment variables from {file_path}")
    
    def _flatten_config_to_env(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        """Flatten nested configuration to environment variables"""
        env_vars = {}
        
        for key, value in config.items():
            env_key = f"{self.prefix}{prefix}{key.upper()}"
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                nested_vars = self._flatten_config_to_env(value, f"{prefix}{key.upper()}_")
                env_vars.update(nested_vars)
            else:
                env_vars[env_key] = self._format_env_value(value)
        
        return env_vars
    
    def watch_env_var(self, key: str) -> None:
        """Add environment variable to watch list for changes"""
        env_key = f"{self.prefix}{key.upper()}"
        self._watched_vars.add(env_key)
        logger.debug(f"Watching environment variable: {env_key}")
    
    def unwatch_env_var(self, key: str) -> None:
        """Remove environment variable from watch list"""
        env_key = f"{self.prefix}{key.upper()}"
        self._watched_vars.discard(env_key)
        logger.debug(f"Stopped watching environment variable: {env_key}")
    
    def check_watched_vars(self) -> Dict[str, Any]:
        """Check for changes in watched environment variables"""
        changes = {}
        
        for env_key in self._watched_vars:
            current_value = os.environ.get(env_key)
            cached_value = self._env_cache.get(env_key)
            
            if current_value != cached_value:
                if current_value is not None:
                    parsed_value = self._parse_env_value(current_value)
                    self._env_cache[env_key] = parsed_value
                    changes[env_key] = parsed_value
                else:
                    # Variable was removed
                    self._env_cache.pop(env_key, None)
                    changes[env_key] = None
        
        return changes
    
    def validate_env_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate environment-based configuration"""
        issues = []
        
        # Check for required environment variables
        required_vars = self._get_required_env_vars()
        
        for var in required_vars:
            if var not in os.environ:
                issues.append(f"Required environment variable missing: {var}")
        
        # Validate specific configuration values
        if 'docker' in config:
            docker_config = config['docker']
            if 'timeout' in docker_config:
                timeout = docker_config['timeout']
                if not isinstance(timeout, int) or timeout < 5:
                    issues.append("BLASTDOCK_DOCKER_TIMEOUT must be an integer >= 5")
        
        if 'security' in config:
            security_config = config['security']
            if 'password_length' in security_config:
                length = security_config['password_length']
                if not isinstance(length, int) or length < 12:
                    issues.append("BLASTDOCK_SECURITY_PASSWORD_LENGTH must be an integer >= 12")
        
        return issues
    
    def _get_required_env_vars(self) -> List[str]:
        """Get list of required environment variables"""
        # Define any required environment variables
        return []
    
    def _get_timestamp(self) -> str:
        """Get current timestamp string"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def create_docker_env_file(self, config: Dict[str, Any], output_path: str) -> None:
        """Create Docker-compatible .env file"""
        docker_vars = {}
        
        # Extract Docker-specific environment variables
        if 'environment_variables' in config:
            docker_vars.update(config['environment_variables'])
        
        # Add database variables if present
        if 'default_ports' in config:
            ports = config['default_ports']
            if 'mysql' in ports:
                docker_vars['MYSQL_PORT'] = str(ports['mysql'])
            if 'postgresql' in ports:
                docker_vars['POSTGRES_PORT'] = str(ports['postgresql'])
        
        # Write Docker .env file
        with open(output_path, 'w') as f:
            f.write("# Docker Environment Variables\n")
            f.write(f"# Generated at: {self._get_timestamp()}\n\n")
            
            for key, value in sorted(docker_vars.items()):
                # Ensure proper escaping for Docker
                if ' ' in str(value) or '"' in str(value):
                    value = f'"{value}"'
                f.write(f"{key}={value}\n")
        
        logger.info(f"Created Docker environment file: {output_path}")
    
    def get_config_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}
        
        # Check for specific override patterns
        override_prefix = f"{self.prefix}OVERRIDE_"
        
        for key, value in os.environ.items():
            if key.startswith(override_prefix):
                config_key = key[len(override_prefix):].lower().replace('_', '.')
                parsed_value = self._parse_env_value(value)
                overrides[config_key] = parsed_value
        
        return overrides
    
    def apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration"""
        overrides = self.get_config_overrides()
        env_config = self.get_env_config()
        
        # Merge environment configuration
        merged_config = self._deep_merge(config, env_config)
        
        # Apply specific overrides
        for key, value in overrides.items():
            self._set_nested_value(merged_config, key, value)
        
        return merged_config
    
    def _deep_merge(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result