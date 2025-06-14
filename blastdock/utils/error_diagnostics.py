"""
Advanced error diagnostics and recovery system for BlastDock
"""

import os
import sys
import traceback
import time
import json
import platform
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from ..exceptions import BlastDockError, get_error_severity, ErrorSeverity
from ..constants import ERROR_MESSAGES
from .logging import get_logger


logger = get_logger(__name__)


@dataclass
class ErrorContext:
    """Comprehensive error context information"""
    timestamp: datetime
    error_id: str
    error_type: str
    error_message: str
    severity: str
    
    # System context
    system_info: Dict[str, str]
    python_version: str
    blastdock_version: str
    working_directory: str
    
    # Error details
    traceback_info: List[str]
    stack_trace: str
    error_code: Optional[str] = None
    
    # Operational context
    command: Optional[str] = None
    project_name: Optional[str] = None
    template_name: Optional[str] = None
    operation: Optional[str] = None
    
    # Environment context
    docker_status: Optional[Dict[str, Any]] = None
    traefik_status: Optional[Dict[str, Any]] = None
    disk_space: Optional[Dict[str, str]] = None
    network_status: Optional[Dict[str, Any]] = None
    
    # Recovery information
    suggested_solutions: List[str] = None
    documentation_links: List[str] = None
    troubleshooting_steps: List[str] = None
    recovery_commands: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime to ISO format
        data['timestamp'] = self.timestamp.isoformat()
        return data


