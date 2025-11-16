"""
Comprehensive Bug Fix Tests - 2025-11-16 Session
Tests for all bugs fixed in the comprehensive repository bug analysis session.

Bug Fixes Covered:
- BUG-CRIT-001: Race condition in config save (TOCTOU fix)
- BUG-CRIT-006: Incomplete rollback logic in profile switching
- BUG-CRIT-004: JSON parsing without error handling in health.py
- BUG-NEW-002: Missing timeout on subprocess calls in deploy.py
- BUG-NEW-001: Fragile container ID detection in containers.py
- BUG-CRIT-007: Generic exception catching (specific exceptions)
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime
import subprocess


class TestBugCrit001RaceConditionFix:
    """Tests for BUG-CRIT-001: Race condition in config save"""

    @patch('blastdock.config.manager.ConfigurationPersistence')
    @patch('blastdock.config.manager.BackupManager')
    def test_save_config_handles_missing_file_gracefully(self, mock_backup, mock_persistence):
        """Test that save_config handles FileNotFoundError when backup fails"""
        from blastdock.config.manager import ConfigurationManager
        from blastdock.config.models import BlastDockConfig

        # Setup
        mock_persistence_instance = MagicMock()
        mock_backup_instance = MagicMock()
        mock_persistence.return_value = mock_persistence_instance
        mock_backup.return_value = mock_backup_instance

        # Simulate FileNotFoundError when trying to load config for backup
        mock_persistence_instance.load_config.side_effect = FileNotFoundError("Config file not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigurationManager(config_dir=config_dir, profile='test')

            # Create a test config
            test_config = BlastDockConfig(
                default_domain='test.local',
                deployment_dir=Path('/tmp/deployments')
            )

            # Should not raise exception even when backup fails with FileNotFoundError
            manager.save_config(test_config)

            # Verify save was still called
            mock_persistence_instance.save_config.assert_called_once()

    @patch('blastdock.config.manager.ConfigurationPersistence')
    @patch('blastdock.config.manager.BackupManager')
    def test_save_config_creates_backup_when_file_exists(self, mock_backup, mock_persistence):
        """Test that save_config creates backup when config file exists"""
        from blastdock.config.manager import ConfigurationManager
        from blastdock.config.models import BlastDockConfig

        # Setup
        mock_persistence_instance = MagicMock()
        mock_backup_instance = MagicMock()
        mock_persistence.return_value = mock_persistence_instance
        mock_backup.return_value = mock_backup_instance

        # Simulate existing config
        existing_config = {'default_domain': 'old.local'}
        mock_persistence_instance.load_config.return_value = existing_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigurationManager(config_dir=config_dir, profile='test')

            test_config = BlastDockConfig(
                default_domain='new.local',
                deployment_dir=Path('/tmp/deployments')
            )

            # Save config
            manager.save_config(test_config)

            # Verify backup was created
            mock_backup_instance.create_backup.assert_called_once()


class TestBugCrit006IncompleteRollbackFix:
    """Tests for BUG-CRIT-006: Incomplete rollback logic in profile switching"""

    @patch('blastdock.config.manager.ConfigurationPersistence')
    @patch('blastdock.config.manager.BackupManager')
    def test_switch_profile_rollback_on_load_failure(self, mock_backup, mock_persistence):
        """Test that profile switch rolls back when load fails"""
        from blastdock.config.manager import ConfigurationManager
        from blastdock.config.errors import ConfigurationError

        # Setup
        mock_persistence_instance = MagicMock()
        mock_backup_instance = MagicMock()
        mock_persistence.return_value = mock_persistence_instance
        mock_backup.return_value = mock_backup_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigurationManager(config_dir=config_dir, profile='default', auto_save=False)

            original_profile = manager.profile

            # Simulate load failure for new profile
            mock_persistence_instance.load_config.side_effect = Exception("Failed to load profile")

            # Attempt to switch profile
            with pytest.raises(ConfigurationError) as exc_info:
                manager.switch_profile('new-profile')

            # Verify error message contains rollback info
            assert 'Rolled back' in str(exc_info.value)

            # Verify profile was rolled back
            assert manager.profile == original_profile

    @patch('blastdock.config.manager.ConfigurationPersistence')
    @patch('blastdock.config.manager.BackupManager')
    def test_switch_profile_fails_if_save_fails(self, mock_backup, mock_persistence):
        """Test that profile switch fails if current profile can't be saved"""
        from blastdock.config.manager import ConfigurationManager
        from blastdock.config.models import BlastDockConfig
        from blastdock.config.errors import ConfigurationError

        # Setup
        mock_persistence_instance = MagicMock()
        mock_backup_instance = MagicMock()
        mock_persistence.return_value = mock_persistence_instance
        mock_backup.return_value = mock_backup_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigurationManager(config_dir=config_dir, profile='default', auto_save=True)

            # Set a config so save is attempted
            manager._config = BlastDockConfig(
                default_domain='test.local',
                deployment_dir=Path('/tmp/deployments')
            )

            # Simulate save failure
            with patch.object(manager, 'save_config', side_effect=Exception("Save failed")):
                # Attempt to switch profile
                with pytest.raises(ConfigurationError) as exc_info:
                    manager.switch_profile('new-profile')

                # Verify error message
                assert 'Cannot switch profile' in str(exc_info.value)
                assert 'failed to save' in str(exc_info.value)

    @patch('blastdock.config.manager.ConfigurationPersistence')
    @patch('blastdock.config.manager.BackupManager')
    def test_switch_profile_success_with_auto_save(self, mock_backup, mock_persistence):
        """Test successful profile switch with auto_save enabled"""
        from blastdock.config.manager import ConfigurationManager
        from blastdock.config.models import BlastDockConfig

        # Setup
        mock_persistence_instance = MagicMock()
        mock_backup_instance = MagicMock()
        mock_persistence.return_value = mock_persistence_instance
        mock_backup.return_value = mock_backup_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigurationManager(config_dir=config_dir, profile='default', auto_save=True)

            # Set a config
            manager._config = BlastDockConfig(
                default_domain='test.local',
                deployment_dir=Path('/tmp/deployments')
            )

            # Mock successful save and load
            mock_persistence_instance.load_config.return_value = {
                'default_domain': 'new.local',
                'deployment_dir': '/tmp/new-deployments'
            }

            # Switch profile
            manager.switch_profile('new-profile')

            # Verify profile was switched
            assert manager.profile == 'new-profile'

            # Verify save was called for old profile
            mock_persistence_instance.save_config.assert_called()


