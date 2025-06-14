"""
Log analysis system for BlastDock deployments
"""

import re
import time
import json
import os
from typing import Dict, List, Any, Optional, Tuple, Pattern
from dataclasses import dataclass, field
from collections import defaultdict, Counter
from enum import Enum

from ..utils.logging import get_logger
from ..utils.docker_utils import DockerClient

logger = get_logger(__name__)


class LogLevel(Enum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"


@dataclass
class LogEntry:
    """Parsed log entry"""
    timestamp: float
    level: LogLevel
    message: str
    source: str
    container: str
    project: str
    raw_line: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogPattern:
    """Log pattern for analysis"""
    name: str
    pattern: Pattern[str]
    level: LogLevel
    description: str
    severity: int  # 1-10, 10 being most severe
    action: Optional[str] = None


@dataclass
class LogAnalysisResult:
    """Result of log analysis"""
    project_name: str
    analysis_time: float
    total_lines: int
    parsed_lines: int
    error_count: int
    warning_count: int
    patterns_found: Dict[str, int]
    top_errors: List[Dict[str, Any]]
    recommendations: List[str]
    timeline: List[Dict[str, Any]]


class LogAnalyzer:
    """Advanced log analysis system"""
    
    def __init__(self):
        """Initialize log analyzer"""
        self.logger = get_logger(__name__)
        self.docker_client = DockerClient()
        
        # Predefined log patterns
        self._patterns = self._initialize_patterns()
        
        # Analysis cache
        self._analysis_cache: Dict[str, LogAnalysisResult] = {}
        self._cache_ttl = 300  # 5 minutes
        
        self.logger.debug("Log analyzer initialized")
    
    def _initialize_patterns(self) -> List[LogPattern]:
        """Initialize common log patterns"""
        patterns = [
            # Error patterns
            LogPattern(
                name="database_connection_error",
                pattern=re.compile(r"(database|db|sql).*(connection|connect).*(error|failed|timeout)", re.IGNORECASE),
                level=LogLevel.ERROR,
                description="Database connection issues",
                severity=8,
                action="Check database availability and connection settings"
            ),
            LogPattern(
                name="out_of_memory",
                pattern=re.compile(r"(out of memory|oom|memory.*(allocation|limit))", re.IGNORECASE),
                level=LogLevel.FATAL,
                description="Out of memory errors",
                severity=10,
                action="Increase memory limits or optimize memory usage"
            ),
            LogPattern(
                name="permission_denied",
                pattern=re.compile(r"permission.*(denied|error)|access.*(denied|forbidden)", re.IGNORECASE),
                level=LogLevel.ERROR,
                description="Permission and access errors",
                severity=7,
                action="Check file permissions and user access rights"
            ),
            LogPattern(
                name="network_timeout",
                pattern=re.compile(r"(network|connection|socket).*(timeout|timed out)", re.IGNORECASE),
                level=LogLevel.WARN,
                description="Network timeout issues",
                severity=6,
                action="Check network connectivity and timeout settings"
            ),
            LogPattern(
                name="disk_space_full",
                pattern=re.compile(r"(disk|space|filesystem).*(full|no space)", re.IGNORECASE),
                level=LogLevel.FATAL,
                description="Disk space issues",
                severity=9,
                action="Free up disk space or increase storage"
            ),
            LogPattern(
                name="ssl_certificate_error",
                pattern=re.compile(r"(ssl|tls|certificate).*(error|invalid|expired)", re.IGNORECASE),
                level=LogLevel.ERROR,
                description="SSL/TLS certificate issues",
                severity=7,
                action="Check and renew SSL certificates"
            ),
            
            # Warning patterns
            LogPattern(
                name="deprecated_api",
                pattern=re.compile(r"deprecated|deprecation", re.IGNORECASE),
                level=LogLevel.WARN,
                description="Deprecated API usage",
                severity=4,
                action="Update to use current API versions"
            ),
            LogPattern(
                name="slow_query",
                pattern=re.compile(r"(slow|long).*(query|request)|query.*slow", re.IGNORECASE),
                level=LogLevel.WARN,
                description="Slow database queries",
                severity=5,
                action="Optimize database queries and indexes"
            ),
            LogPattern(
                name="retry_attempt",
                pattern=re.compile(r"retrying|retry.*attempt|attempting.*retry", re.IGNORECASE),
                level=LogLevel.WARN,
                description="Retry attempts",
                severity=3,
                action="Investigate root cause of failures requiring retries"
            ),
            
            # Info patterns
            LogPattern(
                name="startup_complete",
                pattern=re.compile(r"(started|startup|ready|listening).*(on|port|server)", re.IGNORECASE),
                level=LogLevel.INFO,
                description="Service startup completion",
                severity=1,
                action=None
            ),
            LogPattern(
                name="user_login",
                pattern=re.compile(r"(user|login|authentication).*(success|logged in)", re.IGNORECASE),
                level=LogLevel.INFO,
                description="User authentication events",
                severity=1,
                action=None
            ),
            
            # Performance patterns
            LogPattern(
                name="high_response_time",
                pattern=re.compile(r"response.*time.*[0-9]+\s*[ms|sec].*[5-9][0-9][0-9][0-9]", re.IGNORECASE),
                level=LogLevel.WARN,
                description="High response times",
                severity=6,
                action="Investigate performance bottlenecks"
            ),
            LogPattern(
                name="thread_pool_exhaustion",
                pattern=re.compile(r"(thread|pool).*(exhausted|full|limit)", re.IGNORECASE),
                level=LogLevel.ERROR,
                description="Thread pool exhaustion",
                severity=8,
                action="Increase thread pool size or optimize processing"
            )
        ]
        
        return patterns
    
    def analyze_project_logs(self, project_name: str, tail_lines: int = 1000, 
                           time_window_hours: int = 24) -> LogAnalysisResult:
        """Analyze logs for a project"""
        cache_key = f"{project_name}:{tail_lines}:{time_window_hours}"
        
        # Check cache
        if cache_key in self._analysis_cache:
            cached_result = self._analysis_cache[cache_key]
            if time.time() - cached_result.analysis_time < self._cache_ttl:
                return cached_result
        
        start_time = time.time()
        
        try:
            # Get container logs
            containers = self.docker_client.get_container_status(project_name)
            if not containers:
                return LogAnalysisResult(
                    project_name=project_name,
                    analysis_time=start_time,
                    total_lines=0,
                    parsed_lines=0,
                    error_count=0,
                    warning_count=0,
                    patterns_found={},
                    top_errors=[],
                    recommendations=[],
                    timeline=[]
                )
            
            all_logs = []
            total_lines = 0
            
            # Collect logs from all containers
            for container in containers:
                container_name = container['name']
                try:
                    # Get logs for container
                    logs = self.docker_client.get_container_logs(
                        container_name, 
                        tail=tail_lines // len(containers)  # Distribute lines across containers
                    )
                    
                    if logs:
                        log_lines = logs.strip().split('\n')
                        for line in log_lines:
                            if line.strip():
                                parsed_entry = self._parse_log_line(
                                    line, container_name, project_name
                                )
                                if parsed_entry:
                                    all_logs.append(parsed_entry)
                                total_lines += 1
                
                except Exception as e:
                    self.logger.warning(f"Failed to get logs for container {container_name}: {e}")
            
            # Sort logs by timestamp
            all_logs.sort(key=lambda x: x.timestamp)
            
            # Filter by time window
            cutoff_time = time.time() - (time_window_hours * 3600)
            filtered_logs = [log for log in all_logs if log.timestamp >= cutoff_time]
            
            # Analyze logs
            analysis_result = self._analyze_log_entries(
                filtered_logs, project_name, start_time, total_lines
            )
            
            # Cache result
            self._analysis_cache[cache_key] = analysis_result
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing logs for {project_name}: {e}")
            return LogAnalysisResult(
                project_name=project_name,
                analysis_time=start_time,
                total_lines=0,
                parsed_lines=0,
                error_count=0,
                warning_count=0,
                patterns_found={},
                top_errors=[],
                recommendations=[f"Log analysis failed: {str(e)}"],
                timeline=[]
            )
    
    def _parse_log_line(self, line: str, container_name: str, project_name: str) -> Optional[LogEntry]:
        """Parse a single log line"""
        try:
            # Try to extract timestamp
            timestamp = self._extract_timestamp(line)
            if timestamp is None:
                timestamp = time.time()  # Use current time if no timestamp found
            
            # Try to extract log level
            level = self._extract_log_level(line)
            
            # Extract message (remove timestamp and level if present)
            message = self._clean_message(line)
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source=container_name,
                container=container_name,
                project=project_name,
                raw_line=line
            )
            
        except Exception as e:
            self.logger.debug(f"Failed to parse log line: {e}")
            return None
    
    def _extract_timestamp(self, line: str) -> Optional[float]:
        """Extract timestamp from log line"""
        # Common timestamp patterns
        timestamp_patterns = [
            # ISO format: 2023-12-01T10:30:45.123Z
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?)',
            # Docker format: 2023-12-01 10:30:45
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            # Syslog format: Dec  1 10:30:45
            r'([A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})',
            # Unix timestamp: [1701427845.123]
            r'\[(\d{10}(?:\.\d{3})?)\]'
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                timestamp_str = match.group(1)
                try:
                    # Try different parsing methods
                    if 'T' in timestamp_str:
                        # ISO format
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        return dt.timestamp()
                    elif '-' in timestamp_str and ' ' in timestamp_str:
                        # YYYY-MM-DD HH:MM:SS format
                        from datetime import datetime
                        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        return dt.timestamp()
                    elif timestamp_str.replace('.', '').isdigit():
                        # Unix timestamp
                        return float(timestamp_str)
                except Exception:
                    continue
        
        return None
    
    def _extract_log_level(self, line: str) -> LogLevel:
        """Extract log level from log line"""
        line_upper = line.upper()
        
        # Common log level patterns
        if re.search(r'\b(FATAL|CRIT|CRITICAL)\b', line_upper):
            return LogLevel.FATAL
        elif re.search(r'\b(ERROR|ERR)\b', line_upper):
            return LogLevel.ERROR
        elif re.search(r'\b(WARN|WARNING)\b', line_upper):
            return LogLevel.WARN
        elif re.search(r'\b(INFO|INFORMATION)\b', line_upper):
            return LogLevel.INFO
        elif re.search(r'\b(DEBUG|DBG)\b', line_upper):
            return LogLevel.DEBUG
        elif re.search(r'\b(TRACE|TRC)\b', line_upper):
            return LogLevel.TRACE
        else:
            # Default to INFO if no level found
            return LogLevel.INFO
    
    def _clean_message(self, line: str) -> str:
        """Clean log message by removing timestamp and level prefixes"""
        # Remove common prefixes
        cleaned = line
        
        # Remove timestamps
        cleaned = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?\s*', '', cleaned)
        cleaned = re.sub(r'[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s*', '', cleaned)
        cleaned = re.sub(r'\[\d{10}(?:\.\d{3})?\]\s*', '', cleaned)
        
        # Remove log levels
        cleaned = re.sub(r'\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|ERR|FATAL|CRIT|CRITICAL)\b:?\s*', '', cleaned, flags=re.IGNORECASE)
        
        # Remove Docker container prefixes
        cleaned = re.sub(r'^\w+\s*\|\s*', '', cleaned)
        
        return cleaned.strip()
    
    def _analyze_log_entries(self, log_entries: List[LogEntry], project_name: str,
                           analysis_time: float, total_lines: int) -> LogAnalysisResult:
        """Analyze parsed log entries"""
        parsed_lines = len(log_entries)
        error_count = sum(1 for log in log_entries if log.level == LogLevel.ERROR)
        warning_count = sum(1 for log in log_entries if log.level == LogLevel.WARN)
        
        # Pattern matching
        patterns_found = defaultdict(int)
        matched_patterns = []
        
        for log_entry in log_entries:
            for pattern in self._patterns:
                if pattern.pattern.search(log_entry.message):
                    patterns_found[pattern.name] += 1
                    matched_patterns.append((log_entry, pattern))
        
        # Top errors analysis
        error_messages = [log.message for log in log_entries if log.level in [LogLevel.ERROR, LogLevel.FATAL]]
        error_counter = Counter(error_messages)
        top_errors = [
            {
                'message': msg,
                'count': count,
                'percentage': (count / len(error_messages) * 100) if error_messages else 0
            }
            for msg, count in error_counter.most_common(10)
        ]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(patterns_found, matched_patterns)
        
        # Create timeline
        timeline = self._create_timeline(log_entries)
        
        return LogAnalysisResult(
            project_name=project_name,
            analysis_time=analysis_time,
            total_lines=total_lines,
            parsed_lines=parsed_lines,
            error_count=error_count,
            warning_count=warning_count,
            patterns_found=dict(patterns_found),
            top_errors=top_errors,
            recommendations=recommendations,
            timeline=timeline
        )
    
    def _generate_recommendations(self, patterns_found: Dict[str, int], 
                                matched_patterns: List[Tuple[LogEntry, LogPattern]]) -> List[str]:
        """Generate recommendations based on log analysis"""
        recommendations = []
        
        # High severity patterns
        high_severity_patterns = [
            (pattern, count) for pattern_name, count in patterns_found.items()
            for pattern in self._patterns if pattern.name == pattern_name and pattern.severity >= 7
        ]
        
        for pattern, count in high_severity_patterns:
            if pattern.action:
                recommendations.append(f"{pattern.action} (found {count} occurrences)")
        
        # Frequent error patterns
        frequent_patterns = [(name, count) for name, count in patterns_found.items() if count >= 5]
        for pattern_name, count in frequent_patterns:
            pattern = next((p for p in self._patterns if p.name == pattern_name), None)
            if pattern and pattern.action and pattern.action not in [r.split(' (')[0] for r in recommendations]:
                recommendations.append(f"{pattern.action} (frequent issue: {count} occurrences)")
        
        # General recommendations based on patterns
        if patterns_found.get('database_connection_error', 0) > 0:
            recommendations.append("Consider implementing database connection pooling and retry logic")
        
        if patterns_found.get('out_of_memory', 0) > 0:
            recommendations.append("Increase container memory limits and implement memory profiling")
        
        if patterns_found.get('network_timeout', 0) > 0:
            recommendations.append("Review network configuration and implement proper timeout handling")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _create_timeline(self, log_entries: List[LogEntry]) -> List[Dict[str, Any]]:
        """Create timeline of significant events"""
        timeline = []
        
        # Group logs by hour
        hourly_stats = defaultdict(lambda: {'errors': 0, 'warnings': 0, 'info': 0, 'events': []})
        
        for log_entry in log_entries:
            hour_key = int(log_entry.timestamp // 3600) * 3600  # Round to hour
            
            if log_entry.level == LogLevel.ERROR:
                hourly_stats[hour_key]['errors'] += 1
            elif log_entry.level == LogLevel.WARN:
                hourly_stats[hour_key]['warnings'] += 1
            else:
                hourly_stats[hour_key]['info'] += 1
            
            # Track significant events
            for pattern in self._patterns:
                if pattern.severity >= 7 and pattern.pattern.search(log_entry.message):
                    hourly_stats[hour_key]['events'].append({
                        'pattern': pattern.name,
                        'message': log_entry.message[:100],  # Truncate
                        'container': log_entry.container,
                        'timestamp': log_entry.timestamp
                    })
        
        # Convert to timeline format
        for hour_timestamp, stats in sorted(hourly_stats.items()):
            timeline.append({
                'timestamp': hour_timestamp,
                'hour': time.strftime('%H:00', time.localtime(hour_timestamp)),
                'date': time.strftime('%Y-%m-%d', time.localtime(hour_timestamp)),
                'errors': stats['errors'],
                'warnings': stats['warnings'],
                'info': stats['info'],
                'significant_events': stats['events'][:5]  # Top 5 events per hour
            })
        
        return timeline[-24:]  # Last 24 hours
    
    def get_real_time_analysis(self, project_name: str, container_name: str = None) -> Dict[str, Any]:
        """Get real-time log analysis"""
        try:
            # Get recent logs (last 100 lines)
            if container_name:
                containers = [{'name': container_name}]
            else:
                containers = self.docker_client.get_container_status(project_name)
            
            recent_logs = []
            
            for container in containers:
                try:
                    logs = self.docker_client.get_container_logs(container['name'], tail=100)
                    if logs:
                        log_lines = logs.strip().split('\n')[-10:]  # Last 10 lines per container
                        for line in log_lines:
                            if line.strip():
                                parsed_entry = self._parse_log_line(
                                    line, container['name'], project_name
                                )
                                if parsed_entry:
                                    recent_logs.append(parsed_entry)
                except Exception as e:
                    self.logger.debug(f"Failed to get recent logs for {container['name']}: {e}")
            
            # Sort by timestamp
            recent_logs.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Quick analysis
            error_count = sum(1 for log in recent_logs if log.level == LogLevel.ERROR)
            warning_count = sum(1 for log in recent_logs if log.level == LogLevel.WARN)
            
            # Check for immediate issues
            critical_patterns = []
            for log_entry in recent_logs:
                for pattern in self._patterns:
                    if pattern.severity >= 8 and pattern.pattern.search(log_entry.message):
                        critical_patterns.append({
                            'pattern': pattern.name,
                            'description': pattern.description,
                            'message': log_entry.message,
                            'container': log_entry.container,
                            'timestamp': log_entry.timestamp
                        })
            
            return {
                'project_name': project_name,
                'timestamp': time.time(),
                'recent_logs_count': len(recent_logs),
                'recent_errors': error_count,
                'recent_warnings': warning_count,
                'critical_issues': critical_patterns,
                'latest_entries': [
                    {
                        'timestamp': log.timestamp,
                        'level': log.level.value,
                        'message': log.message[:200],  # Truncate
                        'container': log.container
                    }
                    for log in recent_logs[:5]
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error in real-time analysis: {e}")
            return {
                'project_name': project_name,
                'timestamp': time.time(),
                'error': str(e)
            }
    
    def add_custom_pattern(self, pattern: LogPattern):
        """Add custom log pattern"""
        self._patterns.append(pattern)
        self.logger.info(f"Added custom log pattern: {pattern.name}")
    
    def export_analysis(self, result: LogAnalysisResult, format: str = 'json') -> str:
        """Export analysis result"""
        if format.lower() == 'json':
            return json.dumps({
                'project_name': result.project_name,
                'analysis_time': result.analysis_time,
                'total_lines': result.total_lines,
                'parsed_lines': result.parsed_lines,
                'error_count': result.error_count,
                'warning_count': result.warning_count,
                'patterns_found': result.patterns_found,
                'top_errors': result.top_errors,
                'recommendations': result.recommendations,
                'timeline': result.timeline
            }, indent=2)
        else:
            # Plain text format
            lines = [
                f"Log Analysis Report for {result.project_name}",
                f"Analysis Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(result.analysis_time))}",
                f"Total Lines: {result.total_lines}",
                f"Parsed Lines: {result.parsed_lines}",
                f"Errors: {result.error_count}",
                f"Warnings: {result.warning_count}",
                "",
                "Patterns Found:",
                *[f"  {name}: {count}" for name, count in result.patterns_found.items()],
                "",
                "Recommendations:",
                *[f"  • {rec}" for rec in result.recommendations],
                "",
                "Top Errors:",
                *[f"  {err['message']} ({err['count']} times)" for err in result.top_errors[:5]]
            ]
            return '\n'.join(lines)


# Global log analyzer instance
_log_analyzer = None


def get_log_analyzer() -> LogAnalyzer:
    """Get global log analyzer instance"""
    global _log_analyzer
    if _log_analyzer is None:
        _log_analyzer = LogAnalyzer()
    return _log_analyzer