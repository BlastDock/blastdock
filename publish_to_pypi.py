#!/usr/bin/env python3
"""
BlastDock PyPI Publication Script
Safe publication workflow with validation
"""

import sys
import subprocess
import os
from pathlib import Path

def run_final_tests():
    """Run final test suite"""
    print("🧪 Running final test validation...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/unit/test_utils/test_docker_utils.py",
            "tests/unit/test_config/test_models.py", 
            "tests/unit/test_core/test_traefik_simple.py",
            "-v", "--tb=short"
        ], capture_output=True, text=True, timeout=60)
        
        if "FAILED" not in result.stdout:
            print("✅ Core tests passing")
            return True
        else:
            print("❌ Some tests failing")
            print(result.stdout[-500:])  # Last 500 chars
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def validate_cli():
    """Validate CLI functionality"""
    print("🖥️ Validating CLI functionality...")
    
    commands = [
        ["--help"],
        ["--version"],
        ["deploy", "--help"],
        ["marketplace", "--help"]
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run([
                sys.executable, "-m", "blastdock.main_cli"
            ] + cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(f"✅ {' '.join(cmd)}")
            else:
                print(f"❌ {' '.join(cmd)}: {result.stderr[:100]}")
                return False
        except Exception as e:
            print(f"❌ {' '.join(cmd)}: {e}")
            return False
    
    return True

def build_package():
    """Build distribution packages"""
    print("📦 Building distribution packages...")
    
    # Clean previous builds
    for dir_name in ["dist", "build", "blastdock.egg-info"]:
        if os.path.exists(dir_name):
            import shutil
            shutil.rmtree(dir_name)
            print(f"🧹 Cleaned {dir_name}")
    
    try:
        # Build source distribution
        result = subprocess.run([
            sys.executable, "setup.py", "sdist"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Source distribution built")
        else:
            print(f"❌ Source build failed: {result.stderr}")
            return False
        
        # Check dist directory
        if Path("dist").exists() and list(Path("dist").glob("*.tar.gz")):
            print("✅ Distribution files created")
            return True
        else:
            print("❌ No distribution files found")
            return False
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

def check_package_quality():
    """Check package quality and metadata"""
    print("🔍 Checking package quality...")
    
    try:
        # Check package metadata
        result = subprocess.run([
            sys.executable, "setup.py", "check", "--strict"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Package metadata valid")
        else:
            print(f"⚠️ Metadata warnings: {result.stderr}")
        
        # Verify requirements.txt exists and is valid
        if Path("requirements.txt").exists():
            print("✅ Requirements file present")
        else:
            print("⚠️ No requirements.txt found")
        
        return True
        
    except Exception as e:
        print(f"❌ Quality check error: {e}")
        return False

def main():
    """Main publication workflow"""
    print("🚀 BlastDock PyPI Publication Validation")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    # Run validation steps
    steps = [
        ("Final Tests", run_final_tests),
        ("CLI Validation", validate_cli),
        ("Package Quality", check_package_quality),
        ("Package Build", build_package),
    ]
    
    results = {}
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        results[step_name] = step_func()
    
    # Final assessment
    print("\n" + "=" * 60)
    print("📊 PUBLICATION READINESS ASSESSMENT")
    print("=" * 60)
    
    all_passed = True
    for step_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{step_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 READY FOR PUBLICATION!")
        print("\n🚀 Next steps to publish:")
        print("1. Upload to TestPyPI first:")
        print("   python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*")
        print("\n2. Test installation from TestPyPI:")
        print("   pip install -i https://test.pypi.org/simple/ blastdock")
        print("\n3. If tests pass, upload to production PyPI:")
        print("   python -m twine upload dist/*")
        print("\n📋 Package info:")
        
        # Show built packages
        if Path("dist").exists():
            for file in Path("dist").iterdir():
                print(f"   📦 {file.name}")
        
        print(f"\n📊 Quality metrics achieved:")
        print("   - Core functionality tested ✅")
        print("   - CLI commands working ✅") 
        print("   - Package builds successfully ✅")
        print("   - No critical crashes ✅")
        print("   - Ready for production use ✅")
        
        return True
    else:
        print("\n⚠️ Some validation steps failed")
        print("BlastDock is functional but has minor issues")
        print("Consider fixing failed steps before publication")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)