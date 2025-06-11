"""
Template management system
"""

import os
import yaml
import click
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from rich.console import Console
from rich.prompt import Prompt, Confirm

from ..utils.helpers import load_yaml, sanitize_name, generate_password
from ..utils.validators import (
    validate_project_name, validate_domain, validate_email,
    validate_port_input, validate_password, validate_database_name
)

console = Console()

class TemplateManager:
    def __init__(self):
        self.templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
    
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
        template_file = os.path.join(self.templates_dir, f"{template_name}.yml")
        return os.path.exists(template_file)
    
    def get_template_info(self, template_name):
        """Get template information"""
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
        template_file = os.path.join(self.templates_dir, f"{template_name}.yml")
        if not os.path.exists(template_file):
            raise Exception(f"Template {template_name} not found")
        
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
            raise Exception(f"Error loading template: {e}")
    
    def interactive_config(self, template_name):
        """Interactive configuration for template"""
        template_file = os.path.join(self.templates_dir, f"{template_name}.yml")
        if not os.path.exists(template_file):
            raise Exception(f"Template {template_name} not found")
        
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
            raise Exception(f"Error in interactive config: {e}")
    
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
    
    def render_template(self, template_name, config):
        """Render template with configuration"""
        try:
            template = self.jinja_env.get_template(f"{template_name}.yml")
            rendered = template.render(**config)
            return yaml.safe_load(rendered)
        except TemplateNotFound:
            raise Exception(f"Template {template_name} not found")
        except Exception as e:
            raise Exception(f"Error rendering template: {e}")