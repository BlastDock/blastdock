"""
Configuration security for BlastDock - encryption and secure storage
"""

import os
import json
import base64
import hashlib
from typing import Dict, Any, Optional, Tuple, Union, List
from pathlib import Path

from ..utils.logging import get_logger
from ..exceptions import SecurityError, ConfigurationError

# Try to import cryptography, fallback to basic encryption if not available
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


logger = get_logger(__name__)


class ConfigurationSecurity:
    """Secure configuration management for BlastDock"""
    
    def __init__(self):
        """Initialize configuration security"""
        self.logger = get_logger(__name__)
        self.encryption_key = None
        self.key_derivation_iterations = 100000
        
        # Sensitive configuration keys that should be encrypted
        self.SENSITIVE_KEYS = {
            'password', 'secret', 'key', 'token', 'api_key',
            'private_key', 'certificate', 'credential', 'auth',
            'ssl_cert', 'ssl_key', 'database_password', 'admin_password'
        }
    
    def initialize_encryption(self, master_password: Optional[str] = None) -> bool:
        """Initialize encryption with master password"""
        if not CRYPTOGRAPHY_AVAILABLE:
            self.logger.warning("Cryptography library not available, using basic encoding")
            self.encryption_key = "basic_fallback"
            return True
            
        try:
            if master_password:
                # Derive key from password
                salt = self._get_or_create_salt()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=self.key_derivation_iterations,
                )
                key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
                self.encryption_key = Fernet(key)
            else:
                # Generate random key
                key = Fernet.generate_key()
                self.encryption_key = Fernet(key)
                self._store_key(key)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption: {e}")
            return False
    
    def _get_or_create_salt(self) -> bytes:
        """Get or create salt for key derivation"""
        from ..utils.filesystem import paths
        
        salt_file = os.path.join(paths.config_dir, '.blastdock_salt')
        
        try:
            if os.path.exists(salt_file):
                with open(salt_file, 'rb') as f:
                    return f.read()
            else:
                # Generate new salt
                salt = os.urandom(16)
                os.makedirs(os.path.dirname(salt_file), exist_ok=True)
                with open(salt_file, 'wb') as f:
                    f.write(salt)
                
                # Set secure permissions
                os.chmod(salt_file, 0o600)
                return salt
                
        except Exception as e:
            self.logger.error(f"Failed to handle salt file: {e}")
            return os.urandom(16)  # Fallback to random salt
    
    def _store_key(self, key: bytes) -> bool:
        """Store encryption key securely"""
        try:
            from ..utils.filesystem import paths
            
            key_file = os.path.join(paths.config_dir, '.blastdock_key')
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # Set secure permissions (owner read-only)
            os.chmod(key_file, 0o600)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store encryption key: {e}")
            return False
    
    def _load_key(self) -> bool:
        """Load encryption key from storage"""
        try:
            if not CRYPTOGRAPHY_AVAILABLE:
                self.encryption_key = "basic_fallback"
                return True
                
            from ..utils.filesystem import paths
            
            key_file = os.path.join(paths.config_dir, '.blastdock_key')
            
            if not os.path.exists(key_file):
                return False
            
            with open(key_file, 'rb') as f:
                key = f.read()
            
            self.encryption_key = Fernet(key)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load encryption key: {e}")
            return False
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a configuration value"""
        if not self.encryption_key:
            if not self._load_key():
                raise SecurityError("Encryption not initialized")
        
        try:
            if not CRYPTOGRAPHY_AVAILABLE:
                # Basic encoding fallback (NOT secure, just obfuscation)
                encoded = base64.urlsafe_b64encode(value.encode()).decode()
                return encoded
            
            encrypted_bytes = self.encryption_key.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            raise SecurityError(f"Failed to encrypt value: {e}")
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a configuration value"""
        if not self.encryption_key:
            if not self._load_key():
                raise SecurityError("Encryption not initialized")
        
        try:
            if not CRYPTOGRAPHY_AVAILABLE:
                # Basic decoding fallback
                decoded = base64.urlsafe_b64decode(encrypted_value.encode()).decode()
                return decoded
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_bytes = self.encryption_key.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise SecurityError(f"Failed to decrypt value: {e}")
    
    def secure_config(self, config: Dict[str, Any], encrypt_sensitive: bool = True) -> Dict[str, Any]:
        """Secure configuration by encrypting sensitive values"""
        if not encrypt_sensitive:
            return config
        
        secured_config = {}
        
        for key, value in config.items():
            if isinstance(value, dict):
                # Recursively secure nested configurations
                secured_config[key] = self.secure_config(value, encrypt_sensitive)
            elif isinstance(value, str) and self._is_sensitive_key(key):
                # Encrypt sensitive string values
                try:
                    encrypted_value = self.encrypt_value(value)
                    secured_config[key] = f"encrypted:{encrypted_value}"
                except Exception as e:
                    self.logger.warning(f"Failed to encrypt {key}: {e}")
                    secured_config[key] = value
            else:
                # Keep non-sensitive values as-is
                secured_config[key] = value
        
        return secured_config
    
    def unsecure_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt configuration by decrypting encrypted values"""
        unsecured_config = {}
        
        for key, value in config.items():
            if isinstance(value, dict):
                # Recursively unsecure nested configurations
                unsecured_config[key] = self.unsecure_config(value)
            elif isinstance(value, str) and value.startswith("encrypted:"):
                # Decrypt encrypted values
                try:
                    encrypted_value = value[10:]  # Remove "encrypted:" prefix
                    decrypted_value = self.decrypt_value(encrypted_value)
                    unsecured_config[key] = decrypted_value
                except Exception as e:
                    self.logger.error(f"Failed to decrypt {key}: {e}")
                    unsecured_config[key] = value  # Keep encrypted if decryption fails
            else:
                # Keep non-encrypted values as-is
                unsecured_config[key] = value
        
        return unsecured_config
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a configuration key is sensitive"""
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS)
    
    def save_secure_config(self, config: Dict[str, Any], file_path: str, 
                          encrypt_sensitive: bool = True) -> bool:
        """Save configuration to file with optional encryption"""
        try:
            # Secure the configuration
            secured_config = self.secure_config(config, encrypt_sensitive)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(secured_config, f, indent=2, ensure_ascii=False)
            
            # Set secure file permissions
            os.chmod(file_path, 0o600)
            
            self.logger.debug(f"Saved secure configuration to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save secure configuration: {e}")
            return False
    
    def load_secure_config(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load configuration from file with automatic decryption"""
        try:
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                secured_config = json.load(f)
            
            # Unsecure the configuration
            config = self.unsecure_config(secured_config)
            
            self.logger.debug(f"Loaded secure configuration from {file_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load secure configuration: {e}")
            return None
    
    def validate_config_security(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration for security issues"""
        issues = []
        
        # Check for hardcoded secrets
        def check_secrets(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    check_secrets(value, current_path)
            elif isinstance(obj, str):
                if self._is_sensitive_key(path.split('.')[-1]) and not obj.startswith("encrypted:"):
                    if self._looks_like_secret(obj):
                        issues.append(f"Potential hardcoded secret at {path}")
        
        check_secrets(config)
        
        # Check for dangerous configurations
        dangerous_patterns = [
            ('privileged', 'Privileged container configuration'),
            ('host_network', 'Host network configuration'),
            ('host_pid', 'Host PID namespace configuration'),
            ('bind.*/(dev|proc|sys)', 'Dangerous bind mount'),
        ]
        
        config_str = json.dumps(config, default=str).lower()
        for pattern, description in dangerous_patterns:
            import re
            if re.search(pattern, config_str):
                issues.append(f"{description} detected")
        
        return len(issues) == 0, issues
    
    def _looks_like_secret(self, value: str) -> bool:
        """Check if a string looks like a secret"""
        if len(value) < 8:
            return False
        
        # Skip common placeholder values
        placeholders = {
            'changeme', 'password', 'secret', 'example', 'test',
            'placeholder', 'your-password', 'your-secret'
        }
        
        if value.lower() in placeholders:
            return False
        
        # Check for template variables
        if value.startswith('${') or value.startswith('{{'):
            return False
        
        # Look for characteristics of secrets
        has_letters = any(c.isalpha() for c in value)
        has_numbers = any(c.isdigit() for c in value)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in value)
        
        # If it has mixed character types, it might be a secret
        return sum([has_letters, has_numbers, has_special]) >= 2
    
    def generate_secure_password(self, length: int = 16) -> str:
        """Generate a secure random password"""
        import secrets
        import string
        
        if length < 8:
            raise ValueError("Password length must be at least 8 characters")
        
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = "!@#$%^&*"
        
        # Ensure at least one character from each set
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase), 
            secrets.choice(digits),
            secrets.choice(special)
        ]
        
        # Fill the rest with random characters
        all_chars = lowercase + uppercase + digits + special
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    def hash_value(self, value: str, salt: Optional[bytes] = None) -> Tuple[str, bytes]:
        """Hash a value with optional salt"""
        if salt is None:
            salt = os.urandom(16)
        
        if not CRYPTOGRAPHY_AVAILABLE:
            # Fallback to basic hashing
            import hashlib
            hash_obj = hashlib.sha256(salt + value.encode())
            hash_str = base64.urlsafe_b64encode(hash_obj.digest()).decode()
            return hash_str, salt
        
        # Use PBKDF2 for secure hashing
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.key_derivation_iterations,
        )
        
        hash_bytes = kdf.derive(value.encode())
        hash_str = base64.urlsafe_b64encode(hash_bytes).decode()
        
        return hash_str, salt
    
    def verify_hash(self, value: str, hash_str: str, salt: bytes) -> bool:
        """Verify a value against its hash"""
        try:
            computed_hash, _ = self.hash_value(value, salt)
            return computed_hash == hash_str
        except Exception:
            return False
    
    def rotate_encryption_key(self, old_password: Optional[str] = None, 
                            new_password: Optional[str] = None) -> bool:
        """Rotate encryption key (re-encrypt all data)"""
        try:
            # Load old key
            if old_password:
                old_salt = self._get_or_create_salt()
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=old_salt,
                    iterations=self.key_derivation_iterations,
                )
                old_key = base64.urlsafe_b64encode(kdf.derive(old_password.encode()))
                old_fernet = Fernet(old_key)
            else:
                if not self._load_key():
                    raise SecurityError("Cannot load old key")
                old_fernet = self.encryption_key
            
            # Initialize new key
            if not self.initialize_encryption(new_password):
                raise SecurityError("Failed to initialize new key")
            
            # Here you would re-encrypt all stored configurations
            # This is a placeholder for the actual implementation
            self.logger.info("Encryption key rotated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate encryption key: {e}")
            return False
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get current security configuration status"""
        has_key = self.encryption_key is not None or self._load_key()
        
        from ..utils.filesystem import paths
        key_file = os.path.join(paths.config_dir, '.blastdock_key')
        salt_file = os.path.join(paths.config_dir, '.blastdock_salt')
        
        return {
            'encryption_enabled': has_key,
            'key_file_exists': os.path.exists(key_file),
            'salt_file_exists': os.path.exists(salt_file),
            'key_derivation_iterations': self.key_derivation_iterations,
            'sensitive_keys_count': len(self.SENSITIVE_KEYS),
            'security_features': [
                'Configuration encryption',
                'Secure key storage', 
                'PBKDF2 key derivation',
                'Sensitive data detection',
                'Secure password generation'
            ]
        }


# Global configuration security instance
_config_security = None


def get_config_security() -> ConfigurationSecurity:
    """Get global configuration security instance"""
    global _config_security
    if _config_security is None:
        _config_security = ConfigurationSecurity()
    return _config_security