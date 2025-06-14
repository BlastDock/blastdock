"""
Simple configuration models without Pydantic validators for compatibility
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class DefaultPortsConfig(BaseModel):
    """Default ports configuration"""
    wordpress: int = Field(default=8080, description="WordPress default port")
    mysql: int = Field(default=3306, description="MySQL default port")
    postgresql: int = Field(default=5432, description="PostgreSQL default port")
    n8n: int = Field(default=5678, description="n8n default port")
    nginx: int = Field(default=80, description="Nginx default port")
    redis: int = Field(default=6379, description="Redis default port")
    grafana: int = Field(default=3000, description="Grafana default port")
    prometheus: int = Field(default=9090, description="Prometheus default port")
    traefik: int = Field(default=8080, description="Traefik dashboard port")
    portainer: int = Field(default=9000, description="Portainer default port")


class LoggingConfig(BaseModel):
    """Simple logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_to_console: bool = Field(default=True, description="Enable console logging")
    max_log_size: int = Field(default=10 * 1024 * 1024, description="Max log file size in bytes")
    backup_count: int = Field(default=5, description="Number of backup log files")


class DockerConfig(BaseModel):
    """Simple Docker configuration"""
    compose_version: str = Field(default="3.8", description="Docker Compose version")
    default_restart_policy: str = Field(default="unless-stopped", description="Default restart policy")
    timeout: int = Field(default=30, description="Docker command timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    traefik_network: str = Field(default="traefik", description="Traefik network name")
    traefik_cert_resolver: str = Field(default="letsencrypt", description="Traefik certificate resolver")


class SecurityConfig(BaseModel):
    """Simple security configuration"""
    auto_generate_passwords: bool = Field(default=True, description="Auto-generate secure passwords")
    password_length: int = Field(default=16, description="Generated password length")
    confirm_destructive_operations: bool = Field(default=True, description="Confirm destructive operations")


class TemplateConfig(BaseModel):
    """Simple template configuration"""
    auto_update: bool = Field(default=True, description="Auto-update templates")
    cache_enabled: bool = Field(default=True, description="Enable template caching")


class BlastDockConfig(BaseModel):
    """Simple BlastDock configuration"""
    version: str = Field(default="1.2.0", description="Configuration version")
    default_ports: DefaultPortsConfig = Field(default_factory=DefaultPortsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Global settings  
    editor: str = Field(default="", description="Preferred text editor")
    browser: str = Field(default="", description="Preferred web browser")
    timezone: str = Field(default="UTC", description="Default timezone")
    default_domain: str = Field(default="localhost", description="Default domain for auto-subdomains")
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a nested setting using dot notation"""
        try:
            obj = self
            for part in key.split('.'):
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return default
            return obj
        except Exception:
            return default