"""
BlastDock - Docker Deployment CLI Tool
Simplify Docker application deployment with templates
"""

from ._version import __version__, get_version, get_version_info, get_system_info

__author__ = "Blast Dock Team"
__email__ = "team@blastdock.com"
__description__ = "Simplify Docker application deployment with templates"
__url__ = "https://blastdock.com"

# Initialize logging and filesystem paths on import
from .utils.filesystem import initialize_directories
from .utils.logging import initialize_logging

# Initialize directories but don't initialize logging here 
# (let CLI handle that with user preferences)
try:
    initialize_directories()
except Exception:
    # Silently ignore initialization errors during import
    pass

__all__ = [
    "__version__",
    "get_version", 
    "get_version_info",
    "get_system_info",
]