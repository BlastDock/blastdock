"""
Alert management system for BlastDock monitoring
"""

import os
import time
import threading
import json
import subprocess
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

# Optional email imports (for notifications)
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

from ..utils.logging import get_logger

logger = get_logger(__name__)


class AlertSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    description: str
    metric_name: str
    condition: str  # 'gt', 'lt', 'eq', 'ne', 'gte', 'lte'
    threshold: float
    severity: AlertSeverity
    duration_seconds: int = 300  # How long condition must be true to fire
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class Alert:
    """Active alert instance"""
    rule_name: str
    severity: AlertSeverity
    message: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    status: AlertStatus
    fired_at: float
    resolved_at: Optional[float] = None
    silenced_until: Optional[float] = None
    notification_sent: bool = False


@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    name: str
    type: str  # 'email', 'webhook', 'slack', 'discord', 'command'
    config: Dict[str, Any]
    enabled: bool = True
    severities: List[AlertSeverity] = field(default_factory=lambda: list(AlertSeverity))


class AlertManager:
    """Comprehensive alert management system"""
    
    def __init__(self):
        """Initialize alert manager"""
        self.logger = get_logger(__name__)
        
        # Alert rules and active alerts
        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._alerts_lock = threading.RLock()
        
        # Notification channels
        self._notification_channels: Dict[str, NotificationChannel] = {}
        
        # Alert evaluation
        self._evaluation_active = False
        self._evaluation_thread = None
        self._evaluation_interval = 30.0  # 30 seconds
        
        # Metric conditions tracking
        self._condition_state: Dict[str, Dict[str, Any]] = {}
        
        # Alert statistics
        self.stats = {
            'total_alerts': 0,
            'active_alerts': 0,
            'resolved_alerts': 0,
            'notifications_sent': 0,
            'rules_evaluated': 0
        }
        
        # Initialize default rules
        self._initialize_default_rules()
        
        self.logger.debug("Alert manager initialized")
    
    def _initialize_default_rules(self):
        """Initialize default alert rules"""
        default_rules = [
            AlertRule(
                name="high_cpu_usage",
                description="Container CPU usage is high",
                metric_name="container_cpu_percent",
                condition="gte",
                threshold=90.0,
                severity=AlertSeverity.WARNING,
                duration_seconds=300,
                annotations={
                    "summary": "High CPU usage detected",
                    "description": "Container {{ $labels.container }} in project {{ $labels.project }} has high CPU usage ({{ $value }}%)"
                }
            ),
            AlertRule(
                name="critical_cpu_usage",
                description="Container CPU usage is critical",
                metric_name="container_cpu_percent",
                condition="gte",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                duration_seconds=180,
                annotations={
                    "summary": "Critical CPU usage detected",
                    "description": "Container {{ $labels.container }} in project {{ $labels.project }} has critical CPU usage ({{ $value }}%)"
                }
            ),
            AlertRule(
                name="high_memory_usage",
                description="Container memory usage is high",
                metric_name="container_memory_percent",
                condition="gte",
                threshold=85.0,
                severity=AlertSeverity.WARNING,
                duration_seconds=300,
                annotations={
                    "summary": "High memory usage detected",
                    "description": "Container {{ $labels.container }} in project {{ $labels.project }} has high memory usage ({{ $value }}%)"
                }
            ),
            AlertRule(
                name="container_down",
                description="Container is not running",
                metric_name="container_uptime_seconds",
                condition="eq",
                threshold=0.0,
                severity=AlertSeverity.CRITICAL,
                duration_seconds=60,
                annotations={
                    "summary": "Container is down",
                    "description": "Container {{ $labels.container }} in project {{ $labels.project }} is not running"
                }
            ),
            AlertRule(
                name="health_check_failing",
                description="Health check success rate is low",
                metric_name="health_check_success_rate",
                condition="lt",
                threshold=80.0,
                severity=AlertSeverity.WARNING,
                duration_seconds=600,
                annotations={
                    "summary": "Health checks failing",
                    "description": "Service {{ $labels.service }} in project {{ $labels.project }} has low health check success rate ({{ $value }}%)"
                }
            ),
            AlertRule(
                name="deployment_duration_high",
                description="Deployment taking too long",
                metric_name="deployment_duration_seconds",
                condition="gt",
                threshold=600.0,  # 10 minutes
                severity=AlertSeverity.WARNING,
                duration_seconds=0,  # Immediate
                annotations={
                    "summary": "Slow deployment detected",
                    "description": "Deployment of project {{ $labels.project }} took {{ $value }} seconds"
                }
            )
        ]
        
        for rule in default_rules:
            self._rules[rule.name] = rule
    
    def add_rule(self, rule: AlertRule):
        """Add or update an alert rule"""
        with self._alerts_lock:
            self._rules[rule.name] = rule
        
        self.logger.info(f"Added alert rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove an alert rule"""
        with self._alerts_lock:
            if rule_name in self._rules:
                del self._rules[rule_name]
                
                # Clear any related condition state
                if rule_name in self._condition_state:
                    del self._condition_state[rule_name]
                
                self.logger.info(f"Removed alert rule: {rule_name}")
                return True
        
        return False
    
    def get_rules(self) -> List[AlertRule]:
        """Get all alert rules"""
        with self._alerts_lock:
            return list(self._rules.values())
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable an alert rule"""
        with self._alerts_lock:
            if rule_name in self._rules:
                self._rules[rule_name].enabled = True
                self.logger.info(f"Enabled alert rule: {rule_name}")
                return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable an alert rule"""
        with self._alerts_lock:
            if rule_name in self._rules:
                self._rules[rule_name].enabled = False
                self.logger.info(f"Disabled alert rule: {rule_name}")
                return True
        return False
    
    def add_notification_channel(self, channel: NotificationChannel):
        """Add notification channel"""
        self._notification_channels[channel.name] = channel
        self.logger.info(f"Added notification channel: {channel.name} ({channel.type})")
    
    def remove_notification_channel(self, channel_name: str) -> bool:
        """Remove notification channel"""
        if channel_name in self._notification_channels:
            del self._notification_channels[channel_name]
            self.logger.info(f"Removed notification channel: {channel_name}")
            return True
        return False
    
    def evaluate_rules(self, metrics_data: Dict[str, Any]):
        """Evaluate alert rules against metrics"""
        current_time = time.time()
        
        with self._alerts_lock:
            for rule_name, rule in self._rules.items():
                if not rule.enabled:
                    continue
                
                try:
                    self._evaluate_rule(rule, metrics_data, current_time)
                    self.stats['rules_evaluated'] += 1
                except Exception as e:
                    self.logger.error(f"Error evaluating rule {rule_name}: {e}")
    
    def _evaluate_rule(self, rule: AlertRule, metrics_data: Dict[str, Any], current_time: float):
        """Evaluate a single alert rule"""
        # Get metric values that match the rule
        metric_values = self._get_metric_values_for_rule(rule, metrics_data)
        
        for metric_key, value in metric_values.items():
            # Check if condition is met
            condition_met = self._evaluate_condition(rule.condition, value, rule.threshold)
            
            # Track condition state for duration-based alerts
            state_key = f"{rule.name}:{metric_key}"
            
            if state_key not in self._condition_state:
                self._condition_state[state_key] = {
                    'first_time': None,
                    'last_time': None,
                    'consecutive_count': 0
                }
            
            state = self._condition_state[state_key]
            
            if condition_met:
                if state['first_time'] is None:
                    state['first_time'] = current_time
                state['last_time'] = current_time
                state['consecutive_count'] += 1
                
                # Check if duration threshold is met
                duration_met = (current_time - state['first_time']) >= rule.duration_seconds
                
                if duration_met:
                    self._fire_alert(rule, metric_key, value, current_time)
            else:
                # Condition not met, reset state and resolve any active alerts
                if state['first_time'] is not None:
                    self._resolve_alert(rule, metric_key, current_time)
                
                state['first_time'] = None
                state['last_time'] = None
                state['consecutive_count'] = 0
    
    def _get_metric_values_for_rule(self, rule: AlertRule, 
                                   metrics_data: Dict[str, Any]) -> Dict[str, float]:
        """Get metric values that apply to this rule"""
        metric_values = {}
        
        # This would typically query the metrics collector
        # For now, simulate getting recent metric values
        if rule.metric_name in metrics_data:
            metric_info = metrics_data[rule.metric_name]
            
            # If metric has recent values, evaluate each
            if 'recent_values' in metric_info:
                for i, point in enumerate(metric_info['recent_values'][-5:]):  # Last 5 points
                    # Create a unique key for this metric point
                    # In practice, this would include labels to identify specific containers/services
                    metric_key = f"{rule.metric_name}:{i}"
                    metric_values[metric_key] = point['value']
            
            # Also check summary values
            elif 'summary' in metric_info and 'avg' in metric_info['summary']:
                metric_key = f"{rule.metric_name}:avg"
                metric_values[metric_key] = metric_info['summary']['avg']
        
        return metric_values
    
    def _evaluate_condition(self, condition: str, value: float, threshold: float) -> bool:
        """Evaluate if condition is met"""
        if condition == 'gt':
            return value > threshold
        elif condition == 'gte':
            return value >= threshold
        elif condition == 'lt':
            return value < threshold
        elif condition == 'lte':
            return value <= threshold
        elif condition == 'eq':
            return abs(value - threshold) < 0.001  # Float equality with tolerance
        elif condition == 'ne':
            return abs(value - threshold) >= 0.001
        else:
            self.logger.warning(f"Unknown condition: {condition}")
            return False
    
    def _fire_alert(self, rule: AlertRule, metric_key: str, value: float, current_time: float):
        """Fire an alert"""
        alert_id = f"{rule.name}:{metric_key}"
        
        # Check if alert is already active
        if alert_id in self._active_alerts:
            existing_alert = self._active_alerts[alert_id]
            if existing_alert.status == AlertStatus.FIRING:
                return  # Alert already firing
        
        # Create new alert
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            message=self._format_alert_message(rule, value),
            labels=rule.labels.copy(),
            annotations=rule.annotations.copy(),
            status=AlertStatus.FIRING,
            fired_at=current_time
        )
        
        # Add metric-specific labels
        alert.labels['metric_key'] = metric_key
        alert.labels['metric_value'] = str(value)
        
        self._active_alerts[alert_id] = alert
        self._alert_history.append(alert)
        
        # Update statistics
        self.stats['total_alerts'] += 1
        self.stats['active_alerts'] += 1
        
        # Send notifications
        self._send_notifications(alert)
        
        self.logger.warning(f"Alert fired: {rule.name} - {alert.message}")
    
    def _resolve_alert(self, rule: AlertRule, metric_key: str, current_time: float):
        """Resolve an alert"""
        alert_id = f"{rule.name}:{metric_key}"
        
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            
            if alert.status == AlertStatus.FIRING:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = current_time
                
                # Update statistics
                self.stats['active_alerts'] -= 1
                self.stats['resolved_alerts'] += 1
                
                # Send resolution notifications
                self._send_resolution_notifications(alert)
                
                self.logger.info(f"Alert resolved: {rule.name}")
            
            # Remove from active alerts
            del self._active_alerts[alert_id]
    
    def _format_alert_message(self, rule: AlertRule, value: float) -> str:
        """Format alert message with template substitution"""
        message = rule.description
        
        # Simple template substitution
        message = message.replace("{{ $value }}", str(value))
        
        # Add labels if available (simplified)
        for key, val in rule.labels.items():
            message = message.replace(f"{{{{ $labels.{key} }}}}", val)
        
        return message
    
    def _send_notifications(self, alert: Alert):
        """Send alert notifications to configured channels"""
        for channel_name, channel in self._notification_channels.items():
            if not channel.enabled:
                continue
            
            if alert.severity not in channel.severities:
                continue
            
            try:
                self._send_notification_to_channel(alert, channel)
                alert.notification_sent = True
                self.stats['notifications_sent'] += 1
            except Exception as e:
                self.logger.error(f"Failed to send notification to {channel_name}: {e}")
    
    def _send_resolution_notifications(self, alert: Alert):
        """Send alert resolution notifications"""
        for channel_name, channel in self._notification_channels.items():
            if not channel.enabled:
                continue
            
            if alert.severity not in channel.severities:
                continue
            
            try:
                self._send_resolution_to_channel(alert, channel)
            except Exception as e:
                self.logger.error(f"Failed to send resolution to {channel_name}: {e}")
    
    def _send_notification_to_channel(self, alert: Alert, channel: NotificationChannel):
        """Send notification to specific channel"""
        if channel.type == 'email':
            self._send_email_notification(alert, channel)
        elif channel.type == 'webhook':
            self._send_webhook_notification(alert, channel)
        elif channel.type == 'command':
            self._send_command_notification(alert, channel)
        else:
            self.logger.warning(f"Unsupported notification channel type: {channel.type}")
    
    def _send_resolution_to_channel(self, alert: Alert, channel: NotificationChannel):
        """Send resolution notification to specific channel"""
        # Similar to _send_notification_to_channel but for resolutions
        if channel.type == 'email':
            self._send_email_resolution(alert, channel)
        elif channel.type == 'webhook':
            self._send_webhook_resolution(alert, channel)
        elif channel.type == 'command':
            self._send_command_resolution(alert, channel)
    
    def _send_email_notification(self, alert: Alert, channel: NotificationChannel):
        """Send email notification"""
        if not EMAIL_AVAILABLE:
            raise ValueError("Email functionality not available - missing email modules")
        
        config = channel.config
        
        smtp_server = config.get('smtp_server')
        smtp_port = config.get('smtp_port', 587)
        username = config.get('username')
        password = config.get('password')
        from_email = config.get('from_email')
        to_emails = config.get('to_emails', [])
        
        if not all([smtp_server, username, password, from_email, to_emails]):
            raise ValueError("Email configuration incomplete")
        
        # Create message
        msg = MimeMultipart()
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = f"[{alert.severity.value.upper()}] BlastDock Alert: {alert.rule_name}"
        
        # Create email body
        body = f"""
BlastDock Alert Notification

Severity: {alert.severity.value.upper()}
Rule: {alert.rule_name}
Message: {alert.message}
Fired At: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.fired_at))}

Labels:
{json.dumps(alert.labels, indent=2)}

Annotations:
{json.dumps(alert.annotations, indent=2)}

--
BlastDock Monitoring System
"""
        
        msg.attach(MimeText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
    
    def _send_email_resolution(self, alert: Alert, channel: NotificationChannel):
        """Send email resolution notification"""
        if not EMAIL_AVAILABLE:
            return  # Silently skip if email not available
        
        config = channel.config
        
        smtp_server = config.get('smtp_server')
        smtp_port = config.get('smtp_port', 587)
        username = config.get('username')
        password = config.get('password')
        from_email = config.get('from_email')
        to_emails = config.get('to_emails', [])
        
        if not all([smtp_server, username, password, from_email, to_emails]):
            return
        
        # Create message
        msg = MimeMultipart()
        msg['From'] = from_email
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = f"[RESOLVED] BlastDock Alert: {alert.rule_name}"
        
        # Create email body
        duration = alert.resolved_at - alert.fired_at if alert.resolved_at else 0
        body = f"""
BlastDock Alert Resolution

Rule: {alert.rule_name}
Message: {alert.message}
Fired At: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.fired_at))}
Resolved At: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(alert.resolved_at or time.time()))}
Duration: {int(duration)} seconds

--
BlastDock Monitoring System
"""
        
        msg.attach(MimeText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
    
    def _send_webhook_notification(self, alert: Alert, channel: NotificationChannel):
        """Send webhook notification"""
        import requests
        
        config = channel.config
        url = config.get('url')
        
        if not url:
            raise ValueError("Webhook URL not configured")
        
        payload = {
            'alert': {
                'rule_name': alert.rule_name,
                'severity': alert.severity.value,
                'message': alert.message,
                'status': alert.status.value,
                'fired_at': alert.fired_at,
                'labels': alert.labels,
                'annotations': alert.annotations
            }
        }
        
        headers = config.get('headers', {})
        timeout = config.get('timeout', 10)
        
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
    
    def _send_webhook_resolution(self, alert: Alert, channel: NotificationChannel):
        """Send webhook resolution notification"""
        import requests
        
        config = channel.config
        url = config.get('url')
        
        if not url:
            return
        
        payload = {
            'alert': {
                'rule_name': alert.rule_name,
                'severity': alert.severity.value,
                'message': alert.message,
                'status': 'resolved',
                'fired_at': alert.fired_at,
                'resolved_at': alert.resolved_at,
                'labels': alert.labels,
                'annotations': alert.annotations
            }
        }
        
        headers = config.get('headers', {})
        timeout = config.get('timeout', 10)
        
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
    
    def _send_command_notification(self, alert: Alert, channel: NotificationChannel):
        """Send notification via command execution"""
        config = channel.config
        command = config.get('command')
        
        if not command:
            raise ValueError("Command not configured")
        
        # Prepare environment variables with alert data
        env = {
            'ALERT_RULE_NAME': alert.rule_name,
            'ALERT_SEVERITY': alert.severity.value,
            'ALERT_MESSAGE': alert.message,
            'ALERT_STATUS': alert.status.value,
            'ALERT_FIRED_AT': str(alert.fired_at),
            'ALERT_LABELS': json.dumps(alert.labels),
            'ALERT_ANNOTATIONS': json.dumps(alert.annotations)
        }
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            env={**os.environ, **env},
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {result.stderr}")
    
    def _send_command_resolution(self, alert: Alert, channel: NotificationChannel):
        """Send resolution notification via command execution"""
        config = channel.config
        command = config.get('resolution_command', config.get('command'))
        
        if not command:
            return
        
        # Prepare environment variables
        env = {
            'ALERT_RULE_NAME': alert.rule_name,
            'ALERT_SEVERITY': alert.severity.value,
            'ALERT_MESSAGE': alert.message,
            'ALERT_STATUS': 'resolved',
            'ALERT_FIRED_AT': str(alert.fired_at),
            'ALERT_RESOLVED_AT': str(alert.resolved_at or time.time()),
            'ALERT_LABELS': json.dumps(alert.labels),
            'ALERT_ANNOTATIONS': json.dumps(alert.annotations)
        }
        
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            env={**os.environ, **env},
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            self.logger.warning(f"Resolution command failed: {result.stderr}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        with self._alerts_lock:
            return [alert for alert in self._active_alerts.values() 
                   if alert.status == AlertStatus.FIRING]
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history"""
        with self._alerts_lock:
            return self._alert_history[-limit:]
    
    def silence_alert(self, rule_name: str, metric_key: str, duration_seconds: int):
        """Silence an alert for specified duration"""
        alert_id = f"{rule_name}:{metric_key}"
        
        with self._alerts_lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                alert.status = AlertStatus.SILENCED
                alert.silenced_until = time.time() + duration_seconds
                
                self.logger.info(f"Silenced alert {alert_id} for {duration_seconds} seconds")
                return True
        
        return False
    
    def unsilence_alert(self, rule_name: str, metric_key: str):
        """Remove silence from an alert"""
        alert_id = f"{rule_name}:{metric_key}"
        
        with self._alerts_lock:
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]
                if alert.status == AlertStatus.SILENCED:
                    alert.status = AlertStatus.FIRING
                    alert.silenced_until = None
                    
                    self.logger.info(f"Unsilenced alert {alert_id}")
                    return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get alert manager statistics"""
        with self._alerts_lock:
            return {
                **self.stats,
                'rules_count': len(self._rules),
                'enabled_rules': len([r for r in self._rules.values() if r.enabled]),
                'notification_channels': len(self._notification_channels),
                'active_alerts_current': len([a for a in self._active_alerts.values() 
                                            if a.status == AlertStatus.FIRING])
            }
    
    def start_evaluation(self, interval: float = 30.0):
        """Start background alert evaluation"""
        if self._evaluation_active:
            return
        
        self._evaluation_interval = interval
        self._evaluation_active = True
        
        self._evaluation_thread = threading.Thread(
            target=self._evaluation_loop,
            name='alert-evaluator',
            daemon=True
        )
        self._evaluation_thread.start()
        
        self.logger.info(f"Started alert evaluation (interval: {interval}s)")
    
    def stop_evaluation(self):
        """Stop background alert evaluation"""
        if not self._evaluation_active:
            return
        
        self._evaluation_active = False
        
        if self._evaluation_thread and self._evaluation_thread.is_alive():
            self._evaluation_thread.join(timeout=5)
        
        self.logger.info("Stopped alert evaluation")
    
    def _evaluation_loop(self):
        """Background evaluation loop"""
        while self._evaluation_active:
            try:
                # This would integrate with metrics collector
                # For now, skip actual evaluation
                self.logger.debug("Alert evaluation cycle (metrics integration needed)")
                
                # Check for silenced alerts that should be unsilenced
                current_time = time.time()
                with self._alerts_lock:
                    for alert in self._active_alerts.values():
                        if (alert.status == AlertStatus.SILENCED and 
                            alert.silenced_until and 
                            current_time >= alert.silenced_until):
                            alert.status = AlertStatus.FIRING
                            alert.silenced_until = None
                
                time.sleep(self._evaluation_interval)
                
            except Exception as e:
                self.logger.error(f"Error in alert evaluation loop: {e}")
                time.sleep(self._evaluation_interval)


# Global alert manager instance
_alert_manager = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager