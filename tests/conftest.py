"""
Pytest configuration and shared fixtures for BlastDock tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from click.testing import CliRunner

@pytest.fixture
def cli_runner():
    """Click CLI test runner"""
    return CliRunner()

@pytest.fixture
def temp_dir():
    """Temporary directory for tests"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)

@pytest.fixture
def mock_docker_client():
    """Mock Docker client"""
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.containers = Mock()
    mock_client.containers.list.return_value = []
    mock_client.images = Mock()
    mock_client.images.list.return_value = []
    mock_client.networks = Mock()
    mock_client.info.return_value = {'Version': '20.10.0'}
    mock_client.version.return_value = {'Version': '20.10.0'}
    return mock_client

@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = Mock()
    config.projects_dir = "/tmp/blastdock/projects"
    config.templates_dir = "/tmp/blastdock/templates"
    config.default_domain = "localhost"
    config.enable_traefik = True
    return config

@pytest.fixture
def mock_config_manager():
    """Mock configuration manager"""
    manager = Mock()
    manager.config = mock_config()
    manager.profile = "default"
    manager.get_value.return_value = "test_value"
    manager.set_value.return_value = True
    return manager

@pytest.fixture
def sample_template():
    """Sample template data"""
    return {
        'name': 'wordpress',
        'display_name': 'WordPress',
        'description': 'WordPress with MySQL',
        'version': '1.0.0',
        'fields': {
            'domain': {
                'type': 'string',
                'description': 'Domain name',
                'required': False,
                'default': 'localhost'
            },
            'mysql_password': {
                'type': 'password',
                'description': 'MySQL root password',
                'required': True
            }
        },
        'compose': {
            'version': '3.8',
            'services': {
                'wordpress': {
                    'image': 'wordpress:latest',
                    'ports': ['80:80'],
                    'environment': {
                        'WORDPRESS_DB_HOST': 'mysql',
                        'WORDPRESS_DB_PASSWORD': '{{ mysql_password }}'
                    }
                },
                'mysql': {
                    'image': 'mysql:8.0',
                    'environment': {
                        'MYSQL_ROOT_PASSWORD': '{{ mysql_password }}'
                    }
                }
            }
        }
    }

@pytest.fixture
def invalid_template():
    """Invalid template data for error testing"""
    return {
        'name': '',  # Invalid: empty name
        'compose': {
            'services': {}  # Invalid: no services
        }
    }

@pytest.fixture
def mock_template_registry():
    """Mock template registry"""
    registry = Mock()
    registry.get_template.return_value = sample_template()
    registry.list_templates.return_value = ['wordpress', 'nginx', 'mysql']
    return registry

@pytest.fixture
def mock_deployment_manager():
    """Mock deployment manager"""
    manager = Mock()
    manager.deploy_project.return_value = {
        'success': True,
        'project_name': 'test-project',
        'template': 'wordpress',
        'compose_file': '/tmp/test-project/docker-compose.yml'
    }
    return manager

@pytest.fixture
def mock_marketplace():
    """Mock marketplace"""
    marketplace = Mock()
    marketplace.search.return_value = [
        {
            'id': 'wordpress',
            'display_name': 'WordPress',
            'category': 'CMS',
            'rating': 4.5,
            'downloads': 1000,
            'traefik_compatible': True
        }
    ]
    return marketplace

@pytest.fixture(autouse=True)
def mock_logging():
    """Mock logging to avoid log files during tests"""
    with patch('blastdock.utils.logging.get_logger') as mock_logger:
        logger = Mock()
        mock_logger.return_value = logger
        yield logger

@pytest.fixture
def mock_flask_app():
    """Mock Flask application"""
    app = Mock()
    app.run.return_value = None
    return app

@pytest.fixture
def sample_project_config():
    """Sample project configuration"""
    return {
        'name': 'test-project',
        'template': 'wordpress',
        'config': {
            'domain': 'test.localhost',
            'mysql_password': 'secret123'
        },
        'directory': '/tmp/blastdock/projects/test-project',
        'created_at': 1640995200.0,
        'status': 'deployed'
    }

@pytest.fixture
def mock_subprocess():
    """Mock subprocess calls"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(
            returncode=0,
            stdout='Success',
            stderr=''
        )
        yield mock_run

@pytest.fixture(scope="session")
def test_data_dir():
    """Test data directory"""
    return Path(__file__).parent / "fixtures"

# Environment variable mocks
@pytest.fixture(autouse=True)
def mock_env_vars():
    """Mock environment variables"""
    env_vars = {
        'HOME': '/tmp',
        'BLASTDOCK_CONFIG_DIR': '/tmp/.blastdock',
        'DOCKER_HOST': 'unix:///var/run/docker.sock'
    }
    with patch.dict('os.environ', env_vars):
        yield env_vars