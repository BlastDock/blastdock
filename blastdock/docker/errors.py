"""
Docker-specific error classes and handlers
"""

from typing import List, Optional, Dict, Any


class DockerError(Exception):
    """Base class for Docker-related errors"""
    
    def __init__(self, message: str, details: Optional[str] = None, 
                 suggestions: Optional[List[str]] = None):
        super().__init__(message)
        self.message = message
        self.details = details
        self.suggestions = suggestions or []


class DockerNotFoundError(DockerError):
    """Raised when Docker is not installed or not found"""
    
    def __init__(self, message: str = "Docker not found"):
        super().__init__(
            message,
            "Docker CLI or daemon is not available on this system",
            [
                "Install Docker Desktop or Docker Engine",
                "Check if Docker service is running",
                "Add Docker to your system PATH",
                "Verify Docker installation with 'docker --version'"
            ]
        )


class DockerNotRunningError(DockerError):
    """Raised when Docker daemon is not running"""
    
    def __init__(self, message: str = "Docker daemon not running"):
        super().__init__(
            message,
            "Docker daemon is not accessible or not started",
            [
                "Start Docker Desktop or Docker service",
                "Check Docker daemon status: 'sudo systemctl status docker'",
                "Restart Docker service: 'sudo systemctl restart docker'",
                "Verify Docker is running: 'docker info'"
            ]
        )


class DockerConnectionError(DockerError):
    """Raised when connection to Docker daemon fails"""
    
    def __init__(self, message: str = "Failed to connect to Docker daemon",
                 error_details: Optional[str] = None):
        super().__init__(
            message,
            error_details or "Unable to establish connection to Docker daemon",
            [
                "Check Docker daemon is running",
                "Verify user permissions for Docker socket",
                "Add user to docker group: 'sudo usermod -aG docker $USER'",
                "Check Docker socket permissions: 'ls -la /var/run/docker.sock'",
                "Try running with sudo if necessary"
            ]
        )


class DockerComposeError(DockerError):
    """Raised when Docker Compose operations fail"""
    
    def __init__(self, message: str, compose_file: Optional[str] = None,
                 service: Optional[str] = None, exit_code: Optional[int] = None):
        details = f"Docker Compose operation failed"
        if compose_file:
            details += f" for file: {compose_file}"
        if service:
            details += f", service: {service}"
        if exit_code:
            details += f", exit code: {exit_code}"
        
        suggestions = [
            "Check Docker Compose file syntax",
            "Verify all required images are available",
            "Check port conflicts and resource availability",
            "Review service dependencies and startup order"
        ]
        
        if service:
            suggestions.extend([
                f"Check {service} service configuration",
                f"Review {service} service logs for details"
            ])
        
        super().__init__(message, details, suggestions)
        self.compose_file = compose_file
        self.service = service
        self.exit_code = exit_code


class ContainerError(DockerError):
    """Raised when container operations fail"""
    
    def __init__(self, message: str, container_name: Optional[str] = None,
                 container_id: Optional[str] = None, exit_code: Optional[int] = None):
        details = "Container operation failed"
        if container_name:
            details += f" for container: {container_name}"
        elif container_id:
            details += f" for container ID: {container_id[:12]}"
        
        suggestions = [
            "Check container logs for error details",
            "Verify container configuration",
            "Check resource availability (CPU, memory, disk)",
            "Review port and volume mappings"
        ]
        
        if exit_code:
            details += f", exit code: {exit_code}"
            if exit_code == 125:
                suggestions.append("Container configuration error - check Dockerfile and run command")
            elif exit_code == 126:
                suggestions.append("Container command not executable - check command permissions")
            elif exit_code == 127:
                suggestions.append("Container command not found - check command path and availability")
        
        super().__init__(message, details, suggestions)
        self.container_name = container_name
        self.container_id = container_id
        self.exit_code = exit_code


class ImageError(DockerError):
    """Raised when image operations fail"""
    
    def __init__(self, message: str, image_name: Optional[str] = None,
                 registry: Optional[str] = None):
        details = "Docker image operation failed"
        if image_name:
            details += f" for image: {image_name}"
        if registry:
            details += f" from registry: {registry}"
        
        suggestions = [
            "Check image name and tag spelling",
            "Verify registry credentials and access",
            "Check network connectivity to registry",
            "Try pulling image manually: 'docker pull <image>'"
        ]
        
        if registry:
            suggestions.extend([
                f"Verify access to registry: {registry}",
                "Check registry authentication"
            ])
        
        super().__init__(message, details, suggestions)
        self.image_name = image_name
        self.registry = registry


