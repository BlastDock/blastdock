"""
Cross-platform filesystem utilities with XDG Base Directory support
"""

import os
import sys
from pathlib import Path
from typing import Optional
from platformdirs import user_config_dir, user_data_dir, user_cache_dir, user_log_dir


class BlastDockPaths:
    """
    Centralized path management following XDG Base Directory Specification
    and platform-specific conventions
    """
    
    APP_NAME = "blastdock"
    APP_AUTHOR = "BlastDock"
    
    def __init__(self):
        self._config_dir: Optional[Path] = None
        self._data_dir: Optional[Path] = None
        self._cache_dir: Optional[Path] = None
        self._log_dir: Optional[Path] = None
        self._templates_dir: Optional[Path] = None
        self._deploys_dir: Optional[Path] = None
    
    @property
    def config_dir(self) -> Path:
        """Get user configuration directory"""
        if self._config_dir is None:
            self._config_dir = Path(user_config_dir(self.APP_NAME, self.APP_AUTHOR))
        return self._config_dir
    
    @property
    def data_dir(self) -> Path:
        """Get user data directory"""
        if self._data_dir is None:
            self._data_dir = Path(user_data_dir(self.APP_NAME, self.APP_AUTHOR))
        return self._data_dir
    
    @property
    def cache_dir(self) -> Path:
        """Get user cache directory"""
        if self._cache_dir is None:
            self._cache_dir = Path(user_cache_dir(self.APP_NAME, self.APP_AUTHOR))
        return self._cache_dir
    
    @property
    def log_dir(self) -> Path:
        """Get user log directory"""
        if self._log_dir is None:
            self._log_dir = Path(user_log_dir(self.APP_NAME, self.APP_AUTHOR))
        return self._log_dir
    
    @property
    def templates_dir(self) -> Path:
        """Get templates directory (user data + templates)"""
        if self._templates_dir is None:
            self._templates_dir = self.data_dir / "templates"
        return self._templates_dir
    
    @property
    def deploys_dir(self) -> Path:
        """Get deployments directory (user data + deploys)"""
        if self._deploys_dir is None:
            self._deploys_dir = self.data_dir / "deploys"
        return self._deploys_dir
    
    @property
    def config_file(self) -> Path:
        """Get main configuration file path"""
        return self.config_dir / "config.yml"
    
    @property
    def system_templates_dir(self) -> Path:
        """Get system-wide templates directory"""
        if sys.platform == "win32":
            # Windows: Use PROGRAMDATA
            return Path(os.environ.get("PROGRAMDATA", "C:\\ProgramData")) / self.APP_NAME / "templates"
        else:
            # Unix/Linux: Use /usr/share
            return Path("/usr/share") / self.APP_NAME / "templates"
    
    def get_project_path(self, project_name: str) -> Path:
        """Get path for a specific project"""
        return self.deploys_dir / project_name
    
    def ensure_directories(self) -> None:
        """Ensure all necessary directories exist"""
        directories = [
            self.config_dir,
            self.data_dir,
            self.cache_dir,
            self.log_dir,
            self.templates_dir,
            self.deploys_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_template_search_paths(self) -> list[Path]:
        """Get ordered list of template search paths"""
        return [
            self.templates_dir,  # User templates (highest priority)
            self.system_templates_dir,  # System templates
            # Fallback to package templates
            Path(__file__).parent.parent / "templates",
        ]


# Global instance
paths = BlastDockPaths()


# Backward compatibility functions
def get_deploys_dir() -> str:
    """Get deploys directory (backward compatibility)"""
    return str(paths.deploys_dir)


def get_project_path(project_name: str) -> str:
    """Get project path (backward compatibility)"""
    return str(paths.get_project_path(project_name))


def ensure_dir(path: str | Path) -> None:
    """Ensure directory exists (backward compatibility)"""
    Path(path).mkdir(parents=True, exist_ok=True)


def get_config_dir() -> str:
    """Get configuration directory"""
    return str(paths.config_dir)


def get_data_dir() -> str:
    """Get data directory"""
    return str(paths.data_dir)


def get_cache_dir() -> str:
    """Get cache directory"""
    return str(paths.cache_dir)


def get_log_dir() -> str:
    """Get log directory"""
    return str(paths.log_dir)


def get_templates_dir() -> str:
    """Get templates directory"""
    return str(paths.templates_dir)


def initialize_directories() -> None:
    """Initialize all BlastDock directories"""
    paths.ensure_directories()