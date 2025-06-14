"""
Template validation and enhancement system for BlastDock
"""

import os
import yaml
import re
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from ..constants import DOMAIN_PATTERN


class ValidationLevel(str, Enum):
    """Validation severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


class TraefikCompatibility(str, Enum):
    """Traefik compatibility levels"""
    FULL = "full"
    PARTIAL = "partial"
    BASIC = "basic"
    NONE = "none"


@dataclass
class ValidationResult:
    """Single validation result"""
    level: ValidationLevel
    category: str
    message: str
    suggestion: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class TemplateAnalysis:
    """Complete template analysis result"""
    template_name: str
    file_path: str
    is_valid: bool
    traefik_compatibility: TraefikCompatibility
    results: List[ValidationResult]
    metadata: Dict[str, Any]
    
    @property
    def error_count(self) -> int:
        return len([r for r in self.results if r.level == ValidationLevel.ERROR])
    
    @property
    def warning_count(self) -> int:
        return len([r for r in self.results if r.level == ValidationLevel.WARNING])
    
    @property
    def score(self) -> float:
        """Calculate template quality score (0-100)"""
        if not self.results:
            return 50.0
        
        errors = self.error_count
        warnings = self.warning_count
        total_checks = len(self.results)
        
        # Penalize errors heavily, warnings moderately
        penalty = (errors * 20) + (warnings * 5)
        base_score = max(0, 100 - penalty)
        
        # Bonus for Traefik compatibility
        traefik_bonus = {
            TraefikCompatibility.FULL: 20,
            TraefikCompatibility.PARTIAL: 10,
            TraefikCompatibility.BASIC: 5,
            TraefikCompatibility.NONE: 0
        }
        
        score = min(100, base_score + traefik_bonus[self.traefik_compatibility])
        return round(score, 1)


class TemplateValidator:
    """Comprehensive template validator and enhancer"""
    
    def __init__(self, templates_dir: str = None):
        """Initialize validator with templates directory"""
        if templates_dir is None:
            # Default to package templates directory
            package_dir = Path(__file__).parent.parent
            templates_dir = package_dir / 'templates'
        
        self.templates_dir = Path(templates_dir)
        self.required_sections = [
            'template_info',
            'fields',
            'compose'
        ]
        self.required_template_info = [
            'description',
            'version',
            'services'
        ]
    
    def validate_all_templates(self) -> Dict[str, TemplateAnalysis]:
        """Validate all templates in the directory"""
        results = {}
        
        for template_file in self.templates_dir.glob('*.yml'):
            if template_file.is_file():
                template_name = template_file.stem
                analysis = self.validate_template(str(template_file))
                results[template_name] = analysis
        
        return results
    
    def validate_template(self, template_path: str) -> TemplateAnalysis:
        """Validate a single template file"""
        template_path = Path(template_path)
        template_name = template_path.stem
        results = []
        metadata = {}
        
        try:
            # Load and parse YAML
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                template_data = yaml.safe_load(content)
            
            if template_data is None:
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="structure",
                    message="Template file is empty or invalid YAML"
                ))
                return TemplateAnalysis(
                    template_name=template_name,
                    file_path=str(template_path),
                    is_valid=False,
                    traefik_compatibility=TraefikCompatibility.NONE,
                    results=results,
                    metadata=metadata
                )
            
            # Validate structure
            results.extend(self._validate_structure(template_data))
            
            # Validate template info
            if 'template_info' in template_data:
                results.extend(self._validate_template_info(template_data['template_info']))
                metadata.update(template_data['template_info'])
            
            # Validate fields
            if 'fields' in template_data:
                results.extend(self._validate_fields(template_data['fields']))
            
            # Validate compose configuration
            if 'compose' in template_data:
                results.extend(self._validate_compose(template_data['compose']))
            
            # Analyze Traefik compatibility
            traefik_compatibility = self._analyze_traefik_compatibility(template_data)
            results.extend(self._validate_traefik_config(template_data, traefik_compatibility))
            
            # Validate security aspects
            results.extend(self._validate_security(template_data))
            
            # Validate performance aspects
            results.extend(self._validate_performance(template_data))
            
            # Check for common issues
            results.extend(self._check_common_issues(template_data, content))
            
            is_valid = all(r.level != ValidationLevel.ERROR for r in results)
            
            return TemplateAnalysis(
                template_name=template_name,
                file_path=str(template_path),
                is_valid=is_valid,
                traefik_compatibility=traefik_compatibility,
                results=results,
                metadata=metadata
            )
            
        except yaml.YAMLError as e:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="syntax",
                message=f"YAML syntax error: {str(e)}"
            ))
        except Exception as e:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="general",
                message=f"Validation error: {str(e)}"
            ))
        
        return TemplateAnalysis(
            template_name=template_name,
            file_path=str(template_path),
            is_valid=False,
            traefik_compatibility=TraefikCompatibility.NONE,
            results=results,
            metadata=metadata
        )
    
    def _validate_structure(self, template_data: Dict) -> List[ValidationResult]:
        """Validate basic template structure"""
        results = []
        
        for section in self.required_sections:
            if section not in template_data:
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="structure",
                    message=f"Missing required section: {section}",
                    suggestion=f"Add '{section}:' section to template"
                ))
            else:
                results.append(ValidationResult(
                    level=ValidationLevel.SUCCESS,
                    category="structure",
                    message=f"Required section '{section}' found"
                ))
        
        return results
    
    def _validate_template_info(self, template_info: Dict) -> List[ValidationResult]:
        """Validate template_info section"""
        results = []
        
        for field in self.required_template_info:
            if field not in template_info:
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="template_info",
                    message=f"Missing required field in template_info: {field}",
                    suggestion=f"Add '{field}' to template_info section"
                ))
        
        # Validate version format
        if 'version' in template_info:
            version = template_info['version']
            if not re.match(r'^\d+\.\d+(\.\d+)?$', str(version)):
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="template_info",
                    message="Version should follow semantic versioning (e.g., '1.0' or '1.0.0')",
                    suggestion="Use format like '1.0' or '1.0.0'"
                ))
        
        # Validate description
        if 'description' in template_info:
            desc = template_info['description']
            if len(desc) < 10:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="template_info",
                    message="Description is too short",
                    suggestion="Provide a more detailed description (at least 10 characters)"
                ))
            elif len(desc) > 200:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="template_info",
                    message="Description is very long",
                    suggestion="Keep description under 200 characters"
                ))
        
        # Validate services list
        if 'services' in template_info:
            services = template_info['services']
            if not isinstance(services, list) or len(services) == 0:
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="template_info",
                    message="Services must be a non-empty list",
                    suggestion="Provide list of service names"
                ))
        
        return results
    
    def _validate_fields(self, fields: Dict) -> List[ValidationResult]:
        """Validate fields section"""
        results = []
        
        for field_name, field_config in fields.items():
            if not isinstance(field_config, dict):
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="fields",
                    message=f"Field '{field_name}' must be a dictionary",
                    suggestion="Use dictionary format with 'type', 'description', etc."
                ))
                continue
            
            # Check required field properties
            if 'type' not in field_config:
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="fields",
                    message=f"Field '{field_name}' missing 'type' property",
                    suggestion="Add 'type' property (string, port, password, etc.)"
                ))
            
            if 'description' not in field_config:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="fields",
                    message=f"Field '{field_name}' missing 'description' property",
                    suggestion="Add 'description' for better user experience"
                ))
            
            # Validate field types
            valid_types = [
                'string', 'password', 'port', 'domain', 'email', 'url',
                'boolean', 'integer', 'float', 'choice', 'database_name'
            ]
            
            if 'type' in field_config:
                field_type = field_config['type']
                if field_type not in valid_types:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="fields",
                        message=f"Field '{field_name}' has unknown type '{field_type}'",
                        suggestion=f"Use one of: {', '.join(valid_types)}"
                    ))
            
            # Validate port fields
            if field_config.get('type') == 'port':
                if 'default' in field_config:
                    try:
                        port = int(field_config['default'])
                        if not (1 <= port <= 65535):
                            results.append(ValidationResult(
                                level=ValidationLevel.ERROR,
                                category="fields",
                                message=f"Field '{field_name}' has invalid port number {port}",
                                suggestion="Use port number between 1 and 65535"
                            ))
                    except (ValueError, TypeError):
                        results.append(ValidationResult(
                            level=ValidationLevel.ERROR,
                            category="fields",
                            message=f"Field '{field_name}' has non-numeric default port",
                            suggestion="Use numeric port value"
                        ))
            
            # Validate domain fields
            if field_config.get('type') == 'domain':
                if 'default' in field_config and field_config['default']:
                    domain = field_config['default']
                    if not re.match(DOMAIN_PATTERN, domain):
                        results.append(ValidationResult(
                            level=ValidationLevel.WARNING,
                            category="fields",
                            message=f"Field '{field_name}' has invalid default domain format",
                            suggestion="Use valid domain format (e.g., example.com)"
                        ))
        
        return results
    
    def _validate_compose(self, compose: Dict) -> List[ValidationResult]:
        """Validate docker-compose configuration"""
        results = []
        
        # Check version
        if 'version' not in compose:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category="compose",
                message="Docker Compose version not specified",
                suggestion="Add 'version: \"3.8\"' or newer"
            ))
        else:
            version = compose['version']
            try:
                version_num = float(version)
                if version_num < 3.0:
                    results.append(ValidationResult(
                        level=ValidationLevel.WARNING,
                        category="compose",
                        message=f"Docker Compose version {version} is outdated",
                        suggestion="Use version 3.8 or newer"
                    ))
            except (ValueError, TypeError):
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="compose",
                    message="Invalid Docker Compose version format",
                    suggestion="Use format like '3.8'"
                ))
        
        # Check services
        if 'services' not in compose:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="compose",
                message="No services defined in compose section",
                suggestion="Add 'services:' section with at least one service"
            ))
        else:
            services = compose['services']
            if not services:
                results.append(ValidationResult(
                    level=ValidationLevel.ERROR,
                    category="compose",
                    message="Services section is empty",
                    suggestion="Define at least one service"
                ))
            else:
                for service_name, service_config in services.items():
                    results.extend(self._validate_service(service_name, service_config))
        
        return results
    
    def _validate_service(self, service_name: str, service_config: Dict) -> List[ValidationResult]:
        """Validate individual service configuration"""
        results = []
        
        # Check required service properties
        if 'image' not in service_config:
            results.append(ValidationResult(
                level=ValidationLevel.ERROR,
                category="compose",
                message=f"Service '{service_name}' missing 'image' property",
                suggestion="Specify Docker image for the service"
            ))
        
        # Check for restart policy
        if 'restart' not in service_config:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category="compose",
                message=f"Service '{service_name}' missing restart policy",
                suggestion="Add 'restart: unless-stopped' for better reliability"
            ))
        
        # Check container naming
        if 'container_name' in service_config:
            container_name = service_config['container_name']
            if '{{ project_name }}' not in container_name:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="compose",
                    message=f"Service '{service_name}' container name doesn't include project name",
                    suggestion="Use '{{ project_name }}_servicename' format"
                ))
        
        # Check environment variables
        if 'environment' in service_config:
            env_vars = service_config['environment']
            if isinstance(env_vars, dict):
                for var_name, var_value in env_vars.items():
                    if 'password' in var_name.lower() and not str(var_value).startswith('{{'):
                        results.append(ValidationResult(
                            level=ValidationLevel.WARNING,
                            category="security",
                            message=f"Service '{service_name}' has hardcoded password in {var_name}",
                            suggestion="Use template variable like '{{ variable_name }}'"
                        ))
        
        return results
    
    def _analyze_traefik_compatibility(self, template_data: Dict) -> TraefikCompatibility:
        """Analyze Traefik compatibility level"""
        # Check for explicit Traefik compatibility flag
        template_info = template_data.get('template_info', {})
        if template_info.get('traefik_compatible'):
            # Check for full Traefik configuration
            if 'traefik_config' in template_data:
                return TraefikCompatibility.FULL
            
            # Check for Traefik labels in compose
            compose = template_data.get('compose', {})
            services = compose.get('services', {})
            
            has_traefik_labels = False
            has_conditional_traefik = False
            
            for service_config in services.values():
                labels = service_config.get('labels', [])
                if any('traefik' in str(label) for label in labels):
                    has_traefik_labels = True
                
                # Check for conditional Traefik configuration
                if any('{% if traefik' in str(service_config)):
                    has_conditional_traefik = True
            
            if has_traefik_labels and has_conditional_traefik:
                return TraefikCompatibility.PARTIAL
            elif has_traefik_labels:
                return TraefikCompatibility.BASIC
        
        return TraefikCompatibility.NONE
    
    def _validate_traefik_config(self, template_data: Dict, compatibility: TraefikCompatibility) -> List[ValidationResult]:
        """Validate Traefik configuration"""
        results = []
        
        if compatibility == TraefikCompatibility.NONE:
            results.append(ValidationResult(
                level=ValidationLevel.INFO,
                category="traefik",
                message="Template has no Traefik integration",
                suggestion="Consider adding Traefik support for better reverse proxy capabilities"
            ))
        elif compatibility == TraefikCompatibility.FULL:
            # Validate traefik_config section
            traefik_config = template_data.get('traefik_config', {})
            
            if 'service_port' not in traefik_config:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="traefik",
                    message="Traefik config missing 'service_port'",
                    suggestion="Specify the port Traefik should route to"
                ))
            
            # Check for security headers
            middlewares = traefik_config.get('middlewares', [])
            has_security_headers = any(
                'headers' in middleware.get('config', {})
                for middleware in middlewares
            )
            
            if not has_security_headers:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="security",
                    message="No security headers defined in Traefik middlewares",
                    suggestion="Add security headers middleware for better protection"
                ))
        
        return results
    
    def _validate_security(self, template_data: Dict) -> List[ValidationResult]:
        """Validate security aspects"""
        results = []
        
        compose = template_data.get('compose', {})
        services = compose.get('services', {})
        
        for service_name, service_config in services.items():
            # Check for privileged mode
            if service_config.get('privileged'):
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="security",
                    message=f"Service '{service_name}' runs in privileged mode",
                    suggestion="Avoid privileged mode unless absolutely necessary"
                ))
            
            # Check for host networking
            if service_config.get('network_mode') == 'host':
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="security",
                    message=f"Service '{service_name}' uses host networking",
                    suggestion="Use bridge networking with port mapping instead"
                ))
            
            # Check for volume mounts
            volumes = service_config.get('volumes', [])
            for volume in volumes:
                if isinstance(volume, str) and volume.startswith('/'):
                    if ':/etc' in volume or ':/var/run' in volume:
                        results.append(ValidationResult(
                            level=ValidationLevel.WARNING,
                            category="security",
                            message=f"Service '{service_name}' mounts sensitive system directory",
                            suggestion="Ensure this mount is necessary and secure"
                        ))
        
        return results
    
    def _validate_performance(self, template_data: Dict) -> List[ValidationResult]:
        """Validate performance aspects"""
        results = []
        
        compose = template_data.get('compose', {})
        services = compose.get('services', {})
        
        for service_name, service_config in services.items():
            # Check for resource limits
            if 'deploy' not in service_config and 'mem_limit' not in service_config:
                results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    category="performance",
                    message=f"Service '{service_name}' has no resource limits",
                    suggestion="Consider adding memory/CPU limits for better resource management"
                ))
            
            # Check for health checks
            if 'healthcheck' not in service_config:
                results.append(ValidationResult(
                    level=ValidationLevel.INFO,
                    category="performance",
                    message=f"Service '{service_name}' has no health check",
                    suggestion="Add health check for better monitoring and reliability"
                ))
        
        return results
    
    def _check_common_issues(self, template_data: Dict, content: str) -> List[ValidationResult]:
        """Check for common template issues"""
        results = []
        
        # Check for hardcoded values
        if 'localhost' in content and 'server_name' not in content:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category="portability",
                message="Template contains hardcoded 'localhost'",
                suggestion="Use template variables or make it configurable"
            ))
        
        # Check for missing template variables
        template_vars = re.findall(r'\{\{\s*(\w+)\s*\}\}', content)
        fields = template_data.get('fields', {})
        
        for var in set(template_vars):
            if var not in fields and var not in ['project_name', 'default_domain']:
                results.append(ValidationResult(
                    level=ValidationLevel.WARNING,
                    category="template",
                    message=f"Template variable '{var}' not defined in fields",
                    suggestion=f"Add '{var}' to fields section or use predefined variable"
                ))
        
        # Check for deprecated Docker Compose syntax
        if 'links:' in content:
            results.append(ValidationResult(
                level=ValidationLevel.WARNING,
                category="deprecated",
                message="Template uses deprecated 'links' syntax",
                suggestion="Use 'depends_on' instead"
            ))
        
        return results
    
    def enhance_template_traefik_support(self, template_path: str, 
                                        security_level: str = "standard",
                                        enable_rate_limiting: bool = True,
                                        enable_compression: bool = True) -> Tuple[bool, str]:
        """Enhance template with comprehensive Traefik support using advanced enhancer"""
        try:
            # Import here to avoid circular imports
            from ..performance.traefik_enhancer import get_traefik_enhancer, SecurityLevel
            
            enhancer = get_traefik_enhancer()
            
            # Convert security level string to enum
            security_enum = SecurityLevel.STANDARD
            if security_level.lower() == "minimal":
                security_enum = SecurityLevel.MINIMAL
            elif security_level.lower() == "enhanced":
                security_enum = SecurityLevel.ENHANCED
            elif security_level.lower() == "enterprise":
                security_enum = SecurityLevel.ENTERPRISE
            
            # Use advanced Traefik enhancer
            success, message, summary = enhancer.enhance_template(
                template_path, 
                security_level=security_enum,
                enable_rate_limiting=enable_rate_limiting,
                enable_compression=enable_compression
            )
            
            if success and summary:
                detailed_message = (
                    f"{message}. Enhanced {summary.get('services_analyzed', 0)} services. "
                    f"Primary service: {summary.get('primary_service', 'unknown')}. "
                    f"Security level: {security_level}."
                )
                return True, detailed_message
            
            return success, message
            
        except ImportError:
            # Fallback to basic enhancement if advanced enhancer not available
            return self._basic_traefik_enhancement(template_path)
        except Exception as e:
            return False, f"Enhancement failed: {str(e)}"
    
    def _basic_traefik_enhancement(self, template_path: str) -> Tuple[bool, str]:
        """Basic Traefik enhancement fallback"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            if template_data is None:
                return False, "Invalid template file"
            
            # Add or update template_info
            if 'template_info' not in template_data:
                template_data['template_info'] = {}
            
            template_data['template_info']['traefik_compatible'] = True
            
            # Add Traefik configuration if missing
            if 'traefik_config' not in template_data:
                template_data['traefik_config'] = {
                    'service_port': 80,
                    'middlewares': [{
                        'name': f"{Path(template_path).stem}-headers",
                        'config': {
                            'headers': {
                                'customRequestHeaders': {
                                    'X-Forwarded-Proto': 'https'
                                },
                                'customResponseHeaders': {
                                    'X-Frame-Options': 'SAMEORIGIN',
                                    'X-Content-Type-Options': 'nosniff'
                                }
                            }
                        }
                    }],
                    'routing_priority': 1
                }
            
            # Add Traefik fields if missing
            if 'fields' not in template_data:
                template_data['fields'] = {}
            
            traefik_fields = {
                'domain': {
                    'type': 'domain',
                    'description': 'Custom domain (optional)',
                    'default': '',
                    'required': False
                },
                'subdomain': {
                    'type': 'string',
                    'description': 'Subdomain prefix',
                    'default': '{{ project_name }}',
                    'validation': '^[a-z0-9-]+$',
                    'required': False
                },
                'ssl_enabled': {
                    'type': 'boolean',
                    'description': 'Enable SSL/TLS certificates',
                    'default': True,
                    'required': False
                }
            }
            
            for field_name, field_config in traefik_fields.items():
                if field_name not in template_data['fields']:
                    template_data['fields'][field_name] = field_config
            
            # Write enhanced template
            with open(template_path, 'w', encoding='utf-8') as f:
                yaml.dump(template_data, f, default_flow_style=False, allow_unicode=True)
            
            return True, "Template enhanced with basic Traefik support"
            
        except Exception as e:
            return False, f"Basic enhancement failed: {str(e)}"
    
    def generate_validation_report(self, analyses: Dict[str, TemplateAnalysis]) -> str:
        """Generate comprehensive validation report"""
        total_templates = len(analyses)
        valid_templates = sum(1 for a in analyses.values() if a.is_valid)
        total_errors = sum(a.error_count for a in analyses.values())
        total_warnings = sum(a.warning_count for a in analyses.values())
        
        # Count by Traefik compatibility
        traefik_counts = {
            TraefikCompatibility.FULL: 0,
            TraefikCompatibility.PARTIAL: 0,
            TraefikCompatibility.BASIC: 0,
            TraefikCompatibility.NONE: 0
        }
        
        for analysis in analyses.values():
            traefik_counts[analysis.traefik_compatibility] += 1
        
        # Calculate average score
        avg_score = sum(a.score for a in analyses.values()) / total_templates if total_templates > 0 else 0
        
        report = f"""
# BlastDock Template Validation Report

## Summary
- **Total Templates**: {total_templates}
- **Valid Templates**: {valid_templates} ({valid_templates/total_templates*100:.1f}%)
- **Total Errors**: {total_errors}
- **Total Warnings**: {total_warnings}
- **Average Quality Score**: {avg_score:.1f}/100

## Traefik Compatibility
- **Full Support**: {traefik_counts[TraefikCompatibility.FULL]} templates
- **Partial Support**: {traefik_counts[TraefikCompatibility.PARTIAL]} templates
- **Basic Support**: {traefik_counts[TraefikCompatibility.BASIC]} templates
- **No Support**: {traefik_counts[TraefikCompatibility.NONE]} templates

## Top Issues by Category
"""
        
        # Collect all issues by category
        issues_by_category = {}
        for analysis in analyses.values():
            for result in analysis.results:
                if result.level in [ValidationLevel.ERROR, ValidationLevel.WARNING]:
                    category = result.category
                    if category not in issues_by_category:
                        issues_by_category[category] = []
                    issues_by_category[category].append(result)
        
        # Sort categories by issue count
        sorted_categories = sorted(
            issues_by_category.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for category, issues in sorted_categories[:5]:  # Top 5 categories
            error_count = sum(1 for i in issues if i.level == ValidationLevel.ERROR)
            warning_count = sum(1 for i in issues if i.level == ValidationLevel.WARNING)
            report += f"\n### {category.title()}\n"
            report += f"- Errors: {error_count}\n"
            report += f"- Warnings: {warning_count}\n"
        
        report += "\n## Templates Needing Attention\n"
        
        # Sort templates by score (lowest first)
        sorted_templates = sorted(analyses.values(), key=lambda x: x.score)
        
        for analysis in sorted_templates[:10]:  # Bottom 10 templates
            if analysis.error_count > 0 or analysis.warning_count > 5:
                report += f"\n### {analysis.template_name} (Score: {analysis.score}/100)\n"
                report += f"- Errors: {analysis.error_count}\n"
                report += f"- Warnings: {analysis.warning_count}\n"
                report += f"- Traefik Support: {analysis.traefik_compatibility.value}\n"
                
                # Show top 3 issues
                top_issues = [r for r in analysis.results if r.level == ValidationLevel.ERROR][:3]
                if top_issues:
                    report += "- Top Issues:\n"
                    for issue in top_issues:
                        report += f"  - {issue.message}\n"
        
        return report