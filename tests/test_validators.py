"""
Test suite for input validators
"""

import pytest
from blastdock.utils.validators import InputValidator
from blastdock.exceptions import ValidationError, PortValidationError


class TestProjectNameValidation:
    """Test project name validation"""
    
    def test_valid_project_names(self):
        """Test valid project names"""
        valid_names = [
            "myproject",
            "my-project", 
            "my_project",
            "project123",
            "123project",
            "a",
            "project-with-dashes",
            "project_with_underscores"
        ]
        
        for name in valid_names:
            is_valid, error = InputValidator.validate_project_name(name)
            assert is_valid, f"'{name}' should be valid but got error: {error}"
    
    def test_invalid_project_names(self):
        """Test invalid project names"""
        invalid_names = [
            "",
            " ",
            "-project",  # starts with dash
            "project-",  # ends with dash
            "pro--ject", # consecutive dashes
            "my project", # contains space
            "my.project", # contains dot
            "project@name", # contains special char
            "a" * 51,    # too long
            "CON",       # reserved name
            "aux",       # reserved name (case insensitive)
        ]
        
        for name in invalid_names:
            is_valid, error = InputValidator.validate_project_name(name)
            assert not is_valid, f"'{name}' should be invalid but was accepted"


class TestDomainValidation:
    """Test domain validation"""
    
    def test_valid_domains(self):
        """Test valid domain names"""
        valid_domains = [
            "example.com",
            "sub.example.com",
            "test-site.example.org",
            "my-app.herokuapp.com",
            "localhost.localdomain",
            "127.0.0.1",  # IP as domain
        ]
        
        for domain in valid_domains:
            is_valid, error = InputValidator.validate_domain(domain, allow_empty=False)
            assert is_valid, f"'{domain}' should be valid but got error: {error}"
    
    def test_invalid_domains(self):
        """Test invalid domain names"""
        invalid_domains = [
            "invalid",     # no TLD
            ".com",        # starts with dot
            "example.",    # ends with dot
            "ex ample.com", # contains space
            "example..com", # consecutive dots
            "-example.com", # starts with dash
            "example-.com", # ends with dash
        ]
        
        for domain in invalid_domains:
            is_valid, error = InputValidator.validate_domain(domain, allow_empty=False)
            assert not is_valid, f"'{domain}' should be invalid but was accepted"
    
    def test_empty_domain_allowed(self):
        """Test that empty domain is allowed when allow_empty=True"""
        is_valid, error = InputValidator.validate_domain("", allow_empty=True)
        assert is_valid


class TestPortValidation:
    """Test port validation"""
    
    def test_valid_ports(self):
        """Test valid port numbers"""
        valid_ports = [1, 80, 443, 3000, 8080, 65535]
        
        for port in valid_ports:
            is_valid, error = InputValidator.validate_port(port, check_availability=False)
            assert is_valid, f"Port {port} should be valid but got error: {error}"
    
    def test_invalid_ports(self):
        """Test invalid port numbers"""
        invalid_ports = [0, -1, 65536, 100000, "abc", ""]
        
        for port in invalid_ports:
            is_valid, error = InputValidator.validate_port(port, check_availability=False)
            assert not is_valid, f"Port {port} should be invalid but was accepted"
    
    def test_privileged_ports(self):
        """Test privileged port handling"""
        # Should fail without allow_privileged
        is_valid, error = InputValidator.validate_port(80, check_availability=False, allow_privileged=False)
        assert not is_valid
        
        # Should pass with allow_privileged
        is_valid, error = InputValidator.validate_port(80, check_availability=False, allow_privileged=True)
        assert is_valid


class TestPasswordValidation:
    """Test password validation"""
    
    def test_basic_password_validation(self):
        """Test basic password requirements"""
        # Valid passwords
        valid_passwords = [
            "password123",
            "MySecurePass",
            "complex_password_123",
            "a" * 8,  # minimum length
        ]
        
        for password in valid_passwords:
            is_valid, error = InputValidator.validate_password(password)
            assert is_valid, f"Password '{password}' should be valid but got error: {error}"
    
    def test_invalid_passwords(self):
        """Test invalid passwords"""
        invalid_passwords = [
            "",
            "short",    # too short
            "password", # too common
            "123456",   # too common
            "a" * 129,  # too long
        ]
        
        for password in invalid_passwords:
            is_valid, error = InputValidator.validate_password(password)
            assert not is_valid, f"Password '{password}' should be invalid but was accepted"
    
    def test_password_requirements(self):
        """Test password with specific requirements"""
        # Test with uppercase requirement
        is_valid, error = InputValidator.validate_password(
            "password123", require_uppercase=True
        )
        assert not is_valid  # no uppercase
        
        is_valid, error = InputValidator.validate_password(
            "Password123", require_uppercase=True
        )
        assert is_valid  # has uppercase


class TestDatabaseNameValidation:
    """Test database name validation"""
    
    def test_valid_database_names(self):
        """Test valid database names"""
        valid_names = [
            "mydb",
            "my_database",
            "db123",
            "applicationdb",
        ]
        
        for name in valid_names:
            is_valid, error = InputValidator.validate_database_name(name)
            assert is_valid, f"Database name '{name}' should be valid but got error: {error}"
    
    def test_invalid_database_names(self):
        """Test invalid database names"""
        invalid_names = [
            "",
            "123db",      # starts with number
            "my-db",      # contains dash
            "my.db",      # contains dot
            "mysql_test", # starts with mysql (for MySQL)
            "information_schema", # reserved name
        ]
        
        for name in invalid_names:
            is_valid, error = InputValidator.validate_database_name(name)
            assert not is_valid, f"Database name '{name}' should be invalid but was accepted"


class TestSanitization:
    """Test name sanitization"""
    
    def test_sanitize_name(self):
        """Test name sanitization"""
        test_cases = [
            ("my project", "my_project"),
            ("my@project", "my_project"),
            ("my---project", "my_project"),
            ("my___project", "my_project"),
            ("_my_project_", "my_project"),
            ("My Project Name!", "My_Project_Name"),
        ]
        
        for input_name, expected in test_cases:
            result = InputValidator.sanitize_name(input_name)
            assert result == expected, f"Sanitizing '{input_name}' expected '{expected}' but got '{result}'"


if __name__ == "__main__":
    pytest.main([__file__])