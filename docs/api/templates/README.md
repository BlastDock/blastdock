# Templates API Reference

The Templates API provides comprehensive template management, validation, creation, and customization capabilities for BlastDock deployments.

## Classes Overview

- **[TemplateLoader](#templateloader)** - Template loading and caching system
- **[TemplateValidator](#templatevalidator)** - Template validation and security checking
- **[TemplateBuilder](#templatebuilder)** - Custom template creation and modification
- **[TemplateRegistry](#templateregistry)** - Template registry and version management
- **[VariableProcessor](#variableprocessor)** - Template variable processing and validation

## TemplateLoader

The `TemplateLoader` class handles efficient loading and caching of templates.

### Class Definition

```python
from blastdock.templates import TemplateLoader

template_loader = TemplateLoader(
    cache_enabled=True,
    cache_ttl=3600,  # 1 hour
    parallel_loading=True
)
```

### Methods

#### load_template()

Load a template with caching and validation.

```python
def load_template(
    self,
    template_name: str,
    version: Optional[str] = None,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Load template from registry or local path.
    
    Args:
        template_name: Name of template to load
        version: Specific version (latest if None)
        validate: Validate template after loading
    
    Returns:
        Loaded template data with metadata
    """
```

**Example Usage:**

```python
from blastdock.templates import TemplateLoader

template_loader = TemplateLoader()

# Load latest WordPress template
wordpress = template_loader.load_template("wordpress")

print(f"📄 Template: {wordpress['name']} v{wordpress['version']}")
print(f"📝 Description: {wordpress['description']}")
print(f"👤 Author: {wordpress['author']}")
print(f"🏷️  Category: {wordpress['category']}")

# Template structure
print(f"\n📋 Template Structure:")
print(f"   Services: {len(wordpress['services'])}")
for service in wordpress['services']:
    print(f"     • {service['name']} ({service['image']})")

print(f"   Variables: {len(wordpress['variables'])}")
for var in wordpress['variables']:
    required = "✓" if var.get('required', False) else "○"
    default = f" (default: {var['default']})" if var.get('default') else ""
    print(f"     {required} {var['name']}: {var['description']}{default}")

print(f"   Files: {len(wordpress['files'])}")
for file_info in wordpress['files']:
    print(f"     • {file_info['path']} ({file_info['type']})")

# Load specific version
wordpress_old = template_loader.load_template("wordpress", version="5.9")
print(f"\n📄 Loaded WordPress v{wordpress_old['version']}")

# Load with custom validation
try:
    nextcloud = template_loader.load_template(
        template_name="nextcloud",
        validate=True
    )
    print(f"✅ Nextcloud template loaded and validated")
except ValidationError as e:
    print(f"❌ Template validation failed: {e}")
```

#### get_template_metadata()

Get template metadata without loading full content.

```python
def get_template_metadata(
    self,
    template_name: str,
    include_stats: bool = False
) -> Dict[str, Any]:
    """
    Get template metadata without loading full content.
    
    Args:
        template_name: Name of template
        include_stats: Include usage statistics
    
    Returns:
        Template metadata
    """
```

**Example Usage:**

```python
# Get template metadata for quick overview
metadata = template_loader.get_template_metadata(
    template_name="wordpress",
    include_stats=True
)

print(f"📊 WordPress Template Metadata:")
print(f"   Name: {metadata['name']}")
print(f"   Latest Version: {metadata['latest_version']}")
print(f"   Available Versions: {len(metadata['versions'])}")
print(f"   Category: {metadata['category']}")
print(f"   Size: {metadata['size_mb']:.1f} MB")
print(f"   Last Updated: {metadata['last_updated']}")

if 'stats' in metadata:
    stats = metadata['stats']
    print(f"\n📈 Usage Statistics:")
    print(f"   Downloads: {stats['download_count']:,}")
    print(f"   Active Deployments: {stats['active_deployments']:,}")
    print(f"   Rating: {stats['average_rating']:.1f}/5.0")
    print(f"   Reviews: {stats['review_count']}")

# List all available versions
print(f"\n📋 Available Versions:")
for version in metadata['versions']:
    print(f"   • v{version['version']} ({version['release_date']})")
    if version.get('changelog'):
        print(f"     Changes: {version['changelog'][:60]}...")
```

#### batch_load_templates()

Load multiple templates efficiently in parallel.

```python
def batch_load_templates(
    self,
    template_names: List[str],
    parallel: bool = True
) -> Dict[str, Dict[str, Any]]:
    """
    Load multiple templates efficiently.
    
    Args:
        template_names: List of template names to load
        parallel: Load templates in parallel
    
    Returns:
        Dictionary of loaded templates
    """
```

**Example Usage:**

```python
# Load multiple templates for comparison
template_names = ["wordpress", "nextcloud", "mediawiki", "ghost"]

print("🔄 Loading templates in parallel...")
templates = template_loader.batch_load_templates(
    template_names=template_names,
    parallel=True
)

print(f"✅ Loaded {len(templates)} templates:")

# Compare templates
comparison_table = []
for name, template in templates.items():
    comparison_table.append({
        'name': name,
        'version': template['version'],
        'services': len(template['services']),
        'variables': len(template['variables']),
        'size': template.get('size_mb', 0)
    })

# Print comparison table
print(f"\n📊 Template Comparison:")
print(f"{'Name':<12} {'Version':<8} {'Services':<8} {'Variables':<9} {'Size (MB)'}")
print("=" * 55)

for template in comparison_table:
    print(f"{template['name']:<12} {template['version']:<8} {template['services']:<8} "
          f"{template['variables']:<9} {template['size']:.1f}")

# Find templates with similar features
web_templates = [
    name for name, template in templates.items() 
    if template['category'] == 'web'
]
print(f"\n🌐 Web Application Templates: {', '.join(web_templates)}")
```

## TemplateValidator

The `TemplateValidator` class provides comprehensive template validation and security checking.

### Class Definition

```python
from blastdock.templates import TemplateValidator

validator = TemplateValidator(
    strict_mode=True,
    security_checks=True,
    performance_checks=True
)
```

### Methods

#### validate_template()

Perform comprehensive template validation.

```python
def validate_template(
    self,
    template_data: Dict[str, Any],
    validation_level: str = "standard"
) -> Dict[str, Any]:
    """
    Validate template structure and content.
    
    Args:
        template_data: Template data to validate
        validation_level: Validation level (basic, standard, strict)
    
    Returns:
        Validation results with issues and recommendations
    """
```

**Example Usage:**

```python
from blastdock.templates import TemplateValidator

validator = TemplateValidator()

# Load template for validation
template = template_loader.load_template("wordpress")

# Validate template
validation = validator.validate_template(
    template_data=template,
    validation_level="strict"
)

print(f"🔍 Template Validation: {template['name']}")
print(f"   Valid: {'✅' if validation['valid'] else '❌'}")
print(f"   Validation Score: {validation['score']}/100")
print(f"   Validation Level: {validation['level']}")

# Issues breakdown
issues_by_severity = {}
for issue in validation['issues']:
    severity = issue['severity']
    issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1

if issues_by_severity:
    print(f"\n❌ Issues Found:")
    for severity in ['critical', 'high', 'medium', 'low']:
        count = issues_by_severity.get(severity, 0)
        if count > 0:
            severity_icon = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "💡"}
            icon = severity_icon.get(severity, "•")
            print(f"   {icon} {severity.title()}: {count}")

# Detailed issues
if validation['issues']:
    print(f"\n🔍 Detailed Issues:")
    for issue in validation['issues'][:5]:  # Show first 5
        print(f"   • {issue['title']} ({issue['severity']})")
        print(f"     {issue['description']}")
        if issue.get('fix_suggestion'):
            print(f"     💡 Fix: {issue['fix_suggestion']}")

# Security analysis
if 'security_analysis' in validation:
    security = validation['security_analysis']
    print(f"\n🔒 Security Analysis:")
    print(f"   Security Score: {security['score']}/100")
    print(f"   Risk Level: {security['risk_level']}")
    
    if security['vulnerabilities']:
        print(f"   Vulnerabilities: {len(security['vulnerabilities'])}")
        for vuln in security['vulnerabilities'][:3]:
            print(f"     • {vuln['type']}: {vuln['description']}")

# Performance analysis
if 'performance_analysis' in validation:
    performance = validation['performance_analysis']
    print(f"\n⚡ Performance Analysis:")
    print(f"   Performance Score: {performance['score']}/100")
    print(f"   Resource Efficiency: {performance['resource_efficiency']:.1f}%")
    
    if performance['optimizations']:
        print(f"   Suggested Optimizations:")
        for opt in performance['optimizations']:
            print(f"     • {opt}")

# Best practices compliance
if 'best_practices' in validation:
    bp = validation['best_practices']
    print(f"\n📋 Best Practices Compliance:")
    print(f"   Compliance Score: {bp['compliance_score']}/100")
    
    for category, status in bp['categories'].items():
        status_icon = "✅" if status['compliant'] else "❌"
        print(f"   {status_icon} {category.title()}: {status['score']}/100")
```

#### validate_template_variables()

Validate template variables and their configuration.

```python
def validate_template_variables(
    self,
    variables: List[Dict[str, Any]],
    user_values: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate template variables configuration.
    
    Args:
        variables: Template variable definitions
        user_values: User-provided variable values
    
    Returns:
        Variable validation results
    """
```

**Example Usage:**

```python
# Template variable definitions
template_variables = [
    {
        "name": "mysql_password",
        "type": "password",
        "required": True,
        "min_length": 8,
        "description": "MySQL root password"
    },
    {
        "name": "admin_email",
        "type": "email",
        "required": True,
        "description": "Administrator email address"
    },
    {
        "name": "site_title",
        "type": "string",
        "required": False,
        "default": "My WordPress Site",
        "max_length": 100,
        "description": "Website title"
    },
    {
        "name": "memory_limit",
        "type": "integer",
        "required": False,
        "default": 256,
        "min_value": 128,
        "max_value": 2048,
        "description": "PHP memory limit in MB"
    }
]

# User-provided values
user_values = {
    "mysql_password": "weak123",  # Intentionally weak
    "admin_email": "invalid-email",  # Invalid format
    "site_title": "My Amazing WordPress Blog",
    "memory_limit": 512
}

# Validate variables
var_validation = validator.validate_template_variables(
    variables=template_variables,
    user_values=user_values
)

print(f"📝 Variable Validation Results:")
print(f"   Valid: {'✅' if var_validation['valid'] else '❌'}")
print(f"   Variables Checked: {len(var_validation['variables'])}")

# Check individual variables
for var_name, var_result in var_validation['variables'].items():
    status_icon = "✅" if var_result['valid'] else "❌"
    print(f"   {status_icon} {var_name}: {var_result['status']}")
    
    if not var_result['valid']:
        for error in var_result['errors']:
            print(f"      • {error}")
    
    # Show suggestions for improvement
    if var_result.get('suggestions'):
        for suggestion in var_result['suggestions']:
            print(f"      💡 {suggestion}")

# Missing required variables
missing = var_validation.get('missing_required', [])
if missing:
    print(f"\n❌ Missing Required Variables:")
    for var_name in missing:
        var_def = next(v for v in template_variables if v['name'] == var_name)
        print(f"   • {var_name}: {var_def['description']}")

# Security recommendations for variables
if 'security_recommendations' in var_validation:
    print(f"\n🔒 Security Recommendations:")
    for rec in var_validation['security_recommendations']:
        print(f"   • {rec}")
```

#### check_template_compatibility()

Check template compatibility with target environment.

```python
def check_template_compatibility(
    self,
    template_data: Dict[str, Any],
    target_environment: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Check template compatibility with target environment.
    
    Args:
        template_data: Template to check
        target_environment: Target environment specifications
    
    Returns:
        Compatibility analysis results
    """
```

**Example Usage:**

```python
# Target environment specifications
target_env = {
    "docker_version": "24.0.0",
    "compose_version": "2.15.0",
    "platform": "linux/amd64",
    "available_memory": "8GB",
    "available_storage": "100GB",
    "network_features": ["overlay", "bridge"],
    "security_features": ["apparmor", "seccomp"],
    "plugins": ["traefik", "portainer"]
}

# Check compatibility
compatibility = validator.check_template_compatibility(
    template_data=template,
    target_environment=target_env
)

print(f"🔍 Compatibility Check: {template['name']}")
print(f"   Compatible: {'✅' if compatibility['compatible'] else '❌'}")
print(f"   Compatibility Score: {compatibility['score']}/100")

# Requirement analysis
requirements = compatibility['requirements']
print(f"\n📋 Requirements Analysis:")

for req_category, req_status in requirements.items():
    status_icon = "✅" if req_status['met'] else "❌"
    print(f"   {status_icon} {req_category.title()}: {req_status['status']}")
    
    if not req_status['met'] and req_status.get('details'):
        print(f"      Issue: {req_status['details']}")

# Feature compatibility
features = compatibility['features']
print(f"\n🔧 Feature Compatibility:")

for feature, feature_status in features.items():
    if feature_status['available']:
        print(f"   ✅ {feature}: Available")
    else:
        print(f"   ❌ {feature}: Not available")
        if feature_status.get('alternative'):
            print(f"      Alternative: {feature_status['alternative']}")

# Warnings and recommendations
if compatibility['warnings']:
    print(f"\n⚠️  Compatibility Warnings:")
    for warning in compatibility['warnings']:
        print(f"   • {warning}")

if compatibility['recommendations']:
    print(f"\n💡 Recommendations:")
    for rec in compatibility['recommendations']:
        print(f"   • {rec}")

# Resource requirements vs availability
resources = compatibility['resource_analysis']
print(f"\n📊 Resource Analysis:")
print(f"   Memory Required: {resources['memory_required']} / Available: {resources['memory_available']}")
print(f"   Storage Required: {resources['storage_required']} / Available: {resources['storage_available']}")
print(f"   CPU Cores: {resources['cpu_cores_recommended']} recommended")
```

## TemplateBuilder

The `TemplateBuilder` class enables creation and modification of custom templates.

### Class Definition

```python
from blastdock.templates import TemplateBuilder

builder = TemplateBuilder(
    auto_validate=True,
    include_best_practices=True,
    generate_documentation=True
)
```

### Methods

#### create_template()

Create a new template from scratch or based on existing template.

```python
def create_template(
    self,
    template_name: str,
    base_template: Optional[str] = None,
    template_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a new template.
    
    Args:
        template_name: Name for the new template
        base_template: Base template to extend (optional)
        template_config: Template configuration
    
    Returns:
        Path to created template directory
    """
```

**Example Usage:**

```python
from blastdock.templates import TemplateBuilder

builder = TemplateBuilder()

# Create a new template from scratch
template_config = {
    "name": "custom_laravel_app",
    "version": "1.0.0",
    "description": "Custom Laravel application with Redis and PostgreSQL",
    "author": "Your Name",
    "category": "web",
    "tags": ["php", "laravel", "postgresql", "redis"],
    
    "services": [
        {
            "name": "app",
            "image": "php:8.2-fpm",
            "build": {
                "context": "./docker/php",
                "dockerfile": "Dockerfile"
            },
            "environment": [
                "APP_ENV={{app_environment}}",
                "DB_HOST=database",
                "DB_PASSWORD={{database_password}}",
                "REDIS_HOST=redis"
            ],
            "volumes": [
                "./src:/var/www/html"
            ],
            "depends_on": ["database", "redis"]
        },
        {
            "name": "web",
            "image": "nginx:alpine",
            "ports": ["80:80"],
            "volumes": [
                "./docker/nginx/nginx.conf:/etc/nginx/nginx.conf",
                "./src:/var/www/html"
            ],
            "depends_on": ["app"]
        },
        {
            "name": "database",
            "image": "postgres:15",
            "environment": [
                "POSTGRES_DB={{database_name}}",
                "POSTGRES_USER={{database_user}}",
                "POSTGRES_PASSWORD={{database_password}}"
            ],
            "volumes": [
                "postgres_data:/var/lib/postgresql/data"
            ]
        },
        {
            "name": "redis",
            "image": "redis:7-alpine",
            "command": "redis-server --appendonly yes",
            "volumes": [
                "redis_data:/data"
            ]
        }
    ],
    
    "variables": [
        {
            "name": "app_environment",
            "type": "string",
            "description": "Laravel application environment",
            "default": "production",
            "allowed_values": ["local", "staging", "production"]
        },
        {
            "name": "database_name",
            "type": "string",
            "description": "PostgreSQL database name",
            "default": "laravel",
            "required": True
        },
        {
            "name": "database_user",
            "type": "string",
            "description": "PostgreSQL username",
            "default": "laravel",
            "required": True
        },
        {
            "name": "database_password",
            "type": "password",
            "description": "PostgreSQL password",
            "required": True,
            "min_length": 12
        }
    ],
    
    "volumes": [
        "postgres_data",
        "redis_data"
    ],
    
    "networks": [
        "laravel_network"
    ]
}

# Create the template
template_path = builder.create_template(
    template_name="custom_laravel_app",
    template_config=template_config
)

print(f"✅ Template created: {template_path}")

# Create template based on existing one
wordpress_custom = builder.create_template(
    template_name="wordpress_with_redis",
    base_template="wordpress",
    template_config={
        "description": "WordPress with Redis caching",
        "additional_services": [
            {
                "name": "redis",
                "image": "redis:7-alpine",
                "command": "redis-server --appendonly yes"
            }
        ],
        "additional_variables": [
            {
                "name": "enable_redis_cache",
                "type": "boolean",
                "description": "Enable Redis object caching",
                "default": True
            }
        ]
    }
)

print(f"✅ Extended template created: {wordpress_custom}")
```

#### add_service()

Add a new service to existing template.

```python
def add_service(
    self,
    template_path: str,
    service_config: Dict[str, Any]
) -> None:
    """
    Add a service to existing template.
    
    Args:
        template_path: Path to template directory
        service_config: Service configuration
    """
```

**Example Usage:**

```python
# Add monitoring service to existing template
monitoring_service = {
    "name": "monitoring",
    "image": "prom/prometheus:latest",
    "ports": ["9090:9090"],
    "volumes": [
        "./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml"
    ],
    "command": [
        "--config.file=/etc/prometheus/prometheus.yml",
        "--storage.tsdb.path=/prometheus",
        "--web.console.libraries=/etc/prometheus/console_libraries",
        "--web.console.templates=/etc/prometheus/consoles"
    ]
}

builder.add_service(
    template_path=template_path,
    service_config=monitoring_service
)

# Add backup service
backup_service = {
    "name": "backup",
    "image": "alpine:latest",
    "volumes": [
        "postgres_data:/backup/postgres:ro",
        "./backups:/backup/output"
    ],
    "environment": [
        "BACKUP_SCHEDULE={{backup_schedule}}",
        "RETENTION_DAYS={{backup_retention}}"
    ],
    "command": ["sh", "-c", "while true; do sleep 3600; done"]  # Keep alive
}

builder.add_service(template_path, backup_service)

print("✅ Services added to template")
```

#### generate_template_files()

Generate all necessary template files and configurations.

```python
def generate_template_files(
    self,
    template_path: str,
    include_examples: bool = True,
    include_docs: bool = True
) -> Dict[str, str]:
    """
    Generate template files and configurations.
    
    Args:
        template_path: Path to template directory
        include_examples: Include example configurations
        include_docs: Generate documentation
    
    Returns:
        Dictionary of generated files
    """
```

**Example Usage:**

```python
# Generate all template files
generated_files = builder.generate_template_files(
    template_path=template_path,
    include_examples=True,
    include_docs=True
)

print(f"📁 Generated Template Files:")
for file_type, file_path in generated_files.items():
    print(f"   • {file_type}: {file_path}")

# Generated files typically include:
# - docker-compose.yml
# - template.yml (metadata)
# - .env.example
# - README.md
# - docker/ directory with Dockerfiles
# - config/ directory with service configs
# - docs/ directory with documentation

# Validate generated template
validation = validator.validate_template_path(template_path)

if validation['valid']:
    print("✅ Generated template is valid")
else:
    print("❌ Generated template has issues:")
    for issue in validation['issues']:
        print(f"   • {issue}")

# Test template deployment (optional)
test_result = builder.test_template(
    template_path=template_path,
    test_variables={
        "app_environment": "local",
        "database_name": "test_db",
        "database_user": "test_user",
        "database_password": "test_password_123"
    }
)

if test_result['success']:
    print(f"✅ Template test deployment successful")
    print(f"   Test duration: {test_result['duration']:.1f}s")
else:
    print(f"❌ Template test failed: {test_result['error']}")
```

## Advanced Template Examples

### Custom Template Creation Wizard

```python
from blastdock.templates import TemplateBuilder, TemplateValidator
import click

def template_creation_wizard():
    """Interactive template creation wizard."""
    
    builder = TemplateBuilder()
    validator = TemplateValidator()
    
    print("🏗️  BlastDock Template Creation Wizard")
    print("=====================================")
    
    # Basic template info
    template_name = click.prompt("Template name")
    description = click.prompt("Description")
    author = click.prompt("Author name")
    category = click.prompt("Category", default="web")
    
    # Services configuration
    services = []
    while True:
        if click.confirm("Add a service?"):
            service_name = click.prompt("Service name")
            service_image = click.prompt("Docker image")
            
            service = {
                "name": service_name,
                "image": service_image
            }
            
            # Optional service configuration
            if click.confirm("Add environment variables?"):
                env_vars = []
                while True:
                    env_var = click.prompt("Environment variable (KEY=value)", default="")
                    if not env_var:
                        break
                    env_vars.append(env_var)
                service["environment"] = env_vars
            
            if click.confirm("Add port mappings?"):
                ports = []
                while True:
                    port = click.prompt("Port mapping (host:container)", default="")
                    if not port:
                        break
                    ports.append(port)
                service["ports"] = ports
            
            if click.confirm("Add volumes?"):
                volumes = []
                while True:
                    volume = click.prompt("Volume mapping (host:container)", default="")
                    if not volume:
                        break
                    volumes.append(volume)
                service["volumes"] = volumes
            
            services.append(service)
        else:
            break
    
    # Template variables
    variables = []
    while True:
        if click.confirm("Add a template variable?"):
            var_name = click.prompt("Variable name")
            var_type = click.prompt(
                "Variable type", 
                type=click.Choice(["string", "password", "email", "integer", "boolean"])
            )
            var_description = click.prompt("Description")
            var_required = click.confirm("Required?", default=True)
            
            variable = {
                "name": var_name,
                "type": var_type,
                "description": var_description,
                "required": var_required
            }
            
            if not var_required:
                default_value = click.prompt("Default value", default="")
                if default_value:
                    variable["default"] = default_value
            
            variables.append(variable)
        else:
            break
    
    # Build template configuration
    template_config = {
        "name": template_name,
        "version": "1.0.0",
        "description": description,
        "author": author,
        "category": category,
        "services": services,
        "variables": variables
    }
    
    # Preview configuration
    print(f"\n📋 Template Configuration Preview:")
    print(f"   Name: {template_config['name']}")
    print(f"   Services: {len(template_config['services'])}")
    print(f"   Variables: {len(template_config['variables'])}")
    
    if click.confirm("Create template?"):
        try:
            template_path = builder.create_template(
                template_name=template_name,
                template_config=template_config
            )
            
            print(f"✅ Template created: {template_path}")
            
            # Validate created template
            validation = validator.validate_template_path(template_path)
            
            if validation['valid']:
                print("✅ Template validation passed")
            else:
                print("⚠️  Template has validation issues:")
                for issue in validation['issues']:
                    print(f"   • {issue}")
            
            # Generate files
            generated_files = builder.generate_template_files(template_path)
            print(f"📁 Generated {len(generated_files)} template files")
            
        except Exception as e:
            print(f"❌ Template creation failed: {e}")
    else:
        print("❌ Template creation cancelled")

# Run the wizard
template_creation_wizard()
```

### Template Migration Tool

```python
from blastdock.templates import TemplateBuilder, TemplateLoader
import yaml

def migrate_docker_compose_to_template():
    """Migrate existing docker-compose.yml to BlastDock template."""
    
    loader = TemplateLoader()
    builder = TemplateBuilder()
    
    print("🔄 Docker Compose to BlastDock Template Migration")
    print("================================================")
    
    # Load existing docker-compose.yml
    compose_file = click.prompt("Path to docker-compose.yml")
    
    try:
        with open(compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Failed to load compose file: {e}")
        return
    
    # Extract template information
    template_name = click.prompt("Template name")
    description = click.prompt("Template description")
    author = click.prompt("Author")
    
    # Convert services
    services = []
    variables = []
    
    for service_name, service_config in compose_data.get('services', {}).items():
        service = {
            "name": service_name,
            "image": service_config.get('image', 'unknown')
        }
        
        # Convert environment variables to template variables
        if 'environment' in service_config:
            env_vars = []
            for env_var in service_config['environment']:
                if isinstance(env_var, str) and '=' in env_var:
                    key, value = env_var.split('=', 1)
                    
                    # Check if value looks like a variable
                    if value.startswith('${') or '{{' in value:
                        # Extract variable name
                        var_name = key.lower()
                        
                        # Create template variable
                        variable = {
                            "name": var_name,
                            "type": "password" if "password" in key.lower() else "string",
                            "description": f"{key} for {service_name}",
                            "required": True
                        }
                        
                        variables.append(variable)
                        env_vars.append(f"{key}={{{{{var_name}}}}}")
                    else:
                        env_vars.append(env_var)
                else:
                    env_vars.append(env_var)
            
            service["environment"] = env_vars
        
        # Copy other service configuration
        for key in ['ports', 'volumes', 'depends_on', 'command']:
            if key in service_config:
                service[key] = service_config[key]
        
        services.append(service)
    
    # Create template configuration
    template_config = {
        "name": template_name,
        "version": "1.0.0",
        "description": description,
        "author": author,
        "category": "custom",
        "services": services,
        "variables": variables
    }
    
    # Add volumes and networks if present
    if 'volumes' in compose_data:
        template_config['volumes'] = list(compose_data['volumes'].keys())
    
    if 'networks' in compose_data:
        template_config['networks'] = list(compose_data['networks'].keys())
    
    # Create template
    try:
        template_path = builder.create_template(
            template_name=template_name,
            template_config=template_config
        )
        
        print(f"✅ Template migrated successfully: {template_path}")
        
        # Generate template files
        generated_files = builder.generate_template_files(template_path)
        print(f"📁 Generated template files:")
        for file_type, file_path in generated_files.items():
            print(f"   • {file_type}: {file_path}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

# Run migration tool
migrate_docker_compose_to_template()
```

## Next Steps

- 💻 **[CLI API](../cli/)** - Command-line interface components
- 🔧 **[Utils API](../utils/)** - Utility functions and helpers
- 🔒 **[Security API](../security/)** - Return to security features
- 📊 **[Monitoring API](../monitoring/)** - Return to monitoring capabilities