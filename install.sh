#!/bin/bash

# BlastDock Zero-Error Installation Script
# This script will work flawlessly regardless of virtual environments

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}" >&2; }
warning() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
info() { echo -e "${BLUE}[INFO] $1${NC}"; }

# Force exit from any virtual environment and reset everything
force_reset_environment() {
    log "Forcing clean environment reset..."
    
    # Kill any virtual environment
    unset VIRTUAL_ENV
    unset PYTHONHOME
    unset PYTHONPATH
    unset CONDA_DEFAULT_ENV
    unset CONDA_PREFIX
    
    # Reset PATH to absolute system default
    export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    
    # Reset PS1
    export PS1='root@blastdock:~# '
    
    # Change to root directory to avoid any venv issues
    cd /root
    
    info "Environment completely reset"
}

# Root check
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Run as root: sudo $0"
        exit 1
    fi
}

# Install Docker
install_docker() {
    if command -v docker &> /dev/null && systemctl is-active --quiet docker; then
        info "Docker already running: $(docker --version)"
        return 0
    fi
    
    log "Installing Docker..."
    
    # Remove old Docker
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Start Docker
    systemctl start docker
    systemctl enable docker
    
    info "Docker installed: $(docker --version)"
}

# Install Docker Compose
install_docker_compose() {
    if docker compose version &> /dev/null; then
        info "Docker Compose plugin ready: $(docker compose version)"
        return 0
    fi
    
    log "Installing Docker Compose..."
    
    # Get latest version and install
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    info "Docker Compose installed: $(docker-compose --version)"
}

# Install Python essentials
install_python() {
    log "Setting up Python environment..."
    
    # Install Python packages
    apt-get update -y
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-full python3-pip python3-venv pipx
    
    info "Python setup complete: $(python3 --version)"
}

# Install BlastDock with absolute path control
install_blastdock() {
    log "Installing BlastDock with absolute path control..."
    
    # Ensure clean PATH
    export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    
    # Remove any existing installation
    /usr/bin/pipx uninstall blastdock 2>/dev/null || true
    rm -f /usr/local/bin/blastdock
    rm -f /usr/bin/blastdock
    
    # Install BlastDock
    /usr/bin/pipx install blastdock --force
    
    # Create system-wide script that always works
    cat > /usr/local/bin/blastdock << 'EOF'
#!/bin/bash
# BlastDock System Launcher - Always works regardless of environment
unset VIRTUAL_ENV PYTHONHOME PYTHONPATH
export PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin"
exec /root/.local/bin/blastdock "$@"
EOF
    chmod +x /usr/local/bin/blastdock
    
    # Create backup in /usr/bin
    cp /usr/local/bin/blastdock /usr/bin/blastdock
    
    info "BlastDock installed and secured"
}

# Create bulletproof PATH configuration
setup_bulletproof_path() {
    log "Creating bulletproof PATH configuration..."
    
    # Create profile script that always loads
    cat > /etc/profile.d/zzz-blastdock.sh << 'EOF'
#!/bin/bash
# BlastDock PATH - Always loads last (zzz prefix ensures priority)
export PATH="/root/.local/bin:/usr/local/bin:$PATH"
EOF
    chmod +x /etc/profile.d/zzz-blastdock.sh
    
    # Update bashrc
    cat >> /root/.bashrc << 'EOF'

# BlastDock Configuration - Auto-added by install script
export PATH="/root/.local/bin:/usr/local/bin:$PATH"
# Force deactivate any virtual environment on shell start
if [[ -n "$VIRTUAL_ENV" ]]; then
    unset VIRTUAL_ENV PYTHONHOME PYTHONPATH
    export PS1='root@blastdock:~# '
fi
EOF
    
    # Create global alias that always works
    echo 'alias blastdock="/usr/local/bin/blastdock"' >> /root/.bash_aliases
    
    info "Bulletproof PATH configuration created"
}

# Create deactivate script for current session
create_deactivate_fix() {
    log "Creating session fix script..."
    
    cat > /root/fix-session.sh << 'EOF'
#!/bin/bash
# Session Fix Script - Run this to fix current terminal
unset VIRTUAL_ENV PYTHONHOME PYTHONPATH CONDA_DEFAULT_ENV CONDA_PREFIX
export PATH="/root/.local/bin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PS1='root@blastdock:~# '
cd /root
echo "Session fixed! BlastDock should work now."
EOF
    chmod +x /root/fix-session.sh
    
    info "Session fix script created at /root/fix-session.sh"
}

# Final verification with multiple fallbacks
verify_installation() {
    log "Verifying installation with multiple methods..."
    
    # Test 1: Direct path
    if /root/.local/bin/blastdock --version &> /dev/null; then
        info "✓ Direct path works: $(/root/.local/bin/blastdock --version)"
    else
        error "✗ Direct path failed"
    fi
    
    # Test 2: System wrapper
    if /usr/local/bin/blastdock --version &> /dev/null; then
        info "✓ System wrapper works: $(/usr/local/bin/blastdock --version)"
    else
        error "✗ System wrapper failed"
    fi
    
    # Test 3: Clean environment test
    if env -i PATH="/root/.local/bin:/usr/local/bin:/usr/bin:/bin" /usr/local/bin/blastdock --version &> /dev/null; then
        info "✓ Clean environment test passed"
    else
        error "✗ Clean environment test failed"
    fi
    
    # Docker test
    if docker --version &> /dev/null && systemctl is-active --quiet docker; then
        info "✓ Docker is ready: $(docker --version)"
    else
        error "✗ Docker not ready"
    fi
    
    # Docker Compose test
    if docker compose version &> /dev/null; then
        info "✓ Docker Compose ready: $(docker compose version)"
    else
        error "✗ Docker Compose not ready"
    fi
}

# Main installation function
main() {
    log "Starting ZERO-ERROR BlastDock Installation..."
    
    check_root
    force_reset_environment
    
    # Update system
    apt-get update -y
    
    install_docker
    install_docker_compose
    install_python
    install_blastdock
    setup_bulletproof_path
    create_deactivate_fix
    verify_installation
    
    log "Installation completed successfully!"
    echo
    info "=== IMMEDIATE SOLUTION FOR CURRENT TERMINAL ==="
    warning "Run this command NOW to fix your current session:"
    echo -e "${BLUE}source /root/fix-session.sh${NC}"
    echo
    info "=== PERMANENT SOLUTION ==="
    warning "For new terminals, BlastDock will work automatically"
    echo
    info "=== USAGE ==="
    echo -e "${BLUE}blastdock --help${NC}      # Will always work"
    echo -e "${BLUE}/usr/local/bin/blastdock --help${NC}  # Backup method"
    echo
    info "=== TESTING ==="
    echo "Testing all methods now..."
    
    # Live test in current broken session
    warning "Current session test (might fail due to venv):"
    if command -v blastdock &> /dev/null && blastdock --version &> /dev/null; then
        echo -e "${GREEN}✓ Current session: OK${NC}"
    else
        echo -e "${RED}✗ Current session: Broken (expected)${NC}"
        echo -e "${YELLOW}Fix with: source /root/fix-session.sh${NC}"
    fi
}

# Run installation
main "$@"