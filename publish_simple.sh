#!/bin/bash
# Simple BlastDock PyPI Publishing Script (without pip installs)

set -e  # Exit on any error

echo "🚀 BlastDock PyPI Publishing Script (Simple)"
echo "============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "setup.py" ] && [ ! -f "pyproject.toml" ]; then
    print_error "No setup.py or pyproject.toml found. Are you in the BlastDock directory?"
    exit 1
fi

print_status "Starting BlastDock publishing process..."

# Step 1: Clean previous builds
print_status "Step 1: Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info/
print_success "Cleaned previous builds"

# Step 2: Run basic tests
print_status "Step 2: Running basic tests..."

# Test imports
python3 -c "import blastdock; print('✅ BlastDock imports successfully')" || {
    print_error "BlastDock import failed"
    exit 1
}

# Test basic CLI
python3 -c "
from click.testing import CliRunner
from blastdock.main_cli import cli
runner = CliRunner()
result = runner.invoke(cli, ['--help'])
if result.exit_code == 0:
    print('✅ CLI help works')
else:
    print('❌ CLI help failed')
    exit(1)
" || {
    print_error "CLI tests failed"
    exit 1
}

print_success "Basic tests passed"

# Step 3: Check for build tools
print_status "Step 3: Checking for required tools..."

# Try to find setuptools
python3 -c "import setuptools; print('✅ setuptools available')" 2>/dev/null || {
    print_warning "setuptools not available, trying alternate build method"
}

# Step 4: Build the package using setup.py
print_status "Step 4: Building the package..."

if [ -f "setup.py" ]; then
    python3 setup.py sdist bdist_wheel || {
        print_warning "Standard build failed, trying simple sdist..."
        python3 setup.py sdist || {
            print_error "Package build failed"
            exit 1
        }
    }
elif [ -f "pyproject.toml" ]; then
    python3 -m build || {
        print_error "Build failed - need to install build tools"
        echo "Run: pip install build"
        exit 1
    }
else
    print_error "No setup.py or pyproject.toml found"
    exit 1
fi

print_success "Package built successfully"

# Step 5: Show what was built
print_status "Step 5: Package contents:"
ls -la dist/
echo ""

# Step 6: Show package info
if [ -f "dist/"*.whl ]; then
    print_status "Wheel package created: $(ls dist/*.whl)"
fi

if [ -f "dist/"*.tar.gz ]; then
    print_status "Source package created: $(ls dist/*.tar.gz)"
fi

# Step 7: Instructions for manual upload
print_status "Step 7: Ready for upload!"
echo ""
print_warning "MANUAL UPLOAD INSTRUCTIONS:"
echo ""
echo "To upload to TestPyPI first (recommended):"
echo "  twine upload --repository testpypi dist/*"
echo ""
echo "To upload to production PyPI:"
echo "  twine upload dist/*"
echo ""
echo "If you need to install twine:"
echo "  pip install twine"
echo ""
echo "Authentication options:"
echo "  1. Use __token__ as username and your PyPI token as password"
echo "  2. Set environment variables:"
echo "     export TWINE_USERNAME=__token__"
echo "     export TWINE_PASSWORD=your_token_here"
echo "  3. Create ~/.pypirc with your credentials"
echo ""

# Step 8: Test local installation
print_status "Step 8: Testing local installation..."
echo "You can test the built package locally with:"
echo "  pip install dist/blastdock-*.whl"
echo ""

# Step 9: Final checklist
print_success "🎯 Pre-upload Checklist Complete:"
echo "   ✅ Package builds successfully"
echo "   ✅ Basic CLI tests pass"
echo "   ✅ Distribution files created"
echo ""

print_warning "Before uploading to PyPI:"
echo "   🔍 Test the package: pip install dist/blastdock-*.whl"
echo "   🧪 Run: blastdock --help"
echo "   📋 Verify all functionality works"
echo "   🚀 Upload to TestPyPI first"
echo ""

print_success "Build complete! Ready for manual upload to PyPI 🚀"

# Show final commands
echo ""
echo "=== UPLOAD COMMANDS ==="
echo "TestPyPI: twine upload --repository testpypi dist/*"
echo "PyPI:     twine upload dist/*"
echo "======================="