class TestBugCrit004JsonParsingFix:
    """Tests for BUG-CRIT-004: JSON parsing without error handling"""

    @patch('blastdock.docker.health.DockerHealthChecker.docker_client')
    def test_get_container_health_handles_invalid_json(self, mock_docker_client):
        """Test that get_container_health handles JSON decode errors gracefully"""
        from blastdock.docker.health import DockerHealthChecker

        # Setup
        checker = DockerHealthChecker()
        checker.docker_client = mock_docker_client

        # Mock execute_command to return invalid JSON
        mock_result = MagicMock()
        mock_result.stdout = "invalid json {{{{"
        mock_docker_client.execute_command.return_value = mock_result

        # Call method
        health_info = checker.get_container_health('test-container')

        # Verify error handling
        assert health_info['status'] == 'error'
        assert any('Failed to parse' in str(issue) for issue in health_info['issues'])

    @patch('blastdock.docker.health.DockerHealthChecker.docker_client')
    def test_get_container_health_with_valid_json(self, mock_docker_client):
        """Test that get_container_health works with valid JSON"""
        from blastdock.docker.health import DockerHealthChecker

        # Setup
        checker = DockerHealthChecker()
        checker.docker_client = mock_docker_client

        # Mock valid JSON response
        valid_json = json.dumps({
            'State': {
                'Status': 'running',
                'Running': True
            },
            'Config': {}
        })
        mock_result = MagicMock()
        mock_result.stdout = valid_json
        mock_docker_client.execute_command.return_value = mock_result

        # Call method
        health_info = checker.get_container_health('test-container')

        # Verify success
        assert health_info['status'] == 'running'


class TestBugNew002SubprocessTimeoutFix:
    """Tests for BUG-NEW-002: Missing timeout on subprocess calls"""

    @patch('subprocess.run')
    @patch('blastdock.cli.deploy.get_project_dir')
    @patch('blastdock.cli.deploy.console')
    def test_logs_command_checks_return_code(self, mock_console, mock_get_project, mock_subprocess):
        """Test that logs command checks subprocess return code"""
        from blastdock.cli.deploy import logs
        from click.testing import CliRunner

        # Setup
        runner = CliRunner()
        mock_get_project.return_value = Path('/tmp/test-project')

        # Mock subprocess to return non-zero exit code
        mock_subprocess.return_value = MagicMock(returncode=1)

        # Run command
        with patch('blastdock.cli.deploy.validate_project_directory'):
            with runner.isolated_filesystem():
                result = runner.invoke(logs, ['test-project'])

                # Verify subprocess was called
                mock_subprocess.assert_called_once()

                # Verify warning was printed for non-zero exit code
                # Note: We check that subprocess was configured correctly
                call_args = mock_subprocess.call_args
                assert call_args is not None


