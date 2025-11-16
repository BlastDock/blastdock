"""
Tests for bug fixes from 2025-11-16 Session 3
Comprehensive repository bug analysis and fixes
"""

import pytest
import os
import tempfile
import socket
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Test BUG-NEW-001: Path traversal in template_manager.py
class TestTemplateManagerPathTraversal:
    """Test fixes for path traversal vulnerability in TemplateManager"""

    def test_template_name_validation_rejects_path_traversal(self):
        """BUG-NEW-001: Template name validation should reject path traversal sequences"""
        from blastdock.core.template_manager import TemplateManager
        from blastdock.exceptions import TemplateValidationError

        manager = TemplateManager()

        # Test path traversal with ..
        with pytest.raises(TemplateValidationError, match="path traversal"):
            manager.template_exists("../../etc/passwd")

        with pytest.raises(TemplateValidationError, match="path traversal"):
            manager.template_exists("../secret")

        # Test path traversal with absolute paths
        with pytest.raises(TemplateValidationError, match="path traversal"):
            manager.template_exists("/etc/passwd")

        # Test path traversal with backslashes
        with pytest.raises(TemplateValidationError, match="path traversal"):
            manager.template_exists("..\\windows\\system32")

    def test_template_name_validation_rejects_invalid_characters(self):
        """BUG-NEW-001: Template name validation should reject invalid characters"""
        from blastdock.core.template_manager import TemplateManager
        from blastdock.exceptions import TemplateValidationError

        manager = TemplateManager()

        # Test invalid characters
        with pytest.raises(TemplateValidationError, match="invalid characters"):
            manager.template_exists("test@template")

        with pytest.raises(TemplateValidationError, match="invalid characters"):
            manager.template_exists("test template")  # Spaces not allowed

        with pytest.raises(TemplateValidationError, match="invalid characters"):
            manager.template_exists("test$template")

    def test_template_name_validation_accepts_valid_names(self):
        """BUG-NEW-001: Template name validation should accept valid names"""
        from blastdock.core.template_manager import TemplateManager

        manager = TemplateManager()

        # These should not raise exceptions (though template might not exist)
        # We're just testing that validation passes
        try:
            manager.template_exists("valid-template")
            manager.template_exists("valid_template")
            manager.template_exists("ValidTemplate123")
        except Exception as e:
            # If exception is raised, it should not be TemplateValidationError
            from blastdock.exceptions import TemplateValidationError
            assert not isinstance(e, TemplateValidationError), \
                f"Valid template name raised validation error: {e}"

    def test_get_template_info_validates_name(self):
        """BUG-NEW-001: get_template_info should validate template name"""
        from blastdock.core.template_manager import TemplateManager
        from blastdock.exceptions import TemplateValidationError

        manager = TemplateManager()

        with pytest.raises(TemplateValidationError):
            manager.get_template_info("../../../etc/passwd")

    def test_render_template_validates_name(self):
        """BUG-NEW-001: render_template should validate template name"""
        from blastdock.core.template_manager import TemplateManager
        from blastdock.exceptions import TemplateValidationError

        manager = TemplateManager()

        with pytest.raises(TemplateValidationError):
            manager.render_template("../../malicious", {})


# Test BUG-NEW-002: Path traversal in installer.py
class TestTemplateInstallerPathTraversal:
    """Test fixes for path traversal vulnerability in TemplateInstaller"""

    def test_validate_template_name_function(self):
        """BUG-NEW-002: validate_template_name function should reject path traversal"""
        from blastdock.marketplace.installer import validate_template_name
        from blastdock.exceptions import TemplateValidationError

        # Test path traversal sequences
        with pytest.raises(TemplateValidationError, match="path traversal"):
            validate_template_name("../../etc/passwd")

        with pytest.raises(TemplateValidationError, match="path traversal"):
            validate_template_name("../malicious")

        with pytest.raises(TemplateValidationError, match="path traversal"):
            validate_template_name("/absolute/path")

        # Test invalid characters
        with pytest.raises(TemplateValidationError, match="invalid characters"):
            validate_template_name("test@template")

        # Test empty name
        with pytest.raises(TemplateValidationError, match="cannot be empty"):
            validate_template_name("")

    def test_validate_template_name_accepts_valid_names(self):
        """BUG-NEW-002: validate_template_name should accept valid names"""
        from blastdock.marketplace.installer import validate_template_name

        # These should not raise exceptions
        validate_template_name("wordpress")
        validate_template_name("my-template")
        validate_template_name("test_template_123")
        validate_template_name("ValidTemplate")


