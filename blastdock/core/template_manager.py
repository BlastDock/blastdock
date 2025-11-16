"""
Template management system
"""

import os
import re
import yaml
import click
from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from jinja2.sandbox import SandboxedEnvironment
from rich.console import Console
from rich.prompt import Prompt, Confirm

from ..utils.helpers import load_yaml, sanitize_name, generate_password
from ..utils.validators import (
    validate_project_name, validate_domain, validate_email,
    validate_port_input, validate_password, validate_database_name
)
from ..exceptions import TemplateNotFoundError, TemplateValidationError, TemplateRenderError, ConfigurationError

console = Console()

class TemplateManager:
    def __init__(self):
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        # BUG-015 FIX: Use SandboxedEnvironment instead of regular Environment
        # This prevents template injection attacks by restricting access to dangerous operations
        self.jinja_env = SandboxedEnvironment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(['html', 'xml', 'yml', 'yaml'])
        )

        # Patterns that indicate potential template injection attempts
        self.TEMPLATE_INJECTION_PATTERNS = [
            r'\{\{.*\}\}',  # Jinja2 variable syntax
            r'\{%.*%\}',    # Jinja2 statement syntax
            r'\{#.*#\}',    # Jinja2 comment syntax
            r'__.*__',      # Python dunder methods
            r'\.mro\(',     # Method resolution order
            r'\.subclasses\(',  # Subclass access
            r'import\s+',   # Import statements
            r'eval\(',      # eval function
            r'exec\(',      # exec function
            r'__builtins__',  # Builtins access
        ]

        # BUG-NEW-001 FIX: Pattern for validating template names (alphanumeric, hyphens, underscores only)
        self.TEMPLATE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

    def _validate_template_name(self, template_name):
        """Validate template name to prevent path traversal attacks (BUG-NEW-001 FIX)

        Args:
            template_name: The template name to validate

        Raises:
            TemplateValidationError: If template name contains invalid characters or path traversal sequences
        """
        if not template_name:
            raise TemplateValidationError("Template name cannot be empty")

        # Check for path traversal sequences
        if '..' in template_name or '/' in template_name or '\\' in template_name:
            raise TemplateValidationError(
                f"Template name contains path traversal characters: {template_name}"
            )

        # Validate against allowed character pattern
        if not self.TEMPLATE_NAME_PATTERN.match(template_name):
            raise TemplateValidationError(
                f"Template name contains invalid characters. Only alphanumeric, hyphens, and underscores allowed: {template_name}"
            )

    def list_templates(self):
        """List available templates"""
        templates = []
        if os.path.exists(self.templates_dir):
            for file in os.listdir(self.templates_dir):
                if file.endswith('.yml') or file.endswith('.yaml'):
                    templates.append(file.replace('.yml', '').replace('.yaml', ''))
        return sorted(templates)
    
    def template_exists(self, template_name):
        """Check if template exists"""
        # BUG-NEW-001 FIX: Validate template name to prevent path traversal
        self._validate_template_name(template_name)
        template_file = os.path.join(self.templates_dir, f"{template_name}.yml")
        return os.path.exists(template_file)
    
    def get_template_info(self, template_name):
        """Get template information"""
        # BUG-NEW-001 FIX: Validate template name to prevent path traversal
        self._validate_template_name(template_name)
        template_file = os.path.join(self.templates_dir, f"{template_name}.yml")
        if not os.path.exists(template_file):
            return {}

        try:
            template_data = load_yaml(template_file)
            return template_data.get('template_info', {})
        except Exception as e:
            console.print(f"[red]Error loading template info: {e}[/red]")
            return {}
    
    def get_default_config(self, template_name):
        """Get default configuration for template"""
        # BUG-NEW-001 FIX: Validate template name to prevent path traversal
        self._validate_template_name(template_name)
        template_file = os.path.join(self.templates_dir, f"{template_name}.yml")
        if not os.path.exists(template_file):
            raise TemplateNotFoundError(template_name)
        
        try:
            template_data = load_yaml(template_file)
            config = {}
            
            # Extract default values from template
            fields = template_data.get('fields', {})
            for field_name, field_info in fields.items():
                default_value = field_info.get('default', '')
                field_type = field_info.get('type', 'string')
                
                # Handle auto-generated passwords
                if field_type == 'password' and default_value == 'auto':
                    config[field_name] = generate_password()
                else:
                    config[field_name] = default_value
            
            return config
        except Exception as e:
            raise TemplateRenderError(template_name, str(e))
    
    def interactive_config(self, template_name):
        """Interactive configuration for template"""
        # BUG-NEW-001 FIX: Validate template name to prevent path traversal
        self._validate_template_name(template_name)
        template_file = os.path.join(self.templates_dir, f"{template_name}.yml")
        if not os.path.exists(template_file):
            raise TemplateNotFoundError(template_name)
        
        try:
            template_data = load_yaml(template_file)
            config = {}
            
            console.print(f"\n[bold blue]Configuring {template_name}[/bold blue]")
            
            # Get template info
            template_info = template_data.get('template_info', {})
            description = template_info.get('description', '')
            if description:
                console.print(f"[dim]{description}[/dim]\n")
            
            fields = template_data.get('fields', {})
            for field_name, field_info in fields.items():
                config[field_name] = self._prompt_field(field_name, field_info)
            
            return config
        except Exception as e:
            raise ConfigurationError(f"Error in interactive config: {e}")
    
    def _prompt_field(self, field_name, field_info):
        """Prompt user for field value"""
        field_type = field_info.get('type', 'string')
        description = field_info.get('description', field_name)
        default = field_info.get('default', '')
        required = field_info.get('required', False)
        
        while True:
            if field_type == 'boolean':
                return Confirm.ask(description, default=default)
            elif field_type == 'password':
                if default == 'auto':
                    if Confirm.ask(f"Auto-generate {description}?", default=True):
                        return generate_password()
                value = Prompt.ask(description, password=True, default=default if default != 'auto' else '')
            else:
                value = Prompt.ask(description, default=str(default) if default else '')
            
            # Validation
            valid, error_msg = self._validate_field(field_name, value, field_info)
            if valid:
                return value
            elif error_msg:
                console.print(f"[red]{error_msg}[/red]")
            
            if not required and value == '':
                return value
    
    def _validate_field(self, field_name, value, field_info):
        """Validate field value"""
        field_type = field_info.get('type', 'string')
        required = field_info.get('required', False)
        
        if required and not value:
            return False, f"{field_name} is required"
        
        if not value:  # Skip validation for empty optional fields
            return True, ""
        
        # Type-specific validation
        if field_type == 'port':
            return validate_port_input(value)
        elif field_type == 'email':
            return validate_email(value)
        elif field_type == 'domain':
            return validate_domain(value)
        elif field_type == 'password':
            return validate_password(value)
        elif field_type == 'database_name':
            return validate_database_name(value)
        elif field_name.endswith('_name') and field_name.startswith('project'):
            return validate_project_name(value)
        
        return True, ""
    
    def _sanitize_config_value(self, value):
        """Sanitize configuration value to prevent template injection (BUG-015 FIX)

        Args:
            value: The configuration value to sanitize

        Returns:
            Sanitized value

        Raises:
            TemplateValidationError: If dangerous patterns are detected
        """
        if not isinstance(value, str):
            # Non-string values are safe
            return value

        # Check for dangerous patterns
        for pattern in self.TEMPLATE_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise TemplateValidationError(
                    f"Configuration value contains potentially dangerous pattern: {pattern}. "
                    f"Value: {value[:50]}{'...' if len(value) > 50 else ''}"
                )

        return value

    def _sanitize_config(self, config):
        """Sanitize all configuration values recursively (BUG-015 FIX)

        Args:
            config: Configuration dictionary

        Returns:
            Sanitized configuration dictionary
        """
        sanitized = {}

        for key, value in config.items():
            if isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = self._sanitize_config(value)
            elif isinstance(value, list):
                # Sanitize list items
                sanitized[key] = [
                    self._sanitize_config(item) if isinstance(item, dict)
                    else self._sanitize_config_value(item)
                    for item in value
                ]
            else:
                # Sanitize single value
                sanitized[key] = self._sanitize_config_value(value)

        return sanitized

    def render_template(self, template_name, config):
        """Render template with configuration (BUG-015 FIX: Added sanitization)"""
        try:
            # BUG-NEW-001 FIX: Validate template name to prevent path traversal
            self._validate_template_name(template_name)

            # Sanitize config before rendering to prevent template injection
            sanitized_config = self._sanitize_config(config)

            template = self.jinja_env.get_template(f"{template_name}.yml")
            rendered = template.render(**sanitized_config)
            return yaml.safe_load(rendered)
        except TemplateNotFound:
            raise TemplateNotFoundError(template_name)
        except TemplateValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            raise TemplateRenderError(template_name, str(e))