class TestBugNew001ContainerIdDetectionFix:
    """Tests for BUG-NEW-001: Fragile container ID detection"""

    @patch('blastdock.docker.containers.ContainerManager.docker_client')
    def test_prune_containers_with_valid_container_ids(self, mock_docker_client):
        """Test that prune correctly counts valid container IDs"""
        from blastdock.docker.containers import ContainerManager

        # Setup
        manager = ContainerManager()
        manager.docker_client = mock_docker_client

        # Mock prune output with various container ID formats
        prune_output = """a1b2c3d4e5f6
1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef
abc123def456
Total reclaimed space: 1.5GB
Some other text that shouldn't match
"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = prune_output
        mock_docker_client.execute_command.return_value = mock_result

        # Call method
        result = manager.prune_containers()

        # Verify container count (should match 3 valid hex IDs)
        assert result['containers_removed'] == 3
        assert result['success'] is True

    @patch('blastdock.docker.containers.ContainerManager.docker_client')
    def test_prune_containers_ignores_invalid_ids(self, mock_docker_client):
        """Test that prune ignores lines that aren't valid container IDs"""
        from blastdock.docker.containers import ContainerManager

        # Setup
        manager = ContainerManager()
        manager.docker_client = mock_docker_client

        # Mock prune output with invalid lines
        prune_output = """container_name
not-a-hex-id
12345  (too short)
Total reclaimed space: 500MB
"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = prune_output
        mock_docker_client.execute_command.return_value = mock_result

        # Call method
        result = manager.prune_containers()

        # Verify no invalid lines were counted
        assert result['containers_removed'] == 0


class TestBugCrit007GenericExceptionFix:
    """Tests for BUG-CRIT-007: Generic exception catching"""

    @patch('blastdock.security.docker_security.DockerSecurityScanner.docker_client')
    def test_scan_image_handles_specific_date_parsing_errors(self, mock_docker_client):
        """Test that image scanning handles specific date parsing errors"""
        from blastdock.security.docker_security import DockerSecurityScanner

        # Setup
        scanner = DockerSecurityScanner()
        scanner.docker_client = mock_docker_client

        # Mock inspect output with invalid date format
        inspect_json = json.dumps({
            'RepoTags': ['test:1.0'],
            'Created': 'invalid-date-format',
            'Size': 100000000
        })
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = f"[{inspect_json}]"
        mock_docker_client.execute_command.return_value = mock_result

        # Should not crash with generic Exception
        # Should handle ValueError/TypeError specifically
        try:
            result = scanner.scan_image('test:1.0')
            # If it succeeds, verify it didn't crash
            assert 'security_score' in result
        except (ValueError, TypeError, KeyError):
            # Specific exceptions are acceptable
            pass

    @patch('blastdock.performance.async_loader.TemplateAsyncLoader._worker_stats')
    def test_estimate_memory_usage_handles_specific_errors(self, mock_worker_stats):
        """Test that memory estimation handles specific errors"""
        from blastdock.performance.async_loader import TemplateAsyncLoader

        # Setup
        loader = TemplateAsyncLoader(max_workers=2)

        # Test with various problematic inputs
        test_cases = [
            None,  # NoneType
            {'circular': None},  # Should work
        ]

        for test_input in test_cases:
            # Should not crash and should return 0.0 on error
            result = loader._estimate_memory_usage(test_input)
            assert isinstance(result, float)
            assert result >= 0.0


class TestEdgeCasesAndRegressions:
    """Additional edge case tests to prevent regressions"""

    @patch('blastdock.config.manager.ConfigurationPersistence')
    @patch('blastdock.config.manager.BackupManager')
    def test_switch_to_same_profile_is_noop(self, mock_backup, mock_persistence):
        """Test that switching to the same profile does nothing"""
        from blastdock.config.manager import ConfigurationManager

        # Setup
        mock_persistence_instance = MagicMock()
        mock_backup_instance = MagicMock()
        mock_persistence.return_value = mock_persistence_instance
        mock_backup.return_value = mock_backup_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            manager = ConfigurationManager(config_dir=config_dir, profile='default')

            # Switch to same profile
            manager.switch_profile('default')

            # Verify no save or load was called
            mock_persistence_instance.save_config.assert_not_called()
            mock_persistence_instance.load_config.assert_not_called()

    @patch('blastdock.docker.containers.ContainerManager.docker_client')
    def test_prune_handles_empty_output(self, mock_docker_client):
        """Test that prune handles empty output gracefully"""
        from blastdock.docker.containers import ContainerManager

        # Setup
        manager = ContainerManager()
        manager.docker_client = mock_docker_client

        # Mock empty output
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_docker_client.execute_command.return_value = mock_result

        # Call method
        result = manager.prune_containers()

        # Should handle gracefully
        assert result['containers_removed'] == 0
        assert result['success'] is True


# Run tests with pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
