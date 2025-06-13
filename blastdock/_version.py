"""
Version information for BlastDock
"""

__version__ = "1.1.0"
__version_info__ = (1, 1, 0)

# Version components
MAJOR = 1
MINOR = 1
PATCH = 0

# Build information
BUILD_DATE = "2024-01-01"
BUILD_COMMIT = "unknown"

# Minimum requirements
MIN_PYTHON_VERSION = (3, 8)
MIN_DOCKER_VERSION = "20.10.0"
MIN_COMPOSE_VERSION = "2.0.0"

def get_version() -> str:
    """Get the current version string"""
    return __version__

def get_version_info() -> tuple:
    """Get version as tuple"""
    return __version_info__

def get_full_version() -> str:
    """Get full version with build info"""
    version = __version__
    if BUILD_COMMIT != "unknown":
        version += f"+{BUILD_COMMIT[:8]}"
    return version

def check_python_version() -> bool:
    """Check if Python version meets minimum requirements"""
    import sys
    return sys.version_info >= MIN_PYTHON_VERSION

def get_system_info() -> dict:
    """Get system information"""
    import sys
    import platform
    
    return {
        "blastdock_version": get_full_version(),
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.platform(),
        "architecture": platform.architecture()[0],
        "machine": platform.machine(),
        "system": platform.system(),
    }