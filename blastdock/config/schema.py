"""
Configuration schema validation and management
"""

import json
from typing import Dict, Any, List, Optional, Union, Type
from pathlib import Path
from jsonschema import validate, ValidationError, Draft7Validator
from pydantic import BaseModel

from .simple_models import BlastDockConfig

from ..utils.logging import get_logger
from ..utils.filesystem import paths
from ..exceptions import ConfigurationError

logger = get_logger(__name__)


class ConfigSchema:
    """Configuration schema management"""
    
    def __init__(self, schema_dir: Optional[Path] = None):
        self.schema_dir = schema_dir or (paths.config_dir / 'schemas')
        self.schema_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache for loaded schemas
        self._schema_cache: Dict[str, Dict[str, Any]] = {}
        
        # Generate default schemas
        self._generate_default_schemas()
    
    def _generate_default_schemas(self) -> None:
        """Generate default JSON schemas from Pydantic models"""
        try:
            # Generate schema for main configuration
            main_schema = BlastDockConfig.schema()
            self._save_schema('blastdock-config', main_schema)
            
            # Generate schemas for individual components
            from .simple_models import (
                DefaultPortsConfig, LoggingConfig, DockerConfig,
                SecurityConfig
            )
            
            schemas = {
                'default-ports': DefaultPortsConfig.schema(),
                'logging': LoggingConfig.schema(),
                'docker': DockerConfig.schema(),
                'security': SecurityConfig.schema()
            }
            
            for name, schema in schemas.items():
                self._save_schema(name, schema)
            
            logger.debug("Generated default configuration schemas")
            
        except Exception as e:
            logger.warning(f"Failed to generate default schemas: {e}")
    
    def _save_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """Save schema to file"""
        schema_file = self.schema_dir / f"{name}.json"
        
        try:
            with open(schema_file, 'w') as f:
                json.dump(schema, f, indent=2, sort_keys=True)
            
            # Cache the schema
            self._schema_cache[name] = schema
            
        except Exception as e:
            logger.warning(f"Failed to save schema {name}: {e}")
    
    def get_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get schema by name"""
        if name in self._schema_cache:
            return self._schema_cache[name]
        
        schema_file = self.schema_dir / f"{name}.json"
        if schema_file.exists():
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                
                self._schema_cache[name] = schema
                return schema
                
            except Exception as e:
                logger.error(f"Failed to load schema {name}: {e}")
        
        return None
    
    def validate_config_against_schema(self, config: Dict[str, Any], 
                                     schema_name: str = 'blastdock-config') -> List[str]:
        """Validate configuration against JSON schema"""
        schema = self.get_schema(schema_name)
        if not schema:
            return [f"Schema '{schema_name}' not found"]
        
        try:
            validate(instance=config, schema=schema)
            return []  # No validation errors
            
        except ValidationError as e:
            return [self._format_validation_error(e)]
        except Exception as e:
            return [f"Schema validation error: {e}"]
    
    def _format_validation_error(self, error: ValidationError) -> str:
        """Format validation error for user-friendly display"""
        path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        return f"Validation error at {path}: {error.message}"
    
    def validate_partial_config(self, config: Dict[str, Any], section: str) -> List[str]:
        """Validate a specific configuration section"""
        schema = self.get_schema(section)
        if not schema:
            return [f"Schema for section '{section}' not found"]
        
        section_config = config.get(section, {})
        return self.validate_config_against_schema(section_config, section)
    
    def get_schema_documentation(self, schema_name: str) -> Dict[str, Any]:
        """Get documentation from schema"""
        schema = self.get_schema(schema_name)
        if not schema:
            return {}
        
        return {
            'title': schema.get('title', schema_name),
            'description': schema.get('description', ''),
            'properties': self._extract_property_docs(schema.get('properties', {})),
            'required': schema.get('required', []),
            'examples': schema.get('examples', [])
        }
    
    def _extract_property_docs(self, properties: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Extract documentation from schema properties"""
        docs = {}
        
        for prop_name, prop_schema in properties.items():
            docs[prop_name] = {
                'type': prop_schema.get('type', 'unknown'),
                'description': prop_schema.get('description', ''),
                'default': prop_schema.get('default'),
                'enum': prop_schema.get('enum'),
                'minimum': prop_schema.get('minimum'),
                'maximum': prop_schema.get('maximum'),
                'examples': prop_schema.get('examples', [])
            }
            
            # Handle nested objects
            if prop_schema.get('type') == 'object' and 'properties' in prop_schema:
                docs[prop_name]['properties'] = self._extract_property_docs(prop_schema['properties'])
        
        return docs
    
    def create_config_template(self, schema_name: str = 'blastdock-config') -> Dict[str, Any]:
        """Create configuration template from schema"""
        schema = self.get_schema(schema_name)
        if not schema:
            return {}
        
        return self._create_template_from_schema(schema)
    
    def _create_template_from_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Create template configuration from schema"""
        template = {}
        properties = schema.get('properties', {})
        
        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get('type')
            default_value = prop_schema.get('default')
            
            if default_value is not None:
                template[prop_name] = default_value
            elif prop_type == 'object':
                template[prop_name] = self._create_template_from_schema(prop_schema)
            elif prop_type == 'array':
                template[prop_name] = []
            elif prop_type == 'string':
                template[prop_name] = ""
            elif prop_type == 'integer':
                template[prop_name] = 0
            elif prop_type == 'number':
                template[prop_name] = 0.0
            elif prop_type == 'boolean':
                template[prop_name] = False
        
        return template
    
    def list_available_schemas(self) -> List[str]:
        """List all available schemas"""
        schemas = []
        
        for schema_file in self.schema_dir.glob('*.json'):
            schemas.append(schema_file.stem)
        
        return sorted(schemas)
    
    def export_schema(self, schema_name: str, export_path: str) -> None:
        """Export schema to file"""
        schema = self.get_schema(schema_name)
        if not schema:
            raise ConfigurationError(f"Schema '{schema_name}' not found")
        
        with open(export_path, 'w') as f:
            json.dump(schema, f, indent=2, sort_keys=True)
        
        logger.info(f"Exported schema '{schema_name}' to {export_path}")
    
    def import_schema(self, import_path: str, schema_name: str) -> None:
        """Import schema from file"""
        try:
            with open(import_path, 'r') as f:
                schema = json.load(f)
            
            # Validate that it's a valid JSON schema
            Draft7Validator.check_schema(schema)
            
            # Save the schema
            self._save_schema(schema_name, schema)
            
            logger.info(f"Imported schema '{schema_name}' from {import_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to import schema: {e}")


class ConfigValidator:
    """Enhanced configuration validator"""
    
    def __init__(self, schema_manager: Optional[ConfigSchema] = None):
        self.schema_manager = schema_manager or ConfigSchema()
        
        # Custom validation rules
        self._custom_validators: Dict[str, callable] = {}
        self._register_custom_validators()
    
    def _register_custom_validators(self) -> None:
        """Register custom validation rules"""
        self._custom_validators.update({
            'port_range': self._validate_port_range_custom,
            'directory_path': self._validate_directory_path,
            'log_level': self._validate_log_level,
            'docker_version': self._validate_docker_version,
            'positive_integer': self._validate_positive_integer,
            'password_strength': self._validate_password_strength
        })
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Comprehensive configuration validation"""
        issues = []
        
        # Schema validation
        schema_issues = self.schema_manager.validate_config_against_schema(config)
        issues.extend(schema_issues)
        
        # Custom validation rules
        custom_issues = self._run_custom_validations(config)
        issues.extend(custom_issues)
        
        # Cross-section validation
        cross_section_issues = self._validate_cross_sections(config)
        issues.extend(cross_section_issues)
        
        return issues
    
    def _run_custom_validations(self, config: Dict[str, Any]) -> List[str]:
        """Run custom validation rules"""
        issues = []
        
        # Validate default ports
        if 'default_ports' in config:
            for port_name, port_value in config['default_ports'].items():
                if not self._validate_port_range_custom(port_value):
                    issues.append(f"Invalid port value for {port_name}: {port_value}")
        
        # Validate logging configuration
        if 'logging' in config:
            logging_config = config['logging']
            
            if 'level' in logging_config:
                if not self._validate_log_level(logging_config['level']):
                    issues.append(f"Invalid log level: {logging_config['level']}")
            
            if 'log_dir' in logging_config and logging_config['log_dir']:
                if not self._validate_directory_path(logging_config['log_dir']):
                    issues.append(f"Invalid log directory: {logging_config['log_dir']}")
        
        # Validate Docker configuration
        if 'docker' in config:
            docker_config = config['docker']
            
            if 'compose_version' in docker_config:
                if not self._validate_docker_version(docker_config['compose_version']):
                    issues.append(f"Invalid Docker Compose version: {docker_config['compose_version']}")
        
        # Validate security configuration
        if 'security' in config:
            security_config = config['security']
            
            if 'password_length' in security_config:
                if not self._validate_positive_integer(security_config['password_length'], min_val=8):
                    issues.append("Password length must be at least 8 characters")
        
        return issues
    
    def _validate_cross_sections(self, config: Dict[str, Any]) -> List[str]:
        """Validate relationships between configuration sections"""
        issues = []
        
        # Check if monitoring is enabled but metrics retention is too low
        monitoring = config.get('monitoring', {})
        if monitoring.get('enable_metrics', True):
            retention_days = monitoring.get('metrics_retention_days', 30)
            if retention_days < 7:
                issues.append("Metrics retention should be at least 7 days when monitoring is enabled")
        
        # Check if backup is enabled but backup directory is not set
        backup = config.get('backup', {})
        if backup.get('enable_auto_backup', True):
            interval = backup.get('backup_interval_hours', 24)
            if interval < 1:
                issues.append("Backup interval must be at least 1 hour")
        
        # Check performance settings consistency
        performance = config.get('performance', {})
        if performance.get('cache_strategy') == 'memory':
            max_memory = performance.get('max_memory_cache_size', 0)
            if max_memory < 16 * 1024 * 1024:  # 16MB
                issues.append("Memory cache size is too small for memory-only caching strategy")
        
        return issues
    
    def _validate_port_range_custom(self, port: Any) -> bool:
        """Validate port is in valid range"""
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False
    
    def _validate_directory_path(self, path: Any) -> bool:
        """Validate directory path"""
        if not isinstance(path, str):
            return False
        
        try:
            path_obj = Path(path)
            # Check if path is absolute and doesn't contain invalid characters
            return path_obj.is_absolute() and not any(char in str(path_obj) for char in ['<', '>', '|', '*', '?'])
        except Exception:
            return False
    
    def _validate_log_level(self, level: Any) -> bool:
        """Validate log level"""
        if not isinstance(level, str):
            return False
        
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        return level.upper() in valid_levels
    
    def _validate_docker_version(self, version: Any) -> bool:
        """Validate Docker Compose version"""
        if not isinstance(version, str):
            return False
        
        valid_versions = ['3.0', '3.1', '3.2', '3.3', '3.4', '3.5', '3.6', '3.7', '3.8', '3.9']
        return version in valid_versions
    
    def _validate_positive_integer(self, value: Any, min_val: int = 1) -> bool:
        """Validate positive integer with minimum value"""
        try:
            int_value = int(value)
            return int_value >= min_val
        except (ValueError, TypeError):
            return False
    
    def _validate_password_strength(self, password: Any) -> bool:
        """Validate password strength"""
        if not isinstance(password, str):
            return False
        
        # Basic password strength checks
        if len(password) < 8:
            return False
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        return sum([has_upper, has_lower, has_digit, has_special]) >= 3
    
    def validate_section(self, config: Dict[str, Any], section: str) -> List[str]:
        """Validate a specific configuration section"""
        issues = []
        
        # Schema validation for section
        schema_issues = self.schema_manager.validate_partial_config(config, section)
        issues.extend(schema_issues)
        
        # Custom validation for specific sections
        if section in config:
            section_config = config[section]
            
            if section == 'default_ports':
                for port_name, port_value in section_config.items():
                    if not self._validate_port_range_custom(port_value):
                        issues.append(f"Invalid port value for {port_name}: {port_value}")
            
            elif section == 'logging':
                if 'level' in section_config and not self._validate_log_level(section_config['level']):
                    issues.append(f"Invalid log level: {section_config['level']}")
            
            elif section == 'security':
                if 'password_length' in section_config:
                    if not self._validate_positive_integer(section_config['password_length'], min_val=8):
                        issues.append("Password length must be at least 8 characters")
        
        return issues
    
    def add_custom_validator(self, name: str, validator_func: callable) -> None:
        """Add custom validation rule"""
        self._custom_validators[name] = validator_func
    
    def remove_custom_validator(self, name: str) -> None:
        """Remove custom validation rule"""
        self._custom_validators.pop(name, None)
    
    def get_validation_suggestions(self, config: Dict[str, Any]) -> List[str]:
        """Get suggestions for improving configuration"""
        suggestions = []
        
        # Check for missing optional but recommended settings
        if 'backup' not in config:
            suggestions.append("Consider enabling backup configuration for data protection")
        
        if 'monitoring' not in config:
            suggestions.append("Consider enabling monitoring for better observability")
        
        # Check for suboptimal settings
        logging_config = config.get('logging', {})
        if logging_config.get('level', 'INFO') == 'DEBUG':
            suggestions.append("DEBUG log level may impact performance in production")
        
        security_config = config.get('security', {})
        if not security_config.get('enable_secrets_encryption', True):
            suggestions.append("Consider enabling secrets encryption for better security")
        
        performance_config = config.get('performance', {})
        if performance_config.get('cache_strategy') == 'disabled':
            suggestions.append("Enabling caching can improve performance")
        
        return suggestions