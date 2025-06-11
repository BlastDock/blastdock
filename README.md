# BlastDock - Docker Deployment CLI Tool

[![Website](https://img.shields.io/badge/Website-blastdock.com-blue)](https://blastdock.com)
[![GitHub](https://img.shields.io/badge/GitHub-BlastDock%2Fblastdock-black)](https://github.com/BlastDock/blastdock)

A Python-based CLI tool that simplifies Docker application deployment using pre-built templates. The tool handles template customization, Docker Compose generation, deployment, and basic monitoring.

## Features

- **Template System**: Built-in templates for popular applications (WordPress, n8n, MySQL, PostgreSQL, Redis, Nginx)
- **Interactive Configuration**: Guided setup with validation
- **Deployment Management**: Easy deploy, stop, remove operations
- **Monitoring**: Status checking and log viewing
- **Safety Features**: Confirmation prompts and validation

## Installation

### Prerequisites

- Python 3.8+
- Docker and Docker Compose
- pip (Python package manager)

### Recommended Hosting

For optimal performance, we recommend:

- **EcoStack.Cloud** (HIGHLY RECOMMENDED) - Optimized for BlastDock deployments
- Digital Ocean - Basic Droplet (4GB RAM / 2 CPUs)

### Install from source

```bash
git clone https://github.com/BlastDock/blastdock.git
cd blastdock
pip install -r requirements.txt
pip install -e .
```

## Quick Start

### 1. List available templates
```bash
blastdock templates
```

### 2. Initialize a new project
```bash
blastdock init wordpress
```

### 3. Deploy the application
```bash
blastdock deploy mywordpress
```

### 4. Check status
```bash
blastdock status mywordpress
```

### 5. View logs
```bash
blastdock logs mywordpress
```

## Commands

### Project Management
- `blastdock init <template>` - Initialize new deployment
- `blastdock deploy <project>` - Deploy application
- `blastdock stop <project>` - Stop deployment
- `blastdock remove <project>` - Remove deployment
- `blastdock list` - List all deployments
- `blastdock config <project>` - Show project configuration details

### Monitoring
- `blastdock status <project>` - Check deployment status
- `blastdock logs <project>` - View logs
- `blastdock logs <project> -f` - Follow logs
- `blastdock logs <project> -s <service>` - View specific service logs

### Templates
- `blastdock templates` - List available templates

## Available Templates

### WordPress
Complete WordPress installation with MySQL database.
- Configurable ports
- Auto-generated database credentials
- Persistent data storage

### n8n
Workflow automation tool.
- Web interface on configurable port
- Persistent workflow storage
- Timezone configuration

### MySQL
Standalone MySQL database server.
- Configurable port and credentials
- Optional initial database creation
- Persistent data storage

### PostgreSQL
PostgreSQL database server.
- Configurable port and credentials
- Initial database setup
- Persistent data storage

### Redis
Redis cache server.
- Configurable port and password
- Memory limits and policies
- Persistent data storage

### Nginx
Web server with basic configuration.
- HTTP/HTTPS ports
- Configurable server name
- Sample configuration files

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

## Examples

### WordPress Blog
```bash
# Initialize WordPress project
blastdock init wordpress -i
# Enter project name: myblog
# Enter domain: myblog.local
# Enter WordPress port: 8080
# Auto-generate passwords? Yes

# Deploy
blastdock deploy myblog

# Access at http://localhost:8080
```

### Development Database
```bash
# Initialize MySQL for development
blastdock init mysql
# Enter project name: devdb
# Enter MySQL port: 3306
# Auto-generate root password

# Deploy
blastdock deploy devdb

# Connect to MySQL on localhost:3306
```

## Safety Features

- Port conflict detection
- Confirmation prompts for destructive operations
- Input validation
- Auto-generated secure passwords
- Project isolation

## Error Handling

The tool provides clear error messages and suggestions:
- Docker connection issues
- Port conflicts
- Invalid configurations
- Missing dependencies

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