class ErrorDiagnostics:
    """Advanced error diagnostics and recovery system"""
    
    def __init__(self):
        """Initialize diagnostics system"""
        self.logger = get_logger(__name__)
        self.error_history: List[ErrorContext] = []
        self.recovery_strategies = self._load_recovery_strategies()
        self.diagnostic_checks = self._load_diagnostic_checks()
    
    def diagnose_error(self, 
                      exception: Exception,
                      operation_context: Dict[str, Any] = None) -> ErrorContext:
        """Perform comprehensive error diagnosis"""
        
        # Generate unique error ID
        error_id = self._generate_error_id(exception)
        
        # Gather system context
        system_info = self._gather_system_info()
        
        # Extract error information
        error_type = type(exception).__name__
        error_message = str(exception)
        severity = get_error_severity(exception)
        
        # Get traceback information
        traceback_info = traceback.format_exception(type(exception), exception, exception.__traceback__)
        stack_trace = ''.join(traceback_info)
        
        # Get error code if available
        error_code = getattr(exception, 'error_code', None)
        
        # Extract operational context
        operation_context = operation_context or {}
        command = operation_context.get('command')
        project_name = operation_context.get('project_name')
        template_name = operation_context.get('template_name')
        operation = operation_context.get('operation')
        
        # Gather environment context
        docker_status = self._check_docker_status()
        traefik_status = self._check_traefik_status()
        disk_space = self._check_disk_space()
        network_status = self._check_network_status()
        
        # Generate recovery suggestions
        suggested_solutions = self._generate_solutions(exception, operation_context)
        documentation_links = self._get_documentation_links(exception)
        troubleshooting_steps = self._get_troubleshooting_steps(exception)
        recovery_commands = self._get_recovery_commands(exception, operation_context)
        
        # Create error context
        error_context = ErrorContext(
            timestamp=datetime.now(),
            error_id=error_id,
            error_type=error_type,
            error_message=error_message,
            severity=severity,
            system_info=system_info,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            blastdock_version=self._get_blastdock_version(),
            working_directory=os.getcwd(),
            traceback_info=traceback_info,
            stack_trace=stack_trace,
            error_code=error_code,
            command=command,
            project_name=project_name,
            template_name=template_name,
            operation=operation,
            docker_status=docker_status,
            traefik_status=traefik_status,
            disk_space=disk_space,
            network_status=network_status,
            suggested_solutions=suggested_solutions,
            documentation_links=documentation_links,
            troubleshooting_steps=troubleshooting_steps,
            recovery_commands=recovery_commands
        )
        
        # Store in error history
        self.error_history.append(error_context)
        
        # Log error with context
        self._log_error_context(error_context)
        
        return error_context
    
    def _generate_error_id(self, exception: Exception) -> str:
        """Generate unique error ID"""
        timestamp = int(time.time())
        error_type = type(exception).__name__
        return f"BD-{error_type}-{timestamp}"
    
    def _gather_system_info(self) -> Dict[str, str]:
        """Gather comprehensive system information"""
        try:
            return {
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'architecture': platform.architecture()[0],
                'hostname': platform.node(),
                'user': os.getenv('USER', os.getenv('USERNAME', 'unknown')),
                'shell': os.getenv('SHELL', 'unknown'),
                'home': os.getenv('HOME', os.getenv('USERPROFILE', 'unknown')),
                'path_separator': os.pathsep,
                'line_separator': repr(os.linesep)
            }
        except Exception as e:
            self.logger.warning(f"Failed to gather system info: {e}")
            return {'error': str(e)}
    
    def _get_blastdock_version(self) -> str:
        """Get BlastDock version"""
        try:
            from .._version import __version__
            return __version__
        except ImportError:
            return "unknown"
    
    def _check_docker_status(self) -> Dict[str, Any]:
        """Check Docker daemon status"""
        try:
            from ..utils.docker_utils import DockerClient
            
            docker_client = DockerClient()
            
            return {
                'available': docker_client.is_running(),
                'version': docker_client.get_version(),
                'containers_running': len(docker_client.list_containers(all=False)),
                'containers_total': len(docker_client.list_containers(all=True)),
                'images_count': len(docker_client.list_images()),
                'networks_count': len(docker_client.list_networks()),
                'volumes_count': len(docker_client.list_volumes())
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e)
            }
    
    def _check_traefik_status(self) -> Dict[str, Any]:
        """Check Traefik status"""
        try:
            from ..traefik.manager import TraefikManager
            
            traefik_manager = TraefikManager()
            
            return {
                'installed': traefik_manager.is_installed(),
                'running': traefik_manager.is_running(),
                'dashboard_accessible': traefik_manager.is_dashboard_accessible(),
                'network_exists': traefik_manager.network_exists(),
                'container_id': traefik_manager.get_container_id(),
                'services_count': traefik_manager.get_services_count()
            }
        except Exception as e:
            return {
                'installed': False,
                'running': False,
                'error': str(e)
            }
    
    def _check_disk_space(self) -> Dict[str, str]:
        """Check disk space information"""
        try:
            import shutil
            
            # Check current directory
            cwd_usage = shutil.disk_usage('.')
            
            # Check home directory if different
            home_dir = os.path.expanduser('~')
            home_usage = shutil.disk_usage(home_dir) if home_dir != '.' else cwd_usage
            
            def format_bytes(bytes_value):
                """Format bytes to human readable format"""
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if bytes_value < 1024.0:
                        return f"{bytes_value:.1f}{unit}"
                    bytes_value /= 1024.0
                return f"{bytes_value:.1f}PB"
            
            return {
                'current_dir_total': format_bytes(cwd_usage.total),
                'current_dir_used': format_bytes(cwd_usage.used),
                'current_dir_free': format_bytes(cwd_usage.free),
                'home_dir_total': format_bytes(home_usage.total),
                'home_dir_used': format_bytes(home_usage.used),
                'home_dir_free': format_bytes(home_usage.free),
                'current_dir_percent_used': f"{(cwd_usage.used / cwd_usage.total) * 100:.1f}%",
                'home_dir_percent_used': f"{(home_usage.used / home_usage.total) * 100:.1f}%"
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _check_network_status(self) -> Dict[str, Any]:
        """Check network connectivity"""
        try:
            import socket
            import urllib.request
            
            def check_connectivity(host, port, timeout=5):
                try:
                    socket.create_connection((host, port), timeout)
                    return True
                except (socket.timeout, socket.error):
                    return False
            
            def check_http(url, timeout=5):
                try:
                    urllib.request.urlopen(url, timeout=timeout)
                    return True
                except:
                    return False
            
            return {
                'dns_resolution': check_connectivity('8.8.8.8', 53),
                'internet_http': check_http('http://google.com'),
                'internet_https': check_http('https://google.com'),
                'docker_hub': check_http('https://hub.docker.com'),
                'github': check_http('https://github.com'),
                'local_docker': check_connectivity('localhost', 2375) or check_connectivity('localhost', 2376)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_solutions(self, exception: Exception, context: Dict[str, Any]) -> List[str]:
        """Generate context-aware solution suggestions"""
        solutions = []
        
        # Get solutions from recovery strategies
        error_type = type(exception).__name__
        if error_type in self.recovery_strategies:
            solutions.extend(self.recovery_strategies[error_type].get('solutions', []))
        
        # Context-specific solutions
        if isinstance(exception, Exception):
            # Docker-related solutions
            if 'docker' in str(exception).lower():
                solutions.extend([
                    "Ensure Docker Desktop is running",
                    "Check Docker daemon status: sudo systemctl status docker",
                    "Restart Docker daemon: sudo systemctl restart docker",
                    "Verify Docker installation: docker --version"
                ])
            
            # Permission-related solutions
            if 'permission' in str(exception).lower():
                solutions.extend([
                    "Check file/directory permissions",
                    "Run with appropriate user privileges",
                    "Add user to docker group: sudo usermod -aG docker $USER"
                ])
            
            # Network-related solutions
            if 'network' in str(exception).lower() or 'connection' in str(exception).lower():
                solutions.extend([
                    "Check network connectivity",
                    "Verify DNS resolution",
                    "Check firewall settings",
                    "Restart network services"
                ])
            
            # Port-related solutions
            if 'port' in str(exception).lower():
                solutions.extend([
                    "Check if port is already in use: netstat -tuln | grep <port>",
                    "Stop conflicting services",
                    "Use different port number",
                    "Release allocated ports: blastdock ports list"
                ])
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(solutions))
    
    def _get_documentation_links(self, exception: Exception) -> List[str]:
        """Get relevant documentation links"""
        base_docs = "https://docs.blastdock.com"
        
        links = [f"{base_docs}/troubleshooting"]
        
        error_type = type(exception).__name__
        
        # Specific documentation based on error type
        if 'Docker' in error_type:
            links.append(f"{base_docs}/installation/docker")
        elif 'Traefik' in error_type:
            links.append(f"{base_docs}/features/traefik")
        elif 'Template' in error_type:
            links.append(f"{base_docs}/templates")
        elif 'Domain' in error_type:
            links.append(f"{base_docs}/features/domains")
        elif 'SSL' in error_type:
            links.append(f"{base_docs}/features/ssl")
        elif 'Port' in error_type:
            links.append(f"{base_docs}/features/ports")
        elif 'Migration' in error_type:
            links.append(f"{base_docs}/features/migration")
        
        return links
    
    def _get_troubleshooting_steps(self, exception: Exception) -> List[str]:
        """Get step-by-step troubleshooting guide"""
        steps = [
            "1. Check the error message for specific details",
            "2. Verify system requirements are met",
            "3. Check BlastDock logs for additional context"
        ]
        
        error_type = type(exception).__name__
        
        if 'Docker' in error_type:
            steps.extend([
                "4. Verify Docker is installed and running",
                "5. Check Docker daemon permissions",
                "6. Test basic Docker commands: docker ps"
            ])
        elif 'Traefik' in error_type:
            steps.extend([
                "4. Check Traefik installation status",
                "5. Verify Traefik configuration",
                "6. Check Traefik container logs"
            ])
        elif 'Template' in error_type:
            steps.extend([
                "4. Verify template exists and is valid",
                "5. Check template syntax and structure",
                "6. Validate template fields and values"
            ])
        
        steps.append("7. If issue persists, report to BlastDock support")
        
        return steps
    
    def _get_recovery_commands(self, exception: Exception, context: Dict[str, Any]) -> List[str]:
        """Get specific recovery commands"""
        commands = []
        
        error_type = type(exception).__name__
        
        if 'Docker' in error_type:
            commands.extend([
                "docker --version",
                "docker info",
                "sudo systemctl status docker"
            ])
        elif 'Traefik' in error_type:
            commands.extend([
                "blastdock traefik status",
                "blastdock traefik logs",
                "docker logs blastdock-traefik"
            ])
        elif 'Template' in error_type:
            commands.extend([
                "blastdock templates list",
                "blastdock templates validate"
            ])
        elif 'Port' in error_type:
            commands.extend([
                "blastdock ports list",
                "blastdock ports conflicts",
                "netstat -tuln"
            ])
        elif 'Domain' in error_type:
            commands.extend([
                "blastdock domain list",
                "nslookup <domain>",
                "dig <domain>"
            ])
        
        return commands
    
    def _load_recovery_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Load recovery strategies for different error types"""
        return {
            'DockerNotAvailableError': {
                'solutions': [
                    "Start Docker Desktop application",
                    "Install Docker if not installed",
                    "Check Docker daemon service status",
                    "Verify Docker installation path"
                ],
                'quick_fixes': [
                    "sudo systemctl start docker",
                    "docker --version"
                ]
            },
            'TraefikNotInstalledError': {
                'solutions': [
                    "Install Traefik using: blastdock traefik install",
                    "Provide email and domain for Let's Encrypt",
                    "Ensure Docker is running before installation"
                ],
                'quick_fixes': [
                    "blastdock traefik install --email user@example.com --domain example.com"
                ]
            },
            'TemplateNotFoundError': {
                'solutions': [
                    "Check available templates: blastdock templates list",
                    "Verify template name spelling",
                    "Update template cache if needed"
                ],
                'quick_fixes': [
                    "blastdock templates list"
                ]
            },
            'PortConflictError': {
                'solutions': [
                    "Check port usage: blastdock ports list",
                    "Stop conflicting services",
                    "Use different port number",
                    "Release unused port allocations"
                ],
                'quick_fixes': [
                    "blastdock ports conflicts",
                    "netstat -tuln | grep <port>"
                ]
            }
        }
    
    def _load_diagnostic_checks(self) -> Dict[str, callable]:
        """Load diagnostic check functions"""
        return {
            'docker_available': self._check_docker_available,
            'disk_space_sufficient': self._check_disk_space_sufficient,
            'network_connectivity': self._check_network_connectivity,
            'permissions_valid': self._check_permissions_valid,
            'traefik_healthy': self._check_traefik_healthy
        }
    
    def _check_docker_available(self) -> Tuple[bool, str]:
        """Check if Docker is available and running"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, "Docker is available"
            else:
                return False, "Docker command failed"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Docker not found or not responsive"
    
    def _check_disk_space_sufficient(self, min_free_gb: float = 1.0) -> Tuple[bool, str]:
        """Check if sufficient disk space is available"""
        try:
            import shutil
            free_bytes = shutil.disk_usage('.').free
            free_gb = free_bytes / (1024**3)
            
            if free_gb >= min_free_gb:
                return True, f"{free_gb:.1f}GB free space available"
            else:
                return False, f"Only {free_gb:.1f}GB free space (minimum {min_free_gb}GB required)"
        except Exception as e:
            return False, f"Could not check disk space: {e}"
    
    def _check_network_connectivity(self) -> Tuple[bool, str]:
        """Check network connectivity"""
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True, "Network connectivity available"
        except socket.error:
            return False, "No network connectivity"
    
    def _check_permissions_valid(self) -> Tuple[bool, str]:
        """Check if current user has necessary permissions"""
        try:
            # Check if current directory is writable
            test_file = '.blastdock_perm_test'
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return True, "Permissions are valid"
        except (PermissionError, OSError) as e:
            return False, f"Permission error: {e}"
    
    def _check_traefik_healthy(self) -> Tuple[bool, str]:
        """Check if Traefik is healthy"""
        try:
            from ..traefik.manager import TraefikManager
            manager = TraefikManager()
            
            if not manager.is_installed():
                return False, "Traefik not installed"
            elif not manager.is_running():
                return False, "Traefik not running"
            elif not manager.is_healthy():
                return False, "Traefik unhealthy"
            else:
                return True, "Traefik is healthy"
        except Exception as e:
            return False, f"Traefik check failed: {e}"
    
    def _log_error_context(self, error_context: ErrorContext):
        """Log error context for debugging"""
        self.logger.error(f"Error {error_context.error_id}: {error_context.error_message}")
        self.logger.debug(f"Error context: {error_context.to_dict()}")
    
    def run_diagnostics(self) -> Dict[str, Any]:
        """Run comprehensive system diagnostics"""
        results = {}
        
        for check_name, check_func in self.diagnostic_checks.items():
            try:
                success, message = check_func()
                results[check_name] = {
                    'status': 'pass' if success else 'fail',
                    'message': message
                }
            except Exception as e:
                results[check_name] = {
                    'status': 'error',
                    'message': str(e)
                }
        
        return results
    
    def get_error_history(self, limit: int = 50) -> List[ErrorContext]:
        """Get recent error history"""
        return self.error_history[-limit:]
    
    def export_error_report(self, error_context: ErrorContext, file_path: str):
        """Export detailed error report to file"""
        try:
            report_data = {
                'report_type': 'BlastDock Error Report',
                'generated_at': datetime.now().isoformat(),
                'error_context': error_context.to_dict(),
                'system_diagnostics': self.run_diagnostics()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Error report exported to: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to export error report: {e}")
    
    def suggest_recovery_actions(self, error_context: ErrorContext) -> Dict[str, List[str]]:
        """Suggest specific recovery actions based on error context"""
        actions = {
            'immediate': [],
            'short_term': [],
            'preventive': []
        }
        
        # Immediate actions based on severity
        if error_context.severity == ErrorSeverity.CRITICAL:
            actions['immediate'].extend([
                "Stop current operation immediately",
                "Check system resources and availability",
                "Backup any unsaved work"
            ])
        
        # Add error-specific actions
        if error_context.suggested_solutions:
            actions['immediate'].extend(error_context.suggested_solutions[:3])
            actions['short_term'].extend(error_context.suggested_solutions[3:])
        
        # Preventive actions
        actions['preventive'].extend([
            "Regular system maintenance and updates",
            "Monitor resource usage",
            "Keep BlastDock updated to latest version",
            "Backup configurations regularly"
        ])
        
        return actions


# Global diagnostics instance
_diagnostics_instance = None


def get_diagnostics() -> ErrorDiagnostics:
    """Get global diagnostics instance"""
    global _diagnostics_instance
    if _diagnostics_instance is None:
        _diagnostics_instance = ErrorDiagnostics()
    return _diagnostics_instance


def diagnose_and_handle_error(exception: Exception, 
                             operation_context: Dict[str, Any] = None,
                             auto_report: bool = False) -> ErrorContext:
    """Diagnose error and optionally generate report"""
    diagnostics = get_diagnostics()
    error_context = diagnostics.diagnose_error(exception, operation_context)
    
    if auto_report:
        # Generate error report file
        report_file = f"blastdock_error_report_{error_context.error_id}.json"
        diagnostics.export_error_report(error_context, report_file)
    
    return error_context