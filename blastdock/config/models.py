"""
Enhanced configuration models with comprehensive validation
"""

import os
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field
from enum import Enum

# Using Pydantic v1 syntax
from pydantic import validator, root_validator

from ..utils.logging import get_logger

logger = get_logger(__name__)


class LogLevel(str, Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class RestartPolicy(str, Enum):
    """Docker restart policy enumeration"""
    NO = "no"
    ALWAYS = "always"
    ON_FAILURE = "on-failure"
    UNLESS_STOPPED = "unless-stopped"


class CacheStrategy(str, Enum):
    """Cache strategy enumeration"""
    MEMORY = "memory"
    DISK = "disk"
    HYBRID = "hybrid"
    DISABLED = "disabled"


class DefaultPortsConfig(BaseModel):
    """Default ports configuration with validation"""
    wordpress: int = Field(default=8080, ge=1024, le=65535, description="WordPress default port")
    mysql: int = Field(default=3306, ge=1, le=65535, description="MySQL default port")
    postgresql: int = Field(default=5432, ge=1, le=65535, description="PostgreSQL default port")
    n8n: int = Field(default=5678, ge=1024, le=65535, description="n8n default port")
    nginx: int = Field(default=80, ge=1, le=65535, description="Nginx default port")
    redis: int = Field(default=6379, ge=1, le=65535, description="Redis default port")
    grafana: int = Field(default=3000, ge=1024, le=65535, description="Grafana default port")
    prometheus: int = Field(default=9090, ge=1024, le=65535, description="Prometheus default port")
    traefik: int = Field(default=8080, ge=1024, le=65535, description="Traefik dashboard port")
    portainer: int = Field(default=9000, ge=1024, le=65535, description="Portainer default port")
    
    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "wordpress": 8080,
                "mysql": 3306,
                "postgresql": 5432,
                "custom_service": 8000
            }
        }
    


class LoggingConfig(BaseModel):
    """Enhanced logging configuration"""
    level: LogLevel = Field(default=LogLevel.INFO, description="Log level")
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_to_console: bool = Field(default=True, description="Enable console logging")
    json_format: bool = Field(default=False, description="Use JSON log format")
    max_log_size: int = Field(default=10 * 1024 * 1024, ge=1024, description="Max log file size in bytes")
    backup_count: int = Field(default=5, ge=1, le=100, description="Number of backup log files")
    log_dir: Optional[str] = Field(default=None, description="Custom log directory")
    enable_audit_log: bool = Field(default=True, description="Enable audit logging")
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "level": "INFO",
                "log_to_file": True,
                "log_to_console": True,
                "json_format": False,
                "max_log_size": 10485760,
                "backup_count": 5
            }
        }
    
    @validator('log_dir', allow_reuse=True)
    def validate_log_dir(cls, v):
        """Validate log directory exists or can be created"""
        if v and not os.path.exists(v):
            try:
                os.makedirs(v, exist_ok=True)
            except OSError as e:
                logger.warning(f"Cannot create log directory {v}: {e}")
        return v


class DockerConfig(BaseModel):
    """Enhanced Docker configuration"""
    compose_version: str = Field(default="3.8", description="Docker Compose version")
    default_restart_policy: RestartPolicy = Field(default=RestartPolicy.UNLESS_STOPPED, description="Default restart policy")
    timeout: int = Field(default=30, ge=5, le=600, description="Docker command timeout in seconds")
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    build_timeout: int = Field(default=600, ge=60, le=3600, description="Build timeout in seconds")
    pull_timeout: int = Field(default=300, ge=30, le=1800, description="Pull timeout in seconds")
    health_check_interval: int = Field(default=30, ge=10, le=300, description="Health check interval in seconds")
    enable_buildkit: bool = Field(default=True, description="Enable Docker BuildKit")
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "compose_version": "3.8",
                "default_restart_policy": "unless-stopped",
                "timeout": 30,
                "max_retries": 3
            }
        }
    
    @validator('compose_version', allow_reuse=True)
    def validate_compose_version(cls, v):
        """Validate Docker Compose version"""
        valid_versions = ['3.0', '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9']
        if v not in valid_versions:
            raise ValueError(f'Compose version must be one of: {valid_versions}')
        return v


