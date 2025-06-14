# BlastDock API Documentation

Welcome to the comprehensive BlastDock API documentation. This guide covers all public APIs, classes, and modules available in BlastDock v1.1.0.

## Table of Contents

- [Quick Start](#quick-start)
- [Core APIs](#core-apis)
- [Configuration Management](#configuration-management)
- [Template System](#template-system)
- [Docker Integration](#docker-integration)
- [Security & Validation](#security--validation)
- [Monitoring & Performance](#monitoring--performance)
- [CLI Integration](#cli-integration)
- [Examples](#examples)

## Quick Start

```python
from blastdock.core import DeploymentManager
from blastdock.config import get_config_manager

# Initialize BlastDock
config_manager = get_config_manager()
deployment_manager = DeploymentManager()

# Deploy a WordPress application
result = deployment_manager.deploy_template(
    template_name="wordpress",
    project_name="my-blog",
    domain="blog.example.com",
    variables={
        "mysql_password": "secure_password",
        "admin_email": "admin@example.com"
    }
)

if result.success:
    print(f"Deployment successful: {result.project_path}")
else:
    print(f"Deployment failed: {result.error}")
```

## API Reference Structure

The BlastDock API is organized into the following main modules:

### Core Modules
- **[Core APIs](./core/)** - Main deployment and template management
- **[Configuration](./config/)** - Configuration management and persistence
- **[Docker Integration](./docker/)** - Enhanced Docker operations
- **[Security](./security/)** - Security validation and hardening

### Utility Modules
- **[Templates](./templates/)** - Template system and validation
- **[Monitoring](./monitoring/)** - Health checks and metrics
- **[Performance](./performance/)** - Optimization and caching
- **[CLI](./cli/)** - Command-line interface components

### Support Modules
- **[Utils](./utils/)** - Helper functions and utilities
- **[Exceptions](./exceptions/)** - Custom exception classes
- **[Types](./types/)** - Type definitions and protocols

## Installation and Setup

```bash
# Install BlastDock
pip install blastdock

# Initialize configuration
blastdock config init

# Verify installation
blastdock --version
blastdock config validate
```

## Environment Requirements

- Python 3.8+
- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM recommended
- 10GB+ free disk space

## API Conventions

### Return Types
All BlastDock APIs use consistent return patterns:

```python
from blastdock.types import Result, OperationResult

# Standard result type
class Result:
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    warnings: List[str] = []

# Extended operation result
class OperationResult(Result):
    duration: float
    timestamp: datetime
    metadata: Dict[str, Any]
```

### Error Handling
BlastDock uses custom exceptions with detailed context:

```python
from blastdock.exceptions import (
    BlastDockError,
    DeploymentError,
    ConfigurationError,
    ValidationError
)

try:
    deployment_manager.deploy_template("wordpress", "my-blog")
except DeploymentError as e:
    print(f"Deployment failed: {e}")
    print(f"Details: {e.details}")
    print(f"Suggestions: {e.suggestions}")
```

### Logging
All APIs support structured logging:

```python
from blastdock.utils.logging import get_logger

logger = get_logger(__name__)
logger.info("Starting deployment", extra={
    "template": "wordpress",
    "project": "my-blog"
})
```

## Getting Help

- 📖 **Full Documentation**: [docs.blastdock.com](https://docs.blastdock.com)
- 🐛 **Issue Tracker**: [GitHub Issues](https://github.com/blastdock/blastdock/issues)
- 💬 **Community**: [Discord Server](https://discord.gg/blastdock)
- 📧 **Support**: support@blastdock.com

## License

BlastDock is licensed under the MIT License. See [LICENSE](../../LICENSE) for details.