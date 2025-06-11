#!/bin/bash

# ========================================================
# BlastDock Installation Script
# ========================================================
# This script installs BlastDock and its dependencies
# including Docker and Docker Compose if not already installed
# ========================================================

# Text formatting
BOLD="\e[1m"
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
MAGENTA="\e[35m"
CYAN="\e[36m"
RESET="\e[0m"

# Function to print styled messages
print_message() {
    local style=$1
    local message=$2
    echo -e "${style}${message}${RESET}"
}

print_header() {
    local message=$1
    echo ""
    print_message "${BOLD}${BLUE}" "===================================================="
    print_message "${BOLD}${BLUE}" "  $message"
    print_message "${BOLD}${BLUE}" "===================================================="
    echo ""
}

print_step() {
    local message=$1
    print_message "${BOLD}${CYAN}" "➤ $message"
}

print_success() {
    local message=$1
    print_message "${BOLD}${GREEN}" "✓ $message"
}

print_warning() {
    local message=$1
    print_message "${BOLD}${YELLOW}" "⚠ $message"
}

print_error() {
    local message=$1
    print_message "${BOLD}${RED}" "✗ $message"
}

# Check if script is run as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root"
        print_message "${YELLOW}" "Please run with: sudo ./setup.sh"
        exit 1
    fi
}

# Check system requirements
check_system() {
    print_step "Checking system requirements..."
    
    # Check if running on Ubuntu
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" != "ubuntu" ]; then
            print_warning "This script is optimized for Ubuntu, but detected: $PRETTY_NAME"
            print_warning "The script will continue, but may encounter issues."
            sleep 2
        else
            print_success "Running on Ubuntu $VERSION_ID ($PRETTY_NAME)"
        fi
    else
        print_warning "Unable to determine OS. This script is optimized for Ubuntu."
        print_warning "The script will continue, but may encounter issues."
        sleep 2
    fi
    
    # Check for minimum requirements
    print_step "Checking hardware resources..."
    
    # CPU cores
    CPU_CORES=$(grep -c ^processor /proc/cpuinfo)
    if [ "$CPU_CORES" -lt 2 ]; then
        print_warning "Recommended minimum: 2 CPU cores, detected: $CPU_CORES"
    else
        print_success "CPU cores: $CPU_CORES"
    fi
    
    # Memory
    TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_MEM" -lt 2048 ]; then
        print_warning "Recommended minimum: 2GB RAM, detected: ${TOTAL_MEM}MB"
    else
        print_success "Memory: ${TOTAL_MEM}MB"
    fi
    
    # Disk space
    FREE_DISK=$(df -h / | awk 'NR==2 {print $4}')
    print_success "Free disk space: $FREE_DISK"
}

# Update package lists
update_packages() {
    print_step "Updating package lists..."
    apt-get update -qq
    if [ $? -eq 0 ]; then
        print_success "Package lists updated"
    else
        print_error "Failed to update package lists"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    print_step "Installing required dependencies..."
    apt-get install -y -qq \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common \
        python3 \
        python3-pip \
        python3-venv \
        git
    
    if [ $? -eq 0 ]; then
        print_success "Dependencies installed"
    else
        print_error "Failed to install dependencies"
        exit 1
    fi
}

# Check if Docker is installed
check_docker() {
    if command -v docker &> /dev/null; then
        print_success "Docker is already installed"
        DOCKER_VERSION=$(docker --version)
        print_message "${GREEN}" "  $DOCKER_VERSION"
        return 0
    else
        return 1
    fi
}

# Install Docker
install_docker() {
    if check_docker; then
        return
    fi
    
    print_step "Installing Docker..."
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Set up the stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io
    
    # Verify installation
    if command -v docker &> /dev/null; then
        print_success "Docker installed successfully"
        docker --version | xargs -I{} print_message "${GREEN}" "  {}"
        
        # Start and enable Docker service
        systemctl enable --now docker
        
        # Add current user to docker group
        if [ -n "$SUDO_USER" ]; then
            usermod -aG docker $SUDO_USER
            print_success "Added user $SUDO_USER to the docker group"
            print_warning "You may need to log out and back in for this to take effect"
        fi
    else
        print_error "Docker installation failed"
        exit 1
    fi
}

# Check if Docker Compose is installed
check_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose is already installed"
        COMPOSE_VERSION=$(docker-compose --version)
        print_message "${GREEN}" "  $COMPOSE_VERSION"
        return 0
    elif docker compose version &> /dev/null; then
        print_success "Docker Compose plugin is already installed"
        COMPOSE_PLUGIN_VERSION=$(docker compose version | head -n 1)
        print_message "${GREEN}" "  $COMPOSE_PLUGIN_VERSION"
        return 0
    else
        return 1
    fi
}

