"""
Template data models and configuration structures
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator


class FieldType(str, Enum):
    """Template field types"""
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    PORT = "port"
    PASSWORD = "password"
    EMAIL = "email"
    DOMAIN = "domain"
    URL = "url"
    PATH = "path"
    CHOICE = "choice"


class TemplateField(BaseModel):
    """Template field configuration"""
    name: str = Field(..., description="Field name")
    type: FieldType = Field(..., description="Field type")
    description: str = Field(..., description="Field description")
    default: Optional[Union[str, int, bool]] = None
    required: bool = True
    choices: Optional[List[str]] = None
    validation_pattern: Optional[str] = None
    min_value: Optional[int] = None
    max_value: Optional[int] = None
    
    @validator('default')
    def validate_default_type(cls, v, values):
        """Validate default value type matches field type"""
        if v is None:
            return v
        
        field_type = values.get('type')
        if field_type in (FieldType.PORT, FieldType.INTEGER):
            if isinstance(v, str) and v.isdigit():
                return int(v)
            elif isinstance(v, int):
                return v
        elif field_type == FieldType.BOOLEAN:
            if isinstance(v, str):
                return v.lower() in ('true', '1', 'yes')
            elif isinstance(v, bool):
                return v
        
        return v
    
    @validator('choices', always=True)
    def validate_choices(cls, v, values):
        """Validate choices for choice fields"""
        field_type = values.get('type')
        if field_type == FieldType.CHOICE and (v is None or len(v) == 0):
            raise ValueError("Choice fields must have choices defined")
        return v


class ServiceConfig(BaseModel):
    """Service configuration within template"""
    image: str = Field(..., description="Docker image")
    ports: Optional[List[str]] = None
    volumes: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    depends_on: Optional[List[str]] = None
    command: Optional[str] = None
    restart: str = "unless-stopped"
    labels: Optional[Dict[str, str]] = None
    networks: Optional[List[str]] = None


class TraefikConfig(BaseModel):
    """Traefik configuration for template"""
    enabled: bool = True
    service_port: int = Field(..., description="Internal service port")
    path_prefix: Optional[str] = None
    priority: int = 1
    middlewares: Optional[List[str]] = None
    health_check: Optional[str] = None
    sticky_sessions: bool = False


class TemplateConfig(BaseModel):
    """Complete template configuration"""
    # Template metadata
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    version: str = Field(default="1.0", description="Template version")
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    maintainer: Optional[str] = None
    
    # Service configuration
    services: Dict[str, ServiceConfig] = Field(..., description="Docker services")
    networks: Optional[Dict[str, Dict[str, Any]]] = None
    volumes: Optional[Dict[str, Dict[str, Any]]] = None
    
    # Template fields
    fields: Dict[str, TemplateField] = Field(default_factory=dict)
    
    # Traefik configuration
    traefik_config: Optional[TraefikConfig] = None
    
    # Additional files to generate
    config_files: List[Dict[str, str]] = Field(default_factory=list)
    
    # Requirements and dependencies
    requires: List[str] = Field(default_factory=list)
    min_docker_version: Optional[str] = None
    min_compose_version: Optional[str] = None


class Template(BaseModel):
    """Template with runtime information"""
    config: TemplateConfig
    file_path: str = Field(..., description="Template file path")
    is_valid: bool = True
    validation_errors: List[str] = Field(default_factory=list)
    
    # Usage statistics
    usage_count: int = 0
    last_used: Optional[str] = None
    
    def get_service_names(self) -> List[str]:
        """Get list of service names"""
        return list(self.config.services.keys())
    
    def get_primary_service(self) -> Optional[str]:
        """Get the primary service name"""
        if self.config.services:
            # Look for service with same name as template
            if self.config.name in self.config.services:
                return self.config.name
            # Return first service
            return list(self.config.services.keys())[0]
        return None
    
    def supports_traefik(self) -> bool:
        """Check if template supports Traefik integration"""
        return self.config.traefik_config is not None
    
    def get_exposed_ports(self) -> List[int]:
        """Get list of exposed ports from all services"""
        ports = []
        for service in self.config.services.values():
            if service.ports:
                for port_mapping in service.ports:
                    # Extract port number from mapping like "8080:80"
                    if ':' in port_mapping:
                        external_port = port_mapping.split(':')[0]
                        try:
                            ports.append(int(external_port))
                        except ValueError:
                            continue
        return ports
    
    def get_required_fields(self) -> List[str]:
        """Get list of required field names"""
        return [name for name, field in self.config.fields.items() if field.required]
    
    def validate_field_value(self, field_name: str, value: Any) -> bool:
        """Validate a field value against field configuration"""
        if field_name not in self.config.fields:
            return False
        
        field = self.config.fields[field_name]
        
        # Type validation
        if field.type == FieldType.STRING and not isinstance(value, str):
            return False
        elif field.type == FieldType.INTEGER and not isinstance(value, int):
            return False
        elif field.type == FieldType.BOOLEAN and not isinstance(value, bool):
            return False
        elif field.type == FieldType.PORT:
            try:
                port = int(value)
                return 1 <= port <= 65535
            except (ValueError, TypeError):
                return False
        elif field.type == FieldType.EMAIL:
            import re
            from ..constants import EMAIL_PATTERN
            return re.match(EMAIL_PATTERN, str(value)) is not None
        elif field.type == FieldType.DOMAIN:
            import re
            from ..constants import DOMAIN_PATTERN
            return re.match(DOMAIN_PATTERN, str(value)) is not None
        elif field.type == FieldType.CHOICE:
            return field.choices and str(value) in field.choices
        
        # Range validation for integers
        if field.type == FieldType.INTEGER and isinstance(value, int):
            if field.min_value is not None and value < field.min_value:
                return False
            if field.max_value is not None and value > field.max_value:
                return False
        
        # Pattern validation
        if field.validation_pattern and isinstance(value, str):
            import re
            return re.match(field.validation_pattern, value) is not None
        
        return True