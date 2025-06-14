"""
Enhanced input validation and sanitization utilities
"""

import re
import os
import socket
import ipaddress
from pathlib import Path
from typing import Tuple, Optional, List, Union
from urllib.parse import urlparse

from .helpers import validate_port, is_port_available
from ..exceptions import (
    ValidationError, PortValidationError, PortConflictError,
    DomainValidationError, DatabaseNameValidationError, PasswordValidationError
)


class InputValidator:
    """Comprehensive input validation with detailed error reporting"""
    
    # Common regex patterns
    PATTERNS = {
        'project_name': r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$',
        'domain': r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$',
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'database_name': r'^[a-zA-Z][a-zA-Z0-9_]*$',
        'service_name': r'^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$',
        'environment_var': r'^[A-Z][A-Z0-9_]*$',
        'version': r'^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?$',
        'container_name': r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$',
    }
    
    # Reserved names that cannot be used
    RESERVED_NAMES = {
        'project': {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'},
        'database': {'information_schema', 'mysql', 'performance_schema', 'sys', 'postgres', 'template0', 'template1'},
        'service': {'localhost', 'host', 'gateway', 'dns', 'docker', 'compose'},
    }
    
    @classmethod
    def validate_project_name(cls, name: str, raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate project name with comprehensive checks using security validator"""
        try:
            # Use security validator if available for enhanced validation
            try:
                from ..security import get_security_validator
                validator = get_security_validator()
                is_valid, error = validator.validate_project_name(name)
                if not is_valid:
                    raise ValidationError(error or "Invalid project name")
                return True, ""
            except ImportError:
                # Fallback to basic validation if security module not available
                pass
            
            if not name:
                raise ValidationError("Project name cannot be empty")
            
            name = name.strip()
            
            # Length check
            if len(name) < 1 or len(name) > 50:
                raise ValidationError("Project name must be between 1 and 50 characters")
            
            # Pattern check
            if not re.match(cls.PATTERNS['project_name'], name):
                raise ValidationError(
                    "Project name must start and end with alphanumeric characters, "
                    "and can contain hyphens and underscores in between"
                )
            
            # Reserved names check
            if name.lower() in cls.RESERVED_NAMES['project']:
                raise ValidationError(f"'{name}' is a reserved name and cannot be used")
            
            # Docker naming constraints
            if name.startswith('-') or name.endswith('-'):
                raise ValidationError("Project name cannot start or end with a hyphen")
            
            if '--' in name:
                raise ValidationError("Project name cannot contain consecutive hyphens")
            
            return True, ""
            
        except ValidationError as e:
            if raise_on_error:
                raise
            return False, str(e)
    
    @classmethod
    def validate_domain(cls, domain: str, allow_empty: bool = True, raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate domain name"""
        try:
            if not domain:
                if allow_empty:
                    return True, ""
                raise DomainValidationError(domain, "Domain cannot be empty")
            
            domain = domain.strip().lower()
            
            # Length check
            if len(domain) > 253:
                raise DomainValidationError(domain, "Domain name too long (max 253 characters)")
            
            # Pattern check
            if not re.match(cls.PATTERNS['domain'], domain):
                raise DomainValidationError(domain, "Invalid domain name format")
            
            # Check for valid TLD
            parts = domain.split('.')
            if len(parts) < 2:
                raise DomainValidationError(domain, "Domain must have at least one dot")
            
            # Check each label
            for part in parts:
                if len(part) > 63:
                    raise DomainValidationError(domain, f"Domain label '{part}' too long (max 63 characters)")
                if part.startswith('-') or part.endswith('-'):
                    raise DomainValidationError(domain, f"Domain label '{part}' cannot start or end with hyphen")
            
            return True, ""
            
        except DomainValidationError as e:
            if raise_on_error:
                raise
            return False, e.reason
    
    @classmethod
    def validate_email(cls, email: str, allow_empty: bool = True, raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate email address"""
        try:
            if not email:
                if allow_empty:
                    return True, ""
                raise ValidationError("Email address cannot be empty")
            
            email = email.strip().lower()
            
            # Length check
            if len(email) > 254:
                raise ValidationError("Email address too long")
            
            # Pattern check
            if not re.match(cls.PATTERNS['email'], email):
                raise ValidationError("Invalid email address format")
            
            # Split and validate parts
            local, domain = email.rsplit('@', 1)
            
            if len(local) > 64:
                raise ValidationError("Email local part too long (max 64 characters)")
            
            # Validate domain part
            is_valid, error = cls.validate_domain(domain, allow_empty=False)
            if not is_valid:
                raise ValidationError(f"Invalid email domain: {error}")
            
            return True, ""
            
        except ValidationError as e:
            if raise_on_error:
                raise
            return False, str(e)
    
    @classmethod
    def validate_port(cls, port: Union[str, int], 
                     check_availability: bool = True, 
                     allow_privileged: bool = False,
                     raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate port number with availability check"""
        try:
            # Convert to int if string
            try:
                port_num = int(port)
            except (ValueError, TypeError):
                raise PortValidationError(str(port), "Must be a valid number")
            
            # Range check
            if port_num < 1 or port_num > 65535:
                raise PortValidationError(str(port), "Must be between 1 and 65535")
            
            # Privileged ports check
            if not allow_privileged and port_num < 1024:
                raise PortValidationError(str(port), "Privileged ports (< 1024) require special permissions")
            
            # Common reserved ports warning
            reserved_ports = {22, 25, 53, 80, 110, 143, 443, 993, 995}
            if port_num in reserved_ports:
                # This is a warning, not an error
                pass
            
            # Availability check
            if check_availability and not is_port_available(port_num):
                # Try to identify what's using the port
                conflicting_service = cls._identify_port_usage(port_num)
                raise PortConflictError(port_num, conflicting_service)
            
            return True, ""
            
        except (PortValidationError, PortConflictError) as e:
            if raise_on_error:
                raise
            return False, str(e)
    
    @classmethod
    def validate_password(cls, password: str, 
                         min_length: int = 8, 
                         require_special: bool = False,
                         require_numbers: bool = False,
                         require_uppercase: bool = False,
                         raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate password with configurable requirements"""
        try:
            if not password:
                raise PasswordValidationError("Password cannot be empty")
            
            # Length check
            if len(password) < min_length:
                raise PasswordValidationError(f"Password must be at least {min_length} characters long")
            
            if len(password) > 128:
                raise PasswordValidationError("Password too long (max 128 characters)")
            
            # Character requirements
            checks = []
            
            if require_uppercase and not re.search(r'[A-Z]', password):
                checks.append("at least one uppercase letter")
            
            if require_numbers and not re.search(r'\d', password):
                checks.append("at least one number")
            
            if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                checks.append("at least one special character")
            
            if checks:
                raise PasswordValidationError(f"Password must contain {', '.join(checks)}")
            
            # Common weak password check
            weak_passwords = {'password', '123456', 'qwerty', 'admin', 'test', 'guest'}
            if password.lower() in weak_passwords:
                raise PasswordValidationError("Password is too common and weak")
            
            return True, ""
            
        except PasswordValidationError as e:
            if raise_on_error:
                raise
            return False, e.reason
    
    @classmethod
    def validate_database_name(cls, name: str, db_type: str = "mysql", raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate database name for specific database types"""
        try:
            if not name:
                raise DatabaseNameValidationError(name, "Database name cannot be empty")
            
            name = name.strip()
            
            # Length checks based on database type
            max_lengths = {
                'mysql': 64,
                'postgresql': 63,
                'mongodb': 64,
                'redis': 255,
            }
            
            max_length = max_lengths.get(db_type.lower(), 64)
            if len(name) > max_length:
                raise DatabaseNameValidationError(name, f"Database name too long for {db_type} (max {max_length} characters)")
            
            # Pattern check
            if not re.match(cls.PATTERNS['database_name'], name):
                raise DatabaseNameValidationError(
                    name, 
                    "Database name must start with a letter and contain only letters, numbers, and underscores"
                )
            
            # Reserved names check
            if name.lower() in cls.RESERVED_NAMES['database']:
                raise DatabaseNameValidationError(name, f"'{name}' is a reserved database name")
            
            # Database-specific rules
            if db_type.lower() == 'mysql':
                if name.lower().startswith('mysql'):
                    raise DatabaseNameValidationError(name, "MySQL database names cannot start with 'mysql'")
            
            elif db_type.lower() == 'postgresql':
                if name.lower().startswith('pg_'):
                    raise DatabaseNameValidationError(name, "PostgreSQL database names cannot start with 'pg_'")
            
            return True, ""
            
        except DatabaseNameValidationError as e:
            if raise_on_error:
                raise
            return False, e.reason
    
    @classmethod
    def validate_service_name(cls, name: str, raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate Docker service name"""
        try:
            if not name:
                raise ValidationError("Service name cannot be empty")
            
            name = name.strip().lower()
            
            # Length check
            if len(name) > 63:
                raise ValidationError("Service name too long (max 63 characters)")
            
            # Pattern check
            if not re.match(cls.PATTERNS['service_name'], name):
                raise ValidationError(
                    "Service name must start with a letter, end with alphanumeric, "
                    "and contain only lowercase letters, numbers, and hyphens"
                )
            
            # Reserved names check
            if name in cls.RESERVED_NAMES['service']:
                raise ValidationError(f"'{name}' is a reserved service name")
            
            return True, ""
            
        except ValidationError as e:
            if raise_on_error:
                raise
            return False, str(e)
    
    @classmethod
    def validate_path(cls, path: str, must_exist: bool = False, 
                     must_be_writable: bool = False, raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate file system path"""
        try:
            if not path:
                raise ValidationError("Path cannot be empty")
            
            path_obj = Path(path)
            
            # Check if path exists when required
            if must_exist and not path_obj.exists():
                raise ValidationError(f"Path does not exist: {path}")
            
            # Check if writable when required
            if must_be_writable:
                if path_obj.exists():
                    if not os.access(path, os.W_OK):
                        raise ValidationError(f"Path is not writable: {path}")
                else:
                    # Check parent directory
                    parent = path_obj.parent
                    if not parent.exists() or not os.access(parent, os.W_OK):
                        raise ValidationError(f"Parent directory is not writable: {parent}")
            
            return True, ""
            
        except ValidationError as e:
            if raise_on_error:
                raise
            return False, str(e)
    
    @classmethod
    def validate_url(cls, url: str, allowed_schemes: Optional[List[str]] = None, 
                    raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate URL format"""
        try:
            if not url:
                raise ValidationError("URL cannot be empty")
            
            parsed = urlparse(url)
            
            if not parsed.scheme:
                raise ValidationError("URL must include a scheme (http, https, etc.)")
            
            if allowed_schemes and parsed.scheme not in allowed_schemes:
                raise ValidationError(f"URL scheme must be one of: {allowed_schemes}")
            
            if not parsed.netloc:
                raise ValidationError("URL must include a hostname")
            
            return True, ""
            
        except ValidationError as e:
            if raise_on_error:
                raise
            return False, str(e)
    
    @classmethod
    def validate_ip_address(cls, ip: str, version: Optional[int] = None, 
                           raise_on_error: bool = False) -> Tuple[bool, str]:
        """Validate IP address"""
        try:
            if not ip:
                raise ValidationError("IP address cannot be empty")
            
            ip_obj = ipaddress.ip_address(ip)
            
            if version and ip_obj.version != version:
                raise ValidationError(f"Expected IPv{version} address")
            
            return True, ""
            
        except (ipaddress.AddressValueError, ValidationError) as e:
            if raise_on_error:
                raise ValidationError(f"Invalid IP address: {e}")
            return False, f"Invalid IP address: {e}"
    
    @classmethod
    def sanitize_name(cls, name: str, max_length: int = 50, 
                     allowed_chars: str = "a-zA-Z0-9_-") -> str:
        """Sanitize a name by removing invalid characters"""
        if not name:
            return ""
        
        # Remove invalid characters
        pattern = f"[^{allowed_chars}]"
        sanitized = re.sub(pattern, "_", name)
        
        # Remove consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip("_")
        
        return sanitized
    
    @classmethod
    def _identify_port_usage(cls, port: int) -> Optional[str]:
        """Try to identify what service is using a port"""
        try:
            # Try to connect and see if we get any identifying information
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                if result == 0:
                    return "unknown service"
        except:
            pass
        
        # Common port mappings
        common_ports = {
            22: "SSH",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            993: "IMAPS",
            995: "POP3S",
            3306: "MySQL",
            5432: "PostgreSQL",
            6379: "Redis",
            27017: "MongoDB",
        }
        
        return common_ports.get(port)


# Backward compatibility functions
def validate_project_name(name: str) -> Tuple[bool, str]:
    """Validate project name (backward compatibility)"""
    return InputValidator.validate_project_name(name)


def validate_domain(domain: str) -> Tuple[bool, str]:
    """Validate domain (backward compatibility)"""
    return InputValidator.validate_domain(domain)


def validate_email(email: str) -> Tuple[bool, str]:
    """Validate email (backward compatibility)"""
    return InputValidator.validate_email(email)


def validate_port_input(port: Union[str, int], check_availability: bool = True) -> Tuple[bool, str]:
    """Validate port input (backward compatibility)"""
    return InputValidator.validate_port(port, check_availability)


def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password (backward compatibility)"""
    return InputValidator.validate_password(password)


def validate_database_name(name: str) -> Tuple[bool, str]:
    """Validate database name (backward compatibility)"""
    return InputValidator.validate_database_name(name)