# Test BUG-NEW-004: Socket resource leak in health_checker.py
class TestSocketResourceLeak:
    """Test fixes for socket resource leak in health checker"""

    def test_socket_closed_on_success(self):
        """BUG-NEW-004: Socket should be closed even on successful connection"""
        from blastdock.monitoring.health_checker import HealthChecker, HealthCheckConfig

        checker = HealthChecker()
        config = HealthCheckConfig(timeout=1)

        # Mock socket that succeeds
        with patch('socket.socket') as mock_socket_class:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 0  # Success
            mock_socket_class.return_value = mock_sock

            result = checker._check_tcp(config, '127.0.0.1', 80)

            # Verify socket.close() was called
            mock_sock.close.assert_called_once()

    def test_socket_closed_on_failure(self):
        """BUG-NEW-004: Socket should be closed even on failed connection"""
        from blastdock.monitoring.health_checker import HealthChecker, HealthCheckConfig

        checker = HealthChecker()
        config = HealthCheckConfig(timeout=1)

        # Mock socket that fails
        with patch('socket.socket') as mock_socket_class:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 111  # Connection refused
            mock_socket_class.return_value = mock_sock

            result = checker._check_tcp(config, '127.0.0.1', 80)

            # Verify socket.close() was called
            mock_sock.close.assert_called_once()

    def test_socket_closed_on_exception(self):
        """BUG-NEW-004: Socket should be closed even if exception occurs"""
        from blastdock.monitoring.health_checker import HealthChecker, HealthCheckConfig

        checker = HealthChecker()
        config = HealthCheckConfig(timeout=1)

        # Mock socket that raises exception during connect_ex
        with patch('socket.socket') as mock_socket_class:
            mock_sock = MagicMock()
            mock_sock.connect_ex.side_effect = OSError("Network unreachable")
            mock_socket_class.return_value = mock_sock

            try:
                result = checker._check_tcp(config, '127.0.0.1', 80)
            except:
                pass  # We expect an error

            # Verify socket.close() was called despite exception
            mock_sock.close.assert_called_once()


# Test BUG-NEW-005: TOCTOU race condition in file_security.py
class TestTOCTOURaceCondition:
    """Test fixes for TOCTOU race condition in FileSecurity"""

    def test_safe_copy_handles_file_deletion_during_copy(self):
        """BUG-NEW-005: safe_copy_file should handle file deletion during copy"""
        from blastdock.security.file_security import FileSecurity

        security = FileSecurity()

        with tempfile.NamedTemporaryFile(delete=False) as src_file:
            src_path = src_file.name
            src_file.write(b"test content")

        dst_path = tempfile.mktemp()

        try:
            # Mock shutil.copy2 to delete file before copying
            original_copy2 = __import__('shutil').copy2

            def mock_copy2(src, dst):
                # Delete source file before copy completes
                os.unlink(src)
                raise FileNotFoundError(f"File not found: {src}")

            with patch('shutil.copy2', side_effect=mock_copy2):
                success, error = security.safe_copy_file(src_path, dst_path)

            # Should handle gracefully
            assert not success
            assert "deleted during copy" in error.lower()

        finally:
            # Cleanup
            if os.path.exists(src_path):
                os.unlink(src_path)
            if os.path.exists(dst_path):
                os.unlink(dst_path)

    def test_safe_copy_handles_permission_error(self):
        """BUG-NEW-005: safe_copy_file should handle permission errors gracefully"""
        from blastdock.security.file_security import FileSecurity

        security = FileSecurity()

        with tempfile.NamedTemporaryFile(delete=False) as src_file:
            src_path = src_file.name
            src_file.write(b"test content")

        dst_path = tempfile.mktemp()

        try:
            # Mock shutil.copy2 to raise PermissionError
            with patch('shutil.copy2', side_effect=PermissionError("Permission denied")):
                success, error = security.safe_copy_file(src_path, dst_path, preserve_permissions=True)

            # Should handle gracefully
            assert not success
            assert "permission" in error.lower()

        finally:
            if os.path.exists(src_path):
                os.unlink(src_path)


