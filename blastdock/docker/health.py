"""
Docker health checking and monitoring utilities
"""

import time
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

from ..utils.logging import get_logger
from .client import get_docker_client
from .errors import DockerError, ContainerError

logger = get_logger(__name__)


class DockerHealthChecker:
    """Comprehensive Docker health checker"""
    
    def __init__(self):
        """Initialize health checker"""
        self.docker_client = get_docker_client()
        self.logger = get_logger(__name__)
    
    def check_docker_daemon_health(self) -> Dict[str, Any]:
        """Check Docker daemon health and performance"""
        health_report = {
            'healthy': False,
            'daemon_responsive': False,
            'performance_metrics': {},
            'resource_usage': {},
            'issues': [],
            'recommendations': []
        }
        
        try:
            # Check daemon responsiveness
            start_time = time.time()
            availability = self.docker_client.check_docker_availability()
            response_time = time.time() - start_time
            
            health_report['daemon_responsive'] = availability['docker_running']
            health_report['performance_metrics']['response_time'] = response_time
            
            if response_time > 5.0:
                health_report['issues'].append("Docker daemon is responding slowly")
                health_report['recommendations'].append("Check system resources and Docker daemon logs")
            
            if not availability['docker_running']:
                health_report['issues'].append("Docker daemon not running")
                return health_report
            
            # Get system information
            system_info = self.docker_client.get_system_info()
            
            # Check resource usage
            if 'system' in system_info:
                sys_info = system_info['system']
                health_report['resource_usage'] = {
                    'containers_total': sys_info.get('containers', 0),
                    'containers_running': sys_info.get('containers_running', 0),
                    'containers_stopped': sys_info.get('containers_stopped', 0),
                    'images_total': sys_info.get('images', 0),
                    'memory_total': sys_info.get('memory'),
                    'cpus': sys_info.get('cpus')
                }
                
                # Check for potential issues
                containers_total = sys_info.get('containers', 0)
                containers_running = sys_info.get('containers_running', 0)
                
                if containers_total > 50:
                    health_report['recommendations'].append("Consider cleaning up unused containers")
                
                if containers_running > 20:
                    health_report['issues'].append(f"High number of running containers: {containers_running}")
                    health_report['recommendations'].append("Monitor resource usage and consider scaling limits")
            
            # Check disk space (Docker root directory)
            try:
                result = self.docker_client.execute_command(['docker', 'system', 'df'])
                health_report['performance_metrics']['disk_usage'] = result.stdout
                
                # Parse disk usage for warnings
                if 'Total' in result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if 'Local Volumes' in line or 'Build Cache' in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                size_str = parts[2]
                                if 'GB' in size_str:
                                    try:
                                        size_gb = float(size_str.replace('GB', ''))
                                        if size_gb > 10:
                                            health_report['recommendations'].append(
                                                f"High disk usage detected: {size_str}"
                                            )
                                    except ValueError:
                                        pass
                        
            except Exception as e:
                health_report['issues'].append(f"Could not check disk usage: {str(e)}")
            
            # Overall health determination
            health_report['healthy'] = (
                health_report['daemon_responsive'] and
                len(health_report['issues']) == 0 and
                response_time < 2.0
            )
            
        except Exception as e:
            health_report['issues'].append(f"Health check failed: {str(e)}")
            self.logger.error(f"Docker daemon health check failed: {e}")
        
        return health_report
    
    def check_container_health(self, container_id: str) -> Dict[str, Any]:
        """Check health of a specific container"""
        health_info = {
            'container_id': container_id,
            'healthy': False,
            'status': 'unknown',
            'health_checks': [],
            'resource_usage': {},
            'network_info': {},
            'issues': [],
            'recommendations': []
        }
        
        try:
            # Get container information
            result = self.docker_client.execute_command([
                'docker', 'inspect', container_id, '--format', '{{json .}}'
            ])
            
            container_info = json.loads(result.stdout)
            
            # Basic status
            state = container_info.get('State', {})
            health_info['status'] = state.get('Status', 'unknown')
            health_info['healthy'] = state.get('Status') == 'running'
            
            # Health check information
            health_config = container_info.get('Config', {}).get('Healthcheck')
            if health_config:
                health_info['health_checks'].append({
                    'configured': True,
                    'test': health_config.get('Test', []),
                    'interval': health_config.get('Interval'),
                    'timeout': health_config.get('Timeout'),
                    'retries': health_config.get('Retries')
                })
                
                # Get health status
                health_state = state.get('Health', {})
                if health_state:
                    health_info['health_checks'].append({
                        'status': health_state.get('Status'),
                        'failing_streak': health_state.get('FailingStreak', 0),
                        'log': health_state.get('Log', [])[-3:]  # Last 3 health check results
                    })
                    
                    if health_state.get('Status') != 'healthy':
                        health_info['issues'].append(f"Container health check status: {health_state.get('Status')}")
            else:
                health_info['recommendations'].append("Consider adding health check to container")
            
            # Resource usage
            try:
                stats_result = self.docker_client.execute_command([
                    'docker', 'stats', container_id, '--no-stream', '--format',
                    '{{json .}}'
                ])
                
                stats = json.loads(stats_result.stdout)
                health_info['resource_usage'] = {
                    'cpu_percent': stats.get('CPUPerc', '0%'),
                    'memory_usage': stats.get('MemUsage', '0B / 0B'),
                    'memory_percent': stats.get('MemPerc', '0%'),
                    'network_io': stats.get('NetIO', '0B / 0B'),
                    'block_io': stats.get('BlockIO', '0B / 0B')
                }
                
                # Check for resource issues
                cpu_str = stats.get('CPUPerc', '0%').replace('%', '')
                try:
                    cpu_percent = float(cpu_str)
                    if cpu_percent > 80:
                        health_info['issues'].append(f"High CPU usage: {cpu_percent}%")
                except ValueError:
                    pass
                
                mem_str = stats.get('MemPerc', '0%').replace('%', '')
                try:
                    mem_percent = float(mem_str)
                    if mem_percent > 90:
                        health_info['issues'].append(f"High memory usage: {mem_percent}%")
                except ValueError:
                    pass
                
            except Exception as e:
                health_info['recommendations'].append("Could not get resource statistics")
            
            # Network information
            networks = container_info.get('NetworkSettings', {}).get('Networks', {})
            for network_name, network_info in networks.items():
                health_info['network_info'][network_name] = {
                    'ip_address': network_info.get('IPAddress'),
                    'gateway': network_info.get('Gateway'),
                    'network_id': network_info.get('NetworkID')
                }
            
            # Check for restart count
            restart_count = state.get('RestartCount', 0)
            if restart_count > 5:
                health_info['issues'].append(f"Container has restarted {restart_count} times")
                health_info['recommendations'].append("Check container logs for recurring issues")
            
            # Check exit code if not running
            if state.get('Status') != 'running':
                exit_code = state.get('ExitCode')
                if exit_code and exit_code != 0:
                    health_info['issues'].append(f"Container exited with code: {exit_code}")
                    health_info['recommendations'].append("Check container logs for error details")
            
        except Exception as e:
            health_info['issues'].append(f"Container health check failed: {str(e)}")
            self.logger.error(f"Container health check failed for {container_id}: {e}")
        
        return health_info
    
    def check_compose_project_health(self, project_name: str, 
                                   compose_file: Optional[str] = None) -> Dict[str, Any]:
        """Check health of all services in a Docker Compose project"""
        project_health = {
            'project_name': project_name,
            'healthy': False,
            'services': {},
            'overall_status': 'unknown',
            'issues': [],
            'recommendations': []
        }
        
        try:
            from .compose import ComposeManager
            compose_manager = ComposeManager(project_name=project_name)
            
            # Get service status
            service_status = compose_manager.get_service_status(compose_file)
            
            healthy_services = 0
            total_services = len(service_status)
            
            for service_name, service_info in service_status.items():
                service_health = {
                    'name': service_info.get('name', service_name),
                    'state': service_info.get('state', 'unknown'),
                    'healthy': False,
                    'issues': []
                }
                
                # Check service state
                state = service_info.get('state', '').lower()
                if state == 'running':
                    service_health['healthy'] = True
                    healthy_services += 1
                elif state in ['exited', 'dead']:
                    service_health['issues'].append(f"Service is {state}")
                elif state == 'restarting':
                    service_health['issues'].append("Service is constantly restarting")
                
                # Get container health if available
                container_name = service_info.get('name')
                if container_name:
                    try:
                        container_health = self.check_container_health(container_name)
                        service_health.update({
                            'resource_usage': container_health.get('resource_usage', {}),
                            'health_checks': container_health.get('health_checks', [])
                        })
                        service_health['issues'].extend(container_health.get('issues', []))
                    except Exception as e:
                        service_health['issues'].append(f"Could not check container health: {str(e)}")
                
                project_health['services'][service_name] = service_health
            
            # Determine overall health
            if total_services == 0:
                project_health['overall_status'] = 'no_services'
                project_health['issues'].append("No services found in project")
            elif healthy_services == total_services:
                project_health['overall_status'] = 'healthy'
                project_health['healthy'] = True
            elif healthy_services > 0:
                project_health['overall_status'] = 'partially_healthy'
                project_health['issues'].append(f"Only {healthy_services}/{total_services} services are healthy")
            else:
                project_health['overall_status'] = 'unhealthy'
                project_health['issues'].append("No services are healthy")
            
            # Generate recommendations
            if not project_health['healthy']:
                project_health['recommendations'].extend([
                    "Check service logs for error details",
                    "Verify service dependencies and startup order",
                    "Check resource availability and limits"
                ])
            
        except Exception as e:
            project_health['issues'].append(f"Project health check failed: {str(e)}")
            self.logger.error(f"Compose project health check failed for {project_name}: {e}")
        
        return project_health
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get overall Docker environment health summary"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'overall_healthy': False,
            'daemon_health': {},
            'projects': [],
            'containers': [],
            'system_resources': {},
            'recommendations': []
        }
        
        try:
            # Check daemon health
            summary['daemon_health'] = self.check_docker_daemon_health()
            
            # Get all containers
            result = self.docker_client.execute_command([
                'docker', 'ps', '-a', '--format', '{{json .}}'
            ])
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        container = json.loads(line)
                        containers.append(container)
                    except json.JSONDecodeError:
                        continue
            
            # Check container health
            running_containers = [c for c in containers if c.get('State') == 'running']
            summary['containers'] = [
                {
                    'id': c.get('ID', '')[:12],
                    'name': c.get('Names', ''),
                    'image': c.get('Image', ''),
                    'status': c.get('Status', ''),
                    'state': c.get('State', '')
                }
                for c in containers[:10]  # Limit to first 10
            ]
            
            # System resources summary
            if summary['daemon_health'].get('resource_usage'):
                resources = summary['daemon_health']['resource_usage']
                summary['system_resources'] = {
                    'total_containers': resources.get('containers_total', 0),
                    'running_containers': resources.get('containers_running', 0),
                    'total_images': resources.get('images_total', 0)
                }
            
            # Overall health determination
            summary['overall_healthy'] = (
                summary['daemon_health'].get('healthy', False) and
                len(summary['daemon_health'].get('issues', [])) == 0
            )
            
            # Collect recommendations
            summary['recommendations'].extend(summary['daemon_health'].get('recommendations', []))
            
        except Exception as e:
            summary['recommendations'].append(f"Health summary generation failed: {str(e)}")
            self.logger.error(f"Health summary generation failed: {e}")
        
        return summary
    
    def monitor_container_performance(self, container_id: str, 
                                   duration: int = 60) -> Dict[str, Any]:
        """Monitor container performance over time"""
        performance_data = {
            'container_id': container_id,
            'duration': duration,
            'samples': [],
            'averages': {},
            'trends': {},
            'alerts': []
        }
        
        try:
            start_time = time.time()
            sample_interval = max(1, duration // 60)  # Max 60 samples
            
            while time.time() - start_time < duration:
                try:
                    # Get current stats
                    result = self.docker_client.execute_command([
                        'docker', 'stats', container_id, '--no-stream', '--format', '{{json .}}'
                    ])
                    
                    stats = json.loads(result.stdout)
                    sample = {
                        'timestamp': time.time(),
                        'cpu_percent': self._parse_percentage(stats.get('CPUPerc', '0%')),
                        'memory_percent': self._parse_percentage(stats.get('MemPerc', '0%')),
                        'memory_usage': stats.get('MemUsage', '0B / 0B'),
                        'network_io': stats.get('NetIO', '0B / 0B'),
                        'block_io': stats.get('BlockIO', '0B / 0B')
                    }
                    
                    performance_data['samples'].append(sample)
                    
                    # Check for alerts
                    if sample['cpu_percent'] > 90:
                        performance_data['alerts'].append({
                            'timestamp': sample['timestamp'],
                            'type': 'high_cpu',
                            'value': sample['cpu_percent']
                        })
                    
                    if sample['memory_percent'] > 95:
                        performance_data['alerts'].append({
                            'timestamp': sample['timestamp'],
                            'type': 'high_memory',
                            'value': sample['memory_percent']
                        })
                    
                    time.sleep(sample_interval)
                    
                except Exception as e:
                    self.logger.warning(f"Performance sample failed: {e}")
                    time.sleep(sample_interval)
            
            # Calculate averages and trends
            if performance_data['samples']:
                cpu_values = [s['cpu_percent'] for s in performance_data['samples']]
                memory_values = [s['memory_percent'] for s in performance_data['samples']]
                
                performance_data['averages'] = {
                    'cpu_percent': sum(cpu_values) / len(cpu_values),
                    'memory_percent': sum(memory_values) / len(memory_values),
                    'max_cpu': max(cpu_values),
                    'max_memory': max(memory_values)
                }
                
                # Simple trend calculation (linear regression would be better)
                if len(cpu_values) >= 2:
                    cpu_trend = cpu_values[-1] - cpu_values[0]
                    memory_trend = memory_values[-1] - memory_values[0]
                    
                    performance_data['trends'] = {
                        'cpu_trend': 'increasing' if cpu_trend > 5 else 'decreasing' if cpu_trend < -5 else 'stable',
                        'memory_trend': 'increasing' if memory_trend > 5 else 'decreasing' if memory_trend < -5 else 'stable'
                    }
            
        except Exception as e:
            performance_data['alerts'].append({
                'timestamp': time.time(),
                'type': 'monitoring_error',
                'message': str(e)
            })
            self.logger.error(f"Container performance monitoring failed: {e}")
        
        return performance_data
    
    def _parse_percentage(self, percent_str: str) -> float:
        """Parse percentage string to float"""
        try:
            return float(percent_str.replace('%', ''))
        except ValueError:
            return 0.0