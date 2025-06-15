#!/usr/bin/env python3
"""
Build script for PyPI that ensures compatible metadata version

This script:
1. Builds the distribution files
2. Fixes the metadata version to be compatible with twine/PyPI
3. Validates the packages before upload
"""

import subprocess
import sys
import shutil
from pathlib import Path
from fix_metadata import fix_wheel_metadata, fix_sdist_metadata

def run_command(cmd, check=True):
    """Run a command and return the result"""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    
    if result.stdout:
        print(result.stdout)
    
    return result

def clean_build_dirs():
    """Clean build directories"""
    print("Cleaning build directories...")
    dirs_to_clean = ['dist', 'build', 'blastdock.egg-info']
    for dir_name in dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
    print("Build directories cleaned.")

def build_distributions():
    """Build wheel and source distributions"""
    print("\nBuilding distributions...")
    run_command([sys.executable, '-m', 'build'])
    print("Distributions built successfully.")

def fix_metadata():
    """Fix metadata version in distributions"""
    print("\nFixing metadata versions...")
    dist_dir = Path('dist')
    
    # Fix all wheel files
    for wheel in dist_dir.glob('*.whl'):
        fix_wheel_metadata(wheel)
    
    # Fix all sdist files
    for sdist in dist_dir.glob('*.tar.gz'):
        fix_sdist_metadata(sdist)
    
    print("Metadata versions fixed.")

def validate_packages():
    """Validate packages with twine check"""
    print("\nValidating packages with twine...")
    result = run_command(['twine', 'check', 'dist/*'], check=False)
    
    if result.returncode != 0:
        print("ERROR: Package validation failed!")
        print(result.stderr)
        return False
    
    print("All packages passed validation!")
    return True

def main():
    """Main build process"""
    print("BlastDock PyPI Build Script")
    print("=" * 60)
    
    # Step 1: Clean
    clean_build_dirs()
    
    # Step 2: Build
    build_distributions()
    
    # Step 3: Fix metadata
    fix_metadata()
    
    # Step 4: Validate
    if not validate_packages():
        print("\nBuild failed validation. Please fix the issues and try again.")
        return 1
    
    print("\n" + "=" * 60)
    print("SUCCESS! Packages are ready for upload to PyPI.")
    print("\nTo upload to PyPI, run:")
    print("  twine upload dist/*")
    print("\nTo upload to TestPyPI first, run:")
    print("  twine upload --repository testpypi dist/*")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())