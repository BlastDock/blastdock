# Security API Reference

The Security API provides comprehensive security validation, password generation, and hardening features for BlastDock deployments.

## Classes Overview

- **[SecurityValidator](#securityvalidator)** - Security validation and compliance checking
- **[PasswordManager](#passwordmanager)** - Secure password generation and validation
- **[SecurityHardening](#securityhardening)** - Security hardening recommendations
- **[VulnerabilityScanner](#vulnerabilityscanner)** - Security vulnerability detection

## SecurityValidator

The `SecurityValidator` class provides comprehensive security validation for templates and deployments.

### Class Definition

```python
from blastdock.security import SecurityValidator

validator = SecurityValidator(
    strict_mode=True,
    compliance_level="high"
)
```

### Methods

#### validate_template_security()

Validate template security configuration.

```python
def validate_template_security(
    self,
    template_path: str,
    check_images: bool = True,
    check_configs: bool = True
) -> Dict[str, Any]:
    """
    Validate template security configuration.
    
    Args:
        template_path: Path to template directory
        check_images: Validate container image security
        check_configs: Check configuration security
    
    Returns:
        Security validation results
    """
```

**Example Usage:**

```python
# Validate template security
validation = validator.validate_template_security(
    template_path="./templates/wordpress",
    check_images=True,
    check_configs=True
)

print(f"🔒 Security Validation: {validation['template_name']}")
print(f"   Security Score: {validation['security_score']}/100")
print(f"   Risk Level: {validation['risk_level']}")

if validation['issues']:
    print("\n❌ Security Issues:")
    for issue in validation['issues']:
        severity_icon = {"critical": "🚨", "high": "⚠️", "medium": "⚡", "low": "💡"}
        icon = severity_icon.get(issue['severity'], "•")
        print(f"   {icon} {issue['title']}")
        print(f"      {issue['description']}")
        if issue.get('remediation'):
            print(f"      💡 Fix: {issue['remediation']}")

if validation['recommendations']:
    print("\n💡 Security Recommendations:")
    for rec in validation['recommendations']:
        print(f"   • {rec}")
```

#### scan_deployment_security()

Scan running deployment for security vulnerabilities.

```python
def scan_deployment_security(
    self,
    project_name: str,
    deep_scan: bool = False
) -> Dict[str, Any]:
    """
    Scan deployment for security vulnerabilities.
    
    Args:
        project_name: Name of project to scan
        deep_scan: Perform comprehensive vulnerability scan
    
    Returns:
        Security scan results
    """
```

**Example Usage:**

```python
# Scan deployment security
scan_result = validator.scan_deployment_security(
    project_name="production-blog",
    deep_scan=True
)

print(f"🔍 Security Scan: {scan_result['project_name']}")
print(f"   Scan Time: {scan_result['scan_duration']:.1f}s")
print(f"   Security Score: {scan_result['security_score']}/100")

# Show vulnerability summary
vulnerabilities = scan_result['vulnerabilities']
by_severity = {}
for vuln in vulnerabilities:
    severity = vuln['severity']
    by_severity[severity] = by_severity.get(severity, 0) + 1

print("\n🚨 Vulnerability Summary:")
for severity in ['critical', 'high', 'medium', 'low']:
    count = by_severity.get(severity, 0)
    if count > 0:
        icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[severity]
        print(f"   {icon} {severity.title()}: {count}")

# Show detailed vulnerabilities
if vulnerabilities:
    print("\n🔍 Detailed Vulnerabilities:")
    for vuln in vulnerabilities[:5]:  # Show first 5
        print(f"   📋 {vuln['title']} ({vuln['severity']})")
        print(f"      Component: {vuln['component']}")
        print(f"      CVE: {vuln.get('cve_id', 'N/A')}")
        if vuln.get('fix_available'):
            print(f"      🔧 Fix: {vuln['fix_description']}")
```

#### validate_environment_security()

Validate deployment environment security.

```python
def validate_environment_security(
    self,
    environment: str = "production"
) -> Dict[str, Any]:
    """
    Validate environment security configuration.
    
    Args:
        environment: Environment name to validate
    
    Returns:
        Environment security validation results
    """
```

**Example Usage:**

```python
# Validate production environment security
env_validation = validator.validate_environment_security("production")

print(f"🌍 Environment Security: {env_validation['environment']}")
print(f"   Compliance: {env_validation['compliance_level']}")
print(f"   Security Controls: {len(env_validation['security_controls'])}")

# Check security controls
for control in env_validation['security_controls']:
    status_icon = "✅" if control['enabled'] else "❌"
    print(f"   {status_icon} {control['name']}: {control['status']}")
    if not control['enabled'] and control.get('importance') == 'critical':
        print(f"      🚨 Critical security control disabled!")

# Check compliance requirements
if env_validation['compliance_checks']:
    print("\n📋 Compliance Checks:")
    for check in env_validation['compliance_checks']:
        result_icon = "✅" if check['passed'] else "❌"
        print(f"   {result_icon} {check['requirement']}")
        if not check['passed']:
            print(f"      📄 Details: {check['details']}")
```

## PasswordManager

The `PasswordManager` class handles secure password generation and validation.

### Class Definition

```python
from blastdock.security import PasswordManager

password_manager = PasswordManager(
    default_length=16,
    complexity_level="high"
)
```

### Methods

#### generate_password()

Generate cryptographically secure passwords.

```python
def generate_password(
    self,
    length: int = None,
    include_symbols: bool = True,
    exclude_ambiguous: bool = True,
    custom_charset: Optional[str] = None
) -> str:
    """
    Generate a secure password.
    
    Args:
        length: Password length (uses default if None)
        include_symbols: Include special characters
        exclude_ambiguous: Exclude ambiguous characters (0, O, l, 1)
        custom_charset: Custom character set to use
    
    Returns:
        Generated secure password
    """
```

**Example Usage:**

```python
# Generate standard secure password
password = password_manager.generate_password(
    length=20,
    include_symbols=True,
    exclude_ambiguous=True
)

print(f"🔐 Generated Password: {password}")

# Generate password for database
db_password = password_manager.generate_password(
    length=32,
    include_symbols=False,  # Some databases don't like symbols
    exclude_ambiguous=True
)

# Generate API key
api_key = password_manager.generate_password(
    length=64,
    custom_charset="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
)

print(f"🔑 API Key: {api_key}")

# Batch generate passwords for multiple services
services = ['mysql', 'redis', 'admin_user', 'api_token']
passwords = {}

for service in services:
    passwords[service] = password_manager.generate_password(
        length=24 if 'token' in service else 16
    )
    print(f"🔐 {service}: {passwords[service]}")
```

#### validate_password_strength()

Validate password strength and security.

```python
def validate_password_strength(
    self,
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digits: bool = True,
    require_symbols: bool = True
) -> Dict[str, Any]:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        min_length: Minimum required length
        require_uppercase: Require uppercase letters
        require_lowercase: Require lowercase letters
        require_digits: Require digits
        require_symbols: Require special characters
    
    Returns:
        Password validation results
    """
```

**Example Usage:**

```python
# Validate user-provided password
user_password = "MySecureP@ssw0rd123"
validation = password_manager.validate_password_strength(
    password=user_password,
    min_length=12,
    require_symbols=True
)

print(f"🔍 Password Validation:")
print(f"   Strength: {validation['strength']}")  # weak/medium/strong/very_strong
print(f"   Score: {validation['score']}/100")
print(f"   Valid: {'✅' if validation['valid'] else '❌'}")

if validation['issues']:
    print("\n❌ Issues:")
    for issue in validation['issues']:
        print(f"   • {issue}")

if validation['suggestions']:
    print("\n💡 Suggestions:")
    for suggestion in validation['suggestions']:
        print(f"   • {suggestion}")

# Check against common passwords
if validation['is_common']:
    print("⚠️  Warning: This password appears in common password lists")

# Entropy analysis
print(f"\n📊 Password Analysis:")
print(f"   Entropy: {validation['entropy']:.1f} bits")
print(f"   Character Types: {validation['character_types']}")
print(f"   Pattern Analysis: {validation['pattern_score']}/10")
```

#### generate_secure_config()

Generate secure configuration with random passwords.

```python
def generate_secure_config(
    self,
    template_variables: Dict[str, Any],
    auto_generate: bool = True
) -> Dict[str, Any]:
    """
    Generate secure configuration with auto-generated passwords.
    
    Args:
        template_variables: Template variable definitions
        auto_generate: Auto-generate passwords for password fields
    
    Returns:
        Configuration with secure passwords
    """
```

**Example Usage:**

```python
# Template variable definitions
template_vars = {
    "mysql_password": {"type": "password", "required": True},
    "admin_password": {"type": "password", "required": True},
    "redis_password": {"type": "password", "required": False},
    "app_name": {"type": "string", "default": "MyApp"},
    "admin_email": {"type": "email", "required": True}
}

# Generate secure configuration
secure_config = password_manager.generate_secure_config(
    template_variables=template_vars,
    auto_generate=True
)

print("🔐 Generated Secure Configuration:")
for key, value in secure_config.items():
    if "password" in key.lower():
        print(f"   {key}: {'*' * len(value)} (length: {len(value)})")
    else:
        print(f"   {key}: {value}")

# Save passwords securely
password_manager.save_passwords_to_vault(
    project_name="my-secure-app",
    passwords=secure_config
)

print("💾 Passwords saved to secure vault")
```

## SecurityHardening

The `SecurityHardening` class provides security hardening recommendations and implementations.

### Class Definition

```python
from blastdock.security import SecurityHardening

hardening = SecurityHardening(
    compliance_framework="CIS",  # CIS, NIST, PCI-DSS
    environment="production"
)
```

### Methods

#### analyze_security_posture()

Analyze current security posture and provide recommendations.

```python
def analyze_security_posture(
    self,
    project_name: str,
    include_infrastructure: bool = True
) -> Dict[str, Any]:
    """
    Analyze security posture of deployment.
    
    Args:
        project_name: Name of project to analyze
        include_infrastructure: Include infrastructure analysis
    
    Returns:
        Security posture analysis results
    """
```

**Example Usage:**

```python
# Analyze security posture
analysis = hardening.analyze_security_posture(
    project_name="production-app",
    include_infrastructure=True
)

print(f"🛡️  Security Posture Analysis: {analysis['project_name']}")
print(f"   Overall Score: {analysis['security_score']}/100")
print(f"   Risk Level: {analysis['risk_level']}")
print(f"   Compliance: {analysis['compliance_score']}/100")

# Security categories analysis
categories = analysis['categories']
for category, data in categories.items():
    score = data['score']
    status_icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
    print(f"   {status_icon} {category.title()}: {score}/100")

# High-priority recommendations
if analysis['high_priority_issues']:
    print(f"\n🚨 High Priority Issues ({len(analysis['high_priority_issues'])}):")
    for issue in analysis['high_priority_issues'][:3]:
        print(f"   • {issue['title']}")
        print(f"     Impact: {issue['impact']}")
        print(f"     Effort: {issue['effort']}")

# Quick wins
if analysis['quick_wins']:
    print(f"\n⚡ Quick Security Wins:")
    for win in analysis['quick_wins']:
        print(f"   ✨ {win['title']} (Impact: {win['impact']}, Effort: {win['effort']})")
```

#### apply_security_hardening()

Apply security hardening configurations.

```python
def apply_security_hardening(
    self,
    project_name: str,
    hardening_profile: str = "standard",
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Apply security hardening to deployment.
    
    Args:
        project_name: Name of project to harden
        hardening_profile: Hardening profile (minimal, standard, strict)
        dry_run: Show what would be applied without making changes
    
    Returns:
        Hardening application results
    """
```

**Example Usage:**

```python
# Apply security hardening (dry run first)
dry_run_result = hardening.apply_security_hardening(
    project_name="production-app",
    hardening_profile="strict",
    dry_run=True
)

print(f"🔍 Security Hardening Plan (Dry Run):")
print(f"   Profile: {dry_run_result['profile']}")
print(f"   Changes: {len(dry_run_result['planned_changes'])}")

for change in dry_run_result['planned_changes']:
    print(f"   📋 {change['category']}: {change['description']}")
    print(f"      Impact: {change['impact']}")
    if change.get('requires_restart'):
        print("      ⚠️  Requires service restart")

# Apply hardening after review
if input("Apply hardening? (y/N): ").lower() == 'y':
    result = hardening.apply_security_hardening(
        project_name="production-app",
        hardening_profile="strict",
        dry_run=False
    )
    
    if result['success']:
        print(f"✅ Security hardening applied successfully")
        print(f"   Applied: {len(result['applied_changes'])} changes")
        print(f"   Security Score Improvement: +{result['score_improvement']}")
    else:
        print(f"❌ Hardening failed: {result['error']}")
```

#### generate_security_report()

Generate comprehensive security report.

```python
def generate_security_report(
    self,
    project_name: str,
    output_format: str = "html",
    include_recommendations: bool = True
) -> str:
    """
    Generate comprehensive security report.
    
    Args:
        project_name: Name of project to report on
        output_format: Report format (html, pdf, json, markdown)
        include_recommendations: Include security recommendations
    
    Returns:
        Path to generated report file
    """
```

**Example Usage:**

```python
# Generate comprehensive security report
report_path = hardening.generate_security_report(
    project_name="production-app",
    output_format="html",
    include_recommendations=True
)

print(f"📊 Security report generated: {report_path}")

# Generate executive summary (PDF)
executive_report = hardening.generate_security_report(
    project_name="production-app",
    output_format="pdf",
    include_recommendations=False
)

print(f"📋 Executive summary: {executive_report}")

# Programmatic access (JSON)
json_report = hardening.generate_security_report(
    project_name="production-app",
    output_format="json",
    include_recommendations=True
)

import json
with open(json_report, 'r') as f:
    report_data = json.load(f)
    
print(f"📊 Security Report Summary:")
print(f"   Overall Score: {report_data['summary']['overall_score']}")
print(f"   Critical Issues: {report_data['summary']['critical_issues']}")
print(f"   Compliance: {report_data['summary']['compliance_status']}")
```

## Advanced Security Examples

### Automated Security Pipeline

```python
from blastdock.security import SecurityValidator, SecurityHardening, PasswordManager

def automated_security_pipeline(project_name: str):
    """Comprehensive automated security pipeline."""
    
    validator = SecurityValidator(strict_mode=True)
    hardening = SecurityHardening(environment="production")
    password_manager = PasswordManager()
    
    print(f"🔒 Starting security pipeline for: {project_name}")
    
    # Step 1: Security scan
    print("1️⃣ Running security scan...")
    scan_result = validator.scan_deployment_security(
        project_name=project_name,
        deep_scan=True
    )
    
    critical_vulns = [v for v in scan_result['vulnerabilities'] if v['severity'] == 'critical']
    if critical_vulns:
        print(f"🚨 CRITICAL: {len(critical_vulns)} critical vulnerabilities found!")
        for vuln in critical_vulns:
            print(f"   • {vuln['title']} (CVE: {vuln.get('cve_id', 'N/A')})")
        return False
    
    # Step 2: Security posture analysis
    print("2️⃣ Analyzing security posture...")
    posture = hardening.analyze_security_posture(project_name)
    
    if posture['security_score'] < 70:
        print(f"⚠️  Security score too low: {posture['security_score']}/100")
        
        # Step 3: Apply automated hardening
        print("3️⃣ Applying security hardening...")
        hardening_result = hardening.apply_security_hardening(
            project_name=project_name,
            hardening_profile="standard"
        )
        
        if hardening_result['success']:
            print(f"✅ Security hardening applied (+{hardening_result['score_improvement']} points)")
        else:
            print(f"❌ Hardening failed: {hardening_result['error']}")
            return False
    
    # Step 4: Password security audit
    print("4️⃣ Auditing password security...")
    password_audit = password_manager.audit_project_passwords(project_name)
    
    weak_passwords = password_audit['weak_passwords']
    if weak_passwords:
        print(f"🔐 Found {len(weak_passwords)} weak passwords")
        
        # Auto-rotate weak passwords
        for service, password_info in weak_passwords.items():
            new_password = password_manager.generate_password(length=24)
            password_manager.rotate_password(
                project_name=project_name,
                service=service,
                new_password=new_password
            )
            print(f"   🔄 Rotated password for {service}")
    
    # Step 5: Generate compliance report
    print("5️⃣ Generating compliance report...")
    report_path = hardening.generate_security_report(
        project_name=project_name,
        output_format="pdf"
    )
    
    # Final security score
    final_scan = validator.scan_deployment_security(project_name)
    final_score = final_scan['security_score']
    
    print(f"✅ Security pipeline completed!")
    print(f"   Final Security Score: {final_score}/100")
    print(f"   Report: {report_path}")
    
    return final_score >= 80

# Run automated security pipeline
success = automated_security_pipeline("production-blog")
```

### Security Monitoring Dashboard

```python
from blastdock.security import SecurityValidator
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

def security_monitoring_dashboard():
    """Real-time security monitoring dashboard."""
    
    console = Console()
    validator = SecurityValidator()
    
    # Get all deployments
    from blastdock.core import DeploymentManager
    deployment_manager = DeploymentManager()
    deployments = deployment_manager.list_deployments()
    
    while True:
        console.clear()
        
        # Security overview table
        table = Table(title="🔒 BlastDock Security Dashboard")
        table.add_column("Project", style="cyan")
        table.add_column("Security Score", style="green")
        table.add_column("Vulnerabilities", style="red")
        table.add_column("Last Scan", style="blue")
        table.add_column("Status", style="yellow")
        
        total_critical = 0
        total_high = 0
        
        for deployment in deployments:
            scan_result = validator.scan_deployment_security(deployment['name'])
            
            score = scan_result['security_score']
            vulns = scan_result['vulnerabilities']
            
            # Count vulnerabilities by severity
            critical = len([v for v in vulns if v['severity'] == 'critical'])
            high = len([v for v in vulns if v['severity'] == 'high'])
            
            total_critical += critical
            total_high += high
            
            # Status based on score
            if score >= 80:
                status = "🟢 Good"
            elif score >= 60:
                status = "🟡 Fair"
            else:
                status = "🔴 Poor"
            
            vuln_summary = f"C:{critical} H:{high}"
            last_scan = scan_result['scan_timestamp'].strftime('%H:%M:%S')
            
            table.add_row(
                deployment['name'],
                f"{score}/100",
                vuln_summary,
                last_scan,
                status
            )
        
        console.print(table)
        
        # Security alerts panel
        if total_critical > 0 or total_high > 0:
            alert_text = f"🚨 Security Alerts: {total_critical} Critical, {total_high} High"
            alert_panel = Panel(alert_text, style="bold red")
            console.print("\n", alert_panel)
        
        time.sleep(30)  # Refresh every 30 seconds

# Run security monitoring dashboard
security_monitoring_dashboard()
```

## Next Steps

- 📊 **[Monitoring API](../monitoring/)** - Advanced monitoring capabilities
- 🎯 **[Performance API](../performance/)** - Performance optimization
- 🏗️ **[Templates API](../templates/)** - Template system and validation
- 💻 **[CLI API](../cli/)** - Command-line interface components