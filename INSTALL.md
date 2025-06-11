# Installation Guide

## Prerequisites

Before installing the Docker Deployment CLI Tool, make sure you have:

1. **Python 3.8+** installed
2. **Docker** installed and running
3. **Docker Compose** installed
4. **pip** (Python package manager) installed

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

## Installation Steps

### 1. Clone or Download the Project

```bash
# If using git
git clone <repository-url>
cd blastdock

# Or download and extract the archive
```

### 2. Run Installation Test

```bash
python3 test_installation.py
```

This will verify that all files are in place and modules can be imported.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install the Package

```bash
# Install in development mode (recommended)
pip install -e .

# Or install normally
pip install .
```

### 5. Verify Installation

```bash
# Check if the command is available
blastdock --help

# List available templates
blastdock templates
```

## Alternative Installation Methods

### Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv blastdock-env

# Activate virtual environment
source blastdock-env/bin/activate  # Linux/Mac
# or
blastdock-env\Scripts\activate     # Windows

# Install dependencies and package
pip install -r requirements.txt
pip install -e .
```

### System-wide Installation

```bash
# Install system-wide (may require sudo)
sudo pip install -r requirements.txt
sudo pip install .
```

## Troubleshooting

### Common Issues

#### 1. Python command not found
- Use `python3` instead of `python`
- Ensure Python 3.8+ is installed

#### 2. Permission denied errors
- Use `sudo` for system-wide installation
- Use virtual environment instead

#### 3. Docker connection errors
- Ensure Docker daemon is running
- Check Docker permissions for your user

#### 4. Module import errors
- Ensure you're in the correct directory
- Check that all files are present

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