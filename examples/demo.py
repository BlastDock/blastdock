#!/usr/bin/env python3
"""
Demo script showing programmatic usage of blastdock
"""

import sys
import os

# Add blastdock to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'blastdock'))

from core.template_manager import TemplateManager
from core.deployment_manager import DeploymentManager
from core.monitor import Monitor

def demo_template_system():
    """Demonstrate template system"""
    print("=== Template System Demo ===")
    
    tm = TemplateManager()
    
    # List templates
    templates = tm.list_templates()
    print(f"Available templates: {', '.join(templates)}")
    
    # Get template info
    for template in templates[:3]:  # Show first 3
        info = tm.get_template_info(template)
        description = info.get('description', 'No description')
        print(f"  {template}: {description}")
    
    # Get default config for WordPress
    if 'wordpress' in templates:
        config = tm.get_default_config('wordpress')
        print(f"\nWordPress default config keys: {list(config.keys())}")

def demo_deployment_manager():
    """Demonstrate deployment manager"""
    print("\n=== Deployment Manager Demo ===")
    
    dm = DeploymentManager()
    
    # List existing projects
    projects = dm.list_projects()
    print(f"Existing projects: {projects if projects else 'None'}")
    
    # Show project structure
    print("\nProject structure will be created in: ./deploys/")

def demo_monitoring():
    """Demonstrate monitoring"""
    print("\n=== Monitoring Demo ===")
    
    monitor = Monitor()
    dm = DeploymentManager()
    
    projects = dm.list_projects()
    if projects:
        project = projects[0]
        status = monitor.get_status(project)
        print(f"Status of '{project}': {status}")
    else:
        print("No projects to monitor")

def main():
    print("Docker Deployment CLI Tool - Programmatic Demo")
    print("=" * 50)
    
    try:
        demo_template_system()
        demo_deployment_manager()
        demo_monitoring()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nTo use the CLI:")
        print("  blastdock templates")
        print("  blastdock init <template>")
        print("  blastdock deploy <project>")
        
    except Exception as e:
        print(f"Demo error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())