class NetworkError(DockerError):
    """Raised when Docker network operations fail"""
    
    def __init__(self, message: str, network_name: Optional[str] = None):
        details = "Docker network operation failed"
        if network_name:
            details += f" for network: {network_name}"
        
        suggestions = [
            "Check network name and configuration",
            "Verify no IP address conflicts",
            "Check network driver compatibility",
            "List existing networks: 'docker network ls'"
        ]
        
        super().__init__(message, details, suggestions)
        self.network_name = network_name


class VolumeError(DockerError):
    """Raised when Docker volume operations fail"""
    
    def __init__(self, message: str, volume_name: Optional[str] = None,
                 mount_point: Optional[str] = None):
        details = "Docker volume operation failed"
        if volume_name:
            details += f" for volume: {volume_name}"
        if mount_point:
            details += f" at mount point: {mount_point}"
        
        suggestions = [
            "Check volume name and permissions",
            "Verify mount point exists and is accessible",
            "Check disk space availability",
            "Review volume driver configuration"
        ]
        
        super().__init__(message, details, suggestions)
        self.volume_name = volume_name
        self.mount_point = mount_point


def get_docker_error_suggestions(error: Exception) -> List[str]:
    """Get contextual suggestions for Docker errors"""
    error_str = str(error).lower()
    suggestions = []
    
    if "permission denied" in error_str:
        suggestions.extend([
            "Add user to docker group: 'sudo usermod -aG docker $USER'",
            "Restart your session after adding to docker group",
            "Check Docker socket permissions",
            "Try running with sudo if necessary"
        ])
    
    elif "connection refused" in error_str or "cannot connect" in error_str:
        suggestions.extend([
            "Start Docker daemon or Docker Desktop",
            "Check if Docker service is running",
            "Verify Docker socket is accessible"
        ])
    
    elif "no such file or directory" in error_str:
        suggestions.extend([
            "Install Docker if not already installed",
            "Check Docker installation path",
            "Verify Docker binary is in PATH"
        ])
    
    elif "port" in error_str and "already in use" in error_str:
        suggestions.extend([
            "Use different port mapping",
            "Stop service using the conflicting port",
            "Check port availability with 'netstat -tulpn'"
        ])
    
    elif "pull access denied" in error_str or "unauthorized" in error_str:
        suggestions.extend([
            "Check image name and tag",
            "Login to registry: 'docker login'",
            "Verify repository access permissions",
            "Check if image exists in registry"
        ])
    
    elif "network" in error_str:
        suggestions.extend([
            "Check network connectivity",
            "Verify DNS resolution",
            "Check firewall settings",
            "Try with different network driver"
        ])
    
    elif "out of space" in error_str or "no space left" in error_str:
        suggestions.extend([
            "Free up disk space",
            "Clean up Docker images: 'docker image prune'",
            "Remove unused volumes: 'docker volume prune'",
            "Remove unused containers: 'docker container prune'"
        ])
    
    return suggestions


def create_docker_error(error: Exception, operation: str = "Docker operation",
                       context: Optional[Dict[str, Any]] = None) -> DockerError:
    """Create appropriate Docker error based on the original exception"""
    error_str = str(error).lower()
    context = context or {}
    
    # Determine specific error type
    if "permission denied" in error_str:
        return DockerConnectionError(
            f"{operation} failed due to permission error",
            str(error)
        )
    
    elif "connection refused" in error_str or "cannot connect" in error_str:
        return DockerNotRunningError(f"{operation} failed - Docker daemon not accessible")
    
    elif "no such file or directory" in error_str and "docker" in error_str:
        return DockerNotFoundError(f"{operation} failed - Docker not found")
    
    elif "compose" in operation.lower():
        return DockerComposeError(
            f"{operation} failed",
            context.get('compose_file'),
            context.get('service'),
            getattr(error, 'returncode', None)
        )
    
    elif "container" in operation.lower():
        return ContainerError(
            f"{operation} failed",
            context.get('container_name'),
            context.get('container_id'),
            getattr(error, 'returncode', None)
        )
    
    elif "image" in operation.lower():
        return ImageError(
            f"{operation} failed",
            context.get('image_name'),
            context.get('registry')
        )
    
    elif "network" in operation.lower():
        return NetworkError(
            f"{operation} failed",
            context.get('network_name')
        )
    
    elif "volume" in operation.lower():
        return VolumeError(
            f"{operation} failed",
            context.get('volume_name'),
            context.get('mount_point')
        )
    
    else:
        # Generic Docker error
        suggestions = get_docker_error_suggestions(error)
        return DockerError(f"{operation} failed", str(error), suggestions)