# Test BUG-NEW-006: Async loader initialization
class TestAsyncLoaderInitialization:
    """Test fixes for async loader partial initialization"""

    @pytest.mark.asyncio
    async def test_async_loader_cleanup_on_failure(self):
        """BUG-NEW-006: Async loader should cleanup on initialization failure"""
        from blastdock.performance.async_loader import get_async_loader, _async_loader

        # Reset global loader
        import blastdock.performance.async_loader as loader_module
        loader_module._async_loader = None

        # Mock AsyncTemplateLoader.start() to fail
        with patch('blastdock.performance.async_loader.AsyncTemplateLoader.start',
                   side_effect=RuntimeError("Initialization failed")):
            with pytest.raises(RuntimeError, match="Failed to initialize"):
                await get_async_loader()

        # Verify global loader is still None after failed initialization
        assert loader_module._async_loader is None


# Test BUG-NEW-007: Silent exceptions in alert_manager.py
class TestSilentExceptionsLogging:
    """Test that silent exceptions are now properly logged"""

    def test_email_unavailable_is_logged(self):
        """BUG-NEW-007: Missing email modules should be logged"""
        from blastdock.monitoring.alert_manager import AlertManager, Alert, NotificationChannel

        manager = AlertManager()
        alert = Alert(rule_name="test", severity="high", message="test")
        channel = NotificationChannel(name="email", type="email", config={})

        # Patch EMAIL_AVAILABLE to False
        with patch('blastdock.monitoring.alert_manager.EMAIL_AVAILABLE', False):
            with patch.object(manager.logger, 'debug') as mock_debug:
                manager._send_email_resolution(alert, channel)

                # Verify logging occurred
                mock_debug.assert_called()
                call_args = str(mock_debug.call_args)
                assert 'unavailable' in call_args.lower() or 'modules' in call_args.lower()

    def test_incomplete_email_config_is_logged(self):
        """BUG-NEW-007: Incomplete email configuration should be logged"""
        from blastdock.monitoring.alert_manager import AlertManager, Alert, NotificationChannel

        manager = AlertManager()
        alert = Alert(rule_name="test_alert", severity="high", message="test")
        channel = NotificationChannel(name="email", type="email",
                                    config={'smtp_server': 'smtp.example.com'})  # Incomplete config

        with patch('blastdock.monitoring.alert_manager.EMAIL_AVAILABLE', True):
            with patch.object(manager.logger, 'warning') as mock_warning:
                manager._send_email_resolution(alert, channel)

                # Verify warning was logged
                mock_warning.assert_called()
                call_args = str(mock_warning.call_args)
                assert 'incomplete' in call_args.lower() or 'missing' in call_args.lower()


# Test BUG-NEW-008: Type validation in environment.py
class TestTypeValidation:
    """Test type validation in environment configuration"""

    def test_environment_variables_type_validation(self):
        """BUG-NEW-008: create_docker_env_file should validate environment_variables type"""
        from blastdock.config.environment import EnvironmentManager

        manager = EnvironmentManager()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            output_path = f.name

        try:
            # Test with invalid type (list instead of dict)
            config = {
                'environment_variables': ['VAR1=value1', 'VAR2=value2']  # Invalid: list, not dict
            }

            with patch.object(manager.logger, 'warning') as mock_warning:
                manager.create_docker_env_file(config, output_path)

                # Verify warning was logged about type mismatch
                mock_warning.assert_called()
                call_args = str(mock_warning.call_args)
                assert 'not a dict' in call_args.lower()

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_default_ports_type_validation(self):
        """BUG-NEW-008: create_docker_env_file should validate default_ports type"""
        from blastdock.config.environment import EnvironmentManager

        manager = EnvironmentManager()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            output_path = f.name

        try:
            # Test with invalid type (string instead of dict)
            config = {
                'default_ports': "3306,5432"  # Invalid: string, not dict
            }

            with patch.object(manager.logger, 'warning') as mock_warning:
                manager.create_docker_env_file(config, output_path)

                # Verify warning was logged about type mismatch
                mock_warning.assert_called()
                call_args = str(mock_warning.call_args)
                assert 'not a dict' in call_args.lower()

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)
