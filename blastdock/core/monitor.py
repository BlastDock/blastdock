"""
Monitoring and status checking system
"""

from ..utils.docker_utils import DockerClient
from .deployment_manager import DeploymentManager
from rich.text import Text
from rich.table import Table

class Monitor:
    def __init__(self):
        self.docker_client = DockerClient()
        self.deployment_manager = DeploymentManager()
    
    def get_status(self, project_name):
        """Get simple status of a project"""
        if not self.deployment_manager.project_exists(project_name):
            return "Not Found"
        
        try:
            containers = self.docker_client.get_container_status(project_name)
            
            if not containers:
                return "Stopped"
            
            running_count = sum(1 for c in containers if c['status'] == 'running')
            total_count = len(containers)
            
            if running_count == total_count:
                return "Running"
            elif running_count > 0:
                return f"Partial ({running_count}/{total_count})"
            else:
                return "Stopped"
        
        except Exception:
            return "Error"
    
    def get_detailed_status(self, project_name):
        """Get detailed status information"""
        if not self.deployment_manager.project_exists(project_name):
            return Text("Project not found", style="red")
        
        try:
            containers = self.docker_client.get_container_status(project_name)
            metadata = self.deployment_manager.get_project_metadata(project_name)
            
            # Create status text
            status_text = Text()
            status_text.append(f"Project: {project_name}\n", style="bold cyan")
            status_text.append(f"Template: {metadata.get('template', 'unknown')}\n", style="blue")
            status_text.append(f"Created: {self.deployment_manager.get_project_created_date(project_name)}\n\n", style="dim")
            
            if not containers:
                status_text.append("No containers found\n", style="yellow")
                return status_text
            
            # Container status table
            table = Table(title="Container Status")
            table.add_column("Container", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Image", style="blue")
            table.add_column("Ports", style="magenta")
            
            for container in containers:
                # Format ports
                ports_str = ""
                if container['ports']:
                    port_mappings = []
                    for internal_port, external_mappings in container['ports'].items():
                        if external_mappings:
                            for mapping in external_mappings:
                                port_mappings.append(f"{mapping['HostPort']}:{internal_port}")
                    ports_str = ", ".join(port_mappings)
                
                # Color status
                status = container['status']
                if status == 'running':
                    status_style = "green"
                elif status in ['exited', 'stopped']:
                    status_style = "red"
                else:
                    status_style = "yellow"
                
                table.add_row(
                    container['name'],
                    Text(status, style=status_style),
                    container['image'],
                    ports_str
                )
            
            # Convert table to text (simplified representation)
            status_text.append("Containers:\n", style="bold")
            for container in containers:
                status_color = "green" if container['status'] == 'running' else "red"
                status_text.append(f"  • {container['name']}: ", style="cyan")
                status_text.append(f"{container['status']}", style=status_color)
                status_text.append(f" ({container['image']})\n", style="dim")
            
            return status_text
        
        except Exception as e:
            return Text(f"Error getting status: {str(e)}", style="red")
    
    def get_resource_usage(self, project_name):
        """Get resource usage information"""
        # This would require additional Docker API calls
        # For now, return basic info
        try:
            containers = self.docker_client.get_container_status(project_name)
            return {
                'container_count': len(containers),
                'running_count': sum(1 for c in containers if c['status'] == 'running')
            }
        except Exception:
            return {'container_count': 0, 'running_count': 0}
    
    def health_check(self, project_name):
        """Perform health check on project"""
        if not self.deployment_manager.project_exists(project_name):
            return False, "Project not found"
        
        try:
            containers = self.docker_client.get_container_status(project_name)
            
            if not containers:
                return False, "No containers found"
            
            unhealthy_containers = [
                c['name'] for c in containers 
                if c['status'] not in ['running', 'restarting']
            ]
            
            if unhealthy_containers:
                return False, f"Unhealthy containers: {', '.join(unhealthy_containers)}"
            
            return True, "All containers healthy"
        
        except Exception as e:
            return False, f"Health check failed: {str(e)}"
    
    def get_logs(self, project_name, service=None, tail=50):
        """Get logs for a project"""
        if not self.deployment_manager.project_exists(project_name):
            raise Exception(f"Project '{project_name}' not found")
        
        return self.deployment_manager.show_logs(project_name, follow=False, service=service)
    
    def follow_logs(self, project_name, service=None):
        """Follow logs for a project"""
        if not self.deployment_manager.project_exists(project_name):
            raise Exception(f"Project '{project_name}' not found")
        
        return self.deployment_manager.show_logs(project_name, follow=True, service=service)