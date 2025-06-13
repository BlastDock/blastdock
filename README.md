# BlastDock - Docker Deployment CLI Tool

[![PyPI version](https://badge.fury.io/py/blastdock.svg)](https://badge.fury.io/py/blastdock)
[![Website](https://img.shields.io/badge/Website-blastdock.com-blue)](https://blastdock.com)
[![GitHub](https://img.shields.io/badge/GitHub-BlastDock%2Fblastdock-black)](https://github.com/BlastDock/blastdock)

A powerful Python-based CLI tool that simplifies Docker application deployment with comprehensive Traefik reverse proxy integration, automatic SSL certificate management, and intelligent domain routing. Deploy applications with zero-conflict domain management and production-ready SSL certificates in minutes.

## Features

### 🚀 **New in v1.1.0 - Comprehensive Traefik Integration**

- **🔄 Automatic Reverse Proxy**: Traefik integration with auto-installation and configuration
- **🌐 Smart Domain Management**: Automatic subdomain generation and custom domain support  
- **🔒 SSL Automation**: Let's Encrypt certificates with automatic renewal
- **⚡ Zero-Conflict Deployment**: Intelligent port allocation and conflict detection
- **🔧 Migration Tools**: Seamless migration of existing deployments to Traefik
- **📊 Advanced Monitoring**: SSL certificate status and domain health checks

### 📦 **Core Features**

- **Template System**: 100+ built-in templates for popular applications
- **Interactive Configuration**: Guided setup with comprehensive validation
- **Deployment Management**: Deploy, stop, remove operations with safety checks
- **Monitoring**: Real-time status checking and log streaming
- **Safety Features**: Confirmation prompts, input validation, and rollback capabilities

## Installation

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- pip (Python package manager)

### 📦 **Install from PyPI (Recommended)**

```bash
# Install the latest version
pip install blastdock

# Install specific version
pip install blastdock==1.1.0

# Upgrade existing installation
pip install --upgrade blastdock
```

### 🛠 **Install from Source**

```bash
git clone https://github.com/BlastDock/blastdock.git
cd blastdock
pip install -r requirements.txt
pip install -e .
```

### 🌐 **Recommended Hosting**

For optimal performance, we recommend:

- **EcoStack.Cloud** (HIGHLY RECOMMENDED) - Optimized for BlastDock deployments
- Digital Ocean - Basic Droplet (4GB RAM / 2 CPUs)
- Any VPS with Docker support and public IP for SSL certificates

## Quick Start

### 🚀 **Option 1: Deploy with Traefik (Recommended for Production)**

```bash
# 1. Install Traefik with SSL support
blastdock traefik install --email your@email.com --domain yourdomain.com

# 2. List available templates
blastdock templates

# 3. Initialize project with Traefik integration
blastdock init wordpress --traefik --ssl

# 4. Deploy with automatic SSL and domain routing
blastdock deploy mywordpress

# 5. Access at https://mywordpress.yourdomain.com (SSL automatic!)
```

### 🛠 **Option 2: Traditional Port-Based Deployment**

```bash
# 1. List available templates
blastdock templates

# 2. Initialize a new project
blastdock init wordpress --no-traefik

# 3. Deploy the application
blastdock deploy mywordpress

# 4. Check status
blastdock status mywordpress

# 5. View logs
blastdock logs mywordpress
```

## Commands

### 🎯 **Project Management**
- `blastdock init <template>` - Initialize new deployment with Traefik options
- `blastdock deploy <project>` - Deploy application with SSL and domain routing
- `blastdock stop <project>` - Stop deployment
- `blastdock remove <project>` - Remove deployment and clean up domains
- `blastdock list` - List all deployments with status
- `blastdock config <project>` - Show project configuration details

### 🔄 **Traefik Management**
- `blastdock traefik install` - Install Traefik with Let's Encrypt
- `blastdock traefik status` - Show Traefik status and certificate info
- `blastdock traefik restart` - Restart Traefik service
- `blastdock traefik logs` - View Traefik logs
- `blastdock traefik dashboard` - Open Traefik dashboard
- `blastdock traefik remove` - Remove Traefik installation

### 🌐 **Domain Management**
- `blastdock domain list` - List all used domains and subdomains
- `blastdock domain check <domain>` - Check domain availability and DNS
- `blastdock domain set-default <domain>` - Set default domain for deployments

### 🔌 **Port Management**
- `blastdock ports list` - Show all port allocations and conflicts
- `blastdock ports conflicts` - Check for port conflicts
- `blastdock ports reserve <port>` - Reserve a specific port
- `blastdock ports release <port>` - Release a reserved port

### 🔧 **Migration Tools**
- `blastdock migrate to-traefik [project]` - Migrate project(s) to Traefik
- `blastdock migrate rollback <project>` - Rollback Traefik migration

### 🔒 **SSL Certificate Management**
- `blastdock ssl status` - Show SSL certificate status for all domains
- `blastdock ssl renew <domain>` - Force certificate renewal
- `blastdock ssl test <domain>` - Test SSL configuration

### 📊 **Monitoring**
- `blastdock status <project>` - Check deployment status with domain info
- `blastdock logs <project>` - View logs
- `blastdock logs <project> -f` - Follow logs
- `blastdock logs <project> -s <service>` - View specific service logs

### 📋 **Templates**
- `blastdock templates` - List 100+ available templates

## 📋 Available Templates

BlastDock includes **100+ production-ready templates** for popular applications:

### 🌐 **Web Applications**
- **WordPress** - Complete blog/CMS with MySQL
- **Ghost** - Modern publishing platform
- **Drupal** - Enterprise content management
- **Joomla** - Flexible CMS platform
- **NextCloud** - Self-hosted cloud storage
- **WikiJS** - Modern wiki software

### 🔧 **Development Tools**
- **GitLab** - Complete DevOps platform
- **Gitea** - Lightweight Git service
- **Jenkins** - CI/CD automation
- **Drone** - Modern CI platform
- **SonarQube** - Code quality analysis

### 📊 **Databases**
- **MySQL** - Popular relational database
- **PostgreSQL** - Advanced SQL database  
- **MongoDB** - NoSQL document database
- **Redis** - In-memory data store
- **InfluxDB** - Time series database
- **CockroachDB** - Distributed SQL

### 📈 **Monitoring & Analytics**
- **Grafana** - Data visualization
- **Prometheus** - Metrics collection
- **Metabase** - Business intelligence
- **Matomo** - Privacy-focused analytics
- **Plausible** - Simple web analytics

### 💬 **Communication**
- **Mattermost** - Team messaging
- **Rocket.Chat** - Team collaboration
- **Discord** - Community platform
- **Matrix** - Decentralized chat

### 🎮 **Media & Entertainment**
- **Jellyfin** - Media streaming
- **Plex** - Media organization
- **Airsonic** - Music streaming
- **PhotoPrism** - Photo management

### ⚙️ **All Templates Support:**
- 🔄 **Traefik Integration** - Automatic reverse proxy setup
- 🔒 **SSL Certificates** - Let's Encrypt automation
- 🌐 **Custom Domains** - Your domain or auto-generated subdomains
- 📦 **One-Click Deploy** - Production-ready in minutes
- 🔧 **Easy Migration** - Upgrade existing deployments

View all templates:
```bash
blastdock templates
```

## Project Structure

After initialization, projects are organized as:

```
./deploys/
├── project1/
│   ├── docker-compose.yml
│   ├── .env
│   ├── .blastdock.json
│   ├── config/
│   └── logs/
└── project2/
    ├── docker-compose.yml
    ├── .env
    └── config/
```

## Configuration

### Interactive Mode
Use the `-i` flag for interactive configuration:
```bash
blastdock init wordpress -i
```

### Environment Variables
Each project gets its own `.env` file with configuration variables.

### Global Configuration
Global settings are stored in `~/.blastdock/config.yml`.

## 🚀 Examples

### 🌐 **Production WordPress with SSL**
```bash
# Install Traefik with your domain
blastdock traefik install --email admin@yourdomain.com --domain yourdomain.com

# Initialize WordPress with Traefik integration
blastdock init wordpress --traefik --ssl
# Enter project name: myblog
# Auto-generated subdomain: myblog.yourdomain.com
# SSL certificates: Enabled

# Deploy with automatic SSL
blastdock deploy myblog

# ✅ Access at https://myblog.yourdomain.com (SSL automatic!)
```

### 🔧 **Development Environment**
```bash
# Initialize MySQL for development (no Traefik)
blastdock init mysql --no-traefik
# Enter project name: devdb
# Enter MySQL port: 3306
# Auto-generate root password

# Deploy
blastdock deploy devdb

# Connect to MySQL on localhost:3306
```

### 📊 **Full-Stack Application**
```bash
# Deploy multiple services with domain routing
blastdock init nextcloud --traefik --domain cloud.yourdomain.com
blastdock init grafana --traefik --subdomain monitoring
blastdock init redis --traefik --subdomain cache

# Deploy all services
blastdock deploy nextcloud
blastdock deploy grafana  
blastdock deploy redis

# Access:
# ✅ https://cloud.yourdomain.com (NextCloud)
# ✅ https://monitoring.yourdomain.com (Grafana)
# ✅ https://cache.yourdomain.com (Redis)
```

### 🔄 **Migrate Existing Project**
```bash
# Check migration compatibility
blastdock migrate to-traefik

# Migrate specific project to Traefik
blastdock migrate to-traefik myproject --ssl

# Migrate all compatible projects
blastdock migrate to-traefik --all
```

## 🛡️ Safety Features

### 🔒 **Security & Validation**
- **Port Conflict Detection** - Automatic detection and resolution
- **Domain Validation** - DNS checking and availability verification
- **SSL Certificate Monitoring** - Automatic renewal and health checks
- **Input Validation** - Comprehensive validation for all user inputs
- **Auto-Generated Secure Passwords** - Cryptographically secure defaults

### 🔄 **Operational Safety**
- **Confirmation Prompts** - Interactive confirmations for destructive operations
- **Project Isolation** - Complete separation between deployments
- **Backup & Rollback** - Migration backup and rollback capabilities
- **Dry Run Mode** - Test migrations without making changes
- **Health Checks** - Automatic service health monitoring

## 🚨 Advanced Error Handling

BlastDock provides intelligent error detection and resolution:

### 🔧 **Infrastructure Issues**
- **Docker Connection** - Automatic Docker daemon detection and suggestions
- **Port Conflicts** - Smart port allocation with conflict resolution
- **Network Issues** - DNS and connectivity troubleshooting
- **SSL Problems** - Certificate validation and renewal guidance

### ⚙️ **Configuration Issues**
- **Invalid Configurations** - Detailed validation with suggestions
- **Missing Dependencies** - Automatic dependency checking
- **Template Errors** - Template validation and syntax checking
- **Domain Problems** - DNS propagation and SSL certificate issues

### 📋 **Detailed Diagnostics**
- **Comprehensive Logs** - Structured logging with context
- **Health Checks** - Service-level health monitoring
- **Migration Validation** - Pre-migration compatibility checks
- **Recovery Suggestions** - Actionable steps for problem resolution

## Development

### Adding New Templates

1. Create a new YAML file in `blastdock/templates/`
2. Define template structure with fields and compose configuration
3. Test with `blastdock init <template-name>`

### Template Format
```yaml
template_info:
  description: "Service description"
  version: "1.0"
  services:
    - service1

fields:
  field_name:
    type: string|port|password|domain|email
    description: "Field description"
    default: "default_value"
    required: true|false

compose:
  # Docker Compose configuration
  version: '3.8'
  services:
    # Service definitions with Jinja2 templating

config_files:
  # Optional configuration files to create
  - path: config/file.conf
    content: |
      # File content with templating
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Visit our website: [blastdock.com](https://blastdock.com)
- Review existing issues on [GitHub](https://github.com/BlastDock/blastdock/issues)
- Create a new issue with details
- Join our community forum at [community.blastdock.com](https://community.blastdock.com)