class SecurityConfig(BaseModel):
    """Enhanced security configuration"""
    auto_generate_passwords: bool = Field(default=True, description="Auto-generate secure passwords")
    password_length: int = Field(default=16, ge=12, le=128, description="Generated password length")
    password_complexity: bool = Field(default=True, description="Require complex passwords")
    confirm_destructive_operations: bool = Field(default=True, description="Confirm destructive operations")
    require_port_confirmation: bool = Field(default=True, description="Confirm port assignments")
    enable_secrets_encryption: bool = Field(default=True, description="Encrypt stored secrets")
    secrets_key_rotation_days: int = Field(default=90, ge=30, le=365, description="Secret key rotation interval")
    audit_sensitive_operations: bool = Field(default=True, description="Audit sensitive operations")
    max_failed_attempts: int = Field(default=5, ge=3, le=20, description="Max failed authentication attempts")
    
    class Config:
        json_schema_extra = {
            "example": {
                "auto_generate_passwords": True,
                "password_length": 16,
                "confirm_destructive_operations": True,
                "enable_secrets_encryption": True
            }
        }
    
    @validator('password_length', allow_reuse=True)
    def validate_password_length(cls, v):
        """Validate password length"""
        if v < 12:
            raise ValueError('Password length must be at least 12 characters for security')
        return v


class TemplateConfig(BaseModel):
    """Enhanced template configuration"""
    auto_update: bool = Field(default=False, description="Auto-update templates")
    update_check_interval: int = Field(default=86400, ge=3600, description="Update check interval in seconds")
    custom_template_dirs: List[str] = Field(default_factory=list, description="Custom template directories")
    template_cache_ttl: int = Field(default=3600, ge=60, description="Template cache TTL in seconds")
    enable_template_validation: bool = Field(default=True, description="Enable template validation")
    allow_insecure_templates: bool = Field(default=False, description="Allow templates with security warnings")
    max_template_size: int = Field(default=50 * 1024 * 1024, description="Max template size in bytes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "auto_update": False,
                "custom_template_dirs": ["/path/to/custom/templates"],
                "enable_template_validation": True
            }
        }
    
    @validator('custom_template_dirs', allow_reuse=True)
    def validate_template_dirs(cls, v):
        """Validate template directories"""
        validated_dirs = []
        for dir_path in v:
            if not os.path.isabs(dir_path):
                raise ValueError(f'Template directory must be absolute path: {dir_path}')
            if os.path.exists(dir_path) and not os.path.isdir(dir_path):
                raise ValueError(f'Template path is not a directory: {dir_path}')
            validated_dirs.append(dir_path)
        return validated_dirs


class PerformanceConfig(BaseModel):
    """Performance configuration"""
    cache_strategy: CacheStrategy = Field(default=CacheStrategy.HYBRID, description="Caching strategy")
    max_memory_cache_size: int = Field(default=128 * 1024 * 1024, ge=16 * 1024 * 1024, description="Max memory cache size in bytes")
    max_disk_cache_size: int = Field(default=1024 * 1024 * 1024, ge=100 * 1024 * 1024, description="Max disk cache size in bytes")
    cache_cleanup_interval: int = Field(default=3600, ge=300, description="Cache cleanup interval in seconds")
    parallel_operations: int = Field(default=4, ge=1, le=16, description="Number of parallel operations")
    enable_compression: bool = Field(default=True, description="Enable data compression")
    optimization_level: int = Field(default=2, ge=0, le=3, description="Optimization level (0-3)")
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "cache_strategy": "hybrid",
                "max_memory_cache_size": 134217728,
                "parallel_operations": 4
            }
        }


class MonitoringConfig(BaseModel):
    """Monitoring configuration"""
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_retention_days: int = Field(default=30, ge=1, le=365, description="Metrics retention period")
    health_check_enabled: bool = Field(default=True, description="Enable health checks")
    health_check_interval: int = Field(default=60, ge=10, le=600, description="Health check interval in seconds")
    alert_on_failures: bool = Field(default=True, description="Send alerts on failures")
    alert_threshold: int = Field(default=3, ge=1, le=10, description="Alert threshold for consecutive failures")
    enable_performance_monitoring: bool = Field(default=True, description="Enable performance monitoring")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enable_metrics": True,
                "health_check_enabled": True,
                "alert_on_failures": True
            }
        }


