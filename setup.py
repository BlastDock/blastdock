#!/usr/bin/env python3

from setuptools import setup, find_packages
import os

# Read version from _version.py
version_file = os.path.join("blastdock", "_version.py")
with open(version_file) as f:
    exec(f.read())

# Read README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="blastdock",
    version=__version__,
    author="BlastDock Team",
    author_email="info@blastdock.com",
    description="Docker Deployment CLI Tool - Simplify Docker application deployment",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/BlastDock/blastdock",
    project_urls={
        "Bug Tracker": "https://github.com/BlastDock/blastdock/issues",
        "Homepage": "https://blastdock.com",
        "Repository": "https://github.com/BlastDock/blastdock",
        "Documentation": "https://docs.blastdock.com",
    },
    packages=find_packages(),
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
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Systems Administration",
        "Environment :: Console",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "blastdock=blastdock.main_cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "blastdock": [
            "templates/*.yml",
            "templates/*.yaml", 
            "templates/**/*.yml",
            "templates/**/*.yaml"
        ],
    },
    keywords=["docker", "deployment", "automation", "cli", "templates", "containers"],
    license="MIT",
)