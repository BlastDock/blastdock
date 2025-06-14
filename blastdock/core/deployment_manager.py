"""
Deployment management system
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

from ..utils.helpers import (
    get_deploys_dir, get_project_path, ensure_dir,
    save_yaml, save_json, load_json, load_yaml
)
from ..utils.docker_utils import DockerClient
from .template_manager import TemplateManager
from .traefik import TraefikIntegrator
from .domain import DomainManager

class DeploymentManager:
    def __init__(self):
        self.deploys_dir = get_deploys_dir()
        self.docker_client = DockerClient()
        self.template_manager = TemplateManager()
        self.domain_manager = DomainManager()
        self.traefik_integrator = TraefikIntegrator(self.domain_manager)
        ensure_dir(self.deploys_dir)
    
    def create_deployment(self, project_name, template_name, config):
        """Create a new deployment"""
        project_path = get_project_path(project_name)
        
        if os.path.exists(project_path):
            raise Exception(f"Project '{project_name}' already exists")
        
        # Create project directory structure
        ensure_dir(project_path)
        ensure_dir(os.path.join(project_path, 'config'))
        ensure_dir(os.path.join(project_path, 'logs'))
        
        # Add project name to config
        config['project_name'] = project_name
        
        # Load the raw template to get metadata
        template_file = os.path.join(self.template_manager.templates_dir, f"{template_name}.yml")
        raw_template_data = load_yaml(template_file)
        
        # Render template
        template_data = self.template_manager.render_template(template_name, config)
        
        # Get compose data
        compose_data = template_data.get('compose', {})
        
        # Process with TraefikIntegrator if enabled
        compose_data = self.traefik_integrator.process_compose(
            compose_data, 
            project_name, 
            raw_template_data,  # Pass raw template for metadata
            config
        )
        
        # Create docker-compose.yml
        compose_file = os.path.join(project_path, 'docker-compose.yml')
        save_yaml(compose_data, compose_file)
        
        # Create .env file
        env_file = os.path.join(project_path, '.env')
        with open(env_file, 'w') as f:
            f.write(f"PROJECT_NAME={project_name}\n")
            for key, value in config.items():
                if key != 'project_name':
                    f.write(f"{key.upper()}={value}\n")
        
        # Create config files if specified in template
        config_files = template_data.get('config_files', [])
        for config_file in config_files:
            file_path = os.path.join(project_path, config_file['path'])
            ensure_dir(os.path.dirname(file_path))
            
            # Render config file content
            from jinja2 import Template
            template = Template(config_file['content'])
            content = template.render(**config)
            
            with open(file_path, 'w') as f:
                f.write(content)
        
        # Get domain configuration if Traefik is enabled
        domain_config = None
        if self._is_traefik_enabled(config, raw_template_data):
            domain_config = self.domain_manager.get_domain_config(project_name, config)
        
        # Save project metadata
        metadata = {
            'project_name': project_name,
            'template': template_name,
            'created': datetime.now().isoformat(),
            'config': config,
            'domain_config': domain_config
        }
        metadata_file = os.path.join(project_path, '.blastdock.json')
        save_json(metadata, metadata_file)
        
        return project_path
    
    def project_exists(self, project_name):
        """Check if project exists"""
        project_path = get_project_path(project_name)
        return os.path.exists(project_path) and os.path.exists(
            os.path.join(project_path, '.blastdock.json')
        )
    
    def list_projects(self):
        """List all projects"""
        projects = []
        if os.path.exists(self.deploys_dir):
            for item in os.listdir(self.deploys_dir):
                project_path = os.path.join(self.deploys_dir, item)
                if os.path.isdir(project_path) and os.path.exists(
                    os.path.join(project_path, '.blastdock.json')
                ):
                    projects.append(item)
        return sorted(projects)
    
    def get_project_metadata(self, project_name):
        """Get project metadata"""
        project_path = get_project_path(project_name)
        metadata_file = os.path.join(project_path, '.blastdock.json')
        
        if not os.path.exists(metadata_file):
            return {}
        
        try:
            return load_json(metadata_file)
        except Exception:
            return {}
    
    def get_project_template(self, project_name):
        """Get project template name"""
        metadata = self.get_project_metadata(project_name)
        return metadata.get('template', 'unknown')
    
    def get_project_created_date(self, project_name):
        """Get project creation date"""
        metadata = self.get_project_metadata(project_name)
        created = metadata.get('created', '')
        if created:
            try:
                dt = datetime.fromisoformat(created)
                return dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        return 'unknown'
    
    def get_project_config(self, project_name):
        """Get project configuration"""
        metadata = self.get_project_metadata(project_name)
        config = metadata.get('config', {})
        
        # Add additional metadata
        enhanced_config = {
            'project_name': project_name,
            'template': metadata.get('template', 'unknown'),
            'created': metadata.get('created', 'unknown'),
            'config': config
        }
        
        return enhanced_config
    
    def deploy(self, project_name):
        """Deploy a project"""
        if not self.project_exists(project_name):
            raise Exception(f"Project '{project_name}' not found")
        
        if not self.docker_client.is_docker_running():
            raise Exception("Docker is not running")
        
        project_path = get_project_path(project_name)
        
        # Run docker-compose up
        success, output = self.docker_client.compose_up(project_path, project_name)
        
        if not success:
            raise Exception(f"Deployment failed: {output}")
        
        return output
    
    def stop(self, project_name):
        """Stop a project"""
        if not self.project_exists(project_name):
            raise Exception(f"Project '{project_name}' not found")
        
        project_path = get_project_path(project_name)
        
        # Run docker-compose down
        success, output = self.docker_client.compose_down(project_path, project_name)
        
        if not success:
            raise Exception(f"Stop failed: {output}")
        
        return output
    
    def remove(self, project_name, keep_data=False):
        """Remove a project"""
        if not self.project_exists(project_name):
            raise Exception(f"Project '{project_name}' not found")
        
        project_path = get_project_path(project_name)
        
        # Stop and remove containers 
        try:
            if keep_data:
                # Use docker-compose down (keeps volumes)
                success, output = self.docker_client.compose_down(project_path, project_name)
                if not success:
                    raise Exception(f"Failed to stop containers: {output}")
            else:
                # Use docker-compose down --volumes (removes volumes too)
                success, output = self.docker_client.compose_down_with_volumes(project_path, project_name)
                if not success:
                    raise Exception(f"Failed to stop containers and remove volumes: {output}")
        except Exception:
            pass  # Continue even if stop fails
        
        # Remove project directory
        shutil.rmtree(project_path)
        
        return f"Project '{project_name}' removed"
    
    def show_logs(self, project_name, follow=False, service=None):
        """Show project logs"""
        if not self.project_exists(project_name):
            raise Exception(f"Project '{project_name}' not found")
        
        project_path = get_project_path(project_name)
        
        success, output = self.docker_client.compose_logs(
            project_path, project_name, service=service, follow=follow
        )
        
        if not success:
            raise Exception(f"Failed to get logs: {output}")
        
        if not follow:
            print(output)
        
        return output
    
    def _is_traefik_enabled(self, user_config, template_data):
        """Check if Traefik should be enabled for this deployment."""
        # Check user config first
        if 'traefik_enabled' in user_config:
            return user_config['traefik_enabled']
            
        # Check template default
        fields = template_data.get('fields', {})
        if 'traefik_enabled' in fields:
            return fields['traefik_enabled'].get('default', True)
            
        # Default to enabled if template is Traefik compatible
        template_info = template_data.get('template_info', {})
        return template_info.get('traefik_compatible', False)
    def _create_project_directory(self, project_name):
        """Create project directory"""
        from pathlib import Path
        import os
        
        config = self._get_config()
        projects_dir = getattr(config, 'projects_dir', os.path.expanduser('~/blastdock/projects'))
        project_dir = Path(projects_dir) / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir
    
    def _write_compose_file(self, compose_data, project_dir):
        """Write docker-compose.yml file"""
        import yaml
        
        compose_file = project_dir / 'docker-compose.yml'
        with open(compose_file, 'w') as f:
            yaml.dump(compose_data, f, default_flow_style=False)
        return True
    
    def _write_env_file(self, env_vars, project_dir):
        """Write .env file"""
        env_file = project_dir / '.env'
        with open(env_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        return True
    
    def _run_docker_compose(self, project_dir, project_name):
        """Run docker-compose up"""
        import subprocess
        
        try:
            result = subprocess.run([
                'docker-compose', '-p', project_name, 'up', '-d'
            ], cwd=project_dir, capture_output=True, text=True)
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _validate_project_name(self, name):
        """Validate project name"""
        import re
        return bool(re.match(r'^[a-z0-9-]+$', name)) and len(name) > 0
    
    def _get_config(self):
        """Get configuration"""
        try:
            from .config import get_config
            return get_config()
        except:
            # Fallback mock config
            class MockConfig:
                projects_dir = "~/blastdock/projects"
            return MockConfig()

