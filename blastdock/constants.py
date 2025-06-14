"""
BlastDock Constants - Application-wide constants and configuration
"""

import os
from pathlib import Path

# Version Information
APP_NAME = "blastdock"
APP_DESCRIPTION = "Docker Deployment CLI Tool with Traefik Integration"

# Directory Structure
DEFAULT_DEPLOY_DIR = "./deploys"
CONFIG_DIR_NAME = ".blastdock"
TEMPLATES_DIR = "templates"
LOGS_DIR = "logs"
DATA_DIR = "data"

# File Names
COMPOSE_FILE = "docker-compose.yml"
ENV_FILE = ".env"
PROJECT_CONFIG_FILE = ".blastdock.json"
GLOBAL_CONFIG_FILE = "config.yml"
DOMAINS_FILE = "domains.json"
PORTS_FILE = "ports.json"
SSL_CONFIG_FILE = "ssl.json"

# Traefik Configuration
TRAEFIK_CONTAINER_NAME = "blastdock-traefik"
TRAEFIK_NETWORK = "blastdock-network"
TRAEFIK_PROJECT_NAME = "blastdock-traefik"
TRAEFIK_CONFIG_DIR = "traefik"
TRAEFIK_CERTS_DIR = "letsencrypt"

# Network Configuration
DEFAULT_DOMAIN = "blastdock.local"
TRAEFIK_DASHBOARD_PORT = 8080
TRAEFIK_HTTP_PORT = 80
TRAEFIK_HTTPS_PORT = 443

# Port Ranges
DEFAULT_PORT_RANGE_START = 8000
DEFAULT_PORT_RANGE_END = 9000
RESERVED_PORTS = [22, 80, 443, 8080, 3306, 5432, 6379]

# Docker Configuration
DOCKER_COMPOSE_VERSION = "3.8"
DEFAULT_RESTART_POLICY = "unless-stopped"

# SSL Configuration
SSL_CERT_EXPIRY_WARNING_DAYS = 30
SSL_CERT_RENEWAL_DAYS = 7

# Validation Patterns
DOMAIN_PATTERN = r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$'
PROJECT_NAME_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$'
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Template Categories
TEMPLATE_CATEGORIES = {
    'web': ['wordpress', 'ghost', 'drupal', 'joomla', 'nextcloud', 'wikijs'],
    'database': ['mysql', 'postgresql', 'mongodb', 'redis', 'influxdb', 'cockroachdb'],
    'monitoring': ['grafana', 'prometheus', 'metabase', 'matomo', 'plausible'],
    'development': ['gitlab', 'gitea', 'jenkins', 'drone', 'sonarqube'],
    'communication': ['mattermost', 'rocketchat', 'matrix'],
    'media': ['jellyfin', 'plex', 'airsonic', 'photoprism'],
}

# Error Messages
ERROR_MESSAGES = {
    'docker_not_running': "Docker daemon is not running. Please start Docker and try again.",
    'template_not_found': "Template '{template}' not found. Use 'blastdock templates' to see available templates.",
    'project_not_found': "Project '{project}' not found. Use 'blastdock list' to see existing projects.",
    'domain_invalid': "Invalid domain format: {domain}",
    'port_in_use': "Port {port} is already in use by another service.",
    'traefik_not_installed': "Traefik is not installed. Use 'blastdock traefik install' to install it.",
    'ssl_cert_error': "SSL certificate error for domain {domain}: {error}",
    'network_error': "Network connectivity error: {error}",
}

# Success Messages
SUCCESS_MESSAGES = {
    'project_created': "✓ Successfully created project '{project}'",
    'project_deployed': "✓ Successfully deployed '{project}'",
    'project_stopped': "✓ Successfully stopped '{project}'",
    'project_removed': "✓ Successfully removed '{project}'",
    'traefik_installed': "✓ Traefik installed successfully",
    'ssl_cert_issued': "✓ SSL certificate issued for {domain}",
    'migration_complete': "✓ Migration to Traefik completed successfully",
}

# Timeouts (in seconds)
DOCKER_TIMEOUT = 30
HTTP_TIMEOUT = 10
DNS_TIMEOUT = 5
SSL_CERT_TIMEOUT = 300

# Logging Configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Feature Flags
ENABLE_TELEMETRY = False
ENABLE_AUTO_UPDATE = False
ENABLE_ANALYTICS = False