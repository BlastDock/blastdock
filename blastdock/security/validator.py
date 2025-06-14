"""
Comprehensive security validator for BlastDock operations
"""

import re
import os
import subprocess
import ipaddress
import urllib.parse
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path

from ..utils.logging import get_logger
from ..exceptions import SecurityError, ValidationError


logger = get_logger(__name__)


class SecurityValidator:
    """Comprehensive security validation for all BlastDock inputs and operations"""
    
    def __init__(self):
        """Initialize security validator"""
        self.logger = get_logger(__name__)
        
        # Security patterns
        self.DANGEROUS_PATTERNS = [
            r'[\;\|\&\$\`]',  # Shell injection
            r'\.\./',  # Path traversal
            r'<script',  # XSS
            r'javascript:',  # JavaScript injection
            r'data:',  # Data URIs
            r'eval\(',  # Code execution
            r'exec\(',  # Code execution
            r'system\(',  # System calls
            r'subprocess\.',  # Subprocess calls
            r'__import__',  # Dynamic imports
        ]
        
        # Allowed characters for different input types
        self.PROJECT_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
        self.DOMAIN_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9.-]+$')
        self.TEMPLATE_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
        
        # File extension allowlists
        self.ALLOWED_CONFIG_EXTENSIONS = {'.yml', '.yaml', '.json', '.toml', '.ini'}
        self.ALLOWED_TEMPLATE_EXTENSIONS = {'.yml', '.yaml', '.json', '.jinja', '.j2'}
        self.DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.cmd', '.sh', '.ps1', '.scr', '.com'}
    
    def validate_project_name(self, project_name: str) -> Tuple[bool, Optional[str]]:
        """Validate project name for security"""
        if not project_name:
            return False, "Project name cannot be empty"
        
        if len(project_name) > 64:
            return False, "Project name too long (max 64 characters)"
        
        if not self.PROJECT_NAME_PATTERN.match(project_name):
            return False, "Project name contains invalid characters (only a-z, A-Z, 0-9, _, - allowed)"
        
        # Check for reserved names
        reserved_names = {
            'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5',
            'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4',
            'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9', 'root', 'admin', 'system'
        }
        
        if project_name.lower() in reserved_names:
            return False, f"'{project_name}' is a reserved name"
        
        return True, None
    
    def validate_template_name(self, template_name: str) -> Tuple[bool, Optional[str]]:
        """Validate template name for security"""
        if not template_name:
            return False, "Template name cannot be empty"
        
        if len(template_name) > 64:
            return False, "Template name too long (max 64 characters)"
        
        if not self.TEMPLATE_NAME_PATTERN.match(template_name):
            return False, "Template name contains invalid characters"
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, template_name, re.IGNORECASE):
                return False, f"Template name contains potentially dangerous pattern: {pattern}"
        
        return True, None
    
    def validate_domain_name(self, domain: str) -> Tuple[bool, Optional[str]]:
        """Validate domain name for security"""
        if not domain:
            return False, "Domain cannot be empty"
        
        if len(domain) > 253:
            return False, "Domain name too long (max 253 characters)"
        
        if not self.DOMAIN_NAME_PATTERN.match(domain):
            return False, "Domain contains invalid characters"
        
        # Check for localhost/private domains
        if domain.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
            return False, "Cannot use localhost or loopback addresses"
        
        # Basic domain format validation
        parts = domain.split('.')
        if len(parts) < 2:
            return False, "Domain must have at least one dot"
        
        for part in parts:
            if not part or len(part) > 63:
                return False, "Invalid domain part length"
            if part.startswith('-') or part.endswith('-'):
                return False, "Domain parts cannot start or end with hyphen"
        
        return True, None
    
    def validate_port_number(self, port: Union[int, str]) -> Tuple[bool, Optional[str]]:
        """Validate port number for security"""
        try:
            port_int = int(port)
        except (ValueError, TypeError):
            return False, "Port must be a valid integer"
        
        if port_int < 1 or port_int > 65535:
            return False, "Port must be between 1 and 65535"
        
        # Check for privileged ports
        if port_int < 1024:
            return False, "Cannot use privileged ports (< 1024)"
        
        # Check for commonly reserved ports
        reserved_ports = {22, 25, 53, 80, 110, 143, 443, 993, 995}
        if port_int in reserved_ports:
            return False, f"Port {port_int} is reserved for system services"
        
        return True, None
    
    def validate_file_path(self, file_path: str, base_dir: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Validate file path for security (prevent path traversal)"""
        if not file_path:
            return False, "File path cannot be empty"
        
        # Normalize path
        try:
            normalized_path = os.path.normpath(file_path)
        except Exception:
            return False, "Invalid file path format"
        
        # Check for path traversal
        if '..' in normalized_path:
            return False, "Path traversal detected"
        
        if normalized_path.startswith('/'):
            return False, "Absolute paths not allowed"
        
        # Check against base directory if provided
        if base_dir:
            try:
                full_path = os.path.join(base_dir, normalized_path)
                resolved_path = os.path.realpath(full_path)
                base_resolved = os.path.realpath(base_dir)
                
                if not resolved_path.startswith(base_resolved):
                    return False, "Path escapes base directory"
            except Exception:
                return False, "Path validation failed"
        
        # Check file extension
        file_ext = Path(file_path).suffix.lower()
        if file_ext in self.DANGEROUS_EXTENSIONS:
            return False, f"Dangerous file extension: {file_ext}"
        
        return True, None
    
    def validate_docker_image_name(self, image_name: str) -> Tuple[bool, Optional[str]]:
        """Validate Docker image name for security"""
        if not image_name:
            return False, "Image name cannot be empty"
        
        if len(image_name) > 256:
            return False, "Image name too long"
        
        # Docker image name pattern
        image_pattern = re.compile(r'^[a-z0-9._/-]+(?::[a-zA-Z0-9._-]+)?$')
        if not image_pattern.match(image_name):
            return False, "Invalid Docker image name format"
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, image_name, re.IGNORECASE):
                return False, f"Image name contains dangerous pattern: {pattern}"
        
        # Prevent pulling from untrusted registries
        if image_name.startswith('docker.io/') and 'library/' not in image_name:
            # Allow official images but warn about user images
            pass
        
        return True, None
    
    def validate_environment_variable(self, name: str, value: str) -> Tuple[bool, Optional[str]]:
        """Validate environment variable for security"""
        if not name:
            return False, "Environment variable name cannot be empty"
        
        # Environment variable name pattern
        env_name_pattern = re.compile(r'^[A-Z_][A-Z0-9_]*$')
        if not env_name_pattern.match(name):
            return False, "Invalid environment variable name format"
        
        # Check for dangerous variable names
        dangerous_env_vars = {
            'PATH', 'LD_LIBRARY_PATH', 'LD_PRELOAD', 'HOME', 'USER', 'SHELL',
            'PS1', 'IFS', 'BASH_ENV', 'ENV', 'CDPATH'
        }
        
        if name in dangerous_env_vars:
            return False, f"Cannot override system environment variable: {name}"
        
        # Validate value
        if len(value) > 4096:
            return False, "Environment variable value too long"
        
        # Check for dangerous patterns in value
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return False, f"Environment variable value contains dangerous pattern: {pattern}"
        
        return True, None
    
    def validate_yaml_content(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate YAML content for security issues"""
        try:
            import yaml
        except ImportError:
            return False, "PyYAML not available for validation"
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"YAML content contains dangerous pattern: {pattern}"
        
        # Check for YAML bomb patterns
        yaml_bomb_patterns = [
            r'&\w+\s+\[\*\w+',  # YAML bomb reference
            r'\*\w+\s*,\s*\*\w+',  # Multiple references
        ]
        
        for pattern in yaml_bomb_patterns:
            if re.search(pattern, content):
                return False, "Potential YAML bomb detected"
        
        # Try to parse safely
        try:
            yaml.safe_load(content)
        except yaml.YAMLError as e:
            return False, f"Invalid YAML syntax: {e}"
        
        return True, None
    
    def validate_docker_compose_content(self, content: str) -> Tuple[bool, Optional[str]]:
        """Validate Docker Compose content for security"""
        # First validate as YAML
        is_valid, error = self.validate_yaml_content(content)
        if not is_valid:
            return is_valid, error
        
        # Check for dangerous Docker Compose configurations
        dangerous_configs = [
            r'privileged:\s*true',  # Privileged containers
            r'user:\s*["\']?root["\']?',  # Root user
            r'--privileged',  # Privileged flag
            r'host_pid:\s*true',  # Host PID namespace
            r'host_network:\s*true',  # Host network
            r'host_ipc:\s*true',  # Host IPC
            r'/var/run/docker\.sock',  # Docker socket access
            r'/dev/',  # Device access
            r'/proc/',  # Proc filesystem access
            r'/sys/',  # Sys filesystem access
        ]
        
        for pattern in dangerous_configs:
            if re.search(pattern, content, re.IGNORECASE):
                return False, f"Dangerous Docker configuration detected: {pattern}"
        
        return True, None
    
    def validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL for security"""
        if not url:
            return False, "URL cannot be empty"
        
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            return False, "Invalid URL format"
        
        # Check scheme
        allowed_schemes = {'http', 'https'}
        if parsed.scheme.lower() not in allowed_schemes:
            return False, f"URL scheme '{parsed.scheme}' not allowed"
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False, f"URL contains dangerous pattern: {pattern}"
        
        # Check for local/private addresses
        if parsed.hostname:
            try:
                ip = ipaddress.ip_address(parsed.hostname)
                if ip.is_private or ip.is_loopback:
                    return False, "Private/loopback IP addresses not allowed"
            except ValueError:
                # Not an IP address, check hostname
                if parsed.hostname.lower() in ['localhost', '127.0.0.1', '0.0.0.0']:
                    return False, "Localhost URLs not allowed"
        
        return True, None
    
    def validate_command(self, command: Union[str, List[str]]) -> Tuple[bool, Optional[str]]:
        """Validate command for security"""
        if isinstance(command, list):
            command_str = ' '.join(command)
        else:
            command_str = command
        
        if not command_str:
            return False, "Command cannot be empty"
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command_str, re.IGNORECASE):
                return False, f"Command contains dangerous pattern: {pattern}"
        
        # Check for dangerous commands
        dangerous_commands = {
            'rm', 'rmdir', 'del', 'format', 'fdisk', 'mkfs', 'dd',
            'sudo', 'su', 'chmod', 'chown', 'passwd', 'useradd',
            'curl', 'wget', 'nc', 'netcat', 'telnet', 'ssh'
        }
        
        # Extract first word (command name)
        first_word = command_str.split()[0] if command_str else ''
        if first_word.lower() in dangerous_commands:
            return False, f"Dangerous command detected: {first_word}"
        
        return True, None
    
    def sanitize_input(self, input_str: str) -> str:
        """Sanitize input string by removing dangerous characters"""
        if not input_str:
            return ""
        
        # Remove null bytes
        sanitized = input_str.replace('\x00', '')
        
        # Remove control characters except newline and tab
        sanitized = ''.join(char for char in sanitized 
                          if ord(char) >= 32 or char in '\n\t')
        
        # Limit length
        max_length = 4096
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    def check_file_permissions(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if file has secure permissions"""
        try:
            stat_info = os.stat(file_path)
            mode = stat_info.st_mode
            
            # Check if file is world-writable
            if mode & 0o002:
                return False, "File is world-writable"
            
            # Check if file is group-writable (optional warning)
            if mode & 0o020:
                self.logger.warning(f"File {file_path} is group-writable")
            
            return True, None
            
        except (OSError, IOError) as e:
            return False, f"Cannot check file permissions: {e}"
    
    def validate_network_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate network configuration for security"""
        if not isinstance(config, dict):
            return False, "Network configuration must be a dictionary"
        
        # Check for dangerous network configurations
        if config.get('host_networking'):
            return False, "Host networking not allowed"
        
        if config.get('privileged_ports'):
            return False, "Privileged ports not allowed"
        
        # Validate port mappings
        ports = config.get('ports', [])
        for port_mapping in ports:
            if isinstance(port_mapping, str):
                # Parse port mapping like "8080:80"
                if ':' in port_mapping:
                    host_port, container_port = port_mapping.split(':', 1)
                    is_valid, error = self.validate_port_number(host_port)
                    if not is_valid:
                        return False, f"Invalid host port: {error}"
        
        return True, None
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        return {
            'validator_version': '1.0.0',
            'security_features': [
                'Input sanitization',
                'Path traversal prevention', 
                'Docker security validation',
                'YAML bomb detection',
                'Command injection prevention',
                'File permission validation',
                'Network security checks'
            ],
            'dangerous_patterns_count': len(self.DANGEROUS_PATTERNS),
            'allowed_extensions': list(self.ALLOWED_CONFIG_EXTENSIONS),
            'blocked_extensions': list(self.DANGEROUS_EXTENSIONS)
        }


# Global validator instance
_security_validator = None


def get_security_validator() -> SecurityValidator:
    """Get global security validator instance"""
    global _security_validator
    if _security_validator is None:
        _security_validator = SecurityValidator()
    return _security_validator