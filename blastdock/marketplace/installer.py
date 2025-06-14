"""
Template Installer
Handles template installation from marketplace
"""

import os
import shutil
import tempfile
from typing import Dict, Optional, Any, List
from pathlib import Path

from ..utils.logging import get_logger
from ..utils.template_validator import TemplateValidator
from .repository import TemplateRepository
from .marketplace import TemplateMarketplace, MarketplaceTemplate

logger = get_logger(__name__)


class TemplateInstaller:
    """Manages template installation process"""
    
    def __init__(self, templates_dir: str = None):
        """Initialize template installer"""
        self.logger = get_logger(__name__)
        
        # Set templates directory
        if templates_dir is None:
            templates_dir = Path(__file__).parent.parent / 'templates'
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.repository = TemplateRepository()
        self.marketplace = TemplateMarketplace()
        self.validator = TemplateValidator()
        
        # Installation cache
        self.installed_templates: Dict[str, Dict[str, Any]] = {}
        self._load_installed_templates()
        
        self.logger.info(f"Template installer initialized with directory: {self.templates_dir}")
    
    def install_template(self, template_id: str, 
                        version: str = 'latest',
                        force: bool = False) -> Dict[str, Any]:
        """Install template from marketplace"""
        
        # Get template from marketplace
        marketplace_template = self.marketplace.get_template(template_id)
        if not marketplace_template:
            return {
                'success': False,
                'error': f"Template '{template_id}' not found in marketplace"
            }
        
        # Check if already installed
        if not force and self.is_installed(marketplace_template.name):
            installed_version = self.get_installed_version(marketplace_template.name)
            return {
                'success': False,
                'error': f"Template '{marketplace_template.name}' already installed (v{installed_version}). Use --force to reinstall."
            }
        
        # Download template package
        self.logger.info(f"Downloading template {template_id} v{version}...")
        
        download_path = self.repository.download_template(template_id, version)
        if not download_path:
            return {
                'success': False,
                'error': f"Failed to download template package"
            }
        
        try:
            # Find template files in download
            template_files = list(download_path.rglob('*.yml'))
            if not template_files:
                return {
                    'success': False,
                    'error': "No template files found in package"
                }
            
            # Use the first .yml file as the main template
            template_file = template_files[0]
            
            # Validate template before installation
            self.logger.info("Validating template...")
            analysis = self.validator.validate_template(str(template_file))
            
            if not analysis.is_valid:
                return {
                    'success': False,
                    'error': f"Template validation failed: {analysis.error_count} errors",
                    'validation_errors': [r.message for r in analysis.results if r.level.value == 'error']
                }
            
            # Install template
            target_name = marketplace_template.name
            target_path = self.templates_dir / f"{target_name}.yml"
            
            # Backup existing template if force installing
            if force and target_path.exists():
                backup_path = self.templates_dir / f"{target_name}.yml.backup"
                shutil.copy2(target_path, backup_path)
                self.logger.info(f"Backed up existing template to {backup_path}")
            
            # Copy template file
            shutil.copy2(template_file, target_path)
            
            # Copy additional files if present
            additional_files = []
            for file_pattern in ['README.md', 'blastdock.yml', '.env.example']:
                source_file = download_path / file_pattern
                if source_file.exists():
                    target_file = self.templates_dir / f"{target_name}_{file_pattern}"
                    shutil.copy2(source_file, target_file)
                    additional_files.append(str(target_file))
            
            # Update installation record
            self.installed_templates[target_name] = {
                'template_id': template_id,
                'version': marketplace_template.version,
                'installed_at': os.path.getmtime(target_path),
                'source': marketplace_template.source,
                'validation_score': analysis.score,
                'traefik_compatible': analysis.traefik_compatibility.value,
                'additional_files': additional_files
            }
            self._save_installed_templates()
            
            # Update marketplace stats
            self.marketplace.update_template_stats(template_id, downloads=1)
            
            # Clean up download
            shutil.rmtree(download_path)
            
            self.logger.info(f"Successfully installed template {target_name} v{marketplace_template.version}")
            
            return {
                'success': True,
                'template_name': target_name,
                'version': marketplace_template.version,
                'path': str(target_path),
                'validation_score': analysis.score,
                'traefik_compatible': analysis.traefik_compatibility.value,
                'additional_files': additional_files
            }
            
        except Exception as e:
            # Clean up on error
            if download_path and download_path.exists():
                shutil.rmtree(download_path)
            
            self.logger.error(f"Failed to install template: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def uninstall_template(self, template_name: str) -> Dict[str, Any]:
        """Uninstall a template"""
        if not self.is_installed(template_name):
            return {
                'success': False,
                'error': f"Template '{template_name}' is not installed"
            }
        
        try:
            # Remove template file
            template_path = self.templates_dir / f"{template_name}.yml"
            if template_path.exists():
                template_path.unlink()
            
            # Remove additional files
            install_info = self.installed_templates.get(template_name, {})
            for file_path in install_info.get('additional_files', []):
                if os.path.exists(file_path):
                    os.unlink(file_path)
            
            # Remove from installed templates
            del self.installed_templates[template_name]
            self._save_installed_templates()
            
            self.logger.info(f"Successfully uninstalled template {template_name}")
            
            return {
                'success': True,
                'template_name': template_name
            }
            
        except Exception as e:
            self.logger.error(f"Failed to uninstall template: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_installed_templates(self) -> List[Dict[str, Any]]:
        """List all installed templates"""
        installed = []
        
        for name, info in self.installed_templates.items():
            template_path = self.templates_dir / f"{name}.yml"
            
            installed.append({
                'name': name,
                'template_id': info.get('template_id', name),
                'version': info.get('version', 'unknown'),
                'source': info.get('source', 'unknown'),
                'installed_at': info.get('installed_at', 0),
                'exists': template_path.exists(),
                'validation_score': info.get('validation_score', 0),
                'traefik_compatible': info.get('traefik_compatible', False)
            })
        
        # Sort by name
        installed.sort(key=lambda x: x['name'])
        
        return installed
    
    def is_installed(self, template_name: str) -> bool:
        """Check if template is installed"""
        return template_name in self.installed_templates
    
    def get_installed_version(self, template_name: str) -> Optional[str]:
        """Get installed version of a template"""
        if template_name in self.installed_templates:
            return self.installed_templates[template_name].get('version')
        return None
    
    def update_template(self, template_name: str) -> Dict[str, Any]:
        """Update installed template to latest version"""
        if not self.is_installed(template_name):
            return {
                'success': False,
                'error': f"Template '{template_name}' is not installed"
            }
        
        # Get template info
        install_info = self.installed_templates[template_name]
        template_id = install_info.get('template_id', template_name)
        
        # Check for newer version
        marketplace_template = self.marketplace.get_template(template_id)
        if not marketplace_template:
            return {
                'success': False,
                'error': f"Template not found in marketplace"
            }
        
        current_version = install_info.get('version', '0.0.0')
        latest_version = marketplace_template.version
        
        if current_version >= latest_version:
            return {
                'success': False,
                'error': f"Already at latest version ({current_version})"
            }
        
        # Install new version
        self.logger.info(f"Updating {template_name} from v{current_version} to v{latest_version}")
        
        return self.install_template(template_id, 'latest', force=True)
    
    def _load_installed_templates(self):
        """Load installed templates registry"""
        registry_file = self.templates_dir / '.installed.json'
        
        if registry_file.exists():
            try:
                import json
                with open(registry_file, 'r') as f:
                    self.installed_templates = json.load(f)
                    
                self.logger.info(f"Loaded {len(self.installed_templates)} installed templates")
                
            except Exception as e:
                self.logger.error(f"Failed to load installed templates: {e}")
                self.installed_templates = {}
    
    def _save_installed_templates(self):
        """Save installed templates registry"""
        registry_file = self.templates_dir / '.installed.json'
        
        try:
            import json
            with open(registry_file, 'w') as f:
                json.dump(self.installed_templates, f, indent=2)
                
            self.logger.debug("Saved installed templates registry")
            
        except Exception as e:
            self.logger.error(f"Failed to save installed templates: {e}")