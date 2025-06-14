# BlastDock v2.0.0 - Complete Usage Guide

## 🚀 Quick Start Guide

### Option 1: Production Setup with Smart Traefik Integration

Perfect for production deployments with automatic SSL certificates and clean templates.

```bash
# 1. Install Traefik (one-time setup)
blastdock traefik install --email admin@yourdomain.com --domain yourdomain.com

# 2. Deploy WordPress with automatic Traefik configuration
blastdock deploy create myblog --template wordpress --traefik

# ✅ BlastDock automatically:
#    - Loads clean template (no Traefik config)
#    - Detects WordPress as web service
#    - Injects all Traefik labels
#    - Configures SSL certificates
#    - Sets up domain routing
#    - Removes port bindings

# 3. Access at https://myblog.yourdomain.com (SSL automatic!)
```

### Option 2: Development Setup (Traditional Ports)

Great for local development without Traefik complexity.

```bash
# 1. Deploy MySQL database
blastdock deploy create devdb --template mysql

# 2. Connect at localhost:3306
blastdock deploy status devdb  # Shows credentials and connection info
```

## 📋 Complete Command Reference

### 🚀 **Deployment Management (NEW)**

```bash
# Create and deploy projects
blastdock deploy create <project> --template <name> [OPTIONS]
  --traefik                 # Enable Traefik integration
  --domain <domain>         # Custom domain (e.g., app.yourdomain.com)
  --subdomain <subdomain>   # Custom subdomain (default: project name)
  --env KEY=VALUE          # Set environment variables

# Manage deployments
blastdock deploy list              # List all deployments
blastdock deploy status <project>  # Detailed status with health
blastdock deploy update <project>  # Update configuration
blastdock deploy remove <project>  # Remove deployment
blastdock deploy logs <project>    # View logs
blastdock deploy exec <project> <command>  # Execute command in container
```

### 🛒 **Template Marketplace (NEW)**

```bash
# Discover templates
blastdock marketplace search [query]     # Search templates
blastdock marketplace featured           # Show featured templates
blastdock marketplace categories         # List categories
blastdock marketplace info <template>    # Template details with ratings

# Install templates
blastdock marketplace install <template>    # Install locally
blastdock marketplace update <template>     # Update template
blastdock marketplace list --installed      # Show installed
blastdock marketplace remove <template>     # Uninstall template
```

### 📊 **Monitoring & Dashboard (NEW)**

```bash
# Health monitoring
blastdock monitoring health <project>       # Check health status
blastdock monitoring metrics <project>      # View metrics
blastdock monitoring alerts                 # Show active alerts
blastdock monitoring dashboard <project>    # Live CLI dashboard

# Web dashboard (NEW)
blastdock monitoring web                    # Start web dashboard
blastdock monitoring web --browser          # Auto-open browser
blastdock monitoring web --port 9000        # Custom port

# Background monitoring
blastdock monitoring background --start     # Start monitoring
blastdock monitoring background --stop      # Stop monitoring
blastdock monitoring background --status    # Check status
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
blastdock traefik restart      # Restart Traefik
blastdock traefik dashboard    # Open dashboard in browser
blastdock traefik remove       # Remove Traefik
```

### 🌐 **Domain Management**

```bash
# Domain operations
blastdock domain list                    # List all domains/subdomains
blastdock domain check <domain>          # Check availability and DNS
blastdock domain set-default <domain>    # Set default domain
blastdock domain validate <domain>       # Validate domain configuration
```

### 🔧 **Configuration Management**

```bash
# BlastDock configuration
blastdock config show                    # Show current configuration
blastdock config set <key> <value>       # Update configuration
blastdock config profiles                # List configuration profiles
blastdock config profile use <name>      # Switch profile
blastdock config validate                # Validate configuration
```

### 🛡️ **Security & Performance**

```bash
# Security scanning
blastdock security scan <project>        # Scan project
blastdock security audit                 # System audit
blastdock security validate              # Validate templates

# Performance optimization
blastdock performance analyze            # Analyze performance
blastdock performance optimize           # Run optimizations
blastdock performance benchmark          # Run benchmarks
```

## 📚 Real-World Examples

### 🌐 **Production WordPress with Smart Traefik**

```bash
# 1. Set up Traefik
blastdock traefik install --email admin@mybusiness.com --domain mybusiness.com

# 2. Deploy WordPress
blastdock deploy create blog --template wordpress --traefik --domain www.mybusiness.com

# 3. Monitor deployment
blastdock monitoring web --browser

# ✅ Access at https://www.mybusiness.com with automatic SSL!
```

### 🛒 **Using the Template Marketplace**

```bash
# 1. Search for CMS templates
blastdock marketplace search cms

# 2. Get details about Ghost
blastdock marketplace info ghost-blog

# 3. Install and deploy
blastdock marketplace install ghost-blog
blastdock deploy create myblog --template ghost --traefik

# 4. Check deployment
blastdock deploy status myblog
```

### 📊 **Complete Monitoring Stack**

```bash
# 1. Deploy monitoring services
blastdock deploy create grafana --template grafana --traefik --subdomain monitor
blastdock deploy create prometheus --template prometheus --traefik --subdomain metrics
blastdock deploy create loki --template grafana-loki --traefik --subdomain logs

# 2. Start web dashboard
blastdock monitoring web --browser

# 3. Access services
# https://monitor.yourdomain.com (Grafana)
# https://metrics.yourdomain.com (Prometheus)
# https://logs.yourdomain.com (Loki)
```

