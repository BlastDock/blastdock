"""
Setup script for Docker Deployment CLI Tool
"""

from setuptools import setup, find_packages
import os

def read_requirements():
    """Read requirements from requirements.txt"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def read_readme():
    """Read README file"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Docker Deployment CLI Tool - Simplify Docker application deployment"

setup(
    name="blastdock",
    version="1.0.0",
    author="Blast Dock Team",
    author_email="team@blastdock.com",
    description="Docker Deployment CLI Tool - Simplify Docker application deployment",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/blastdock/blastdock",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'blastdock': ['templates/*.yml'],
    },
    install_requires=read_requirements(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Tools",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'blastdock=blastdock.cli:cli',
        ],
    },
    keywords="docker deployment automation cli templates",
)