"""
Template-related test fixtures
"""

from typing import Dict, Any, List, Optional
import yaml


class TemplateFixtures:
    """Collection of template fixtures"""
    
    @staticmethod
    def simple_template() -> Dict[str, Any]:
        """Simple template with basic configuration"""
        return {
            'template_info': {
                'name': 'nginx-simple',
                'description': 'Simple Nginx web server',
                'version': '1.0.0',
                'category': 'webserver',
                'maintainer': 'BlastDock Team'
            },
            'fields': [
                {
                    'name': 'port',
                    'label': 'Host Port',
                    'type': 'number',
                    'default': 8080,
                    'required': True,
                    'description': 'Port to expose on the host'
                },
                {
                    'name': 'root_path',
                    'label': 'Document Root',
                    'type': 'string',
                    'default': '/usr/share/nginx/html',
                    'required': False
                }
            ],
            'compose': {
                'version': '3.8',
                'services': {
                    'web': {
                        'image': 'nginx:alpine',
                        'ports': ['${port}:80'],
                        'volumes': ['./html:${root_path}:ro']
                    }
                }
            }
        }
    
    @staticmethod
    def wordpress_template() -> Dict[str, Any]:
        """WordPress template with database"""
        return {
            'template_info': {
                'name': 'wordpress',
                'description': 'WordPress with MySQL database',
                'version': '1.0.0',
                'category': 'cms',
                'web_service': 'wordpress',
                'maintainer': 'BlastDock Team',
                'tags': ['php', 'mysql', 'blog', 'cms']
            },
            'fields': [
                {
                    'name': 'wp_port',
                    'label': 'WordPress Port',
                    'type': 'number',
                    'default': 8080,
                    'required': True
                },
                {
                    'name': 'db_password',
                    'label': 'Database Password',
                    'type': 'password',
                    'required': True,
                    'generate': True,
                    'length': 16
                },
                {
                    'name': 'wp_title',
                    'label': 'Site Title',
                    'type': 'string',
                    'default': 'My WordPress Site',
                    'required': True
                }
            ],
            'compose': {
                'version': '3.8',
                'services': {
                    'wordpress': {
                        'image': 'wordpress:latest',
                        'ports': ['${wp_port}:80'],
                        'environment': {
                            'WORDPRESS_DB_HOST': 'db:3306',
                            'WORDPRESS_DB_USER': 'wordpress',
                            'WORDPRESS_DB_PASSWORD': '${db_password}',
                            'WORDPRESS_DB_NAME': 'wordpress'
                        },
                        'volumes': ['wordpress-data:/var/www/html'],
                        'depends_on': ['db'],
                        'restart': 'unless-stopped'
                    },
                    'db': {
                        'image': 'mysql:8.0',
                        'environment': {
                            'MYSQL_DATABASE': 'wordpress',
                            'MYSQL_USER': 'wordpress',
                            'MYSQL_PASSWORD': '${db_password}',
                            'MYSQL_ROOT_PASSWORD': '${db_password}'
                        },
                        'volumes': ['db-data:/var/lib/mysql'],
                        'restart': 'unless-stopped'
                    }
                },
                'volumes': {
                    'wordpress-data': {},
                    'db-data': {}
                }
            }
        }
    
    @staticmethod
    def template_with_health_checks() -> Dict[str, Any]:
        """Template with health check configurations"""
        return {
            'template_info': {
                'name': 'monitored-app',
                'description': 'Application with health monitoring',
                'version': '1.0.0',
                'category': 'application'
            },
            'fields': [],
            'compose': {
                'version': '3.8',
                'services': {
                    'app': {
                        'image': 'node:16-alpine',
                        'ports': ['3000:3000'],
                        'healthcheck': {
                            'test': ['CMD', 'wget', '--quiet', '--tries=1', '--spider', 'http://localhost:3000/health'],
                            'interval': '30s',
                            'timeout': '3s',
                            'retries': 3,
                            'start_period': '40s'
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def template_with_networks() -> Dict[str, Any]:
        """Template with custom network configuration"""
        return {
            'template_info': {
                'name': 'multi-tier-app',
                'description': 'Multi-tier application with network isolation',
                'version': '1.0.0'
            },
            'fields': [],
            'compose': {
                'version': '3.8',
                'services': {
                    'frontend': {
                        'image': 'nginx:alpine',
                        'ports': ['80:80'],
                        'networks': ['frontend', 'backend']
                    },
                    'api': {
                        'image': 'node:16-alpine',
                        'networks': ['backend']
                    },
                    'database': {
                        'image': 'postgres:13',
                        'networks': ['backend']
                    }
                },
                'networks': {
                    'frontend': {
                        'driver': 'bridge'
                    },
                    'backend': {
                        'driver': 'bridge',
                        'internal': True
                    }
                }
            }
        }
    
    @staticmethod
    def invalid_template() -> Dict[str, Any]:
        """Invalid template for error testing"""
        return {
            'template_info': {
                'name': 'invalid-template'
                # Missing required fields
            },
            'fields': [
                {
                    'name': 'port',
                    # Missing required 'type' field
                    'default': 8080
                }
            ],
            'compose': {
                # Missing version
                'services': {}
            }
        }
    
    @staticmethod
    def template_list() -> List[Dict[str, Any]]:
        """List of template metadata for marketplace"""
        return [
            {
                'name': 'nginx',
                'description': 'Nginx web server',
                'category': 'webserver',
                'version': '1.0.0',
                'downloads': 1500,
                'rating': 4.5,
                'tags': ['web', 'proxy', 'static']
            },
            {
                'name': 'wordpress',
                'description': 'WordPress CMS with MySQL',
                'category': 'cms',
                'version': '2.0.0',
                'downloads': 3000,
                'rating': 4.8,
                'tags': ['blog', 'cms', 'php', 'mysql']
            },
            {
                'name': 'postgres',
                'description': 'PostgreSQL database',
                'category': 'database',
                'version': '1.5.0',
                'downloads': 2500,
                'rating': 4.9,
                'tags': ['database', 'sql', 'postgresql']
            }
        ]


class DeploymentFixtures:
    """Collection of deployment configuration fixtures"""
    
    @staticmethod
    def simple_deployment_config() -> Dict[str, Any]:
        """Simple deployment configuration"""
        return {
            'project_name': 'test-project',
            'template': 'nginx-simple',
            'domain_enabled': False,
            'ssl_enabled': False,
            'config': {
                'port': 8080,
                'root_path': '/usr/share/nginx/html'
            }
        }
    
    @staticmethod
    def deployment_with_traefik() -> Dict[str, Any]:
        """Deployment configuration with Traefik"""
        return {
            'project_name': 'test-app',
            'template': 'wordpress',
            'domain_enabled': True,
            'ssl_enabled': True,
            'domain': 'test-app.example.com',
            'config': {
                'wp_port': 8080,
                'db_password': 'secure_password_123',
                'wp_title': 'Test WordPress Site'
            },
            'traefik': {
                'enabled': True,
                'network': 'traefik-public',
                'entrypoints': ['websecure'],
                'certresolver': 'letsencrypt'
            }
        }
    
    @staticmethod
    def deployment_state() -> Dict[str, Any]:
        """Deployment state information"""
        return {
            'project_name': 'test-project',
            'template': 'nginx-simple',
            'status': 'running',
            'created_at': '2023-01-01T12:00:00Z',
            'updated_at': '2023-01-01T14:00:00Z',
            'containers': [
                {
                    'name': 'test-project_web_1',
                    'id': 'abc123',
                    'status': 'running',
                    'image': 'nginx:alpine',
                    'ports': {'80/tcp': '8080'}
                }
            ],
            'config': {
                'port': 8080,
                'root_path': '/usr/share/nginx/html'
            },
            'health': {
                'overall': 'healthy',
                'services': {
                    'web': {
                        'status': 'healthy',
                        'containers': 1,
                        'healthy_containers': 1
                    }
                }
            }
        }
    
    @staticmethod
    def deployment_history() -> List[Dict[str, Any]]:
        """Deployment history entries"""
        return [
            {
                'timestamp': '2023-01-01T12:00:00Z',
                'action': 'deploy',
                'version': '1.0.0',
                'status': 'success',
                'message': 'Initial deployment'
            },
            {
                'timestamp': '2023-01-01T13:00:00Z',
                'action': 'update',
                'version': '1.0.1',
                'status': 'success',
                'message': 'Updated configuration'
            },
            {
                'timestamp': '2023-01-01T14:00:00Z',
                'action': 'restart',
                'version': '1.0.1',
                'status': 'success',
                'message': 'Restarted services'
            }
        ]


class ConfigurationFixtures:
    """Collection of configuration fixtures"""
    
    @staticmethod
    def blastdock_config() -> Dict[str, Any]:
        """BlastDock configuration"""
        return {
            'version': '1.0.0',
            'default_profile': 'development',
            'profiles': {
                'development': {
                    'docker': {
                        'timeout': 30,
                        'retries': 3
                    },
                    'traefik': {
                        'enabled': False,
                        'network': 'traefik-public'
                    },
                    'monitoring': {
                        'enabled': True,
                        'interval': 60
                    }
                },
                'production': {
                    'docker': {
                        'timeout': 60,
                        'retries': 5
                    },
                    'traefik': {
                        'enabled': True,
                        'network': 'traefik-public',
                        'certresolver': 'letsencrypt'
                    },
                    'monitoring': {
                        'enabled': True,
                        'interval': 30,
                        'alerts': True
                    }
                }
            },
            'marketplace': {
                'registry_url': 'https://registry.blastdock.com',
                'cache_ttl': 3600
            }
        }
    
    @staticmethod
    def user_preferences() -> Dict[str, Any]:
        """User preferences configuration"""
        return {
            'default_editor': 'vim',
            'color_output': True,
            'verbose_logging': False,
            'auto_update_check': True,
            'telemetry_enabled': False,
            'preferred_shell': '/bin/bash'
        }