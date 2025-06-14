"""
Template security scanner for BlastDock templates
"""

import os
import re
import yaml
from typing import Dict, List, Optional, Tuple, Any, Set
from pathlib import Path

from ..utils.logging import get_logger
from ..exceptions import SecurityError, TemplateError
from .validator import get_security_validator


logger = get_logger(__name__)


class TemplateSecurityScanner:
    """Security scanner for BlastDock templates"""
    
    def __init__(self):
        """Initialize template security scanner"""
        self.logger = get_logger(__name__)
        self.security_validator = get_security_validator()
        
        # Dangerous patterns in templates
        self.DANGEROUS_PATTERNS = [
            # Code injection
            r'eval\s*\(',
            r'exec\s*\(',
            r'system\s*\(',
            r'subprocess\.',
            r'os\.system',
            r'__import__',
            
            # Shell injection
            r'\$\([^)]*\)',  # Command substitution
            r'`[^`]*`',      # Backticks
            r';\s*\w+',      # Command chaining
            r'\|\s*\w+',     # Piping
            
            # Path traversal
            r'\.\./',
            r'\.\.\\',
            
            # Network access
            r'wget\s+',
            r'curl\s+',
            r'nc\s+',
            r'netcat\s+',
            
            # Privilege escalation
            r'sudo\s+',
            r'su\s+',
            r'chmod\s+777',
            r'chown\s+root',
        ]
        
        # Sensitive environment variables
        self.SENSITIVE_ENV_PATTERNS = [
            r'password', r'secret', r'key', r'token', r'api_key',
            r'private_key', r'cert', r'credential', r'auth'
        ]
        
        # Dangerous Docker configurations
        self.DANGEROUS_DOCKER_CONFIGS = [
            'privileged', 'user: root', 'user: "root"', "user: 'root'",
            'network_mode: host', 'pid: host', 'ipc: host',
            'cap_add:', 'security_opt:', 'devices:'
        ]
    
    def scan_template(self, template_path: str) -> Dict[str, Any]:
        """Scan a template for security issues"""
        if not os.path.exists(template_path):
            return {
                'template_path': template_path,
                'accessible': False,
                'error': 'Template path does not exist'
            }
        
        try:
            # Determine if it's a directory or file
            if os.path.isdir(template_path):
                return self._scan_template_directory(template_path)
            else:
                return self._scan_template_file(template_path)
                
        except Exception as e:
            return {
                'template_path': template_path,
                'accessible': False,
                'error': f'Failed to scan template: {e}'
            }
    
    def _scan_template_directory(self, template_dir: str) -> Dict[str, Any]:
        """Scan all files in a template directory"""
        security_issues = []
        security_score = 100
        files_scanned = 0
        
        # Scan all YAML/template files
        for root, dirs, files in os.walk(template_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_ext = Path(file).suffix.lower()
                
                # Only scan relevant files
                if file_ext in {'.yml', '.yaml', '.json', '.j2', '.jinja'}:
                    files_scanned += 1
                    file_result = self._scan_template_file(file_path)
                    
                    if file_result.get('security_issues'):
                        for issue in file_result['security_issues']:
                            issue['file'] = os.path.relpath(file_path, template_dir)
                            security_issues.append(issue)
                    
                    # Adjust score based on file results
                    file_score = file_result.get('security_score', 100)
                    if file_score < 100:
                        security_score = min(security_score, file_score)
        
        # Check for required files
        required_files = ['docker-compose.yml', 'docker-compose.yaml']
        has_compose = any(os.path.exists(os.path.join(template_dir, f)) for f in required_files)
        
        if not has_compose:
            security_issues.append({
                'severity': 'medium',
                'issue': 'No docker-compose file found',
                'description': 'Template should include docker-compose configuration',
                'recommendation': 'Add docker-compose.yml file'
            })
            security_score -= 10
        
        return {
            'template_path': template_dir,
            'accessible': True,
            'security_score': max(0, security_score),
            'security_issues': security_issues,
            'files_scanned': files_scanned,
            'scan_type': 'directory'
        }
    
    def _scan_template_file(self, file_path: str) -> Dict[str, Any]:
        """Scan a single template file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {
                'template_path': file_path,
                'accessible': False,
                'error': f'Cannot read file: {e}'
            }
        
        security_issues = []
        security_score = 100
        
        # Check file content for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                security_issues.append({
                    'severity': 'high',
                    'issue': f'Dangerous pattern detected: {pattern}',
                    'description': f'Found {len(matches)} occurrence(s) of potentially dangerous code',
                    'recommendation': 'Review and remove dangerous patterns',
                    'matches': matches[:5]  # Show first 5 matches
                })
                security_score -= 25
        
        # Parse as YAML if possible
        file_ext = Path(file_path).suffix.lower()
        if file_ext in {'.yml', '.yaml'}:
            yaml_result = self._scan_yaml_content(content)
            security_issues.extend(yaml_result['issues'])
            security_score = min(security_score, yaml_result['score'])
        
        # Check for hardcoded secrets
        secret_issues = self._check_hardcoded_secrets(content)
        security_issues.extend(secret_issues)
        if secret_issues:
            security_score -= len(secret_issues) * 15
        
        # Check file permissions
        perm_valid, perm_error = self.security_validator.check_file_permissions(file_path)
        if not perm_valid:
            security_issues.append({
                'severity': 'medium',
                'issue': f'Insecure file permissions: {perm_error}',
                'description': 'File has potentially insecure permissions',
                'recommendation': 'Fix file permissions'
            })
            security_score -= 10
        
        return {
            'template_path': file_path,
            'accessible': True,
            'security_score': max(0, security_score),
            'security_issues': security_issues,
            'scan_type': 'file'
        }
    
    def _scan_yaml_content(self, content: str) -> Dict[str, Any]:
        """Scan YAML content for security issues"""
        issues = []
        score = 100
        
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return {
                'issues': [{
                    'severity': 'high',
                    'issue': f'Invalid YAML syntax: {e}',
                    'description': 'YAML parsing failed',
                    'recommendation': 'Fix YAML syntax errors'
                }],
                'score': 50
            }
        
        if not data:
            return {'issues': [], 'score': 100}
        
        # Check for Docker Compose specific issues
        if isinstance(data, dict) and 'services' in data:
            compose_issues = self._check_docker_compose_security(data)
            issues.extend(compose_issues)
            if compose_issues:
                score -= len(compose_issues) * 10
        
        # Check for YAML bomb patterns
        yaml_str = yaml.dump(data)
        if self._check_yaml_bomb(yaml_str):
            issues.append({
                'severity': 'critical',
                'issue': 'Potential YAML bomb detected',
                'description': 'YAML contains patterns that could cause resource exhaustion',
                'recommendation': 'Remove recursive references and excessive nesting'
            })
            score -= 40
        
        return {'issues': issues, 'score': score}
    
    def _check_docker_compose_security(self, compose_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check Docker Compose configuration for security issues"""
        issues = []
        services = compose_data.get('services', {})
        
        for service_name, service_config in services.items():
            if not isinstance(service_config, dict):
                continue
            
            # Check for dangerous configurations
            for config in self.DANGEROUS_DOCKER_CONFIGS:
                if config in str(service_config).lower():
                    issues.append({
                        'severity': 'high',
                        'issue': f'Dangerous Docker configuration in service {service_name}: {config}',
                        'description': 'This configuration poses security risks',
                        'recommendation': 'Review and secure Docker configuration'
                    })
            
            # Check bind mounts
            volumes = service_config.get('volumes', [])
            for volume in volumes:
                if isinstance(volume, str) and ':' in volume:
                    host_path = volume.split(':')[0]
                    if any(dangerous in host_path for dangerous in 
                           ['/var/run/docker.sock', '/dev', '/proc', '/sys']):
                        issues.append({
                            'severity': 'critical',
                            'issue': f'Dangerous bind mount in service {service_name}: {host_path}',
                            'description': 'Mount provides access to sensitive host resources',
                            'recommendation': 'Use named volumes instead of bind mounts'
                        })
            
            # Check for exposed secrets
            env_vars = service_config.get('environment', [])
            if isinstance(env_vars, dict):
                for env_name, env_value in env_vars.items():
                    if self._is_potential_secret(env_name, str(env_value)):
                        issues.append({
                            'severity': 'high',
                            'issue': f'Potential hardcoded secret in service {service_name}: {env_name}',
                            'description': 'Environment variable may contain sensitive data',
                            'recommendation': 'Use Docker secrets or external configuration'
                        })
        
        return issues
    
    def _check_hardcoded_secrets(self, content: str) -> List[Dict[str, Any]]:
        """Check for hardcoded secrets in content"""
        issues = []
        
        # Common secret patterns
        secret_patterns = [
            (r'password\s*[:=]\s*["\']?[\w@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`!]+["\']?', 'password'),
            (r'api_key\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', 'API key'),
            (r'secret_key\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', 'secret key'),
            (r'token\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', 'token'),
            (r'private_key\s*[:=]\s*["\']?-----BEGIN', 'private key'),
        ]
        
        for pattern, secret_type in secret_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                issues.append({
                    'severity': 'high',
                    'issue': f'Potential hardcoded {secret_type} detected',
                    'description': f'Found {len(matches)} occurrence(s) of potential {secret_type}',
                    'recommendation': f'Move {secret_type} to environment variables or secrets management'
                })
        
        return issues
    
    def _is_potential_secret(self, name: str, value: str) -> bool:
        """Check if an environment variable contains a potential secret"""
        name_lower = name.lower()
        
        # Check if name suggests it's a secret
        for pattern in self.SENSITIVE_ENV_PATTERNS:
            if pattern in name_lower:
                # Check if value looks like a secret (not a placeholder)
                if (len(value) > 8 and 
                    not value.startswith('${') and 
                    not value.startswith('{{') and
                    value not in ['changeme', 'secret', 'password', 'example']):
                    return True
        
        return False
    
    def _check_yaml_bomb(self, yaml_content: str) -> bool:
        """Check for YAML bomb patterns"""
        # Look for patterns that indicate YAML bombs
        yaml_bomb_patterns = [
            r'&\w+\s*\[\s*\*\w+',  # Anchor references
            r'\*\w+\s*,\s*\*\w+',  # Multiple references  
        ]
        
        for pattern in yaml_bomb_patterns:
            if re.search(pattern, yaml_content):
                return True
        
        # Check for excessive nesting or repetition
        if yaml_content.count('*') > 10:  # Too many references
            return True
        
        if yaml_content.count('&') > 5:   # Too many anchors
            return True
        
        return False
    
    def scan_all_templates(self, templates_dir: str) -> Dict[str, Any]:
        """Scan all templates in a directory"""
        if not os.path.exists(templates_dir):
            return {
                'templates_dir': templates_dir,
                'accessible': False,
                'error': 'Templates directory does not exist'
            }
        
        templates_scanned = 0
        templates_with_issues = 0
        all_issues = []
        total_score = 0
        
        try:
            for item in os.listdir(templates_dir):
                template_path = os.path.join(templates_dir, item)
                
                if os.path.isdir(template_path):
                    templates_scanned += 1
                    result = self.scan_template(template_path)
                    
                    if result.get('security_issues'):
                        templates_with_issues += 1
                        # Add template name to each issue
                        for issue in result['security_issues']:
                            issue['template'] = item
                            all_issues.append(issue)
                    
                    total_score += result.get('security_score', 0)
        
        except Exception as e:
            return {
                'templates_dir': templates_dir,
                'accessible': False,
                'error': f'Failed to scan templates: {e}'
            }
        
        average_score = total_score / max(templates_scanned, 1)
        
        # Categorize issues by severity
        critical_issues = [i for i in all_issues if i.get('severity') == 'critical']
        high_issues = [i for i in all_issues if i.get('severity') == 'high']
        medium_issues = [i for i in all_issues if i.get('severity') == 'medium']
        low_issues = [i for i in all_issues if i.get('severity') == 'low']
        
        return {
            'templates_dir': templates_dir,
            'accessible': True,
            'templates_scanned': templates_scanned,
            'templates_with_issues': templates_with_issues,
            'average_security_score': round(average_score, 1),
            'total_issues': len(all_issues),
            'issues_by_severity': {
                'critical': len(critical_issues),
                'high': len(high_issues),
                'medium': len(medium_issues),
                'low': len(low_issues)
            },
            'all_issues': all_issues,
            'summary': self._generate_security_summary(all_issues, templates_scanned)
        }
    
    def _generate_security_summary(self, issues: List[Dict[str, Any]], templates_count: int) -> List[str]:
        """Generate security summary recommendations"""
        summary = []
        
        if not issues:
            summary.append("✅ No security issues found in templates")
            return summary
        
        # Count issue types
        issue_types = {}
        for issue in issues:
            issue_type = issue.get('issue', 'Unknown')
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        # Most common issues
        most_common = sorted(issue_types.items(), key=lambda x: x[1], reverse=True)[:3]
        
        summary.append(f"🔍 Found {len(issues)} security issues across {templates_count} templates")
        summary.append("📊 Most common issues:")
        
        for issue_type, count in most_common:
            summary.append(f"   • {issue_type} ({count} occurrences)")
        
        # Recommendations
        summary.append("💡 Recommendations:")
        summary.append("   • Review and fix critical and high severity issues")
        summary.append("   • Remove hardcoded secrets and credentials")
        summary.append("   • Use non-privileged containers")
        summary.append("   • Implement proper input validation")
        summary.append("   • Use secure Docker configurations")
        
        return summary
    
    def get_security_guidelines(self) -> List[str]:
        """Get template security guidelines"""
        return [
            "Use minimal base images (alpine, distroless)",
            "Run containers as non-root users",
            "Avoid privileged containers",
            "Use read-only root filesystems",
            "Don't hardcode secrets in templates",
            "Use specific image tags, not 'latest'",
            "Limit exposed ports to necessary ones",
            "Use named volumes instead of bind mounts",
            "Validate all user inputs",
            "Keep images and dependencies updated",
            "Use multi-stage builds to reduce attack surface",
            "Implement health checks for services"
        ]


# Global scanner instance
_template_security_scanner = None


def get_template_security_scanner() -> TemplateSecurityScanner:
    """Get global template security scanner instance"""
    global _template_security_scanner
    if _template_security_scanner is None:
        _template_security_scanner = TemplateSecurityScanner()
    return _template_security_scanner