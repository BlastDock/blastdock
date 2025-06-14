#!/usr/bin/env python3
"""
BlastDock Test Runner
Runs comprehensive tests and generates coverage reports
"""

import sys
import subprocess
import os
from pathlib import Path

def install_test_dependencies():
    """Install test dependencies"""
    print("📦 Installing test dependencies...")
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt", "--break-system-packages"
        ], check=True, capture_output=True)
        print("✅ Test dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install test dependencies: {e}")
        print(f"Error output: {e.stderr.decode()}")
        return False

def run_basic_tests():
    """Run basic tests without coverage requirements"""
    print("\n🧪 Running basic tests...")
    
    try:
        # Run tests with basic coverage (no 100% requirement)
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/unit/test_cli/test_main_cli.py",
            "tests/unit/test_cli/test_deploy.py", 
            "tests/unit/test_utils/test_docker_utils.py",
            "tests/unit/test_config/test_models.py",
            "-v",
            "--tb=short",
            "--cov=blastdock",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-fail-under=50"  # Lower threshold for initial run
        ], capture_output=True, text=True)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Basic tests passed!")
            return True
        else:
            print(f"❌ Tests failed with return code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def check_test_structure():
    """Check test file structure"""
    print("\n📁 Checking test structure...")
    
    test_files = [
        "tests/__init__.py",
        "tests/conftest.py",
        "tests/unit/test_cli/test_main_cli.py",
        "tests/unit/test_cli/test_deploy.py",
        "tests/unit/test_utils/test_docker_utils.py",
        "tests/unit/test_config/test_models.py",
    ]
    
    all_exist = True
    for test_file in test_files:
        if Path(test_file).exists():
            print(f"✅ {test_file}")
        else:
            print(f"❌ {test_file} - MISSING")
            all_exist = False
    
    return all_exist

def run_import_tests():
    """Test that core modules can be imported"""
    print("\n🔍 Testing module imports...")
    
    imports_to_test = [
        "blastdock",
        "blastdock.main_cli",
        "blastdock.cli.deploy",
        "blastdock.utils.docker_utils",
        "blastdock.config",
        "blastdock.performance",
        "blastdock.marketplace"
    ]
    
    all_imports_ok = True
    for module in imports_to_test:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module} - {e}")
            all_imports_ok = False
        except Exception as e:
            print(f"⚠️  {module} - {e}")
    
    return all_imports_ok

def run_cli_basic_test():
    """Test basic CLI functionality"""
    print("\n🖥️  Testing CLI basics...")
    
    try:
        # Test CLI help
        result = subprocess.run([
            sys.executable, "-m", "blastdock.main_cli", "--help"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ CLI help works")
            return True
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ CLI help timed out")
        return False
    except Exception as e:
        print(f"❌ CLI test error: {e}")
        return False

def generate_test_report():
    """Generate a test report"""
    print("\n📊 Test Summary Report")
    print("=" * 50)
    
    # Check structure
    structure_ok = check_test_structure()
    print(f"Test Structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    
    # Check imports
    imports_ok = run_import_tests()
    print(f"Module Imports: {'✅ PASS' if imports_ok else '❌ FAIL'}")
    
    # Check CLI
    cli_ok = run_cli_basic_test()
    print(f"CLI Functionality: {'✅ PASS' if cli_ok else '❌ FAIL'}")
    
    # Try to install test deps
    deps_ok = install_test_dependencies()
    print(f"Test Dependencies: {'✅ PASS' if deps_ok else '❌ FAIL'}")
    
    # Run tests if possible
    if deps_ok:
        tests_ok = run_basic_tests()
        print(f"Unit Tests: {'✅ PASS' if tests_ok else '❌ FAIL'}")
    else:
        tests_ok = False
        print("Unit Tests: ⚠️  SKIPPED (dependencies not available)")
    
    print("\n" + "=" * 50)
    
    if all([structure_ok, imports_ok, cli_ok, tests_ok]):
        print("🎉 ALL TESTS PASSED!")
        print("\n📋 Next Steps:")
        print("1. Add more test files to reach 100% coverage")
        print("2. Run: pytest --cov=blastdock --cov-fail-under=100")
        print("3. Review coverage report: open htmlcov/index.html")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("\n🔧 Issues to fix:")
        if not structure_ok:
            print("- Fix test file structure")
        if not imports_ok:
            print("- Fix module import issues")
        if not cli_ok:
            print("- Fix CLI functionality")
        if not deps_ok:
            print("- Install test dependencies")
        if not tests_ok:
            print("- Fix unit test failures")
        return False

def main():
    """Main test runner"""
    print("🚀 BlastDock Test Runner")
    print("========================")
    
    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Add project to Python path
    sys.path.insert(0, str(project_root))
    
    success = generate_test_report()
    
    if success:
        print("\n🎯 Ready for production testing!")
        sys.exit(0)
    else:
        print("\n🔧 Fix issues before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()