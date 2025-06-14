"""
Core configuration module - compatibility layer
"""

# Import from the main config module
from ..config import (
    ConfigManager,
    get_config_manager,
    get_config,
    BlastDockConfig,
    DefaultPortsConfig,
    LoggingConfig,
    DockerConfig,
    SecurityConfig,
    TemplateConfig
)

# Re-export for backward compatibility
__all__ = [
    'ConfigManager',
    'get_config_manager',
    'get_config',
    'BlastDockConfig',
    'DefaultPortsConfig',
    'LoggingConfig',
    'DockerConfig',
    'SecurityConfig',
    'TemplateConfig'
]
