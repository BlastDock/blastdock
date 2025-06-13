#!/bin/bash

# BlastDock Automatic Installation Script
# Version: 2.0
# This script will install BlastDock from source with enhanced features

set -euo pipefail  # Exit on any error, undefined variables, and pipe failures

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/BlastDock/blastdock.git"
INSTALL_DIR="$HOME/.local/blastdock"
BIN_DIR="$HOME/.local/bin"
PYTHON_MIN_VERSION="3.8"

# Functions
print_header() {
    echo -e "${BLUE}🚀 BlastDock Automatic Installation v2.0${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${PURPLE}📋 $1${NC}"
}

check_python_version() {
    if command -v python3 &> /dev/null; then
        local version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        local required_version="$PYTHON_MIN_VERSION"
        
        if [ "$(printf '%s\n' "$required_version" "$version" | sort -V | head -n1)" = "$required_version" ]; then
            print_success "Python $version found"
            return 0
        else
            print_error "Python $version found, but $required_version+ is required"
            return 1
        fi
    else
        print_error "Python 3 is not installed"
        return 1
    fi
}

check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local all_good=true
    
    # Check Python
    if ! check_python_version; then
        all_good=false
    fi
    
    # Check pip
    if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
        print_success "pip found"
    else
        print_error "pip is not installed"
        all_good=false
    fi
    
    # Check git
    if command -v git &> /dev/null; then
        print_success "git found"
    else
        print_error "git is not installed"
        all_good=false
    fi
    
    # Check Docker (optional but recommended)
    if command -v docker &> /dev/null; then
        print_success "Docker found"
    else
        print_warning "Docker not found (recommended for BlastDock)"
    fi
    
    if [ "$all_good" = false ]; then
        echo ""
        print_error "Please install missing prerequisites and try again."
        echo ""
        echo "Installation guides:"
        echo "  Python 3.8+: https://www.python.org/downloads/"
        echo "  Git: https://git-scm.com/downloads"
        echo "  Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
    echo ""
}

setup_directories() {
    print_info "Setting up directories..."
    
    # Create directories if they don't exist
    mkdir -p "$BIN_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    
    # Remove existing installation if it exists
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Existing BlastDock installation found. Removing..."
        rm -rf "$INSTALL_DIR"
    fi
    
    print_success "Directories prepared"
}

install_blastdock() {
    print_info "Installing BlastDock to: $INSTALL_DIR"
    
    # Clone the repository
    echo "📥 Cloning BlastDock repository..."
    if ! git clone "$REPO_URL" "$INSTALL_DIR" --quiet; then
        print_error "Failed to clone repository"
        exit 1
    fi
    
    # Change to installation directory
    cd "$INSTALL_DIR"
    
    # Create virtual environment
    echo "🔧 Creating virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    echo "📦 Upgrading pip..."
    pip install --upgrade pip --quiet
    
    # Install dependencies
    echo "📦 Installing dependencies..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt --quiet
    fi
    
    # Install BlastDock in development mode
    echo "🚀 Installing BlastDock..."
    pip install -e . --quiet
    
    print_success "BlastDock installed successfully"
}

setup_executable() {
    print_info "Setting up executable..."
    
    # Create wrapper script
    cat > "$BIN_DIR/blastdock" << EOF
#!/bin/bash
source "$INSTALL_DIR/venv/bin/activate"
exec python -m blastdock "\$@"
EOF
    
    # Make it executable
    chmod +x "$BIN_DIR/blastdock"
    
    print_success "Executable created at $BIN_DIR/blastdock"
}

setup_path() {
    print_info "Setting up PATH..."
    
    # Add to PATH if not already there
    local shell_rc="$HOME/.bashrc"
    if [ -n "${ZSH_VERSION:-}" ]; then
        shell_rc="$HOME/.zshrc"
    elif [ -n "${FISH_VERSION:-}" ]; then
        shell_rc="$HOME/.config/fish/config.fish"
    fi
    
    if [ -f "$shell_rc" ] && ! grep -q "$BIN_DIR" "$shell_rc"; then
        echo "" >> "$shell_rc"
        echo "# Added by BlastDock installer" >> "$shell_rc"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$shell_rc"
        print_success "Added $BIN_DIR to PATH in $shell_rc"
    fi
    
    # Add to current session
    export PATH="$BIN_DIR:$PATH"
}

run_tests() {
    print_info "Running installation tests..."
    
    if command -v blastdock &> /dev/null; then
        if blastdock --version &> /dev/null; then
            print_success "BlastDock is working correctly"
        else
            print_warning "BlastDock installed but version check failed"
        fi
    else
        print_warning "BlastDock command not found in PATH"
        echo "You may need to restart your terminal or run: source ~/.bashrc"
    fi
}

print_completion() {
    echo ""
    echo -e "${GREEN}🎉 BlastDock installation completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📋 Quick Start:${NC}"
    echo "   1. Restart your terminal or run: source ~/.bashrc"
    echo "   2. List templates:    blastdock templates"
    echo "   3. Initialize app:    blastdock init wordpress"
    echo "   4. Deploy app:        blastdock deploy myapp"
    echo ""
    echo -e "${BLUE}📖 Resources:${NC}"
    echo "   Website: https://blastdock.com"
    echo "   Documentation: https://docs.blastdock.com"
    echo "   GitHub: https://github.com/BlastDock/blastdock"
    echo ""
    echo -e "${PURPLE}💡 Pro Tips:${NC}"
    echo "   • Use 'blastdock --help' for all available commands"
    echo "   • Install Docker for the best experience"
    echo "   • Join our community at https://discord.gg/blastdock"
    echo ""
}

# Main installation flow
main() {
    print_header
    check_prerequisites
    setup_directories
    install_blastdock
    setup_executable
    setup_path
    run_tests
    print_completion
}

# Run main function
main "$@"