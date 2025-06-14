#!/bin/bash
# BlastDock PyPI Publishing Script
# This script helps you safely publish BlastDock to PyPI

set -e  # Exit on any error

echo "🚀 BlastDock PyPI Publishing Script"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Step 2: Run tests if available
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

# Step 3: Install/upgrade build tools
print_status "Step 3: Installing/upgrading build tools..."
pip install --upgrade pip setuptools wheel build twine || {
    print_error "Failed to install build tools"
    exit 1
}
print_success "Build tools ready"

# Step 4: Build the package
print_status "Step 4: Building the package..."
python -m build || {
    print_error "Package build failed"
    exit 1
}
print_success "Package built successfully"

# Step 5: Check the built package
print_status "Step 5: Checking built package..."
twine check dist/* || {
    print_error "Package check failed"
    exit 1
}
print_success "Package check passed"

# Step 6: Show what will be uploaded
print_status "Step 6: Package contents:"
ls -la dist/
echo ""

# Step 7: Ask for confirmation before proceeding
echo "📋 Pre-publication Checklist:"
echo "   ✅ Package builds successfully"
echo "   ✅ Basic CLI tests pass"
echo "   ✅ Package structure validated"
echo ""

print_warning "IMPORTANT SECURITY NOTES:"
echo "   🔒 This script does NOT automatically upload using stored tokens"
echo "   🔒 You must manually provide authentication for security"
echo "   🔒 Never commit PyPI tokens to version control"
echo ""

read -p "Do you want to proceed with TestPyPI upload first? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Publishing cancelled by user"
    exit 0
fi

# Step 8: Upload to TestPyPI first
print_status "Step 8: Uploading to TestPyPI..."
echo "You will be prompted for your TestPyPI credentials."
echo "If you have a token, use '__token__' as username and your token as password."
echo ""

twine upload --repository testpypi dist/* || {
    print_error "TestPyPI upload failed"
    exit 1
}

print_success "Successfully uploaded to TestPyPI!"
echo ""
print_status "Test the TestPyPI package:"
echo "   pip install -i https://test.pypi.org/simple/ blastdock"
echo "   blastdock --help"
echo ""

# Step 9: Confirm for production PyPI
read -p "TestPyPI upload successful. Upload to production PyPI? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Production upload cancelled. Package is available on TestPyPI for testing."
    exit 0
fi

# Step 10: Upload to production PyPI
print_status "Step 10: Uploading to production PyPI..."
echo "You will be prompted for your PyPI credentials."
echo "If you have a token, use '__token__' as username and your token as password."
echo ""

twine upload dist/* || {
    print_error "PyPI upload failed"
    exit 1
}

print_success "🎉 Successfully published BlastDock to PyPI!"
echo ""
print_status "Your package is now available:"
echo "   pip install blastdock"
echo "   https://pypi.org/project/blastdock/"
echo ""
print_status "Next steps:"
echo "   1. Test the published package: pip install blastdock"
echo "   2. Update documentation with new version"
echo "   3. Create a GitHub release"
echo "   4. Announce the release"
echo ""
print_success "Publishing complete! 🚀"