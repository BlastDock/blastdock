# Docker Deployment CLI Tool - Usage Guide

## Quick Start with Virtual Environment

Since you're on a system with externally-managed Python packages, follow these steps:

### 1. Activate the Virtual Environment

```bash
source blastdock-env/bin/activate
```

Your prompt should change to show `(blastdock-env)` indicating the virtual environment is active.

### 2. Verify Installation

```bash
blastdock --help
blastdock templates
```

### 3. Create Your First Project

```bash
# Initialize a MySQL database
blastdock init mysql
# Enter project name: mydb

# Deploy it
blastdock deploy mydb

# Check status
blastdock status mydb

# View logs
blastdock logs mydb
```

### 4. Try WordPress

```bash
# Initialize WordPress with MySQL
blastdock init wordpress
# Enter project name: myblog

# Deploy it
blastdock deploy myblog

# Access at http://localhost:8080 (or your configured port)
```

### 5. Management Commands

```bash
# List all projects
blastdock list

# Stop a project
blastdock stop mydb

# Remove a project (destructive!)
blastdock remove mydb

# View logs in real-time
blastdock logs myblog -f
```

## Deactivating Virtual Environment

When you're done, deactivate the virtual environment:

```bash
deactivate
```

## Reactivating Later

To use blastdock again in a new terminal session:

```bash
cd /path/to/blastdock
source blastdock-env/bin/activate
blastdock list
```

## Available Templates

- **mysql** - Standalone MySQL database (port 3306)
- **postgresql** - PostgreSQL database (port 5432)
- **redis** - Redis cache server (port 6379)
- **nginx** - Web server (ports 80/443)
- **wordpress** - WordPress + MySQL (port 8080)
- **n8n** - Workflow automation (port 5678)

## Example Projects

### Development Database
```bash
blastdock init mysql
# Name: devdb
# Use defaults for everything
blastdock deploy devdb
# Connect to localhost:3306 with generated credentials
```

### Personal Blog
```bash
blastdock init wordpress
# Name: myblog
# Domain: myblog.local
# Port: 8080
blastdock deploy myblog
# Access at http://localhost:8080
```

### Automation Server
```bash
blastdock init n8n
# Name: automation
# Port: 5678
blastdock deploy automation
# Access at http://localhost:5678
```

## Project Structure

Each project creates:
```
./deploys/projectname/
├── docker-compose.yml    # Generated Docker Compose file
├── .env                 # Environment variables
├── .blastdock.json     # Project metadata
├── config/             # Configuration files
└── logs/               # Log files
```

## Tips

1. **Check ports**: Make sure ports aren't already in use
2. **Save credentials**: Check the `.env` file for generated passwords
3. **Backup data**: Use `docker volume ls` to see data volumes
4. **Monitor resources**: Use `docker stats` to check resource usage
5. **Clean up**: Use `blastdock remove` to clean up unused projects

## Troubleshooting

### Docker not running
```bash
sudo systemctl start docker  # Linux
# or start Docker Desktop
```

### Port conflicts
```bash
# Find what's using a port
sudo lsof -i :3306
# or
ss -tulpn | grep :3306
```

### Container won't start
```bash
# Check logs for errors
blastdock logs projectname
# Check Docker logs directly
docker logs containername
```

### Reset everything
```bash
# Remove all projects
blastdock list
blastdock remove project1
blastdock remove project2

# Clean Docker volumes
docker volume prune
```