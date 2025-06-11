"""
Configuration management system
"""

import os
from pathlib import Path
from ..utils.helpers import load_yaml, save_yaml, load_json, save_json

class ConfigManager:
    def __init__(self):
        self.config_dir = os.path.join(Path.home(), '.blastdock')
        self.config_file = os.path.join(self.config_dir, 'config.yml')
        self.ensure_config_dir()
    
    def ensure_config_dir(self):
        """Ensure config directory exists"""
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)
    
    def load_config(self):
        """Load global configuration"""
        if os.path.exists(self.config_file):
            try:
                return load_yaml(self.config_file)
            except Exception:
                pass
        
        return self.get_default_config()
    
    def save_config(self, config):
        """Save global configuration"""
        save_yaml(config, self.config_file)
    
    def get_default_config(self):
        """Get default configuration"""
        return {
            'default_ports': {
                'wordpress': 8080,
                'mysql': 3306,
                'n8n': 5678,
                'nginx': 80
            },
            'auto_generate_passwords': True,
            'confirm_destructive_operations': True,
            'log_level': 'INFO',
            'docker_compose_version': '3.8'
        }
    
    def get_setting(self, key, default=None):
        """Get a specific setting"""
        config = self.load_config()
        return config.get(key, default)
    
    def set_setting(self, key, value):
        """Set a specific setting"""
        config = self.load_config()
        config[key] = value
        self.save_config(config)
    
    def get_default_port(self, service):
        """Get default port for a service"""
        config = self.load_config()
        default_ports = config.get('default_ports', {})
        return default_ports.get(service)
    
    def should_auto_generate_passwords(self):
        """Check if passwords should be auto-generated"""
        return self.get_setting('auto_generate_passwords', True)
    
    def should_confirm_destructive_operations(self):
        """Check if destructive operations should be confirmed"""
        return self.get_setting('confirm_destructive_operations', True)