class NetworkConfig(BaseModel):
    """Network configuration"""
    default_network_driver: str = Field(default="bridge", description="Default network driver")
    enable_ipv6: bool = Field(default=False, description="Enable IPv6 support")
    dns_servers: List[str] = Field(default_factory=lambda: ["8.8.8.8", "8.8.4.4"], description="Default DNS servers")
    subnet_prefix: str = Field(default="172.20.0.0/16", description="Default subnet prefix")
    enable_network_isolation: bool = Field(default=True, description="Enable network isolation")
    default_domain: str = Field(default="localhost", description="Default domain for deployments")
    
    @validator('dns_servers', allow_reuse=True)
    def validate_dns_servers(cls, v):
        """Validate DNS server addresses"""
        import ipaddress
        validated_servers = []
        for dns in v:
            try:
                ipaddress.ip_address(dns)
                validated_servers.append(dns)
            except ipaddress.AddressValueError:
                logger.warning(f"Invalid DNS server address: {dns}")
        return validated_servers or ["8.8.8.8", "8.8.4.4"]


class BackupConfig(BaseModel):
    """Backup configuration"""
    enable_auto_backup: bool = Field(default=True, description="Enable automatic backups")
    backup_interval_hours: int = Field(default=24, ge=1, le=168, description="Backup interval in hours")
    max_backup_count: int = Field(default=7, ge=1, le=100, description="Maximum backup count")
    backup_compression: bool = Field(default=True, description="Enable backup compression")
    backup_encryption: bool = Field(default=True, description="Enable backup encryption")
    remote_backup_enabled: bool = Field(default=False, description="Enable remote backup")
    remote_backup_provider: Optional[str] = Field(default=None, description="Remote backup provider")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enable_auto_backup": True,
                "backup_interval_hours": 24,
                "max_backup_count": 7
            }
        }


class BlastDockConfig(BaseModel):
    """Main BlastDock configuration with all subsections"""
    version: str = Field(default="1.1.0", description="Configuration version")
    
    # Core configurations
    default_ports: DefaultPortsConfig = Field(default_factory=DefaultPortsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    templates: TemplateConfig = Field(default_factory=TemplateConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    backup: BackupConfig = Field(default_factory=BackupConfig)
    
    # Global settings  
    editor: str = Field(default="", description="Preferred text editor")
    browser: str = Field(default="", description="Preferred web browser")
    timezone: str = Field(default="UTC", description="Default timezone")
    language: str = Field(default="en", description="UI language")
    theme: str = Field(default="default", description="UI theme")
    
    # Advanced settings
    experimental_features: Dict[str, bool] = Field(default_factory=dict, description="Experimental features")
    plugin_directories: List[str] = Field(default_factory=list, description="Plugin directories")
    environment_variables: Dict[str, str] = Field(default_factory=dict, description="Custom environment variables")
    
    class Config:
        extra = "allow"
        json_schema_extra = {
            "example": {
                "version": "1.1.0",
                "default_ports": {"wordpress": 8080},
                "logging": {"level": "INFO"},
                "docker": {"compose_version": "3.8"},
                "security": {"auto_generate_passwords": True}
            }
        }
    
    @root_validator(allow_reuse=True)
    def validate_config_compatibility(cls, values):
        """Validate configuration compatibility"""
        version = values.get('version')
        
        # Ensure version compatibility
        if version:
            major_version = version.split('.')[0]
            if major_version != '1':
                logger.warning(f"Configuration version {version} may not be fully compatible")
        
        return values
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a nested setting using dot notation"""
        try:
            obj = self
            for part in key.split('.'):
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    return default
            return obj
        except Exception:
            return default
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a nested setting using dot notation"""
        parts = key.split('.')
        obj = self
        
        # Navigate to the parent object
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                raise ValueError(f"Invalid configuration path: {key}")
        
        # Set the final value
        final_key = parts[-1]
        if hasattr(obj, final_key):
            setattr(obj, final_key, value)
        else:
            raise ValueError(f"Invalid configuration key: {final_key}")
    
    def to_env_dict(self) -> Dict[str, str]:
        """Convert configuration to environment variables"""
        env_dict = {}
        
        def flatten_config(obj, prefix="BLASTDOCK"):
            if isinstance(obj, BaseModel):
                for key, value in obj.dict().items():
                    env_key = f"{prefix}_{key.upper()}"
                    if isinstance(value, dict):
                        flatten_config(value, env_key)
                    elif isinstance(value, (str, int, float, bool)):
                        env_dict[env_key] = str(value)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    env_key = f"{prefix}_{key.upper()}"
                    if isinstance(value, dict):
                        flatten_config(value, env_key)
                    elif isinstance(value, (str, int, float, bool)):
                        env_dict[env_key] = str(value)
        
        flatten_config(self)
        return env_dict