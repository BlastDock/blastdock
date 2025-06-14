"""
Configuration profile management
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass

from .simple_models import BlastDockConfig
from .persistence import ConfigPersistence

from ..utils.filesystem import paths
from ..utils.helpers import load_yaml, save_yaml
from ..utils.logging import get_logger
from ..exceptions import ConfigurationError

logger = get_logger(__name__)


@dataclass
class ProfileInfo:
    """Information about a configuration profile"""
    name: str
    description: Optional[str]
    created_at: datetime
    last_modified: datetime
    size: int
    config_version: str
    is_active: bool = False


class ProfileManager:
    """Manage configuration profiles"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or paths.config_dir
        self.profiles_dir = self.config_dir / 'profiles'
        self.persistence = ConfigPersistence(self.config_dir)
        
        # Ensure directories exist
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Profile metadata cache
        self._profile_cache: Dict[str, ProfileInfo] = {}
        self._refresh_cache()
    
    def _refresh_cache(self) -> None:
        """Refresh the profile metadata cache"""
        self._profile_cache.clear()
        
        # Add default profile
        default_config_file = self.config_dir / 'config.yml'
        if default_config_file.exists():
            stat = default_config_file.stat()
            try:
                config_data = load_yaml(str(default_config_file))
                version = config_data.get('version', '1.0.0')
            except Exception:
                version = '1.0.0'
            
            self._profile_cache['default'] = ProfileInfo(
                name='default',
                description='Default BlastDock configuration',
                created_at=datetime.fromtimestamp(stat.st_ctime),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                size=stat.st_size,
                config_version=version
            )
        
        # Add profile-specific configs
        for config_file in self.config_dir.glob('config-*.yml'):
            profile_name = config_file.stem.replace('config-', '')
            if profile_name != 'default':
                self._add_profile_to_cache(profile_name, config_file)
        
        # Add profiles from profiles directory
        for profile_dir in self.profiles_dir.iterdir():
            if profile_dir.is_dir():
                self._add_profile_dir_to_cache(profile_dir)
    
    def _add_profile_to_cache(self, profile_name: str, config_file: Path) -> None:
        """Add a profile configuration file to cache"""
        try:
            stat = config_file.stat()
            config_data = load_yaml(str(config_file))
            
            # Try to get profile metadata
            metadata = config_data.get('_profile_metadata', {})
            
            self._profile_cache[profile_name] = ProfileInfo(
                name=profile_name,
                description=metadata.get('description', f'Configuration profile: {profile_name}'),
                created_at=datetime.fromisoformat(metadata.get('created_at', datetime.fromtimestamp(stat.st_ctime).isoformat())),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                size=stat.st_size,
                config_version=config_data.get('version', '1.0.0')
            )
        except Exception as e:
            logger.warning(f"Failed to load profile metadata for {profile_name}: {e}")
    
    def _add_profile_dir_to_cache(self, profile_dir: Path) -> None:
        """Add a profile directory to cache"""
        profile_name = profile_dir.name
        config_file = profile_dir / 'config.yml'
        
        if config_file.exists():
            self._add_profile_to_cache(profile_name, config_file)
        else:
            # Create placeholder info for directory without config
            stat = profile_dir.stat()
            self._profile_cache[profile_name] = ProfileInfo(
                name=profile_name,
                description=f'Profile directory: {profile_name}',
                created_at=datetime.fromtimestamp(stat.st_ctime),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                size=0,
                config_version='1.0.0'
            )
    
    def list_profiles(self, refresh: bool = True) -> List[ProfileInfo]:
        """List all available profiles"""
        if refresh:
            self._refresh_cache()
        
        return sorted(self._profile_cache.values(), key=lambda p: p.name)
    
    def get_profile_info(self, profile_name: str) -> Optional[ProfileInfo]:
        """Get information about a specific profile"""
        return self._profile_cache.get(profile_name)
    
    def profile_exists(self, profile_name: str) -> bool:
        """Check if a profile exists"""
        return profile_name in self._profile_cache
    
    def create_profile(self, profile_name: str, description: Optional[str] = None,
                      base_profile: str = 'default', copy_settings: bool = True) -> None:
        """Create a new configuration profile"""
        if not profile_name or profile_name in ['default', '']:
            raise ConfigurationError("Invalid profile name")
        
        if self.profile_exists(profile_name):
            raise ConfigurationError(f"Profile '{profile_name}' already exists")
        
        try:
            # Get base configuration
            if copy_settings and base_profile in self._profile_cache:
                base_config = self._load_profile_config(base_profile)
            else:
                base_config = BlastDockConfig().dict()
            
            # Add profile metadata
            base_config['_profile_metadata'] = {
                'name': profile_name,
                'description': description or f'Configuration profile: {profile_name}',
                'created_at': datetime.now().isoformat(),
                'base_profile': base_profile if copy_settings else None,
                'created_by': 'BlastDock Profile Manager'
            }
            
            # Determine profile storage location
            if self._should_use_profile_directory(profile_name):
                profile_dir = self.profiles_dir / profile_name
                profile_dir.mkdir(exist_ok=True)
                config_file = profile_dir / 'config.yml'
            else:
                config_file = self.config_dir / f'config-{profile_name}.yml'
            
            # Save profile configuration
            save_yaml(base_config, str(config_file))
            
            # Refresh cache
            self._refresh_cache()
            
            logger.info(f"Created profile '{profile_name}' based on '{base_profile}'")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create profile '{profile_name}': {e}")
    
    def _should_use_profile_directory(self, profile_name: str) -> bool:
        """Determine if profile should use directory structure"""
        # Use directory structure for complex profiles or when explicitly requested
        return len(profile_name) > 20 or '.' in profile_name
    
    def _load_profile_config(self, profile_name: str) -> Dict[str, Any]:
        """Load configuration for a specific profile"""
        if profile_name == 'default':
            config_file = self.config_dir / 'config.yml'
        elif (self.config_dir / f'config-{profile_name}.yml').exists():
            config_file = self.config_dir / f'config-{profile_name}.yml'
        elif (self.profiles_dir / profile_name / 'config.yml').exists():
            config_file = self.profiles_dir / profile_name / 'config.yml'
        else:
            raise ConfigurationError(f"Profile '{profile_name}' not found")
        
        return load_yaml(str(config_file))
    
    def delete_profile(self, profile_name: str, confirm: bool = False) -> None:
        """Delete a configuration profile"""
        if profile_name == 'default':
            raise ConfigurationError("Cannot delete default profile")
        
        if not self.profile_exists(profile_name):
            raise ConfigurationError(f"Profile '{profile_name}' does not exist")
        
        if not confirm:
            raise ConfigurationError("Profile deletion requires confirmation")
        
        try:
            # Find and remove profile files
            config_file = self.config_dir / f'config-{profile_name}.yml'
            profile_dir = self.profiles_dir / profile_name
            
            if config_file.exists():
                config_file.unlink()
            
            if profile_dir.exists():
                shutil.rmtree(profile_dir)
            
            # Remove from cache
            self._profile_cache.pop(profile_name, None)
            
            logger.info(f"Deleted profile '{profile_name}'")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to delete profile '{profile_name}': {e}")
    
    def copy_profile(self, source_profile: str, target_profile: str,
                    description: Optional[str] = None) -> None:
        """Copy an existing profile to a new profile"""
        if not self.profile_exists(source_profile):
            raise ConfigurationError(f"Source profile '{source_profile}' does not exist")
        
        if self.profile_exists(target_profile):
            raise ConfigurationError(f"Target profile '{target_profile}' already exists")
        
        try:
            # Load source configuration
            source_config = self._load_profile_config(source_profile)
            
            # Update metadata
            source_config['_profile_metadata'] = {
                'name': target_profile,
                'description': description or f'Copy of {source_profile}',
                'created_at': datetime.now().isoformat(),
                'copied_from': source_profile,
                'created_by': 'BlastDock Profile Manager'
            }
            
            # Save as new profile
            target_file = self.config_dir / f'config-{target_profile}.yml'
            save_yaml(source_config, str(target_file))
            
            # Refresh cache
            self._refresh_cache()
            
            logger.info(f"Copied profile '{source_profile}' to '{target_profile}'")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to copy profile: {e}")
    
    def rename_profile(self, old_name: str, new_name: str) -> None:
        """Rename an existing profile"""
        if old_name == 'default':
            raise ConfigurationError("Cannot rename default profile")
        
        if not self.profile_exists(old_name):
            raise ConfigurationError(f"Profile '{old_name}' does not exist")
        
        if self.profile_exists(new_name):
            raise ConfigurationError(f"Profile '{new_name}' already exists")
        
        try:
            # Load current configuration
            config_data = self._load_profile_config(old_name)
            
            # Update metadata
            if '_profile_metadata' in config_data:
                config_data['_profile_metadata']['name'] = new_name
                config_data['_profile_metadata']['renamed_from'] = old_name
                config_data['_profile_metadata']['renamed_at'] = datetime.now().isoformat()
            
            # Create new profile file
            new_file = self.config_dir / f'config-{new_name}.yml'
            save_yaml(config_data, str(new_file))
            
            # Remove old profile
            self.delete_profile(old_name, confirm=True)
            
            # Refresh cache
            self._refresh_cache()
            
            logger.info(f"Renamed profile '{old_name}' to '{new_name}'")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to rename profile: {e}")
    
    def export_profile(self, profile_name: str, export_path: str,
                      include_metadata: bool = True) -> None:
        """Export a profile to a file"""
        if not self.profile_exists(profile_name):
            raise ConfigurationError(f"Profile '{profile_name}' does not exist")
        
        try:
            config_data = self._load_profile_config(profile_name)
            
            if not include_metadata:
                config_data.pop('_profile_metadata', None)
            else:
                # Add export metadata
                export_metadata = {
                    'exported_at': datetime.now().isoformat(),
                    'exported_from_profile': profile_name,
                    'blastdock_version': config_data.get('version', '1.0.0')
                }
                config_data['_export_metadata'] = export_metadata
            
            # Save to export path
            save_yaml(config_data, export_path)
            
            logger.info(f"Exported profile '{profile_name}' to {export_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to export profile: {e}")
    
    def import_profile(self, import_path: str, profile_name: str,
                      description: Optional[str] = None) -> None:
        """Import a profile from a file"""
        if self.profile_exists(profile_name):
            raise ConfigurationError(f"Profile '{profile_name}' already exists")
        
        try:
            # Load configuration from file
            config_data = load_yaml(import_path)
            
            # Remove export metadata if present
            config_data.pop('_export_metadata', None)
            
            # Update profile metadata
            config_data['_profile_metadata'] = {
                'name': profile_name,
                'description': description or f'Imported profile: {profile_name}',
                'created_at': datetime.now().isoformat(),
                'imported_from': import_path,
                'created_by': 'BlastDock Profile Manager'
            }
            
            # Save as new profile
            profile_file = self.config_dir / f'config-{profile_name}.yml'
            save_yaml(config_data, str(profile_file))
            
            # Refresh cache
            self._refresh_cache()
            
            logger.info(f"Imported profile '{profile_name}' from {import_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to import profile: {e}")
    
    def validate_profile(self, profile_name: str) -> List[str]:
        """Validate a profile configuration"""
        if not self.profile_exists(profile_name):
            raise ConfigurationError(f"Profile '{profile_name}' does not exist")
        
        try:
            config_data = self._load_profile_config(profile_name)
            
            # Basic validation
            issues = []
            
            # Check required fields
            if 'version' not in config_data:
                issues.append("Missing configuration version")
            
            # Check configuration structure
            required_sections = ['default_ports', 'logging', 'docker', 'security']
            for section in required_sections:
                if section not in config_data:
                    issues.append(f"Missing required section: {section}")
            
            # Validate using pydantic model
            try:
                BlastDockConfig(**config_data)
            except Exception as e:
                issues.append(f"Configuration validation error: {e}")
            
            return issues
            
        except Exception as e:
            return [f"Failed to validate profile: {e}"]
    
    def get_profile_dependencies(self, profile_name: str) -> Dict[str, Any]:
        """Get profile dependencies and relationships"""
        if not self.profile_exists(profile_name):
            raise ConfigurationError(f"Profile '{profile_name}' does not exist")
        
        try:
            config_data = self._load_profile_config(profile_name)
            metadata = config_data.get('_profile_metadata', {})
            
            dependencies = {
                'base_profile': metadata.get('base_profile'),
                'copied_from': metadata.get('copied_from'),
                'renamed_from': metadata.get('renamed_from'),
                'imported_from': metadata.get('imported_from'),
                'depends_on_profiles': [],
                'used_by_profiles': []
            }
            
            # Find profiles that depend on this one
            for other_profile in self._profile_cache.keys():
                if other_profile != profile_name:
                    try:
                        other_config = self._load_profile_config(other_profile)
                        other_metadata = other_config.get('_profile_metadata', {})
                        
                        if (other_metadata.get('base_profile') == profile_name or
                            other_metadata.get('copied_from') == profile_name):
                            dependencies['used_by_profiles'].append(other_profile)
                    except Exception:
                        continue
            
            return dependencies
            
        except Exception as e:
            raise ConfigurationError(f"Failed to get profile dependencies: {e}")
    
    def get_profile_statistics(self) -> Dict[str, Any]:
        """Get statistics about all profiles"""
        profiles = self.list_profiles()
        
        total_size = sum(p.size for p in profiles)
        
        # Group by version
        version_counts = {}
        for profile in profiles:
            version = profile.config_version
            version_counts[version] = version_counts.get(version, 0) + 1
        
        # Find oldest and newest
        if profiles:
            oldest = min(profiles, key=lambda p: p.created_at)
            newest = max(profiles, key=lambda p: p.created_at)
        else:
            oldest = newest = None
        
        return {
            'total_profiles': len(profiles),
            'total_size_bytes': total_size,
            'version_distribution': version_counts,
            'oldest_profile': {
                'name': oldest.name,
                'created_at': oldest.created_at.isoformat()
            } if oldest else None,
            'newest_profile': {
                'name': newest.name,
                'created_at': newest.created_at.isoformat()
            } if newest else None,
            'profiles_with_metadata': len([p for p in profiles if self._has_metadata(p.name)]),
            'average_size_bytes': total_size / len(profiles) if profiles else 0
        }
    
    def _has_metadata(self, profile_name: str) -> bool:
        """Check if profile has metadata"""
        try:
            config_data = self._load_profile_config(profile_name)
            return '_profile_metadata' in config_data
        except Exception:
            return False