"""
Test suite for filesystem utilities
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from blastdock.utils.filesystem import BlastDockPaths, paths


class TestBlastDockPaths:
    """Test filesystem path management"""
    
    def test_path_properties(self):
        """Test that all path properties return Path objects"""
        test_paths = BlastDockPaths()
        
        assert isinstance(test_paths.config_dir, Path)
        assert isinstance(test_paths.data_dir, Path) 
        assert isinstance(test_paths.cache_dir, Path)
        assert isinstance(test_paths.log_dir, Path)
        assert isinstance(test_paths.templates_dir, Path)
        assert isinstance(test_paths.deploys_dir, Path)
    
    def test_project_path(self):
        """Test project path generation"""
        test_paths = BlastDockPaths()
        project_path = test_paths.get_project_path("test-project")
        
        assert isinstance(project_path, Path)
        assert project_path.name == "test-project"
        assert project_path.parent == test_paths.deploys_dir
    
    def test_template_search_paths(self):
        """Test template search path ordering"""
        test_paths = BlastDockPaths()
        search_paths = test_paths.get_template_search_paths()
        
        assert isinstance(search_paths, list)
        assert len(search_paths) >= 2
        assert all(isinstance(p, Path) for p in search_paths)
        
        # User templates should be first (highest priority)
        assert search_paths[0] == test_paths.templates_dir
    
    @patch('platform.system')
    def test_system_templates_dir_unix(self, mock_system):
        """Test system templates directory on Unix systems"""
        mock_system.return_value = 'Linux'
        test_paths = BlastDockPaths()
        
        system_dir = test_paths.system_templates_dir
        assert str(system_dir).startswith('/usr/share')
    
    @patch('platform.system')
    @patch('os.environ.get')
    def test_system_templates_dir_windows(self, mock_env_get, mock_system):
        """Test system templates directory on Windows"""
        mock_system.return_value = 'Windows'
        mock_env_get.return_value = 'C:\\ProgramData'
        
        test_paths = BlastDockPaths()
        system_dir = test_paths.system_templates_dir
        assert 'ProgramData' in str(system_dir)
    
    def test_ensure_directories(self):
        """Test directory creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock paths to use temp directory
            test_paths = BlastDockPaths()
            original_data_dir = test_paths._data_dir
            
            try:
                # Override with temp directory
                test_paths._data_dir = Path(temp_dir) / "test_blastdock"
                test_paths._config_dir = Path(temp_dir) / "test_config"
                test_paths._cache_dir = Path(temp_dir) / "test_cache"
                test_paths._log_dir = Path(temp_dir) / "test_logs"
                test_paths._templates_dir = test_paths._data_dir / "templates"
                test_paths._deploys_dir = test_paths._data_dir / "deploys"
                
                # Ensure directories
                test_paths.ensure_directories()
                
                # Check that directories were created
                assert test_paths.config_dir.exists()
                assert test_paths.data_dir.exists()
                assert test_paths.cache_dir.exists()
                assert test_paths.log_dir.exists()
                assert test_paths.templates_dir.exists()
                assert test_paths.deploys_dir.exists()
                
            finally:
                # Restore original
                test_paths._data_dir = original_data_dir


class TestBackwardCompatibility:
    """Test backward compatibility functions"""
    
    def test_get_deploys_dir(self):
        """Test get_deploys_dir function"""
        from blastdock.utils.filesystem import get_deploys_dir
        
        result = get_deploys_dir()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_get_project_path(self):
        """Test get_project_path function"""
        from blastdock.utils.filesystem import get_project_path
        
        result = get_project_path("test-project")
        assert isinstance(result, str)
        assert "test-project" in result
    
    def test_ensure_dir(self):
        """Test ensure_dir function"""
        from blastdock.utils.filesystem import ensure_dir
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_path = Path(temp_dir) / "test" / "nested" / "directory"
            
            # Should not exist initially
            assert not test_path.exists()
            
            # Ensure directory
            ensure_dir(test_path)
            
            # Should exist now
            assert test_path.exists()
            assert test_path.is_dir()


if __name__ == "__main__":
    pytest.main([__file__])