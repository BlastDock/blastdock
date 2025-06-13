"""
Setup script for BlastDock - Docker Deployment CLI Tool
Backward compatibility setup.py (pyproject.toml is the primary configuration)
"""

from setuptools import setup, find_packages
import os
import sys
from pathlib import Path

# Add the package directory to Python path for importing version
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'blastdock'))

try:
    from _version import __version__, MIN_PYTHON_VERSION
except ImportError:
    # Fallback if version import fails
    __version__ = "1.0.0"
    MIN_PYTHON_VERSION = (3, 8)

# Check Python version
if sys.version_info < MIN_PYTHON_VERSION:
    print(f"Error: BlastDock requires Python {'.'.join(map(str, MIN_PYTHON_VERSION))} or higher.")
    print(f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    sys.exit(1)

def read_file(filename):
    """Read file contents"""
    file_path = Path(__file__).parent / filename
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not read {filename}: {e}")
    return ""

def read_requirements():
    """Read requirements from requirements.txt"""
    requirements_content = read_file('requirements.txt')
    if not requirements_content:
        # Fallback requirements if file cannot be read
        return [
            "click>=8.0.0",
            "pyyaml>=6.0",
            "docker>=6.0.0", 
            "rich>=13.0.0",
            "jinja2>=3.0.0",
            "platformdirs>=3.0.0",
            "pydantic>=2.0.0",
        ]
    
    requirements = []
    for line in requirements_content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            requirements.append(line)
    return requirements

def read_readme():
    """Read README file"""
    readme_content = read_file('README.md')
    if readme_content:
        return readme_content
    return "BlastDock - Docker Deployment CLI Tool. Simplify Docker application deployment with pre-built templates."

# Get long description
long_description = read_readme()

# Setup configuration
setup(
    name="blastdock",
    version=__version__,
    author="Blast Dock Team",
    author_email="team@blastdock.com",
    description="Docker Deployment CLI Tool - Simplify Docker application deployment with templates",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BlastDock/blastdock",
    project_urls={
        "Homepage": "https://blastdock.com",
        "Documentation": "https://docs.blastdock.com",
        "Repository": "https://github.com/BlastDock/blastdock",
        "Bug Tracker": "https://github.com/BlastDock/blastdock/issues",
    },
    packages=[
        'blastdock',
        'blastdock.core',
        'blastdock.utils',
    ],
    include_package_data=True,
    package_data={
        'blastdock': [
            'templates/*.yml',
            'templates/*.yaml',
            'templates/**/*.yml',
            'templates/**/*.yaml',
        ],
    },
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
            'pre-commit>=3.0.0',
        ],
        'test': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'pytest-mock>=3.10.0',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
        "Environment :: Console",
    ],
    python_requires=f">={'.'.join(map(str, MIN_PYTHON_VERSION))}",
    entry_points={
        'console_scripts': [
            'blastdock=blastdock.cli:main',
        ],
    },
    keywords="docker deployment automation cli templates containers devops",
    zip_safe=False,  # Required for template files to be accessible
)