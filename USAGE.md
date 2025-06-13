# BlastDock v1.1.0 - Complete Usage Guide

## 🚀 Quick Start Guide

### Option 1: Production Setup with Traefik + SSL

Perfect for production deployments with automatic SSL certificates and domain routing.

```bash
# 1. Install Traefik with your domain
blastdock traefik install --email admin@yourdomain.com --domain yourdomain.com

# 2. Deploy WordPress with automatic SSL
blastdock init wordpress --traefik --ssl --name myblog
blastdock deploy myblog

# ✅ Access at https://myblog.yourdomain.com (SSL automatic!)
```

### Option 2: Development Setup (Traditional Ports)

Great for local development and testing.

```bash
# 1. Deploy MySQL database
blastdock init mysql --no-traefik --name devdb
blastdock deploy devdb

# 2. Connect at localhost:3306 with generated credentials
blastdock status devdb  # Shows credentials and status
```

## 📋 Complete Command Reference

### 🎯 **Project Management**

```bash
# Initialize new project with options
blastdock init <template> [OPTIONS]
  --traefik/--no-traefik    # Enable/disable Traefik integration
  --ssl/--no-ssl            # Enable/disable SSL certificates
  --domain <domain>         # Custom domain (e.g., app.yourdomain.com)
  --subdomain <subdomain>   # Custom subdomain (e.g., app)
  --name <name>             # Project name
  --interactive, -i         # Interactive mode

# Deploy project
blastdock deploy <project>

# Project status and monitoring
blastdock status <project>     # Detailed status with domain info
blastdock logs <project>       # View logs
blastdock logs <project> -f    # Follow logs real-time
blastdock logs <project> -s <service>  # Specific service logs

# Project lifecycle
blastdock stop <project>       # Stop project
blastdock remove <project>     # Remove project (with confirmation)
blastdock list                 # List all projects
blastdock config <project>     # Show project configuration
```

### 🔄 **Traefik Management**

```bash
# Install and configure Traefik
blastdock traefik install --email <email> --domain <domain>
  --dashboard/--no-dashboard    # Enable/disable dashboard
  --dashboard-domain <domain>   # Custom dashboard domain

# Traefik operations
blastdock traefik status       # Show status and certificate info
blastdock traefik logs         # View Traefik logs
blastdock traefik logs -f      # Follow Traefik logs
blastdock traefik restart      # Restart Traefik
blastdock traefik dashboard    # Open dashboard in browser
blastdock traefik remove       # Remove Traefik (with confirmation)
```

### 🌐 **Domain Management**

```bash
# Domain operations
blastdock domain list                    # List all domains/subdomains
blastdock domain check <domain>          # Check domain status and DNS
blastdock domain set-default <domain>    # Set default domain for new projects
```

### 🔌 **Port Management**

```bash
# Port operations
blastdock ports list           # Show all port allocations
blastdock ports conflicts      # Check for port conflicts
blastdock ports reserve <port> # Reserve specific port
blastdock ports release <port> # Release reserved port
```

### 🔒 **SSL Certificate Management**

```bash
# SSL operations
blastdock ssl status           # Show all SSL certificate status
blastdock ssl renew <domain>   # Force certificate renewal
blastdock ssl test <domain>    # Test SSL configuration
```

### 🔧 **Migration Tools**

```bash
# Migration operations
blastdock migrate to-traefik                    # Show migration compatibility
blastdock migrate to-traefik <project>          # Migrate specific project
blastdock migrate to-traefik --all              # Migrate all compatible projects
blastdock migrate to-traefik <project> --dry-run # Test migration
blastdock migrate rollback <project>            # Rollback migration
```

## 📚 Real-World Examples

### 🌐 **Production WordPress Site**

```bash
# 1. Set up Traefik with your domain
blastdock traefik install --email admin@mybusiness.com --domain mybusiness.com

# 2. Deploy WordPress with SSL
blastdock init wordpress --traefik --ssl --domain www.mybusiness.com
blastdock deploy wordpress-site

# 3. Deploy additional services with subdomains
blastdock init grafana --traefik --ssl --subdomain monitoring
blastdock deploy monitoring

# ✅ Access:
# https://www.mybusiness.com (WordPress)
# https://monitoring.mybusiness.com (Grafana)
```

### 🔧 **Development Environment**

```bash
# 1. Set up databases for development
blastdock init mysql --no-traefik --name devdb
blastdock init redis --no-traefik --name cache
blastdock init postgres --no-traefik --name pgdb

# 2. Deploy all services
blastdock deploy devdb
blastdock deploy cache  
blastdock deploy pgdb

# 3. Connect to services
# MySQL: localhost:3306
# Redis: localhost:6379
# PostgreSQL: localhost:5432
```

### 📊 **Monitoring Stack**

```bash
# 1. Deploy monitoring services with Traefik
blastdock init grafana --traefik --ssl --subdomain grafana
blastdock init prometheus --traefik --ssl --subdomain metrics
blastdock init loki --traefik --ssl --subdomain logs

# 2. Deploy all services
blastdock deploy grafana
blastdock deploy prometheus
blastdock deploy loki

# ✅ Access with SSL:
# https://grafana.yourdomain.com
# https://metrics.yourdomain.com  
# https://logs.yourdomain.com
```

### 🔄 **Migrating Existing Projects**

```bash
# 1. Check what can be migrated
blastdock migrate to-traefik

# 2. Test migration (dry run)
blastdock migrate to-traefik myproject --dry-run

# 3. Perform migration with SSL
blastdock migrate to-traefik myproject --ssl

# 4. Rollback if needed
blastdock migrate rollback myproject
```

## 📋 **Available Templates (100+)**

### Popular Templates:
- **wordpress** - WordPress + MySQL with SSL support
- **nextcloud** - Self-hosted cloud storage
- **grafana** - Data visualization and monitoring
- **mysql/postgresql** - Database servers
- **redis** - In-memory data store  
- **nginx** - Web server and reverse proxy
- **gitlab** - Complete DevOps platform
- **jenkins** - CI/CD automation
- **mattermost** - Team communication
- **jellyfin** - Media streaming server

View all available templates:
```bash
blastdock templates
```

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