### 🔧 **Development Environment**

```bash
# 1. Deploy databases without Traefik
blastdock deploy create mysql-dev --template mysql
blastdock deploy create redis-dev --template redis
blastdock deploy create postgres-dev --template postgresql

# 2. Check status
blastdock deploy list

# 3. View connection details
blastdock deploy status mysql-dev
```

## 🏗️ **Clean Architecture Benefits**

### How Templates Stay Clean

**Traditional Approach (Complex):**
```yaml
services:
  wordpress:
    image: wordpress
    {% if traefik_enabled %}
    labels:
      - traefik.enable=true
      - traefik.http.routers.wordpress.rule=Host(`{{ domain }}`)
    networks:
      - traefik
    {% else %}
    ports:
      - "80:80"
    {% endif %}
```

**BlastDock Approach (Clean):**
```yaml
# Template contains NO Traefik configuration!
services:
  wordpress:
    image: wordpress
    ports:
      - "80:80"
    # That's it! BlastDock handles everything else
```

### What BlastDock Does

1. **Loads Clean Template** - No Traefik configuration
2. **Detects Web Service** - From template metadata
3. **Injects Labels** - Dynamically based on project
4. **Manages Networks** - Adds external Traefik network
5. **Configures SSL** - Automatic Let's Encrypt
6. **Sets Up Routing** - Domain/subdomain configuration

## 📋 **Popular Templates**

### Web Applications
- **wordpress** - Blog/CMS with MySQL
- **ghost** - Modern publishing platform
- **nextcloud** - Self-hosted cloud storage
- **gitlab** - Complete DevOps platform
- **discourse** - Community forum
- **matomo** - Web analytics

### Databases
- **mysql** - MySQL database
- **postgresql** - PostgreSQL database
- **mongodb** - NoSQL database
- **redis** - In-memory cache
- **elasticsearch** - Search engine

### Monitoring
- **grafana** - Data visualization
- **prometheus** - Metrics collection
- **uptime-kuma** - Uptime monitoring
- **portainer** - Docker management

### Development
- **jenkins** - CI/CD automation
- **gitea** - Lightweight Git service
- **sonarqube** - Code quality
- **drone** - Modern CI platform

View all 100+ templates:
```bash
blastdock marketplace search
```

## 💡 **Tips & Best Practices**

### 1. **Use Marketplace for Discovery**
```bash
# Instead of: blastdock templates
# Use: blastdock marketplace search
```

### 2. **Always Use Deploy Commands**
```bash
# Instead of: blastdock init + blastdock deploy
# Use: blastdock deploy create
```

### 3. **Monitor with Web Dashboard**
```bash
# Start dashboard for visual monitoring
blastdock monitoring web --browser
```

### 4. **Check Template Compatibility**
```bash
# View Traefik compatibility
blastdock marketplace info <template>
```

### 5. **Use Clean Templates**
- Templates have NO Traefik configuration
- BlastDock handles all complexity
- Same template works everywhere

## 🔍 **Troubleshooting**

### Docker Issues
```bash
# Check Docker status
blastdock diagnostics docker

# System health check
blastdock diagnostics system
```

### Port Conflicts
```bash
# Check port usage
blastdock diagnostics network

# List all ports
blastdock ports list
```

### Traefik Issues
```bash
# Check Traefik logs
blastdock traefik logs -f

# Verify certificates
blastdock ssl status
```

### Deployment Problems
```bash
# Check deployment logs
blastdock deploy logs <project>

# Check health status
blastdock monitoring health <project>
```

## 🎯 **Migration Guide**

### From v1.x to v2.0
```bash
# 1. Update BlastDock
pip install --upgrade blastdock

# 2. Migrate existing deployments
blastdock migrate to-v2 --all

# 3. Start using new commands
blastdock deploy create <project> --template <name>
```

### From Docker Compose
```bash
# 1. Create BlastDock template
blastdock template import docker-compose.yml

# 2. Deploy with BlastDock
blastdock deploy create myapp --template imported
```

## 📚 **Advanced Features**

### Custom Domains
```bash
# Use specific domain
blastdock deploy create app --template nginx --traefik --domain app.example.com

# Use subdomain
blastdock deploy create api --template nodejs --traefik --subdomain api
```

### Environment Variables
```bash
# Set during deployment
blastdock deploy create app --template wordpress \
  --env WORDPRESS_DEBUG=true \
  --env WP_MEMORY_LIMIT=256M
```

### Health Monitoring
```bash
# Configure health checks
blastdock monitoring health <project> --interval 30

# Set up alerts
blastdock monitoring alerts create <project> --cpu 80 --memory 90
```

## 🚀 **Getting Started Checklist**

1. ✅ Install BlastDock: `pip install blastdock`
2. ✅ Check Docker: `blastdock diagnostics docker`
3. ✅ Install Traefik: `blastdock traefik install`
4. ✅ Browse marketplace: `blastdock marketplace featured`
5. ✅ Deploy first app: `blastdock deploy create myapp --template wordpress --traefik`
6. ✅ Monitor: `blastdock monitoring web --browser`

## 📞 **Support**

- **Documentation**: [docs.blastdock.com](https://docs.blastdock.com)
- **GitHub**: [github.com/BlastDock/blastdock](https://github.com/BlastDock/blastdock)
- **Community**: [community.blastdock.com](https://community.blastdock.com)
- **Diagnostics**: `blastdock diagnostics system`