# Install Docker Compose
install_docker_compose() {
    if check_docker_compose; then
        return
    fi
    
    print_step "Installing Docker Compose..."
    
    # Install Docker Compose plugin
    apt-get update -qq
    apt-get install -y -qq docker-compose-plugin
    
    # Verify installation
    if docker compose version &> /dev/null; then
        print_success "Docker Compose plugin installed successfully"
        docker compose version | head -n 1 | xargs -I{} print_message "${GREEN}" "  {}"
    else
        print_warning "Docker Compose plugin installation failed, trying standalone version..."
        
        # Install standalone Docker Compose
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        
        # Verify installation
        if command -v docker-compose &> /dev/null; then
            print_success "Docker Compose installed successfully"
            docker-compose --version | xargs -I{} print_message "${GREEN}" "  {}"
        else
            print_error "Docker Compose installation failed"
            exit 1
        fi
    fi
}

# Install BlastDock
install_blastdock() {
    print_step "Installing BlastDock..."
    
    # Clone repository if not already in it
    if [ ! -f "./setup.sh" ]; then
        print_step "Cloning BlastDock repository..."
        git clone https://github.com/BlastDock/blastdock.git
        cd blastdock
    fi
    
    # Create virtual environment
    python3 -m venv venv
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        print_step "Creating requirements.txt file..."
        cat > requirements.txt << 'EOF'
click>=8.0.0
pyyaml>=6.0
jinja2>=3.0.0
python-dotenv>=0.19.0
requests>=2.26.0
termcolor>=1.1.0
prompt_toolkit>=3.0.0
typer>=0.4.0
rich>=10.0.0
EOF
    fi
    
    # Create setup.py if it doesn't exist
    if [ ! -f "setup.py" ]; then
        print_step "Creating setup.py file..."
        cat > setup.py << 'EOF'
from setuptools import setup, find_packages

setup(
    name="blastdock",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
        "jinja2>=3.0.0",
        "python-dotenv>=0.19.0",
        "requests>=2.26.0",
        "termcolor>=1.1.0",
        "prompt_toolkit>=3.0.0",
        "typer>=0.4.0",
        "rich>=10.0.0",
    ],
    entry_points="""
        [console_scripts]
        blastdock=blastdock.cli:main
    """,
)
EOF
    fi
    
    # Create basic package structure if it doesn't exist
    if [ ! -d "blastdock" ]; then
        print_step "Creating basic package structure..."
        mkdir -p blastdock/templates
        
        # Create __init__.py
        cat > blastdock/__init__.py << 'EOF'
# BlastDock package
__version__ = "0.1.0"
EOF
        
        # Create cli.py
        cat > blastdock/cli.py << 'EOF'
import click
import os
import json
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

@click.group()
def main():
    """BlastDock - Docker Deployment CLI Tool"""
    pass

@main.command()
def templates():
    """List available templates"""
    click.echo("Available templates:")
    click.echo("  - wordpress: WordPress with MySQL")
    click.echo("  - nginx: Nginx web server")

@main.command()
@click.argument("template")
@click.option("-i", "--interactive", is_flag=True, help="Interactive mode")
def init(template, interactive):
    """Initialize a new deployment from template"""
    click.echo(f"Initializing {template} deployment")
    if interactive:
        click.echo("Interactive mode enabled")

@main.command()
@click.argument("project")
def deploy(project):
    """Deploy a project"""
    click.echo(f"Deploying {project}")

@main.command()
@click.argument("project")
def status(project):
    """Check project status"""
    click.echo(f"Status for {project}: Running")

@main.command()
@click.argument("project")
def logs(project):
    """View project logs"""
    click.echo(f"Logs for {project}:")
    click.echo("No logs available")

@main.command()
def list():
    """List all initialized projects"""
    deploys_dir = os.path.join(os.getcwd(), "deploys")
    
    if not os.path.exists(deploys_dir):
        click.echo("No projects found. Initialize a project with 'blastdock init <template>'")
        return
    
    projects = [d for d in os.listdir(deploys_dir) if os.path.isdir(os.path.join(deploys_dir, d))]
    
    if not projects:
        click.echo("No projects found. Initialize a project with 'blastdock init <template>'")
        return
    
    table = Table(title="BlastDock Projects", box=box.ROUNDED)
    table.add_column("Project Name", style="cyan")
    table.add_column("Template", style="green")
    table.add_column("Status", style="yellow")
    
    for project in projects:
        config_file = os.path.join(deploys_dir, project, ".blastdock.json")
        template = "Unknown"
        status = "Not deployed"
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    template = config.get("template", "Unknown")
                    status = "Deployed" if os.path.exists(os.path.join(deploys_dir, project, ".deployed")) else "Not deployed"
            except:
                pass
        
        table.add_row(project, template, status)
    
    console.print(table)

@main.command()
@click.argument("project")
def config(project):
    """Show project configuration"""
    deploys_dir = os.path.join(os.getcwd(), "deploys")
    project_dir = os.path.join(deploys_dir, project)
    
    if not os.path.exists(project_dir):
        click.echo(f"Project '{project}' not found. Initialize it with 'blastdock init <template>'")
        return
    
    config_file = os.path.join(project_dir, ".blastdock.json")
    env_file = os.path.join(project_dir, ".env")
    
    console.print(f"[bold cyan]Configuration for project:[/] [bold green]{project}[/]\n")
    
    # Display project metadata
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
                table = Table(title="Project Metadata", box=box.ROUNDED)
                table.add_column("Property", style="cyan")
                table.add_column("Value", style="green")
                
                for key, value in config.items():
                    if isinstance(value, dict) or isinstance(value, list):
                        value = json.dumps(value, indent=2)
                    table.add_row(key, str(value))
                
                console.print(table)
        except Exception as e:
            console.print(f"[bold red]Error reading config file:[/] {str(e)}")
    else:
        console.print("[yellow]No .blastdock.json configuration file found[/]")
    
    # Display environment variables
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                env_vars = {}
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key] = value
                
                if env_vars:
                    table = Table(title="Environment Variables", box=box.ROUNDED)
                    table.add_column("Variable", style="cyan")
                    table.add_column("Value", style="green")
                    
                    for key, value in env_vars.items():
                        # Mask passwords and sensitive information
                        if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                            value = "*****"
                        table.add_row(key, value)
                    
                    console.print(table)
                else:
                    console.print("[yellow]No environment variables found[/]")
        except Exception as e:
            console.print(f"[bold red]Error reading .env file:[/] {str(e)}")
    else:
        console.print("[yellow]No .env file found[/]")

if __name__ == "__main__":
    main()
EOF
    fi
    
    # Install requirements
    ./venv/bin/pip install -r requirements.txt
    
    # Install BlastDock in development mode
    ./venv/bin/pip install -e .
    
    if [ $? -eq 0 ]; then
        print_success "BlastDock installed successfully"
    else
        print_error "BlastDock installation failed"
        exit 1
    fi
}

# Create activation script
create_activation_script() {
    print_step "Creating activation script..."
    
    cat > activate.sh << 'EOF'
#!/bin/bash
# Activate the BlastDock environment
source venv/bin/activate
echo "BlastDock environment activated. Run 'blastdock --help' to get started."
EOF
    
    chmod +x activate.sh
    print_success "Activation script created: ./activate.sh"
}

# Print final instructions
print_instructions() {
    print_header "Installation Complete!"
    
    echo -e "${BOLD}To use BlastDock:${RESET}"
    echo -e "  1. Activate the environment:  ${YELLOW}source ./activate.sh${RESET}"
    echo -e "  2. List available templates:  ${YELLOW}blastdock templates${RESET}"
    echo -e "  3. Initialize a new project:  ${YELLOW}blastdock init <template>${RESET}"
    echo -e "  4. Deploy your application:   ${YELLOW}blastdock deploy <project>${RESET}"
    echo ""
    echo -e "${BOLD}For more information:${RESET}"
    echo -e "  - View help:                  ${YELLOW}blastdock --help${RESET}"
    echo -e "  - Read documentation:         ${YELLOW}less README.md${RESET}"
    echo -e "  - Visit website:              ${YELLOW}https://blastdock.com${RESET}"
    echo -e "  - GitHub repository:          ${YELLOW}https://github.com/BlastDock/blastdock${RESET}"
    echo ""
    
    if [ -n "$SUDO_USER" ]; then
        print_warning "You may need to log out and back in for Docker permissions to take effect"
    fi
    
    print_message "${BOLD}${GREEN}" "Thank you for installing BlastDock!"
}

# Recommend Ubuntu server
recommend_ubuntu() {
    print_header "Recommended Server Configuration"
    
    echo -e "${BOLD}For optimal performance, we recommend:${RESET}"
    echo -e "  - ${CYAN}Ubuntu Server 22.04 LTS${RESET} (or newer)"
    echo -e "  - At least ${CYAN}2 CPU cores${RESET}"
    echo -e "  - At least ${CYAN}4GB RAM${RESET}"
    echo -e "  - At least ${CYAN}20GB free disk space${RESET}"
    echo ""
    echo -e "${BOLD}Cloud Provider Options:${RESET}"
    echo -e "  - ${BOLD}${GREEN}EcoStack.Cloud:${RESET} ${BOLD}HIGHLY RECOMMENDED${RESET} - Optimized for BlastDock (4GB RAM / 2 CPUs)"
    echo -e "  - ${CYAN}Digital Ocean:${RESET} Basic Droplet (4GB RAM / 2 CPUs)"
    echo ""
    echo -e "${BOLD}Security Recommendations:${RESET}"
    echo -e "  - Use SSH key authentication instead of passwords"
    echo -e "  - Enable automatic security updates"
    echo -e "  - Configure a firewall (UFW) to restrict access"
    echo -e "  - Consider using a reverse proxy with SSL (like Nginx or Traefik)"
    echo ""
}

# Main installation process
main() {
    print_header "BlastDock Installation"
    
    recommend_ubuntu
    
    check_root
    check_system
    update_packages
    install_dependencies
    install_docker
    install_docker_compose
    install_blastdock
    create_activation_script
    print_instructions
}

# Run the installation
main
