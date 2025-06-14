"""
Advanced health checking system for containers and services
"""

import time
import threading
import requests
import socket
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import json

from ..utils.logging import get_logger
from ..utils.docker_utils import DockerClient

logger = get_logger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ServiceHealthConfig:
    """Health check configuration for a service"""
    service_name: str
    check_type: str  # 'http', 'tcp', 'exec', 'docker'
    endpoint: Optional[str] = None
    port: Optional[int] = None
    timeout: float = 10.0
    interval: float = 30.0
    retries: int = 3
    expected_status: int = 200
    expected_content: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    command: Optional[List[str]] = None


class HealthChecker:
    """Advanced health checking system"""
    
    def __init__(self):
        """Initialize health checker"""
        self.logger = get_logger(__name__)
        self.docker_client = DockerClient()
        
        # Health check history
        self._health_history: Dict[str, List[HealthCheckResult]] = {}
        self._max_history = 100
        
        # Service configurations
        self._service_configs: Dict[str, ServiceHealthConfig] = {}
        
        # Background monitoring
        self._monitoring_active = False
        self._monitoring_thread = None
        self._monitoring_interval = 30.0
        
        # Health check statistics
        self.stats = {
            'total_checks': 0,
            'successful_checks': 0,
            'failed_checks': 0,
            'average_response_time': 0,
            'uptime_percentage': 0
        }
        
        self.logger.debug("Health checker initialized")
    
    def register_service_health_config(self, project_name: str, service_name: str, 
                                     config: ServiceHealthConfig):
        """Register health check configuration for a service"""
        key = f"{project_name}:{service_name}"
        self._service_configs[key] = config
        self.logger.info(f"Registered health config for {key}")
    
    def check_project_health(self, project_name: str) -> Dict[str, Any]:
        """Perform comprehensive health check on a project"""
        start_time = time.time()
        
        try:
            # Get container information
            containers = self.docker_client.get_container_status(project_name)
            if not containers:
                return {
                    'overall_status': HealthStatus.UNHEALTHY,
                    'message': 'No containers found',
                    'services': {},
                    'duration_ms': (time.time() - start_time) * 1000
                }
            
            service_results = {}
            overall_healthy = True
            messages = []
            
            for container in containers:
                service_name = container['name'].replace(f"{project_name}_", "").replace(f"{project_name}-", "")
                service_key = f"{project_name}:{service_name}"
                
                # Check container health
                container_result = self._check_container_health(container)
                
                # Check service-specific health if configured
                if service_key in self._service_configs:
                    config = self._service_configs[service_key]
                    service_result = self._check_service_health(config, container)
                    
                    # Combine results
                    if service_result.status != HealthStatus.HEALTHY:
                        container_result = service_result
                
                service_results[service_name] = {
                    'status': container_result.status.value,
                    'message': container_result.message,
                    'response_time_ms': container_result.response_time_ms,
                    'details': container_result.details,
                    'suggestions': container_result.suggestions,
                    'container_info': {
                        'name': container['name'],
                        'image': container['image'],
                        'status': container['status'],
                        'ports': container.get('ports', {})
                    }
                }
                
                if container_result.status != HealthStatus.HEALTHY:
                    overall_healthy = False
                    messages.append(f"{service_name}: {container_result.message}")
                
                # Store in history
                self._store_health_result(service_key, container_result)
            
            # Determine overall status
            if overall_healthy:
                overall_status = HealthStatus.HEALTHY
                overall_message = "All services healthy"
            else:
                # Check if any services are running
                running_services = sum(1 for r in service_results.values() 
                                     if r['status'] == HealthStatus.HEALTHY.value)
                if running_services > 0:
                    overall_status = HealthStatus.DEGRADED
                    overall_message = f"Degraded: {'; '.join(messages)}"
                else:
                    overall_status = HealthStatus.UNHEALTHY
                    overall_message = f"Unhealthy: {'; '.join(messages)}"
            
            # Update statistics
            self.stats['total_checks'] += 1
            if overall_healthy:
                self.stats['successful_checks'] += 1
            else:
                self.stats['failed_checks'] += 1
            
            return {
                'overall_status': overall_status.value,
                'message': overall_message,
                'services': service_results,
                'duration_ms': (time.time() - start_time) * 1000,
                'timestamp': time.time(),
                'project_name': project_name
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed for {project_name}: {e}")
            return {
                'overall_status': HealthStatus.UNKNOWN.value,
                'message': f"Health check error: {str(e)}",
                'services': {},
                'duration_ms': (time.time() - start_time) * 1000,
                'timestamp': time.time(),
                'project_name': project_name
            }
    
    def _check_container_health(self, container_info: Dict[str, Any]) -> HealthCheckResult:
        """Check basic container health"""
        start_time = time.time()
        
        try:
            container_status = container_info['status']
            container_name = container_info['name']
            
            if container_status == 'running':
                # Check if container has been running long enough to be stable
                if 'started_at' in container_info:
                    started_at = container_info['started_at']
                    uptime = time.time() - started_at
                    
                    if uptime < 30:  # Less than 30 seconds
                        return HealthCheckResult(
                            status=HealthStatus.DEGRADED,
                            message="Container recently started, stabilizing",
                            response_time_ms=(time.time() - start_time) * 1000,
                            timestamp=time.time(),
                            details={'uptime_seconds': uptime, 'container_status': container_status}
                        )
                
                # Check container resource usage if available
                try:
                    stats = self.docker_client.get_container_stats(container_name)
                    if stats:
                        cpu_percent = stats.get('cpu_percent', 0)
                        memory_percent = stats.get('memory_percent', 0)
                        
                        details = {
                            'cpu_percent': cpu_percent,
                            'memory_percent': memory_percent,
                            'container_status': container_status
                        }
                        
                        suggestions = []
                        if cpu_percent > 90:
                            suggestions.append("High CPU usage detected - consider scaling")
                        if memory_percent > 90:
                            suggestions.append("High memory usage detected - check for memory leaks")
                        
                        if cpu_percent > 95 or memory_percent > 95:
                            return HealthCheckResult(
                                status=HealthStatus.DEGRADED,
                                message="High resource usage",
                                response_time_ms=(time.time() - start_time) * 1000,
                                timestamp=time.time(),
                                details=details,
                                suggestions=suggestions
                            )
                        
                        return HealthCheckResult(
                            status=HealthStatus.HEALTHY,
                            message="Container running normally",
                            response_time_ms=(time.time() - start_time) * 1000,
                            timestamp=time.time(),
                            details=details
                        )
                    
                except Exception as e:
                    self.logger.debug(f"Could not get container stats for {container_name}: {e}")
                
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Container running",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=time.time(),
                    details={'container_status': container_status}
                )
            
            elif container_status in ['exited', 'stopped']:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Container {container_status}",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=time.time(),
                    details={'container_status': container_status},
                    suggestions=["Check container logs for errors", "Restart the container"]
                )
            
            elif container_status == 'restarting':
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Container restarting",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=time.time(),
                    details={'container_status': container_status},
                    suggestions=["Monitor restart frequency", "Check for crash loops"]
                )
            
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    message=f"Unknown container status: {container_status}",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=time.time(),
                    details={'container_status': container_status}
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Container check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={'error': str(e)}
            )
    
    def _check_service_health(self, config: ServiceHealthConfig, 
                            container_info: Dict[str, Any]) -> HealthCheckResult:
        """Check service-specific health based on configuration"""
        start_time = time.time()
        
        try:
            if config.check_type == 'http':
                return self._check_http_health(config, container_info, start_time)
            elif config.check_type == 'tcp':
                return self._check_tcp_health(config, container_info, start_time)
            elif config.check_type == 'exec':
                return self._check_exec_health(config, container_info, start_time)
            elif config.check_type == 'docker':
                return self._check_docker_health(config, container_info, start_time)
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    message=f"Unknown health check type: {config.check_type}",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=time.time()
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Service health check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={'error': str(e)}
            )
    
    def _check_http_health(self, config: ServiceHealthConfig, 
                          container_info: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """Check HTTP endpoint health"""
        try:
            # Determine URL
            if config.endpoint:
                url = config.endpoint
            else:
                # Try to determine from container ports
                ports = container_info.get('ports', {})
                port = config.port
                
                if not port and ports:
                    # Use first mapped port
                    for internal_port, mappings in ports.items():
                        if mappings and len(mappings) > 0:
                            port = int(mappings[0].get('HostPort', internal_port.split('/')[0]))
                            break
                
                if not port:
                    port = 80  # Default
                
                url = f"http://localhost:{port}/"
            
            # Perform HTTP request
            response = requests.get(
                url,
                timeout=config.timeout,
                headers=config.headers,
                allow_redirects=True
            )
            
            response_time = (time.time() - start_time) * 1000
            
            # Check status code
            if response.status_code != config.expected_status:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"HTTP {response.status_code} (expected {config.expected_status})",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={
                        'url': url,
                        'status_code': response.status_code,
                        'expected_status': config.expected_status
                    },
                    suggestions=[f"Check service logs", f"Verify service is responding at {url}"]
                )
            
            # Check content if specified
            if config.expected_content:
                if config.expected_content not in response.text:
                    return HealthCheckResult(
                        status=HealthStatus.DEGRADED,
                        message="HTTP response missing expected content",
                        response_time_ms=response_time,
                        timestamp=time.time(),
                        details={
                            'url': url,
                            'expected_content': config.expected_content,
                            'response_length': len(response.text)
                        }
                    )
            
            # Successful HTTP check
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message=f"HTTP {response.status_code} OK",
                response_time_ms=response_time,
                timestamp=time.time(),
                details={
                    'url': url,
                    'status_code': response.status_code,
                    'response_length': len(response.text)
                }
            )
            
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP timeout after {config.timeout}s",
                response_time_ms=config.timeout * 1000,
                timestamp=time.time(),
                suggestions=["Check if service is responding", "Increase timeout if service is slow"]
            )
        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message="HTTP connection failed",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                suggestions=["Check if service is running", "Verify port mapping"]
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"HTTP check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={'error': str(e)}
            )
    
    def _check_tcp_health(self, config: ServiceHealthConfig, 
                         container_info: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """Check TCP port connectivity"""
        try:
            port = config.port
            host = 'localhost'
            
            if not port:
                # Try to get port from container
                ports = container_info.get('ports', {})
                if ports:
                    for internal_port, mappings in ports.items():
                        if mappings and len(mappings) > 0:
                            port = int(mappings[0].get('HostPort', internal_port.split('/')[0]))
                            break
            
            if not port:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    message="No port specified for TCP check",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=time.time()
                )
            
            # Attempt TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(config.timeout)
            
            result = sock.connect_ex((host, port))
            sock.close()
            
            response_time = (time.time() - start_time) * 1000
            
            if result == 0:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message=f"TCP port {port} accessible",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={'host': host, 'port': port}
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"TCP port {port} not accessible",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={'host': host, 'port': port, 'error_code': result},
                    suggestions=["Check if service is listening on port", "Verify port mapping"]
                )
                
        except socket.timeout:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"TCP timeout after {config.timeout}s",
                response_time_ms=config.timeout * 1000,
                timestamp=time.time(),
                suggestions=["Check if service is responding", "Increase timeout"]
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"TCP check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={'error': str(e)}
            )
    
    def _check_exec_health(self, config: ServiceHealthConfig, 
                          container_info: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """Check health by executing command in container"""
        if not config.command:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message="No command specified for exec check",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time()
            )
        
        try:
            container_name = container_info['name']
            
            # Execute command in container
            cmd = ['docker', 'exec', container_name] + config.command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if result.returncode == 0:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Command executed successfully",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={
                        'command': ' '.join(config.command),
                        'stdout': result.stdout.strip(),
                        'return_code': result.returncode
                    }
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Command failed with exit code {result.returncode}",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={
                        'command': ' '.join(config.command),
                        'stdout': result.stdout.strip(),
                        'stderr': result.stderr.strip(),
                        'return_code': result.returncode
                    },
                    suggestions=["Check command output for errors", "Verify service is running properly"]
                )
                
        except subprocess.TimeoutExpired:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                message=f"Command timeout after {config.timeout}s",
                response_time_ms=config.timeout * 1000,
                timestamp=time.time(),
                suggestions=["Command may be hanging", "Increase timeout or check service"]
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Exec check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={'error': str(e)}
            )
    
    def _check_docker_health(self, config: ServiceHealthConfig, 
                           container_info: Dict[str, Any], start_time: float) -> HealthCheckResult:
        """Check Docker built-in health check"""
        try:
            container_name = container_info['name']
            
            # Get Docker health status
            inspect_result = subprocess.run(
                ['docker', 'inspect', container_name],
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            if inspect_result.returncode != 0:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    message="Failed to inspect container",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=time.time(),
                    details={'error': inspect_result.stderr.strip()}
                )
            
            inspect_data = json.loads(inspect_result.stdout)[0]
            health_data = inspect_data.get('State', {}).get('Health', {})
            
            if not health_data:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    message="No Docker health check configured",
                    response_time_ms=(time.time() - start_time) * 1000,
                    timestamp=time.time(),
                    suggestions=["Configure Docker HEALTHCHECK in Dockerfile"]
                )
            
            health_status = health_data.get('Status', 'none')
            response_time = (time.time() - start_time) * 1000
            
            if health_status == 'healthy':
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Docker health check passed",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={'docker_health_status': health_status}
                )
            elif health_status == 'unhealthy':
                # Get last health check log
                logs = health_data.get('Log', [])
                last_log = logs[-1] if logs else {}
                
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    message="Docker health check failed",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={
                        'docker_health_status': health_status,
                        'last_check_output': last_log.get('Output', ''),
                        'last_check_exit_code': last_log.get('ExitCode', 0)
                    },
                    suggestions=["Check Docker health check logs", "Review HEALTHCHECK command"]
                )
            elif health_status == 'starting':
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Docker health check starting",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={'docker_health_status': health_status}
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.UNKNOWN,
                    message=f"Unknown Docker health status: {health_status}",
                    response_time_ms=response_time,
                    timestamp=time.time(),
                    details={'docker_health_status': health_status}
                )
                
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Docker health check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=time.time(),
                details={'error': str(e)}
            )
    
    def _store_health_result(self, service_key: str, result: HealthCheckResult):
        """Store health check result in history"""
        if service_key not in self._health_history:
            self._health_history[service_key] = []
        
        self._health_history[service_key].append(result)
        
        # Limit history size
        if len(self._health_history[service_key]) > self._max_history:
            self._health_history[service_key].pop(0)
    
    def get_health_history(self, project_name: str, service_name: str = None, 
                          limit: int = 10) -> List[Dict[str, Any]]:
        """Get health check history for a service or project"""
        if service_name:
            service_key = f"{project_name}:{service_name}"
            history = self._health_history.get(service_key, [])
        else:
            # Get history for all services in project
            history = []
            for key, results in self._health_history.items():
                if key.startswith(f"{project_name}:"):
                    history.extend(results)
            
            # Sort by timestamp
            history.sort(key=lambda r: r.timestamp, reverse=True)
        
        # Convert to dict format and limit results
        return [
            {
                'status': result.status.value,
                'message': result.message,
                'response_time_ms': result.response_time_ms,
                'timestamp': result.timestamp,
                'details': result.details,
                'suggestions': result.suggestions
            }
            for result in history[-limit:]
        ]
    
    def get_health_statistics(self, project_name: str = None) -> Dict[str, Any]:
        """Get health check statistics"""
        if project_name:
            # Filter history for specific project
            project_history = []
            for key, results in self._health_history.items():
                if key.startswith(f"{project_name}:"):
                    project_history.extend(results)
        else:
            # All history
            project_history = []
            for results in self._health_history.values():
                project_history.extend(results)
        
        if not project_history:
            return {
                'total_checks': 0,
                'healthy_checks': 0,
                'unhealthy_checks': 0,
                'degraded_checks': 0,
                'unknown_checks': 0,
                'uptime_percentage': 0,
                'average_response_time_ms': 0
            }
        
        # Calculate statistics
        total_checks = len(project_history)
        healthy_checks = sum(1 for r in project_history if r.status == HealthStatus.HEALTHY)
        unhealthy_checks = sum(1 for r in project_history if r.status == HealthStatus.UNHEALTHY)
        degraded_checks = sum(1 for r in project_history if r.status == HealthStatus.DEGRADED)
        unknown_checks = sum(1 for r in project_history if r.status == HealthStatus.UNKNOWN)
        
        uptime_percentage = (healthy_checks / total_checks * 100) if total_checks > 0 else 0
        avg_response_time = sum(r.response_time_ms for r in project_history) / total_checks
        
        return {
            'total_checks': total_checks,
            'healthy_checks': healthy_checks,
            'unhealthy_checks': unhealthy_checks,
            'degraded_checks': degraded_checks,
            'unknown_checks': unknown_checks,
            'uptime_percentage': uptime_percentage,
            'average_response_time_ms': avg_response_time
        }
    
    def start_background_monitoring(self, interval: float = 30.0):
        """Start background health monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_interval = interval
        self._monitoring_active = True
        
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name='health-monitor',
            daemon=True
        )
        self._monitoring_thread.start()
        
        self.logger.info(f"Started background health monitoring (interval: {interval}s)")
    
    def stop_background_monitoring(self):
        """Stop background health monitoring"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            self._monitoring_thread.join(timeout=5)
        
        self.logger.info("Stopped background health monitoring")
    
    def _monitoring_loop(self):
        """Background monitoring loop"""
        while self._monitoring_active:
            try:
                # Get all active projects
                projects = self.docker_client.list_projects()
                
                for project in projects:
                    if self._monitoring_active:  # Check if still active
                        self.check_project_health(project)
                
                # Sleep for interval
                time.sleep(self._monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self._monitoring_interval)


# Global health checker instance
_health_checker = None


def get_health_checker() -> HealthChecker:
    """Get global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker