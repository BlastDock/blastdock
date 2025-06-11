"""
Input validation utilities
"""

import re
from .helpers import validate_port, is_port_available

def validate_project_name(name):
    """Validate project name"""
    if not name:
        return False, "Project name cannot be empty"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False, "Project name can only contain letters, numbers, hyphens, and underscores"
    
    if len(name) > 50:
        return False, "Project name cannot be longer than 50 characters"
    
    return True, ""

def validate_domain(domain):
    """Validate domain name"""
    if not domain:
        return True, ""  # Domain is optional
    
    pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
    if not re.match(pattern, domain):
        return False, "Invalid domain name format"
    
    return True, ""

def validate_email(email):
    """Validate email address"""
    if not email:
        return True, ""  # Email is optional
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, ""

def validate_port_input(port, check_availability=True):
    """Validate port input"""
    if not validate_port(port):
        return False, "Port must be a number between 1 and 65535"
    
    if check_availability and not is_port_available(int(port)):
        return False, f"Port {port} is already in use"
    
    return True, ""

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    return True, ""

def validate_database_name(name):
    """Validate database name"""
    if not name:
        return False, "Database name cannot be empty"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', name):
        return False, "Database name can only contain letters, numbers, and underscores"
    
    if len(name) > 64:
        return False, "Database name cannot be longer than 64 characters"
    
    return True, ""