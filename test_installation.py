#!/usr/bin/env python3
"""
Test script to verify blastdock installation
"""

import sys
import os

# Add the blastdock directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'blastdock'))

def test_imports():
    """Test that all modules can be imported"""
    try:
        from cli import cli
        print("✓ CLI module imported successfully")
        
        from core.template_manager import TemplateManager
        print("✓ TemplateManager imported successfully")
        
        from core.deployment_manager import DeploymentManager
        print("✓ DeploymentManager imported successfully")
        
        from core.monitor import Monitor
        print("✓ Monitor imported successfully")
        
        from utils.helpers import get_deploys_dir
        print("✓ Helper utilities imported successfully")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_template_manager():
    """Test template manager functionality"""
    try:
        from core.template_manager import TemplateManager
        tm = TemplateManager()
        templates = tm.list_templates()
        print(f"✓ Found {len(templates)} templates: {', '.join(templates)}")
        
        if 'wordpress' in templates:
            info = tm.get_template_info('wordpress')
            print(f"✓ WordPress template info: {info.get('description', 'No description')}")
        
        return True
    except Exception as e:
        print(f"✗ Template manager error: {e}")
        return False

def test_directory_structure():
    """Test that required directories exist"""
    required_dirs = [
        'blastdock',
        'blastdock/core',
        'blastdock/utils',
        'blastdock/templates'
    ]
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✓ Directory exists: {dir_path}")
        else:
            print(f"✗ Missing directory: {dir_path}")
            return False
    
    return True

def main():
    print("Docker Deployment CLI Tool - Installation Test")
    print("=" * 50)
    
    tests = [
        ("Directory Structure", test_directory_structure),
        ("Module Imports", test_imports),
        ("Template Manager", test_template_manager),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        
    print("\n" + "=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Installation looks good.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Install the package: pip install -e .")
        print("3. Test the CLI: blastdock --help")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())