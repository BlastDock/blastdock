"""
Utility helper functions
"""

import json
import yaml
from pathlib import Path

# Import cross-platform filesystem utilities
from .filesystem import (
    get_deploys_dir,
    get_project_path,
    ensure_dir,
    initialize_directories,
)


def load_yaml(file_path):
    """Load YAML file with validation"""
    # BUG-ERR-002 FIX: Add input validation
    if not file_path:
        raise ValueError("file_path cannot be empty")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {file_path}: {e}")
    except PermissionError as e:
        raise PermissionError(f"Cannot read {file_path}: {e}")


def save_yaml(data, file_path):
    """Save data to YAML file"""
    # Ensure parent directory exists
    ensure_dir(Path(file_path).parent)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def load_json(file_path):
    """Load JSON file with validation"""
    # BUG-ERR-002 FIX: Add input validation
    if not file_path:
        raise ValueError("file_path cannot be empty")

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {e}")
    except PermissionError as e:
        raise PermissionError(f"Cannot read {file_path}: {e}")


def save_json(data, file_path):
    """Save data to JSON file"""
    # Ensure parent directory exists
    ensure_dir(Path(file_path).parent)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def sanitize_name(name):
    """Sanitize project/service name"""
    return "".join(c for c in name if c.isalnum() or c in "-_").lower()


def generate_password(length=16):
    """Generate a random password"""
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def validate_port(port):
    """Validate port number"""
    try:
        port = int(port)
        return 1 <= port <= 65535
    except ValueError:
        return False


def is_port_available(port):
    """Check if port is available"""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("localhost", int(port)))
            return result != 0
    except (socket.error, ValueError, OSError) as e:
        # If we can't check the port, assume it's not available
        from .logging import get_logger

        logger = get_logger(__name__)
        logger.debug(f"Could not check port {port}: {e}")
        return False
