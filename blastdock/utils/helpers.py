"""
Utility helper functions
"""

import json
import yaml
from pathlib import Path

# Import cross-platform filesystem utilities  
from .filesystem import (
    get_deploys_dir, get_project_path, ensure_dir,
    initialize_directories
)

def load_yaml(file_path):
    """Load YAML file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def save_yaml(data, file_path):
    """Save data to YAML file"""
    # Ensure parent directory exists
    ensure_dir(Path(file_path).parent)
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

def load_json(file_path):
    """Load JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, file_path):
    """Save data to JSON file"""
    # Ensure parent directory exists
    ensure_dir(Path(file_path).parent)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def sanitize_name(name):
    """Sanitize project/service name"""
    return ''.join(c for c in name if c.isalnum() or c in '-_').lower()

def generate_password(length=16):
    """Generate a random password"""
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

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
            result = s.connect_ex(('localhost', int(port)))
            return result != 0
    except:
        return False