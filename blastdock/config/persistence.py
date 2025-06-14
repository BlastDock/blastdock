"""
Configuration persistence and backup management
"""

import os
import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import hashlib

from ..utils.helpers import load_yaml, save_yaml, load_json, save_json
from ..utils.filesystem import paths
from ..utils.logging import get_logger
from ..exceptions import ConfigurationError

logger = get_logger(__name__)


@dataclass
class ConfigBackupInfo:
    """Information about a configuration backup"""
    filename: str
    timestamp: datetime
    size: int
    checksum: str
    profile: str
    version: str
    description: Optional[str] = None


class ConfigPersistence:
    """Enhanced configuration persistence with multiple format support"""
    
    SUPPORTED_FORMATS = ['yaml', 'yml', 'json', 'toml']
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or paths.config_dir
        self.ensure_directories()
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / 'backups').mkdir(exist_ok=True)
        (self.base_path / 'schemas').mkdir(exist_ok=True)
        (self.base_path / 'profiles').mkdir(exist_ok=True)
    
    def save_config(self, config: Dict[str, Any], filename: str, 
                   format: str = 'yaml', create_backup: bool = True) -> None:
        """Save configuration in specified format"""
        if format not in self.SUPPORTED_FORMATS:
            raise ConfigurationError(f"Unsupported format: {format}")
        
        file_path = self.base_path / filename
        
        # Create backup before saving
        if create_backup and file_path.exists():
            self._create_backup(file_path)
        
        try:
            if format in ['yaml', 'yml']:
                save_yaml(config, str(file_path))
            elif format == 'json':
                save_json(config, str(file_path))
            elif format == 'toml':
                self._save_toml(config, file_path)
            
            logger.info(f"Configuration saved to {file_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def load_config(self, filename: str, format: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from file, auto-detecting format if not specified"""
        file_path = self.base_path / filename
        
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")
        
        # Auto-detect format from extension
        if format is None:
            format = file_path.suffix.lstrip('.')
        
        if format not in self.SUPPORTED_FORMATS:
            raise ConfigurationError(f"Unsupported format: {format}")
        
        try:
            if format in ['yaml', 'yml']:
                return load_yaml(str(file_path))
            elif format == 'json':
                return load_json(str(file_path))
            elif format == 'toml':
                return self._load_toml(file_path)
                
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _save_toml(self, config: Dict[str, Any], file_path: Path) -> None:
        """Save configuration in TOML format"""
        try:
            import tomli_w
            with open(file_path, 'wb') as f:
                tomli_w.dump(config, f)
        except ImportError:
            raise ConfigurationError("TOML support requires 'tomli-w' package")
    
    def _load_toml(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from TOML format"""
        try:
            import tomllib
            with open(file_path, 'rb') as f:
                return tomllib.load(f)
        except ImportError:
            try:
                import tomli
                with open(file_path, 'rb') as f:
                    return tomli.load(f)
            except ImportError:
                raise ConfigurationError("TOML support requires 'tomllib' or 'tomli' package")
    
    def _create_backup(self, file_path: Path) -> None:
        """Create a backup of the configuration file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
        backup_path = self.base_path / 'backups' / backup_name
        
        shutil.copy2(file_path, backup_path)
        logger.debug(f"Created backup: {backup_path}")
    
    def get_file_checksum(self, file_path: Path) -> str:
        """Calculate file checksum"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def export_config(self, config: Dict[str, Any], export_path: str,
                     format: str = 'yaml', include_metadata: bool = True) -> None:
        """Export configuration with metadata"""
        export_data = config.copy()
        
        if include_metadata:
            export_data['_metadata'] = {
                'exported_at': datetime.now().isoformat(),
                'blastdock_version': config.get('version', '1.1.0'),
                'export_format': format,
                'exported_by': 'BlastDock Configuration Manager'
            }
        
        self.save_config(export_data, export_path, format, create_backup=False)
    
    def import_config(self, import_path: str, validate: bool = True) -> Dict[str, Any]:
        """Import configuration with validation"""
        imported_config = self.load_config(import_path)
        
        # Remove metadata if present
        if '_metadata' in imported_config:
            metadata = imported_config.pop('_metadata')
            logger.info(f"Imported configuration from {metadata.get('exported_at', 'unknown time')}")
        
        if validate:
            self._validate_imported_config(imported_config)
        
        return imported_config
    
    def _validate_imported_config(self, config: Dict[str, Any]) -> None:
        """Validate imported configuration"""
        required_sections = ['default_ports', 'logging', 'docker', 'security']
        
        for section in required_sections:
            if section not in config:
                logger.warning(f"Missing configuration section: {section}")
        
        # Validate version compatibility
        version = config.get('version', '1.0.0')
        major_version = version.split('.')[0]
        if major_version != '1':
            logger.warning(f"Configuration version {version} may not be compatible")


class ConfigBackup:
    """Configuration backup management"""
    
    def __init__(self, backup_dir: Optional[Path] = None):
        self.backup_dir = backup_dir or (paths.config_dir / 'backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.persistence = ConfigPersistence()
    
    def create_backup(self, config: Dict[str, Any], profile: str = 'default',
                     description: Optional[str] = None, compression: bool = True) -> str:
        """Create a configuration backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"config_{profile}_{timestamp}"
        
        if compression:
            backup_file = f"{backup_name}.tar.gz"
            self._create_compressed_backup(config, backup_file, description)
        else:
            backup_file = f"{backup_name}.yml"
            self._create_simple_backup(config, backup_file, description)
        
        logger.info(f"Created backup: {backup_file}")
        return backup_file
    
    def _create_simple_backup(self, config: Dict[str, Any], filename: str,
                            description: Optional[str]) -> None:
        """Create a simple YAML backup"""
        backup_data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'description': description,
                'blastdock_version': config.get('version', '1.1.0')
            },
            'configuration': config
        }
        
        backup_path = self.backup_dir / filename
        save_yaml(backup_data, str(backup_path))
    
    def _create_compressed_backup(self, config: Dict[str, Any], filename: str,
                                description: Optional[str]) -> None:
        """Create a compressed backup"""
        import tarfile
        import tempfile
        
        backup_path = self.backup_dir / filename
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create config file
            config_file = Path(temp_dir) / 'config.yml'
            save_yaml(config, str(config_file))
            
            # Create metadata file
            metadata = {
                'created_at': datetime.now().isoformat(),
                'description': description,
                'blastdock_version': config.get('version', '1.1.0'),
                'files': ['config.yml']
            }
            metadata_file = Path(temp_dir) / 'metadata.json'
            save_json(metadata, str(metadata_file))
            
            # Create compressed archive
            with tarfile.open(backup_path, 'w:gz') as tar:
                tar.add(config_file, arcname='config.yml')
                tar.add(metadata_file, arcname='metadata.json')
    
    def restore_backup(self, backup_file: str) -> Dict[str, Any]:
        """Restore configuration from backup"""
        backup_path = self.backup_dir / backup_file
        
        if not backup_path.exists():
            raise ConfigurationError(f"Backup file not found: {backup_file}")
        
        if backup_file.endswith('.tar.gz'):
            return self._restore_compressed_backup(backup_path)
        else:
            return self._restore_simple_backup(backup_path)
    
    def _restore_simple_backup(self, backup_path: Path) -> Dict[str, Any]:
        """Restore from simple YAML backup"""
        backup_data = load_yaml(str(backup_path))
        
        if 'configuration' in backup_data:
            return backup_data['configuration']
        else:
            # Assume the whole file is the configuration
            return backup_data
    
    def _restore_compressed_backup(self, backup_path: Path) -> Dict[str, Any]:
        """Restore from compressed backup"""
        import tarfile
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_dir)
            
            config_file = Path(temp_dir) / 'config.yml'
            if config_file.exists():
                return load_yaml(str(config_file))
            else:
                raise ConfigurationError("Invalid backup format: config.yml not found")
    
    def list_backups(self, profile: Optional[str] = None) -> List[ConfigBackupInfo]:
        """List available backups"""
        backups = []
        
        for backup_file in self.backup_dir.glob('config_*'):
            try:
                backup_info = self._get_backup_info(backup_file)
                if profile is None or backup_info.profile == profile:
                    backups.append(backup_info)
            except Exception as e:
                logger.warning(f"Could not read backup info for {backup_file}: {e}")
        
        return sorted(backups, key=lambda x: x.timestamp, reverse=True)
    
    def _get_backup_info(self, backup_path: Path) -> ConfigBackupInfo:
        """Extract backup information"""
        filename = backup_path.name
        size = backup_path.stat().st_size
        checksum = self.persistence.get_file_checksum(backup_path)
        
        # Extract timestamp from filename
        parts = filename.split('_')
        if len(parts) >= 3:
            timestamp_str = f"{parts[-2]}_{parts[-1].split('.')[0]}"
            timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            profile = '_'.join(parts[1:-2]) if len(parts) > 3 else 'default'
        else:
            timestamp = datetime.fromtimestamp(backup_path.stat().st_mtime)
            profile = 'unknown'
        
        # Try to get version and description from backup
        version = '1.0.0'
        description = None
        
        try:
            if filename.endswith('.tar.gz'):
                # Extract metadata from compressed backup
                import tarfile
                import tempfile
                with tempfile.TemporaryDirectory() as temp_dir:
                    with tarfile.open(backup_path, 'r:gz') as tar:
                        if 'metadata.json' in tar.getnames():
                            tar.extract('metadata.json', temp_dir)
                            metadata = load_json(str(Path(temp_dir) / 'metadata.json'))
                            version = metadata.get('blastdock_version', '1.0.0')
                            description = metadata.get('description')
            else:
                # Extract from YAML backup
                backup_data = load_yaml(str(backup_path))
                if 'metadata' in backup_data:
                    version = backup_data['metadata'].get('blastdock_version', '1.0.0')
                    description = backup_data['metadata'].get('description')
        except Exception:
            pass  # Use defaults if metadata extraction fails
        
        return ConfigBackupInfo(
            filename=filename,
            timestamp=timestamp,
            size=size,
            checksum=checksum,
            profile=profile,
            version=version,
            description=description
        )
    
    def cleanup_old_backups(self, max_age_days: int = 30, max_count: int = 10) -> int:
        """Clean up old backups"""
        backups = self.list_backups()
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        removed_count = 0
        
        # Group backups by profile
        profile_backups = {}
        for backup in backups:
            if backup.profile not in profile_backups:
                profile_backups[backup.profile] = []
            profile_backups[backup.profile].append(backup)
        
        # Clean up each profile
        for profile, profile_backup_list in profile_backups.items():
            # Sort by timestamp (newest first)
            profile_backup_list.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Keep most recent max_count backups
            to_keep = profile_backup_list[:max_count]
            to_remove = profile_backup_list[max_count:]
            
            # Also remove backups older than max_age_days
            for backup in to_keep:
                if backup.timestamp < cutoff_date:
                    to_remove.append(backup)
            
            # Remove old backups
            for backup in to_remove:
                backup_path = self.backup_dir / backup.filename
                try:
                    backup_path.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old backup: {backup.filename}")
                except Exception as e:
                    logger.warning(f"Failed to remove backup {backup.filename}: {e}")
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old backups")
        
        return removed_count
    
    def verify_backup(self, backup_file: str) -> bool:
        """Verify backup integrity"""
        try:
            backup_path = self.backup_dir / backup_file
            
            if not backup_path.exists():
                return False
            
            # Try to restore and validate the backup
            config = self.restore_backup(backup_file)
            
            # Basic validation
            if not isinstance(config, dict):
                return False
            
            # Check for required sections
            required_keys = ['version']
            for key in required_keys:
                if key not in config:
                    logger.warning(f"Backup validation warning: missing key '{key}'")
            
            return True
            
        except Exception as e:
            logger.error(f"Backup verification failed for {backup_file}: {e}")
            return False