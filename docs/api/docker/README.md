# Docker Integration API Reference

The Docker Integration API provides comprehensive Docker operations with enhanced error handling, retry logic, and health monitoring.

## Classes Overview

- **[DockerClient](#dockerclient)** - Enhanced Docker client with retry logic
- **[ComposeManager](#composemanager)** - Docker Compose operations
- **[ContainerManager](#containermanager)** - Container lifecycle management
- **[ImageManager](#imagemanager)** - Docker image operations
- **[NetworkManager](#networkmanager)** - Docker network management
- **[VolumeManager](#volumemanager)** - Docker volume operations
- **[DockerHealthChecker](#dockerhealthchecker)** - Docker health monitoring

## DockerClient

The `DockerClient` class provides a robust Docker client with retry logic and enhanced error handling.

### Class Definition

```python
from blastdock.docker import DockerClient, get_docker_client

# Create client instance
client = DockerClient(timeout=30, max_retries=3)

# Or use the singleton client
client = get_docker_client()
```

### Methods

#### check_docker_availability()

Check Docker daemon availability and capabilities.

```python
def check_docker_availability(self) -> Dict[str, Any]:
    """
    Check Docker daemon availability.
    
    Returns:
        Dict containing availability information:
        - docker_available: bool
        - docker_running: bool
        - docker_version: str
        - docker_compose_available: bool
        - docker_compose_version: str
    """
```

**Example Usage:**

```python
# Check Docker availability
availability = client.check_docker_availability()

print("🐳 Docker Status:")
print(f"   Docker Available: {'✅' if availability['docker_available'] else '❌'}")
print(f"   Docker Running: {'✅' if availability['docker_running'] else '❌'}")
print(f"   Docker Version: {availability['docker_version']}")
print(f"   Compose Available: {'✅' if availability['docker_compose_available'] else '❌'}")
print(f"   Compose Version: {availability['docker_compose_version']}")

# Handle Docker not available
if not availability['docker_available']:
    print("❌ Docker is not installed or not in PATH")
    print("💡 Install Docker: https://docs.docker.com/get-docker/")
elif not availability['docker_running']:
    print("❌ Docker daemon is not running")
    print("💡 Start Docker daemon or Docker Desktop")
```

#### execute_command()

Execute Docker commands with retry logic and error handling.

```python
def execute_command(
    self,
    command: List[str],
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
    check: bool = True
) -> subprocess.CompletedProcess:
    """
    Execute Docker command with retry logic.
    
    Args:
        command: Docker command to execute
        cwd: Working directory
        timeout: Command timeout
        check: Raise exception on non-zero exit
    
    Returns:
        Command execution result
    
    Raises:
        DockerError: If command fails after retries
    """
```

**Example Usage:**

```python
# Execute simple Docker command
try:
    result = client.execute_command(['docker', 'ps'])
    print("📋 Running containers:")
    print(result.stdout)
    
except DockerError as e:
    print(f"❌ Docker command failed: {e}")
    print(f"💡 Suggestions: {', '.join(e.suggestions)}")

# Execute with custom timeout and working directory
result = client.execute_command(
    command=['docker', 'build', '-t', 'my-app', '.'],
    cwd='/path/to/dockerfile',
    timeout=600  # 10 minutes
)
```

#### get_system_info()

Get Docker system information and resource usage.

```python
def get_system_info(self) -> Dict[str, Any]:
    """
    Get Docker system information.
    
    Returns:
        System information including containers, images, volumes, etc.
    """
```

**Example Usage:**

```python
# Get Docker system info
system_info = client.get_system_info()

print("📊 Docker System Information:")
print(f"   Containers: {system_info['system']['containers']}")
print(f"   Running: {system_info['system']['containers_running']}")
print(f"   Paused: {system_info['system']['containers_paused']}")
print(f"   Stopped: {system_info['system']['containers_stopped']}")
print(f"   Images: {system_info['system']['images']}")
print(f"   Server Version: {system_info['system']['server_version']}")
print(f"   Memory: {system_info['system']['memory']:,} bytes")
print(f"   CPUs: {system_info['system']['cpus']}")
```

## ComposeManager

The `ComposeManager` class handles Docker Compose operations with validation and error recovery.

### Class Definition

```python
from blastdock.docker import ComposeManager

compose_manager = ComposeManager(
    project_dir="/path/to/project",
    project_name="my-project"
)
```

### Methods

#### start_services()

Start Docker Compose services with health checking.

```python
def start_services(
    self,
    services: Optional[List[str]] = None,
    build: bool = False,
    pull: bool = False,
    compose_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Start Docker Compose services.
    
    Args:
        services: Specific services to start (None = all)
        build: Build images before starting
        pull: Pull images before starting
        compose_file: Path to compose file
    
    Returns:
        Operation result with timing and service status
    """
```

**Example Usage:**

```python
# Start all services
result = compose_manager.start_services()

if result['success']:
    print(f"✅ Services started in {result['startup_time']:.1f} seconds")
    print(f"📋 Started services: {', '.join(result['services_started'])}")
else:
    print("❌ Failed to start services:")
    for error in result['errors']:
        print(f"   • {error}")

# Start specific services with build
result = compose_manager.start_services(
    services=['web', 'database'],
    build=True,
    pull=True
)

# Monitor service startup
for service in result.get('services_started', []):
    print(f"🔄 Starting {service}...")
    
    # Check service health
    status = compose_manager.get_service_status(service)
    if status[service]['state'] == 'running':
        print(f"✅ {service} is running")
    else:
        print(f"❌ {service} failed to start")
```

#### stop_services()

Stop Docker Compose services gracefully.

```python
def stop_services(
    self,
    services: Optional[List[str]] = None,
    timeout: int = 10,
    compose_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Stop Docker Compose services.
    
    Args:
        services: Specific services to stop (None = all)
        timeout: Stop timeout in seconds
        compose_file: Path to compose file
    
    Returns:
        Operation result with timing
    """
```

**Example Usage:**

```python
# Stop all services
result = compose_manager.stop_services()

if result['success']:
    print(f"🛑 Services stopped in {result['stop_time']:.1f} seconds")
else:
    print("❌ Failed to stop services:")
    for error in result['errors']:
        print(f"   • {error}")

# Stop specific services with custom timeout
result = compose_manager.stop_services(
    services=['web'],
    timeout=30  # 30 second timeout
)
```

#### validate_compose_file()

Validate Docker Compose file and provide recommendations.

```python
def validate_compose_file(self, compose_file: str) -> Dict[str, Any]:
    """
    Validate Docker Compose file.
    
    Args:
        compose_file: Path to compose file
    
    Returns:
        Validation results with issues and recommendations
    """
```

**Example Usage:**

```python
# Validate compose file
validation = compose_manager.validate_compose_file("docker-compose.yml")

print(f"📋 Compose File Validation: {validation['compose_file']}")
print(f"   Valid: {'✅' if validation['valid'] else '❌'}")
print(f"   Version: {validation['version']}")
print(f"   Services: {len(validation['services'])}")

if validation['errors']:
    print("\n❌ Errors:")
    for error in validation['errors']:
        print(f"   • {error}")

if validation['warnings']:
    print("\n⚠️  Warnings:")
    for warning in validation['warnings']:
        print(f"   • {warning}")

if validation['recommendations']:
    print("\n💡 Recommendations:")
    for rec in validation['recommendations']:
        print(f"   • {rec}")

# Service analysis
for service_name, service_info in validation['services'].items():
    print(f"\n🔧 Service: {service_name}")
    print(f"   Image: {service_info['image']}")
    if service_info.get('ports'):
        print(f"   Ports: {', '.join(map(str, service_info['ports']))}")
    if service_info.get('volumes'):
        print(f"   Volumes: {len(service_info['volumes'])}")
```

#### build_services()

Build Docker Compose services with progress monitoring.

```python
def build_services(
    self,
    services: Optional[List[str]] = None,
    no_cache: bool = False,
    pull: bool = False,
    parallel: bool = True,
    compose_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build Docker Compose services.
    
    Args:
        services: Specific services to build (None = all)
        no_cache: Disable build cache
        pull: Pull base images before building
        parallel: Build services in parallel
        compose_file: Path to compose file
    
    Returns:
        Build result with timing and status
    """
```

**Example Usage:**

```python
# Build all services
result = compose_manager.build_services()

if result['success']:
    print(f"🔨 Build completed in {result['build_time']:.1f} seconds")
    print(f"📦 Built services: {', '.join(result['services_built'])}")
    
    # Show build statistics
    if 'build_stats' in result:
        stats = result['build_stats']
        print(f"📊 Build Statistics:")
        print(f"   Total images: {stats['total_images']}")
        print(f"   Cache hits: {stats['cache_hits']}")
        print(f"   Total size: {stats['total_size']}")
else:
    print("❌ Build failed:")
    for error in result['errors']:
        print(f"   • {error}")

# Build with no cache and pull base images
result = compose_manager.build_services(
    services=['web'],
    no_cache=True,
    pull=True,
    parallel=False
)
```

## ContainerManager

The `ContainerManager` class provides comprehensive container lifecycle management.

### Class Definition

```python
from blastdock.docker import ContainerManager

container_manager = ContainerManager()
```

### Methods

#### create_container()

Create a new Docker container with advanced configuration.

```python
def create_container(
    self,
    image: str,
    name: Optional[str] = None,
    command: Optional[List[str]] = None,
    environment: Optional[Dict[str, str]] = None,
    ports: Optional[Dict[str, str]] = None,
    volumes: Optional[Dict[str, str]] = None,
    network: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a Docker container.
    
    Args:
        image: Container image
        name: Container name
        command: Command to run
        environment: Environment variables
        ports: Port mappings
        volumes: Volume mounts
        network: Network to connect to
        labels: Container labels
        **kwargs: Additional Docker options
    
    Returns:
        Creation result with container ID
    """
```

**Example Usage:**

```python
# Create a simple web container
result = container_manager.create_container(
    image="nginx:latest",
    name="my-web-server",
    ports={"80": "8080"},
    environment={
        "NGINX_HOST": "localhost",
        "NGINX_PORT": "80"
    },
    volumes={
        "/host/path": "/container/path"
    },
    labels={
        "app": "web-server",
        "environment": "development"
    }
)

if result['success']:
    print(f"✅ Container created: {result['container_id']}")
    print(f"📛 Name: {result['container_name']}")
else:
    print("❌ Container creation failed:")
    for error in result['errors']:
        print(f"   • {error}")

# Create database container with advanced configuration
result = container_manager.create_container(
    image="postgres:15",
    name="my-database",
    environment={
        "POSTGRES_DB": "myapp",
        "POSTGRES_USER": "myuser",
        "POSTGRES_PASSWORD": "mypassword"
    },
    volumes={
        "postgres_data": "/var/lib/postgresql/data"
    },
    network="my-app-network",
    restart_policy="unless-stopped",
    health_check={
        "test": ["CMD-SHELL", "pg_isready -U myuser"],
        "interval": "30s",
        "timeout": "10s",
        "retries": 3
    }
)
```

#### start_container()

Start a Docker container with health monitoring.

```python
def start_container(
    self,
    container_name: str,
    wait_for_health: bool = True,
    health_timeout: int = 30
) -> Dict[str, Any]:
    """
    Start a Docker container.
    
    Args:
        container_name: Name or ID of container
        wait_for_health: Wait for health check to pass
        health_timeout: Health check timeout
    
    Returns:
        Start result with final state
    """
```

**Example Usage:**

```python
# Start container and wait for health check
result = container_manager.start_container(
    container_name="my-web-server",
    wait_for_health=True,
    health_timeout=60
)

if result['success']:
    print(f"✅ Container started: {result['container_name']}")
    print(f"🏃 Final state: {result['final_state']}")
    print(f"⏱️  Start time: {result['start_time']:.1f} seconds")
    
    if result.get('health_status'):
        print(f"🏥 Health: {result['health_status']}")
else:
    print("❌ Container start failed:")
    for error in result['errors']:
        print(f"   • {error}")

# Start container without waiting for health
result = container_manager.start_container(
    container_name="my-database",
    wait_for_health=False
)
```

#### get_container_info()

Get detailed container information and metrics.

```python
def get_container_info(self, container_name: str) -> Dict[str, Any]:
    """
    Get detailed container information.
    
    Args:
        container_name: Name or ID of container
    
    Returns:
        Detailed container information
    """
```

**Example Usage:**

```python
# Get container information
info = container_manager.get_container_info("my-web-server")

print(f"📦 Container: {info['name']}")
print(f"   ID: {info['id']}")
print(f"   Image: {info['image']}")
print(f"   Status: {info['state']['Status']}")
print(f"   Running: {'✅' if info['state']['Running'] else '❌'}")
print(f"   Created: {info['created']}")
print(f"   Restart Count: {info['restart_count']}")

# Network information
if info.get('network_settings'):
    networks = info['network_settings'].get('Networks', {})
    print(f"   Networks:")
    for network_name, network_info in networks.items():
        print(f"      🌐 {network_name}: {network_info.get('IPAddress', 'N/A')}")

# Port mappings
if info.get('host_config', {}).get('PortBindings'):
    print(f"   Port mappings:")
    for container_port, host_ports in info['host_config']['PortBindings'].items():
        for host_port_info in host_ports:
            host_port = host_port_info['HostPort']
            print(f"      📡 {container_port} -> {host_port}")

# Resource usage (if available)
if info.get('stats'):
    stats = info['stats']
    print(f"   Resource usage:")
    print(f"      💾 Memory: {stats.get('memory_usage', 'N/A')}")
    print(f"      🔄 CPU: {stats.get('cpu_percentage', 'N/A')}")
```

#### execute_command_in_container()

Execute commands inside running containers.

```python
def execute_command_in_container(
    self,
    container_name: str,
    command: List[str],
    user: Optional[str] = None,
    workdir: Optional[str] = None,
    environment: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Execute command in container.
    
    Args:
        container_name: Name or ID of container
        command: Command to execute
        user: User to run command as
        workdir: Working directory
        environment: Additional environment variables
    
    Returns:
        Execution result with stdout/stderr
    """
```

**Example Usage:**

```python
# Execute command in container
result = container_manager.execute_command_in_container(
    container_name="my-web-server",
    command=["nginx", "-t"]  # Test nginx configuration
)

if result['success']:
    print("✅ Command executed successfully")
    print(f"📄 Output: {result['stdout']}")
else:
    print("❌ Command failed")
    print(f"📄 Error: {result['stderr']}")

# Execute interactive command with custom user
result = container_manager.execute_command_in_container(
    container_name="my-database",
    command=["psql", "-U", "myuser", "-c", "SELECT version();"],
    user="postgres",
    workdir="/tmp",
    environment={"PGPASSWORD": "mypassword"}
)

# Execute shell script
result = container_manager.execute_command_in_container(
    container_name="my-app",
    command=["/bin/bash", "-c", "cd /app && npm test"]
)
```

## ImageManager

The `ImageManager` class handles Docker image operations with progress monitoring.

### Class Definition

```python
from blastdock.docker import ImageManager

image_manager = ImageManager()
```

### Methods

#### pull_image()

Pull Docker images with progress monitoring and retry logic.

```python
def pull_image(
    self,
    image_name: str,
    tag: str = 'latest',
    platform: Optional[str] = None
) -> Dict[str, Any]:
    """
    Pull Docker image.
    
    Args:
        image_name: Name of image to pull
        tag: Image tag
        platform: Target platform (linux/amd64, linux/arm64, etc.)
    
    Returns:
        Pull result with timing and size information
    """
```

**Example Usage:**

```python
# Pull latest image
result = image_manager.pull_image("nginx", "latest")

if result['success']:
    print(f"✅ Image pulled: {result['image_name']}")
    print(f"⏱️  Pull time: {result['pull_time']:.1f} seconds")
    print(f"📦 Layers pulled: {result['layers_pulled']}")
    
    if result['size_info']:
        size_mb = result['size_info']['size'] / (1024 * 1024)
        print(f"💾 Image size: {size_mb:.1f} MB")
else:
    print("❌ Image pull failed:")
    for error in result['errors']:
        print(f"   • {error}")

# Pull specific version for specific platform
result = image_manager.pull_image(
    image_name="postgres",
    tag="15-alpine",
    platform="linux/amd64"
)

# Pull multiple images
images_to_pull = [
    ("nginx", "latest"),
    ("postgres", "15"),
    ("redis", "7-alpine")
]

for image_name, tag in images_to_pull:
    print(f"🔄 Pulling {image_name}:{tag}...")
    result = image_manager.pull_image(image_name, tag)
    
    if result['success']:
        print(f"✅ {image_name}:{tag} pulled successfully")
    else:
        print(f"❌ Failed to pull {image_name}:{tag}")
```

#### build_image()

Build Docker images from Dockerfile with advanced options.

```python
def build_image(
    self,
    dockerfile_path: str,
    image_name: str,
    tag: str = 'latest',
    build_args: Optional[Dict[str, str]] = None,
    no_cache: bool = False,
    pull: bool = False,
    context_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build Docker image.
    
    Args:
        dockerfile_path: Path to Dockerfile
        image_name: Name for built image
        tag: Image tag
        build_args: Build arguments
        no_cache: Disable build cache
        pull: Pull base images before building
        context_path: Build context path
    
    Returns:
        Build result with timing and statistics
    """
```

**Example Usage:**

```python
# Build image from Dockerfile
result = image_manager.build_image(
    dockerfile_path="./Dockerfile",
    image_name="my-app",
    tag="v1.0.0",
    build_args={
        "NODE_VERSION": "18",
        "APP_ENV": "production"
    },
    pull=True
)

if result['success']:
    print(f"🔨 Image built: {result['image_name']}")
    print(f"⏱️  Build time: {result['build_time']:.1f} seconds")
    print(f"📋 Build steps: {result['build_steps']}")
    
    if result['size_info']:
        size_mb = result['size_info']['size'] / (1024 * 1024)
        print(f"💾 Image size: {size_mb:.1f} MB")
else:
    print("❌ Image build failed:")
    for error in result['errors']:
        print(f"   • {error}")

# Build with no cache for clean build
result = image_manager.build_image(
    dockerfile_path="./docker/Dockerfile.prod",
    image_name="my-app",
    tag="production",
    context_path=".",
    no_cache=True,
    pull=True
)
```

#### list_images()

List Docker images with filtering and search capabilities.

```python
def list_images(
    self,
    all_images: bool = False,
    filters: Optional[Dict[str, str]] = None
) -> List[Dict[str, Any]]:
    """
    List Docker images.
    
    Args:
        all_images: Include intermediate images
        filters: Image filters (dangling, label, etc.)
    
    Returns:
        List of image information
    """
```

**Example Usage:**

```python
# List all images
images = image_manager.list_images()

print("📋 Docker Images:")
for image in images:
    # Handle multiple tags
    tags = image.get('RepoTags', ['<none>:<none>'])
    for tag in tags:
        size_mb = int(image.get('Size', 0)) / (1024 * 1024)
        created = image.get('CreatedSince', 'Unknown')
        
        print(f"   📦 {tag}")
        print(f"      Size: {size_mb:.1f} MB")
        print(f"      Created: {created}")
        print()

# List only application images
app_images = image_manager.list_images(
    filters={"label": "app=my-application"}
)

# List dangling images (for cleanup)
dangling_images = image_manager.list_images(
    filters={"dangling": "true"}
)

if dangling_images:
    print(f"🗑️  Found {len(dangling_images)} dangling images")
    total_size = sum(img.get('Size', 0) for img in dangling_images)
    total_mb = total_size / (1024 * 1024)
    print(f"💾 Total wasted space: {total_mb:.1f} MB")
```

## Advanced Docker Operations

### Multi-Stage Container Deployment

```python
from blastdock.docker import ComposeManager, ContainerManager, ImageManager

def deploy_full_stack_application():
    """Deploy a complete application stack with proper sequencing."""
    
    compose_manager = ComposeManager(project_name="my-app")
    container_manager = ContainerManager()
    image_manager = ImageManager()
    
    # Step 1: Pull base images
    base_images = ["postgres:15", "redis:7-alpine", "nginx:alpine"]
    
    print("🔄 Pulling base images...")
    for image in base_images:
        result = image_manager.pull_image(image.split(':')[0], image.split(':')[1])
        if result['success']:
            print(f"✅ {image} pulled")
        else:
            print(f"❌ Failed to pull {image}")
            return False
    
    # Step 2: Build application image
    print("🔨 Building application image...")
    build_result = image_manager.build_image(
        dockerfile_path="./Dockerfile",
        image_name="my-app",
        tag="latest",
        build_args={"ENV": "production"}
    )
    
    if not build_result['success']:
        print("❌ Application build failed")
        return False
    
    # Step 3: Start infrastructure services first
    print("🚀 Starting infrastructure services...")
    infra_result = compose_manager.start_services(
        services=['database', 'redis', 'cache']
    )
    
    if not infra_result['success']:
        print("❌ Infrastructure startup failed")
        return False
    
    # Step 4: Wait for database to be ready
    print("⏳ Waiting for database to be ready...")
    import time
    for attempt in range(30):  # 30 attempts, 2 seconds each = 1 minute max
        db_check = container_manager.execute_command_in_container(
            container_name="my-app-database-1",
            command=["pg_isready", "-U", "postgres"]
        )
        
        if db_check['success']:
            print("✅ Database is ready")
            break
        
        time.sleep(2)
    else:
        print("❌ Database startup timeout")
        return False
    
    # Step 5: Run database migrations
    print("🔄 Running database migrations...")
    migration_result = container_manager.execute_command_in_container(
        container_name="my-app-database-1",
        command=["psql", "-U", "postgres", "-f", "/migrations/schema.sql"]
    )
    
    # Step 6: Start application services
    print("🚀 Starting application services...")
    app_result = compose_manager.start_services(
        services=['web', 'api', 'worker']
    )
    
    if not app_result['success']:
        print("❌ Application startup failed")
        return False
    
    print("✅ Full stack deployment completed successfully!")
    return True

# Deploy the application
success = deploy_full_stack_application()
```

### Container Health Monitoring

```python
from blastdock.docker import DockerHealthChecker, ContainerManager

def monitor_application_health():
    """Monitor application health with detailed reporting."""
    
    health_checker = DockerHealthChecker()
    container_manager = ContainerManager()
    
    # Check overall Docker health
    daemon_health = health_checker.check_docker_daemon_health()
    
    print("🏥 Docker Daemon Health:")
    print(f"   Healthy: {'✅' if daemon_health['healthy'] else '❌'}")
    print(f"   Responsive: {'✅' if daemon_health['daemon_responsive'] else '❌'}")
    
    if daemon_health['resource_usage']:
        usage = daemon_health['resource_usage']
        print(f"   Containers: {usage['containers_running']}/{usage['containers_total']}")
        print(f"   Images: {usage['images']}")
        print(f"   Disk Usage: {usage.get('disk_usage', 'N/A')}")
    
    # Check project health
    project_health = health_checker.check_compose_project_health("my-app")
    
    print(f"\n📊 Project Health: {project_health['project_name']}")
    print(f"   Overall Status: {project_health['overall_status']}")
    print(f"   Healthy: {'✅' if project_health['healthy'] else '❌'}")
    
    # Check individual services
    for service_name, service_health in project_health['services'].items():
        status_icon = "✅" if service_health['healthy'] else "❌"
        print(f"   {status_icon} {service_name}: {service_health['status']}")
        
        if not service_health['healthy']:
            for issue in service_health.get('issues', []):
                print(f"      • {issue}")
    
    # Check individual container health
    containers = container_manager.list_containers()
    
    print(f"\n🔍 Individual Container Health:")
    for container in containers:
        container_name = container['name']
        container_health = health_checker.check_container_health(container_name)
        
        status_icon = "✅" if container_health['healthy'] else "❌"
        print(f"   {status_icon} {container_name}: {container_health['status']}")
        
        # Show resource usage if available
        if container_health.get('resource_usage'):
            usage = container_health['resource_usage']
            print(f"      CPU: {usage.get('cpu_percent', 'N/A')}%")
            print(f"      Memory: {usage.get('memory_percent', 'N/A')}%")
        
        # Show health checks
        if container_health.get('health_checks'):
            for check in container_health['health_checks']:
                check_icon = "✅" if check['passing'] else "❌"
                print(f"      {check_icon} {check['name']}: {check['status']}")

# Run health monitoring
monitor_application_health()
```

### Docker Cleanup and Maintenance

```python
from blastdock.docker import ImageManager, VolumeManager, NetworkManager

def cleanup_docker_system():
    """Comprehensive Docker system cleanup."""
    
    image_manager = ImageManager()
    volume_manager = VolumeManager()
    network_manager = NetworkManager()
    
    print("🧹 Starting Docker system cleanup...")
    
    # 1. Remove dangling images
    print("\n🗑️  Removing dangling images...")
    prune_result = image_manager.prune_images(all_images=False)
    
    if prune_result['success']:
        print(f"✅ Removed {prune_result['images_removed']} dangling images")
        print(f"💾 Reclaimed space: {prune_result['space_reclaimed']}")
    else:
        print("❌ Failed to prune images")
    
    # 2. Remove unused volumes
    print("\n🗑️  Removing unused volumes...")
    volume_prune = volume_manager.prune_volumes()
    
    if volume_prune['success']:
        print(f"✅ Removed {volume_prune['volumes_removed']} unused volumes")
        print(f"💾 Reclaimed space: {volume_prune['space_reclaimed']}")
        
        if volume_prune['volumes']:
            for volume in volume_prune['volumes']:
                print(f"   📦 {volume}")
    else:
        print("❌ Failed to prune volumes")
    
    # 3. Remove unused networks
    print("\n🗑️  Removing unused networks...")
    network_prune = network_manager.prune_networks()
    
    if network_prune['success']:
        print(f"✅ Removed {network_prune['networks_removed']} unused networks")
        
        if network_prune['networks']:
            for network in network_prune['networks']:
                print(f"   🌐 {network}")
    else:
        print("❌ Failed to prune networks")
    
    # 4. Show current system usage
    print("\n📊 Current Docker System Usage:")
    
    # List remaining images
    images = image_manager.list_images()
    total_image_size = sum(img.get('Size', 0) for img in images)
    total_image_mb = total_image_size / (1024 * 1024)
    
    print(f"   Images: {len(images)} ({total_image_mb:.1f} MB)")
    
    # List volumes
    volumes = volume_manager.list_volumes()
    print(f"   Volumes: {len(volumes)}")
    
    # List networks
    networks = network_manager.list_networks()
    print(f"   Networks: {len(networks)}")
    
    print("\n✅ Docker cleanup completed!")

# Run cleanup
cleanup_docker_system()
```

### Error Handling Best Practices

```python
from blastdock.docker import DockerError, DockerNotFoundError, DockerNotRunningError
from blastdock.docker import get_docker_client

def robust_docker_operation():
    """Example of robust Docker operations with comprehensive error handling."""
    
    try:
        client = get_docker_client()
        
        # Check Docker availability first
        availability = client.check_docker_availability()
        
        if not availability['docker_available']:
            print("❌ Docker is not installed")
            print("💡 Install Docker: https://docs.docker.com/get-docker/")
            return False
        
        if not availability['docker_running']:
            print("❌ Docker daemon is not running")
            print("💡 Start Docker daemon or Docker Desktop")
            return False
        
        # Perform Docker operations
        result = client.execute_command(['docker', 'ps'])
        print("✅ Docker operation successful")
        return True
        
    except DockerNotFoundError as e:
        print(f"❌ Docker not found: {e}")
        print("💡 Suggestions:")
        for suggestion in e.suggestions:
            print(f"   • {suggestion}")
        return False
        
    except DockerNotRunningError as e:
        print(f"❌ Docker not running: {e}")
        print("💡 Suggestions:")
        for suggestion in e.suggestions:
            print(f"   • {suggestion}")
        return False
        
    except DockerError as e:
        print(f"❌ Docker error: {e}")
        if e.details:
            print(f"📄 Details: {e.details}")
        if e.suggestions:
            print("💡 Suggestions:")
            for suggestion in e.suggestions:
                print(f"   • {suggestion}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

# Run robust operation
success = robust_docker_operation()
```

## Next Steps

- 🔒 **[Security API](../security/)** - Security validation and hardening
- 📊 **[Monitoring API](../monitoring/)** - Advanced monitoring capabilities
- 🎯 **[Performance API](../performance/)** - Performance optimization
- 🏗️ **[Templates API](../templates/)** - Template system and validation