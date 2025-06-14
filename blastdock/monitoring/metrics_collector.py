"""
Metrics collection system for BlastDock deployments
"""

import time
import threading
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import statistics

from ..utils.logging import get_logger
from ..utils.docker_utils import DockerClient

logger = get_logger(__name__)


@dataclass
class MetricPoint:
    """Single metric measurement"""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Series of metric measurements"""
    name: str
    unit: str
    description: str
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """Comprehensive metrics collection system"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self.logger = get_logger(__name__)
        self.docker_client = DockerClient()
        
        # Metric storage
        self._metrics: Dict[str, MetricSeries] = {}
        self._metrics_lock = threading.RLock()
        
        # Collection configuration
        self._collection_active = False
        self._collection_thread = None
        self._collection_interval = 15.0  # 15 seconds
        
        # Metric retention
        self._max_points_per_metric = 1000
        self._retention_days = 7
        
        # Initialize core metrics
        self._initialize_core_metrics()
        
        self.logger.debug("Metrics collector initialized")
    
    def _initialize_core_metrics(self):
        """Initialize core metric series"""
        core_metrics = [
            # Container metrics
            ('container_cpu_percent', '%', 'Container CPU usage percentage'),
            ('container_memory_usage_mb', 'MB', 'Container memory usage in megabytes'),
            ('container_memory_percent', '%', 'Container memory usage percentage'),
            ('container_network_rx_bytes', 'bytes', 'Container network bytes received'),
            ('container_network_tx_bytes', 'bytes', 'Container network bytes transmitted'),
            ('container_disk_read_bytes', 'bytes', 'Container disk read bytes'),
            ('container_disk_write_bytes', 'bytes', 'Container disk write bytes'),
            ('container_uptime_seconds', 'seconds', 'Container uptime in seconds'),
            
            # Project metrics
            ('project_container_count', 'count', 'Number of containers in project'),
            ('project_running_containers', 'count', 'Number of running containers in project'),
            ('project_memory_total_mb', 'MB', 'Total memory usage of project'),
            ('project_cpu_total_percent', '%', 'Total CPU usage of project'),
            
            # System metrics
            ('system_containers_total', 'count', 'Total number of containers'),
            ('system_images_total', 'count', 'Total number of images'),
            ('system_volumes_total', 'count', 'Total number of volumes'),
            ('system_networks_total', 'count', 'Total number of networks'),
            
            # Health metrics
            ('health_check_duration_ms', 'ms', 'Health check duration in milliseconds'),
            ('health_check_success_rate', '%', 'Health check success rate'),
            
            # Performance metrics
            ('deployment_duration_seconds', 'seconds', 'Deployment duration in seconds'),
            ('template_load_duration_ms', 'ms', 'Template loading duration in milliseconds'),
        ]
        
        for name, unit, description in core_metrics:
            self._metrics[name] = MetricSeries(
                name=name,
                unit=unit,
                description=description
            )
    
    def collect_container_metrics(self, project_name: str):
        """Collect metrics for all containers in a project"""
        try:
            containers = self.docker_client.get_container_status(project_name)
            timestamp = time.time()
            
            project_cpu_total = 0
            project_memory_total = 0
            running_count = 0
            
            for container in containers:
                container_name = container['name']
                container_status = container['status']
                
                labels = {
                    'project': project_name,
                    'container': container_name,
                    'image': container['image'],
                    'status': container_status
                }
                
                if container_status == 'running':
                    running_count += 1
                    
                    # Get container stats
                    try:
                        stats = self.docker_client.get_container_stats(container_name)
                        if stats:
                            cpu_percent = stats.get('cpu_percent', 0)
                            memory_usage_mb = stats.get('memory_usage_mb', 0)
                            memory_percent = stats.get('memory_percent', 0)
                            
                            # Container-specific metrics
                            self.record_metric('container_cpu_percent', cpu_percent, timestamp, labels)
                            self.record_metric('container_memory_usage_mb', memory_usage_mb, timestamp, labels)
                            self.record_metric('container_memory_percent', memory_percent, timestamp, labels)
                            
                            # Network metrics
                            network_stats = stats.get('network', {})
                            if network_stats:
                                self.record_metric('container_network_rx_bytes', 
                                                 network_stats.get('rx_bytes', 0), timestamp, labels)
                                self.record_metric('container_network_tx_bytes', 
                                                 network_stats.get('tx_bytes', 0), timestamp, labels)
                            
                            # Disk metrics
                            disk_stats = stats.get('blkio', {})
                            if disk_stats:
                                self.record_metric('container_disk_read_bytes', 
                                                 disk_stats.get('read_bytes', 0), timestamp, labels)
                                self.record_metric('container_disk_write_bytes', 
                                                 disk_stats.get('write_bytes', 0), timestamp, labels)
                            
                            # Accumulate for project totals
                            project_cpu_total += cpu_percent
                            project_memory_total += memory_usage_mb
                            
                            # Uptime
                            if 'started_at' in container:
                                uptime = timestamp - container['started_at']
                                self.record_metric('container_uptime_seconds', uptime, timestamp, labels)
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to get stats for container {container_name}: {e}")
                else:
                    # Record zero values for stopped containers
                    self.record_metric('container_cpu_percent', 0, timestamp, labels)
                    self.record_metric('container_memory_usage_mb', 0, timestamp, labels)
                    self.record_metric('container_memory_percent', 0, timestamp, labels)
                    self.record_metric('container_uptime_seconds', 0, timestamp, labels)
            
            # Project-level metrics
            project_labels = {'project': project_name}
            self.record_metric('project_container_count', len(containers), timestamp, project_labels)
            self.record_metric('project_running_containers', running_count, timestamp, project_labels)
            self.record_metric('project_memory_total_mb', project_memory_total, timestamp, project_labels)
            self.record_metric('project_cpu_total_percent', project_cpu_total, timestamp, project_labels)
            
        except Exception as e:
            self.logger.error(f"Failed to collect container metrics for {project_name}: {e}")
    
    def collect_system_metrics(self):
        """Collect system-wide Docker metrics"""
        try:
            timestamp = time.time()
            
            # Get system info
            system_info = self.docker_client.get_system_info()
            
            if system_info:
                self.record_metric('system_containers_total', 
                                 system_info.get('containers', 0), timestamp)
                self.record_metric('system_images_total', 
                                 system_info.get('images', 0), timestamp)
            
            # Count volumes and networks
            try:
                volumes_info = self.docker_client.list_volumes()
                if volumes_info and 'Volumes' in volumes_info:
                    volume_count = len(volumes_info['Volumes'])
                    self.record_metric('system_volumes_total', volume_count, timestamp)
            except Exception as e:
                self.logger.debug(f"Could not get volume count: {e}")
            
            try:
                networks_info = self.docker_client.list_networks()
                if networks_info:
                    network_count = len(networks_info)
                    self.record_metric('system_networks_total', network_count, timestamp)
            except Exception as e:
                self.logger.debug(f"Could not get network count: {e}")
                
        except Exception as e:
            self.logger.error(f"Failed to collect system metrics: {e}")
    
    def record_metric(self, metric_name: str, value: float, timestamp: float = None, 
                     labels: Dict[str, str] = None):
        """Record a metric value"""
        if timestamp is None:
            timestamp = time.time()
        if labels is None:
            labels = {}
        
        with self._metrics_lock:
            if metric_name not in self._metrics:
                # Create new metric series
                self._metrics[metric_name] = MetricSeries(
                    name=metric_name,
                    unit='',
                    description=f'Custom metric: {metric_name}'
                )
            
            point = MetricPoint(timestamp=timestamp, value=value, labels=labels)
            self._metrics[metric_name].points.append(point)
    
    def record_health_metric(self, project_name: str, service_name: str, 
                           duration_ms: float, success: bool):
        """Record health check metrics"""
        timestamp = time.time()
        labels = {
            'project': project_name,
            'service': service_name
        }
        
        self.record_metric('health_check_duration_ms', duration_ms, timestamp, labels)
        
        # Calculate success rate for the service
        success_rate = self.calculate_health_success_rate(project_name, service_name)
        self.record_metric('health_check_success_rate', success_rate, timestamp, labels)
    
    def record_deployment_metric(self, project_name: str, duration_seconds: float, 
                               success: bool):
        """Record deployment metrics"""
        timestamp = time.time()
        labels = {
            'project': project_name,
            'success': str(success)
        }
        
        self.record_metric('deployment_duration_seconds', duration_seconds, timestamp, labels)
    
    def record_template_metric(self, template_name: str, load_duration_ms: float):
        """Record template loading metrics"""
        timestamp = time.time()
        labels = {
            'template': template_name
        }
        
        self.record_metric('template_load_duration_ms', load_duration_ms, timestamp, labels)
    
    def calculate_health_success_rate(self, project_name: str, service_name: str, 
                                    window_hours: int = 24) -> float:
        """Calculate health check success rate for a service"""
        try:
            cutoff_time = time.time() - (window_hours * 3600)
            
            # Get health check duration points for this service
            duration_metric = self._metrics.get('health_check_duration_ms')
            if not duration_metric:
                return 0.0
            
            relevant_points = [
                p for p in duration_metric.points
                if (p.timestamp >= cutoff_time and 
                    p.labels.get('project') == project_name and
                    p.labels.get('service') == service_name)
            ]
            
            if not relevant_points:
                return 0.0
            
            # Assume success if health check completed (has a duration)
            # In practice, you'd track success/failure separately
            total_checks = len(relevant_points)
            successful_checks = sum(1 for p in relevant_points if p.value > 0)
            
            return (successful_checks / total_checks * 100) if total_checks > 0 else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating health success rate: {e}")
            return 0.0
    
    def get_metric_values(self, metric_name: str, start_time: float = None, 
                         end_time: float = None, labels: Dict[str, str] = None) -> List[MetricPoint]:
        """Get metric values within time range and matching labels"""
        with self._metrics_lock:
            if metric_name not in self._metrics:
                return []
            
            metric = self._metrics[metric_name]
            points = list(metric.points)
        
        # Filter by time range
        if start_time is not None:
            points = [p for p in points if p.timestamp >= start_time]
        if end_time is not None:
            points = [p for p in points if p.timestamp <= end_time]
        
        # Filter by labels
        if labels:
            filtered_points = []
            for point in points:
                if all(point.labels.get(k) == v for k, v in labels.items()):
                    filtered_points.append(point)
            points = filtered_points
        
        return points
    
    def get_metric_summary(self, metric_name: str, start_time: float = None, 
                          end_time: float = None, labels: Dict[str, str] = None) -> Dict[str, Any]:
        """Get statistical summary of metric values"""
        points = self.get_metric_values(metric_name, start_time, end_time, labels)
        
        if not points:
            return {
                'count': 0,
                'min': 0,
                'max': 0,
                'avg': 0,
                'median': 0,
                'p95': 0,
                'p99': 0
            }
        
        values = [p.value for p in points]
        
        try:
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': statistics.mean(values),
                'median': statistics.median(values),
                'p95': self._percentile(values, 95),
                'p99': self._percentile(values, 99)
            }
        except Exception as e:
            self.logger.error(f"Error calculating metric summary: {e}")
            return {'count': len(values), 'error': str(e)}
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile value"""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * percentile / 100
        f = int(k)
        c = k - f
        
        if f == len(sorted_data) - 1:
            return sorted_data[f]
        else:
            return sorted_data[f] * (1 - c) + sorted_data[f + 1] * c
    
    def get_project_dashboard_data(self, project_name: str, 
                                  window_hours: int = 24) -> Dict[str, Any]:
        """Get dashboard data for a project"""
        end_time = time.time()
        start_time = end_time - (window_hours * 3600)
        project_labels = {'project': project_name}
        
        try:
            dashboard_data = {
                'project_name': project_name,
                'time_range_hours': window_hours,
                'timestamp': end_time,
                'metrics': {}
            }
            
            # Key metrics for dashboard
            key_metrics = [
                'project_container_count',
                'project_running_containers', 
                'project_memory_total_mb',
                'project_cpu_total_percent',
                'health_check_success_rate'
            ]
            
            for metric_name in key_metrics:
                summary = self.get_metric_summary(metric_name, start_time, end_time, project_labels)
                points = self.get_metric_values(metric_name, start_time, end_time, project_labels)
                
                dashboard_data['metrics'][metric_name] = {
                    'summary': summary,
                    'recent_values': [
                        {'timestamp': p.timestamp, 'value': p.value}
                        for p in points[-20:]  # Last 20 points
                    ]
                }
            
            # Container-specific metrics
            container_metrics = {}
            containers = self.docker_client.get_container_status(project_name)
            
            for container in containers:
                container_name = container['name']
                container_labels = {
                    'project': project_name,
                    'container': container_name
                }
                
                container_metrics[container_name] = {
                    'cpu': self.get_metric_summary('container_cpu_percent', 
                                                 start_time, end_time, container_labels),
                    'memory': self.get_metric_summary('container_memory_usage_mb', 
                                                    start_time, end_time, container_labels),
                    'uptime': self.get_metric_summary('container_uptime_seconds', 
                                                    start_time, end_time, container_labels)
                }
            
            dashboard_data['containers'] = container_metrics
            
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error generating dashboard data for {project_name}: {e}")
            return {
                'project_name': project_name,
                'error': str(e),
                'timestamp': end_time
            }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get information about all available metrics"""
        with self._metrics_lock:
            return {
                name: {
                    'name': metric.name,
                    'unit': metric.unit,
                    'description': metric.description,
                    'point_count': len(metric.points),
                    'labels': list(set().union(*(p.labels.keys() for p in metric.points))),
                    'latest_timestamp': max((p.timestamp for p in metric.points), default=0)
                }
                for name, metric in self._metrics.items()
            }
    
    def export_metrics(self, format: str = 'json', start_time: float = None, 
                      end_time: float = None) -> str:
        """Export metrics in specified format"""
        if format.lower() == 'prometheus':
            return self._export_prometheus(start_time, end_time)
        else:
            return self._export_json(start_time, end_time)
    
    def _export_json(self, start_time: float = None, end_time: float = None) -> str:
        """Export metrics as JSON"""
        export_data = {
            'export_time': time.time(),
            'start_time': start_time,
            'end_time': end_time,
            'metrics': {}
        }
        
        with self._metrics_lock:
            for name, metric in self._metrics.items():
                points = list(metric.points)
                
                # Filter by time range
                if start_time is not None:
                    points = [p for p in points if p.timestamp >= start_time]
                if end_time is not None:
                    points = [p for p in points if p.timestamp <= end_time]
                
                export_data['metrics'][name] = {
                    'name': metric.name,
                    'unit': metric.unit,
                    'description': metric.description,
                    'points': [
                        {
                            'timestamp': p.timestamp,
                            'value': p.value,
                            'labels': p.labels
                        }
                        for p in points
                    ]
                }
        
        return json.dumps(export_data, indent=2)
    
    def _export_prometheus(self, start_time: float = None, end_time: float = None) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        with self._metrics_lock:
            for name, metric in self._metrics.items():
                # Convert metric name to Prometheus format
                prom_name = f"blastdock_{name}"
                
                # Add help and type
                lines.append(f"# HELP {prom_name} {metric.description}")
                lines.append(f"# TYPE {prom_name} gauge")
                
                points = list(metric.points)
                
                # Filter by time range
                if start_time is not None:
                    points = [p for p in points if p.timestamp >= start_time]
                if end_time is not None:
                    points = [p for p in points if p.timestamp <= end_time]
                
                # Get latest point for each unique label combination
                latest_points = {}
                for point in points:
                    label_key = tuple(sorted(point.labels.items()))
                    if (label_key not in latest_points or 
                        point.timestamp > latest_points[label_key].timestamp):
                        latest_points[label_key] = point
                
                # Format points
                for point in latest_points.values():
                    if point.labels:
                        label_str = ','.join(f'{k}="{v}"' for k, v in sorted(point.labels.items()))
                        lines.append(f"{prom_name}{{{label_str}}} {point.value}")
                    else:
                        lines.append(f"{prom_name} {point.value}")
                
                lines.append("")  # Empty line between metrics
        
        return '\n'.join(lines)
    
    def start_collection(self, interval: float = 15.0):
        """Start background metrics collection"""
        if self._collection_active:
            return
        
        self._collection_interval = interval
        self._collection_active = True
        
        self._collection_thread = threading.Thread(
            target=self._collection_loop,
            name='metrics-collector',
            daemon=True
        )
        self._collection_thread.start()
        
        self.logger.info(f"Started metrics collection (interval: {interval}s)")
    
    def stop_collection(self):
        """Stop background metrics collection"""
        if not self._collection_active:
            return
        
        self._collection_active = False
        
        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=5)
        
        self.logger.info("Stopped metrics collection")
    
    def _collection_loop(self):
        """Background collection loop"""
        while self._collection_active:
            try:
                # Collect system metrics
                self.collect_system_metrics()
                
                # Collect metrics for all projects
                projects = self.docker_client.list_projects()
                for project in projects:
                    if self._collection_active:  # Check if still active
                        self.collect_container_metrics(project)
                
                # Sleep for interval
                time.sleep(self._collection_interval)
                
            except Exception as e:
                self.logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(self._collection_interval)
    
    def cleanup_old_metrics(self):
        """Remove old metric points beyond retention period"""
        cutoff_time = time.time() - (self._retention_days * 24 * 3600)
        
        with self._metrics_lock:
            for metric in self._metrics.values():
                # Remove old points
                while metric.points and metric.points[0].timestamp < cutoff_time:
                    metric.points.popleft()
        
        self.logger.debug(f"Cleaned up metrics older than {self._retention_days} days")


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector