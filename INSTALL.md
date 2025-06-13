# BlastDock Installation Guide

## Prerequisites

Before installing BlastDock v1.1.0, make sure you have:

1. **Python 3.8+** installed
2. **Docker** installed and running
3. **Docker Compose** installed
4. **pip** (Python package manager) installed
5. **Public IP** (recommended for SSL certificates and domain routing)

### Verify Prerequisites

```bash
# Check Python version
python3 --version

# Check Docker
docker --version
docker-compose --version

# Check if Docker is running
docker ps
```

## Installation Methods

### 🚀 **Method 1: Install from PyPI (Recommended)**

```bash
# Install the latest version
pip install blastdock

# Install specific version
pip install blastdock==1.1.0

# Upgrade existing installation
pip install --upgrade blastdock
```

### 🛠 **Method 2: Install from Source**

```bash
# Clone the repository
git clone https://github.com/BlastDock/blastdock.git
cd blastdock

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### 🐍 **Method 3: Using Virtual Environment (Recommended for Development)**

```bash
# Create virtual environment
python3 -m venv blastdock-env

# Activate virtual environment
source blastdock-env/bin/activate  # Linux/Mac
# or
blastdock-env\Scripts\activate     # Windows

# Install BlastDock
pip install blastdock
```

## 🔍 Verify Installation

```bash
# Check if BlastDock is installed
blastdock --version

# Should show: BlastDock, version 1.1.0

# List available templates
blastdock templates

# Check Traefik status (new in v1.1.0)
blastdock traefik status
```

## 🚀 Quick Start After Installation

### Set Up Traefik (Recommended for Production)

```bash
# Install Traefik with SSL support
blastdock traefik install --email your@email.com --domain yourdomain.com

# Verify Traefik is running
blastdock traefik status
```

### Deploy Your First Application

```bash
# Deploy WordPress with automatic SSL
blastdock init wordpress --traefik --ssl
blastdock deploy mywordpress

# ✅ Access at https://mywordpress.yourdomain.com
```

## 🚨 Troubleshooting

### Common Issues

#### 1. **Python/Installation Issues**
```bash
# Python command not found
python3 --version  # Use python3 instead of python

# Permission denied errors
pip install --user blastdock  # Install for current user only

# Virtual environment issues
python3 -m venv venv && source venv/bin/activate
```

#### 2. **Docker Issues**
```bash
# Docker daemon not running
sudo systemctl start docker  # Linux
# or restart Docker Desktop

# Permission denied
sudo usermod -aG docker $USER  # Add user to docker group
newgrp docker  # Refresh group membership
```

#### 3. **Traefik Installation Issues**
```bash
# Port 80/443 already in use
sudo lsof -i :80  # Check what's using port 80
sudo lsof -i :443  # Check what's using port 443

# Stop conflicting services
sudo systemctl stop apache2  # or nginx
```

#### 4. **SSL Certificate Issues**
```bash
# Domain not pointing to server
dig yourdomain.com  # Check DNS resolution

# Firewall blocking ports
sudo ufw allow 80  # Allow HTTP
sudo ufw allow 443  # Allow HTTPS
```

#### 5. **Import/Module Errors**
```bash
# Reinstall with dependencies
pip uninstall blastdock
pip install --no-cache-dir blastdock

# Check installation
pip show blastdock
```

### Getting Help

If you encounter issues:

1. Check the error message carefully
2. Verify prerequisites are met
3. Try installation in a virtual environment
4. Check file permissions

### Testing the Installation

After installation, test with a simple command:

```bash
# List available templates
blastdock templates

# Try initializing a project (don't deploy yet)
blastdock init mysql
# Enter a test project name: testdb
# This should create the project structure without errors
```

## Next Steps

Once installed successfully:

1. Read the [README.md](README.md) for usage instructions
2. Try the quick start guide
3. Explore available templates with `blastdock templates`
4. Initialize your first project with `blastdock init <template>`

## Uninstallation

To remove the tool:

```bash
pip uninstall blastdock
```

To remove all project data:

```bash
rm -rf ./deploys
rm -rf ~/.blastdock
```