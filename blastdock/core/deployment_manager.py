"""
Deployment management system
"""

import os
import shutil
from datetime import datetime
from pathlib import Path

from ..utils.helpers import (
    get_deploys_dir, get_project_path, ensure_dir,
    save_yaml, save_json, load_json
)
from ..utils.docker_utils import DockerClient
from .template_manager import TemplateManager

class DeploymentManager:
    def __init__(self):
        self.deploys_dir = get_deploys_dir()
        self.docker_client = DockerClient()
        self.template_manager = TemplateManager()
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
        
        # Render template
        template_data = self.template_manager.render_template(template_name, config)
        
        # Create docker-compose.yml
        compose_data = template_data.get('compose', {})
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
        
        # Save project metadata
        metadata = {
            'project_name': project_name,
            'template': template_name,
            'created': datetime.now().isoformat(),
            'config': config
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