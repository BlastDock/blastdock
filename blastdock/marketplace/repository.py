"""
Template Repository management
Handles template storage, versioning, and distribution
"""

import os
import json
import shutil
import tempfile
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
import tarfile
import requests

from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TemplatePackage:
    """Template package information"""
    template_id: str
    version: str
    checksum: str
    size: int
    files: List[str]
    metadata: Dict[str, Any]


class TemplateRepository:
    """Manages template storage and distribution"""
    
    def __init__(self, repo_dir: str = None):
        """Initialize template repository"""
        self.logger = get_logger(__name__)
        
        # Set repository directory
        if repo_dir is None:
            repo_dir = Path.home() / '.blastdock' / 'repository'
        self.repo_dir = Path(repo_dir)
        self.repo_dir.mkdir(parents=True, exist_ok=True)
        
        # Repository structure
        self.packages_dir = self.repo_dir / 'packages'
        self.index_dir = self.repo_dir / 'index'
        self.cache_dir = self.repo_dir / 'cache'
        
        for dir_path in [self.packages_dir, self.index_dir, self.cache_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # Repository index
        self.index: Dict[str, Dict[str, TemplatePackage]] = {}
        self._load_index()
        
        # Remote repository URL (for future use)
        self.remote_url = "https://templates.blastdock.com"
        
        self.logger.info(f"Repository initialized at {self.repo_dir}")
    
    def package_template(self, template_path: Path, 
                        template_id: str,
                        version: str,
                        metadata: Dict[str, Any] = None) -> TemplatePackage:
        """Package a template for distribution"""
        metadata = metadata or {}
        
        # Create package directory
        package_name = f"{template_id}-{version}"
        package_file = self.packages_dir / f"{package_name}.tar.gz"
        
        # Collect template files
        files_to_package = []
        for file_path in template_path.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(template_path)
                files_to_package.append(str(relative_path))
        
        # Create tarball
        with tarfile.open(package_file, 'w:gz') as tar:
            tar.add(template_path, arcname=package_name)
        
        # Calculate checksum
        checksum = self._calculate_checksum(package_file)
        
        # Get package size
        package_size = package_file.stat().st_size
        
        # Create package info
        package = TemplatePackage(
            template_id=template_id,
            version=version,
            checksum=checksum,
            size=package_size,
            files=files_to_package,
            metadata=metadata
        )
        
        # Update index
        if template_id not in self.index:
            self.index[template_id] = {}
        self.index[template_id][version] = package
        self._save_index()
        
        self.logger.info(f"Packaged template {template_id} v{version} ({package_size} bytes)")
        
        return package
    
    def get_package(self, template_id: str, version: str = 'latest') -> Optional[TemplatePackage]:
        """Get template package information"""
        if template_id not in self.index:
            return None
        
        versions = self.index[template_id]
        
        if version == 'latest':
            # Get latest version (simple string comparison for MVP)
            latest_version = max(versions.keys())
            return versions[latest_version]
        else:
            return versions.get(version)
    
    def download_template(self, template_id: str, 
                         version: str = 'latest',
                         destination: Path = None) -> Optional[Path]:
        """Download template package"""
        package = self.get_package(template_id, version)
        if not package:
            self.logger.error(f"Package not found: {template_id} v{version}")
            return None
        
        # Check local package
        package_name = f"{template_id}-{package.version}"
        package_file = self.packages_dir / f"{package_name}.tar.gz"
        
        if not package_file.exists():
            # Try to download from remote (future feature)
            self.logger.warning(f"Package file not found locally: {package_file}")
            return None
        
        # Verify checksum
        if self._calculate_checksum(package_file) != package.checksum:
            self.logger.error(f"Checksum mismatch for {package_file}")
            return None
        
        # Extract to destination or temp directory
        if destination is None:
            destination = Path(tempfile.mkdtemp(prefix='blastdock-template-'))
        
        with tarfile.open(package_file, 'r:gz') as tar:
            tar.extractall(destination)
        
        # Return path to extracted template
        extracted_path = destination / package_name
        
        self.logger.info(f"Downloaded template {template_id} v{package.version} to {extracted_path}")
        
        return extracted_path
    
    def list_versions(self, template_id: str) -> List[str]:
        """List available versions for a template"""
        if template_id not in self.index:
            return []
        
        versions = list(self.index[template_id].keys())
        versions.sort(reverse=True)  # Latest first
        return versions
    
    def search_packages(self, query: str = "") -> List[Tuple[str, List[str]]]:
        """Search packages in repository"""
        results = []
        
        for template_id, versions in self.index.items():
            if query.lower() in template_id.lower():
                version_list = list(versions.keys())
                version_list.sort(reverse=True)
                results.append((template_id, version_list))
        
        return results
    
    def import_from_directory(self, templates_dir: Path, 
                            version: str = "1.0.0") -> Dict[str, bool]:
        """Import templates from a directory"""
        results = {}
        
        for template_dir in templates_dir.iterdir():
            if template_dir.is_dir() and not template_dir.name.startswith('.'):
                template_id = template_dir.name
                
                try:
                    # Read template metadata if available
                    metadata_file = template_dir / 'blastdock.yml'
                    metadata = {}
                    
                    if metadata_file.exists():
                        import yaml
                        with open(metadata_file, 'r') as f:
                            metadata = yaml.safe_load(f) or {}
                    
                    # Package the template
                    package = self.package_template(
                        template_dir,
                        template_id,
                        version,
                        metadata
                    )
                    
                    results[template_id] = True
                    self.logger.info(f"Imported template: {template_id}")
                    
                except Exception as e:
                    results[template_id] = False
                    self.logger.error(f"Failed to import {template_id}: {e}")
        
        return results
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _load_index(self):
        """Load repository index"""
        index_file = self.index_dir / 'repository.json'
        
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct index
                for template_id, versions in data.items():
                    self.index[template_id] = {}
                    for version, package_data in versions.items():
                        self.index[template_id][version] = TemplatePackage(**package_data)
                
                self.logger.info(f"Loaded repository index with {len(self.index)} templates")
                
            except Exception as e:
                self.logger.error(f"Failed to load repository index: {e}")
    
    def _save_index(self):
        """Save repository index"""
        index_file = self.index_dir / 'repository.json'
        
        try:
            # Convert to serializable format
            data = {}
            for template_id, versions in self.index.items():
                data[template_id] = {}
                for version, package in versions.items():
                    data[template_id][version] = {
                        'template_id': package.template_id,
                        'version': package.version,
                        'checksum': package.checksum,
                        'size': package.size,
                        'files': package.files,
                        'metadata': package.metadata
                    }
            
            with open(index_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.debug("Saved repository index")
            
        except Exception as e:
            self.logger.error(f"Failed to save repository index: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get repository statistics"""
        total_packages = sum(len(versions) for versions in self.index.values())
        total_size = 0
        
        for template_id, versions in self.index.items():
            for package in versions.values():
                total_size += package.size
        
        return {
            'total_templates': len(self.index),
            'total_packages': total_packages,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'repository_path': str(self.repo_dir),
            'packages_by_template': {
                template_id: len(versions) 
                for template_id, versions in self.index.items()
            }
        }