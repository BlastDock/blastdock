# Performance API Reference

The Performance API provides comprehensive performance optimization, caching, benchmarking, and resource management capabilities for BlastDock deployments.

## Classes Overview

- **[CacheManager](#cachemanager)** - Multi-level caching system for templates and data
- **[PerformanceOptimizer](#performanceoptimizer)** - Automated performance optimization
- **[BenchmarkRunner](#benchmarkrunner)** - Performance benchmarking and testing
- **[ResourceMonitor](#resourcemonitor)** - Resource usage monitoring and optimization
- **[ParallelProcessor](#parallelprocessor)** - Parallel operation execution

## CacheManager

The `CacheManager` class provides a sophisticated multi-level caching system for improved performance.

### Class Definition

```python
from blastdock.performance import CacheManager

cache_manager = CacheManager(
    strategy="hybrid",  # memory, disk, hybrid
    memory_limit="512MB",
    disk_limit="2GB",
    ttl_default=3600  # 1 hour
)
```

### Methods

#### set_cache()

Store data in cache with configurable TTL and levels.

```python
def set_cache(
    self,
    key: str,
    value: Any,
    ttl: Optional[int] = None,
    cache_level: str = "auto",
    tags: Optional[List[str]] = None
) -> bool:
    """
    Store data in cache.
    
    Args:
        key: Cache key
        value: Data to cache
        ttl: Time to live in seconds
        cache_level: Cache level (memory, disk, auto)
        tags: Tags for cache invalidation
    
    Returns:
        True if cached successfully
    """
```

**Example Usage:**

```python
from blastdock.performance import CacheManager

cache_manager = CacheManager()

# Cache template data
template_data = {
    "name": "wordpress",
    "version": "6.3",
    "services": ["web", "database"],
    "compose_file": "docker-compose.yml content..."
}

success = cache_manager.set_cache(
    key="template:wordpress:6.3",
    value=template_data,
    ttl=7200,  # 2 hours
    cache_level="memory",
    tags=["templates", "wordpress"]
)

if success:
    print("✅ Template cached successfully")

# Cache deployment configuration
deployment_config = {
    "project_name": "my-blog",
    "domain": "blog.example.com",
    "variables": {"mysql_password": "hashed_password"},
    "traefik_config": "traefik configuration..."
}

cache_manager.set_cache(
    key="deployment:my-blog:config",
    value=deployment_config,
    ttl=1800,  # 30 minutes
    cache_level="disk",
    tags=["deployments", "my-blog"]
)

# Cache large data automatically
large_data = {"docker_images": [...], "size": "150MB"}
cache_manager.set_cache(
    key="docker:images:latest",
    value=large_data,
    cache_level="auto"  # Automatically choose best level
)
```

#### get_cache()

Retrieve data from cache with fallback options.

```python
def get_cache(
    self,
    key: str,
    default: Any = None,
    refresh_ttl: bool = False
) -> Any:
    """
    Retrieve data from cache.
    
    Args:
        key: Cache key
        default: Default value if key not found
        refresh_ttl: Reset TTL when accessing
    
    Returns:
        Cached data or default value
    """
```

**Example Usage:**

```python
# Get cached template
template = cache_manager.get_cache("template:wordpress:6.3")

if template:
    print(f"📦 Template loaded from cache: {template['name']}")
    print(f"   Version: {template['version']}")
    print(f"   Services: {', '.join(template['services'])}")
else:
    print("❌ Template not in cache, loading from disk...")
    # Load template and cache it
    template = load_template_from_disk("wordpress")
    cache_manager.set_cache("template:wordpress:6.3", template)

# Get with default value
deployment = cache_manager.get_cache(
    key="deployment:my-blog:config",
    default={"status": "not_cached"}
)

# Refresh TTL on access (useful for frequently accessed data)
frequently_used_data = cache_manager.get_cache(
    key="app:session:user123",
    refresh_ttl=True
)
```

#### invalidate_cache()

Invalidate cache entries by key patterns or tags.

```python
def invalidate_cache(
    self,
    pattern: Optional[str] = None,
    tags: Optional[List[str]] = None,
    keys: Optional[List[str]] = None
) -> int:
    """
    Invalidate cache entries.
    
    Args:
        pattern: Key pattern to match (supports wildcards)
        tags: Tags to invalidate
        keys: Specific keys to invalidate
    
    Returns:
        Number of entries invalidated
    """
```

**Example Usage:**

```python
# Invalidate specific deployment
count = cache_manager.invalidate_cache(keys=["deployment:my-blog:config"])
print(f"🗑️ Invalidated {count} cache entries")

# Invalidate all WordPress templates
count = cache_manager.invalidate_cache(pattern="template:wordpress:*")
print(f"🗑️ Invalidated {count} WordPress template cache entries")

# Invalidate by tags
count = cache_manager.invalidate_cache(tags=["templates"])
print(f"🗑️ Invalidated {count} template cache entries")

# Clear all deployment caches
count = cache_manager.invalidate_cache(pattern="deployment:*")
print(f"🗑️ Cleared {count} deployment cache entries")

# Complete cache clear (use with caution)
count = cache_manager.clear_all_cache()
print(f"🗑️ Cleared all cache ({count} entries)")
```

#### get_cache_stats()

Get comprehensive cache statistics and performance metrics.

```python
def get_cache_stats(self) -> Dict[str, Any]:
    """
    Get cache statistics and performance metrics.
    
    Returns:
        Cache statistics including hit rates, memory usage, etc.
    """
```

**Example Usage:**

```python
# Get cache statistics
stats = cache_manager.get_cache_stats()

print("📊 Cache Statistics:")
print(f"   Hit Rate: {stats['hit_rate']:.1f}%")
print(f"   Miss Rate: {stats['miss_rate']:.1f}%")
print(f"   Total Requests: {stats['total_requests']:,}")
print(f"   Cache Hits: {stats['cache_hits']:,}")
print(f"   Cache Misses: {stats['cache_misses']:,}")

# Memory cache stats
memory_stats = stats['memory_cache']
print(f"\n💾 Memory Cache:")
print(f"   Entries: {memory_stats['entries']:,}")
print(f"   Memory Used: {memory_stats['memory_used_mb']:.1f} MB")
print(f"   Memory Limit: {memory_stats['memory_limit_mb']:.1f} MB")
print(f"   Usage: {memory_stats['usage_percentage']:.1f}%")

# Disk cache stats  
disk_stats = stats['disk_cache']
print(f"\n💽 Disk Cache:")
print(f"   Entries: {disk_stats['entries']:,}")
print(f"   Disk Used: {disk_stats['disk_used_mb']:.1f} MB")
print(f"   Disk Limit: {disk_stats['disk_limit_mb']:.1f} MB")
print(f"   Usage: {disk_stats['usage_percentage']:.1f}%")

# Performance metrics
perf_stats = stats['performance']
print(f"\n⚡ Performance:")
print(f"   Avg Get Time: {perf_stats['avg_get_time_ms']:.2f}ms")
print(f"   Avg Set Time: {perf_stats['avg_set_time_ms']:.2f}ms")
print(f"   Evictions: {perf_stats['evictions']:,}")

# Most accessed keys
if 'top_keys' in stats:
    print(f"\n🔥 Most Accessed Keys:")
    for key, access_count in stats['top_keys'][:5]:
        print(f"   • {key}: {access_count:,} accesses")
```

## PerformanceOptimizer

The `PerformanceOptimizer` class provides automated performance optimization capabilities.

### Class Definition

```python
from blastdock.performance import PerformanceOptimizer

optimizer = PerformanceOptimizer(
    auto_optimization=True,
    optimization_level="balanced",  # conservative, balanced, aggressive
    monitoring_enabled=True
)
```

### Methods

#### analyze_performance()

Analyze current performance and identify optimization opportunities.

```python
def analyze_performance(
    self,
    project_name: str,
    analysis_depth: str = "standard"
) -> Dict[str, Any]:
    """
    Analyze project performance.
    
    Args:
        project_name: Name of project to analyze
        analysis_depth: Analysis depth (quick, standard, deep)
    
    Returns:
        Performance analysis results with recommendations
    """
```

**Example Usage:**

```python
from blastdock.performance import PerformanceOptimizer

optimizer = PerformanceOptimizer()

# Analyze project performance
analysis = optimizer.analyze_performance(
    project_name="production-ecommerce",
    analysis_depth="deep"
)

print(f"⚡ Performance Analysis: {analysis['project_name']}")
print(f"   Overall Score: {analysis['performance_score']}/100")
print(f"   Analysis Time: {analysis['analysis_duration']:.1f}s")

# Performance categories
categories = analysis['categories']
for category, data in categories.items():
    score = data['score']
    status_icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
    print(f"   {status_icon} {category.title()}: {score}/100")

# Optimization opportunities
opportunities = analysis['optimization_opportunities']
print(f"\n🚀 Optimization Opportunities ({len(opportunities)}):")

for opp in opportunities[:5]:  # Show top 5
    impact_icon = {"high": "🔥", "medium": "⚡", "low": "💡"}
    icon = impact_icon.get(opp['impact'], "•")
    
    print(f"   {icon} {opp['title']}")
    print(f"      Impact: {opp['impact']} ({opp['impact_score']}/10)")
    print(f"      Effort: {opp['effort']} ({opp['effort_score']}/10)")
    print(f"      Description: {opp['description']}")

# Performance bottlenecks
bottlenecks = analysis['bottlenecks']
if bottlenecks:
    print(f"\n🚨 Performance Bottlenecks:")
    for bottleneck in bottlenecks:
        print(f"   • {bottleneck['component']}: {bottleneck['issue']}")
        print(f"     Impact: {bottleneck['performance_impact']}")
        print(f"     Recommendation: {bottleneck['recommendation']}")

# Resource analysis
resources = analysis['resource_analysis']
print(f"\n📊 Resource Analysis:")
print(f"   CPU Utilization: {resources['cpu_efficiency']:.1f}%")
print(f"   Memory Efficiency: {resources['memory_efficiency']:.1f}%")
print(f"   I/O Performance: {resources['io_performance']:.1f}%")
print(f"   Network Efficiency: {resources['network_efficiency']:.1f}%")
```

#### apply_optimizations()

Apply automated performance optimizations.

```python
def apply_optimizations(
    self,
    project_name: str,
    optimizations: Optional[List[str]] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Apply performance optimizations.
    
    Args:
        project_name: Name of project to optimize
        optimizations: Specific optimizations to apply
        dry_run: Show what would be optimized without applying
    
    Returns:
        Optimization results
    """
```

**Example Usage:**

```python
# Get available optimizations first
available_opts = optimizer.get_available_optimizations("production-ecommerce")

print("🔧 Available Optimizations:")
for opt_id, opt_info in available_opts.items():
    print(f"   • {opt_id}: {opt_info['description']}")
    print(f"     Impact: {opt_info['expected_impact']}")
    print(f"     Risk: {opt_info['risk_level']}")

# Apply optimizations (dry run first)
dry_run_result = optimizer.apply_optimizations(
    project_name="production-ecommerce",
    optimizations=["cache_optimization", "image_optimization", "compose_optimization"],
    dry_run=True
)

print(f"\n🔍 Optimization Plan (Dry Run):")
print(f"   Optimizations: {len(dry_run_result['planned_optimizations'])}")
print(f"   Expected Performance Gain: +{dry_run_result['expected_performance_gain']:.1f}%")
print(f"   Estimated Time: {dry_run_result['estimated_duration']:.1f}s")

for optimization in dry_run_result['planned_optimizations']:
    print(f"\n   📋 {optimization['name']}:")
    print(f"      Changes: {len(optimization['changes'])} modifications")
    print(f"      Expected Impact: +{optimization['expected_impact']:.1f}%")
    if optimization.get('requires_restart'):
        print("      ⚠️  Requires service restart")

# Apply optimizations after review
if input("Apply optimizations? (y/N): ").lower() == 'y':
    result = optimizer.apply_optimizations(
        project_name="production-ecommerce",
        optimizations=["cache_optimization", "image_optimization"],
        dry_run=False
    )
    
    if result['success']:
        print(f"✅ Optimizations applied successfully")
        print(f"   Applied: {len(result['applied_optimizations'])}")
        print(f"   Performance Improvement: +{result['performance_improvement']:.1f}%")
        print(f"   Duration: {result['optimization_duration']:.1f}s")
        
        # Show before/after comparison
        comparison = result['performance_comparison']
        print(f"\n📊 Before/After Comparison:")
        print(f"   Response Time: {comparison['response_time']['before']:.0f}ms → {comparison['response_time']['after']:.0f}ms")
        print(f"   Throughput: {comparison['throughput']['before']:.1f} → {comparison['throughput']['after']:.1f} req/s")
        print(f"   Resource Usage: {comparison['resource_usage']['before']:.1f}% → {comparison['resource_usage']['after']:.1f}%")
    else:
        print(f"❌ Optimization failed: {result['error']}")
```

#### create_performance_profile()

Create custom performance profile for specific use cases.

```python
def create_performance_profile(
    self,
    profile_name: str,
    optimization_rules: Dict[str, Any],
    target_metrics: Dict[str, float]
) -> str:
    """
    Create custom performance profile.
    
    Args:
        profile_name: Name of the performance profile
        optimization_rules: Rules for automatic optimization
        target_metrics: Target performance metrics
    
    Returns:
        Profile ID
    """
```

**Example Usage:**

```python
# Create high-performance profile for production
production_profile = optimizer.create_performance_profile(
    profile_name="production_high_performance",
    optimization_rules={
        "auto_scaling": {
            "enabled": True,
            "cpu_threshold": 70,
            "memory_threshold": 80,
            "scale_factor": 1.5,
            "cooldown_period": 300  # 5 minutes
        },
        "caching": {
            "strategy": "aggressive",
            "cache_templates": True,
            "cache_static_assets": True,
            "cache_api_responses": True,
            "ttl_multiplier": 2.0
        },
        "resource_optimization": {
            "compress_images": True,
            "minify_assets": True,
            "optimize_queries": True,
            "connection_pooling": True
        },
        "monitoring": {
            "continuous_profiling": True,
            "performance_alerts": True,
            "auto_optimization": True
        }
    },
    target_metrics={
        "response_time": 200,      # Target 200ms
        "throughput": 1000,        # Target 1000 req/s
        "cpu_usage": 60,           # Target 60% CPU
        "memory_usage": 70,        # Target 70% memory
        "error_rate": 0.1          # Target 0.1% error rate
    }
)

# Create development profile (less aggressive)
dev_profile = optimizer.create_performance_profile(
    profile_name="development_balanced",
    optimization_rules={
        "auto_scaling": {"enabled": False},
        "caching": {
            "strategy": "moderate",
            "cache_templates": True,
            "cache_static_assets": False,
            "ttl_multiplier": 1.0
        },
        "resource_optimization": {
            "compress_images": False,
            "minify_assets": False,
            "optimize_queries": True
        },
        "monitoring": {
            "continuous_profiling": False,
            "performance_alerts": True
        }
    },
    target_metrics={
        "response_time": 1000,     # More relaxed targets
        "cpu_usage": 80,
        "memory_usage": 85
    }
)

print(f"✅ Performance profiles created:")
print(f"   • Production: {production_profile}")
print(f"   • Development: {dev_profile}")

# Apply profile to project
optimizer.apply_performance_profile(
    project_name="production-ecommerce",
    profile_id=production_profile
)
```

## BenchmarkRunner

The `BenchmarkRunner` class provides comprehensive performance benchmarking and testing capabilities.

### Class Definition

```python
from blastdock.performance import BenchmarkRunner

benchmark_runner = BenchmarkRunner(
    test_duration=300,  # 5 minutes
    concurrent_users=100,
    ramp_up_time=30    # 30 seconds
)
```

### Methods

#### run_load_test()

Run comprehensive load testing on deployments.

```python
def run_load_test(
    self,
    project_name: str,
    test_scenarios: List[Dict[str, Any]],
    duration: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run load test on project.
    
    Args:
        project_name: Name of project to test
        test_scenarios: Test scenarios to execute
        duration: Test duration in seconds
    
    Returns:
        Load test results and performance metrics
    """
```

**Example Usage:**

```python
from blastdock.performance import BenchmarkRunner

benchmark_runner = BenchmarkRunner()

# Define test scenarios
test_scenarios = [
    {
        "name": "homepage_load",
        "method": "GET",
        "path": "/",
        "weight": 40,  # 40% of traffic
        "headers": {"User-Agent": "LoadTest/1.0"}
    },
    {
        "name": "product_browse",
        "method": "GET", 
        "path": "/products",
        "weight": 30,
        "query_params": {"page": "random(1,10)"}
    },
    {
        "name": "search",
        "method": "POST",
        "path": "/search",
        "weight": 20,
        "data": {"q": "random_search_term"}
    },
    {
        "name": "api_calls",
        "method": "GET",
        "path": "/api/v1/products/random(1,1000)",
        "weight": 10,
        "headers": {"Authorization": "Bearer test_token"}
    }
]

# Run load test
print("🚀 Starting load test...")
results = benchmark_runner.run_load_test(
    project_name="production-ecommerce",
    test_scenarios=test_scenarios,
    duration=300  # 5 minutes
)

print(f"📊 Load Test Results: {results['project_name']}")
print(f"   Test Duration: {results['actual_duration']:.1f}s")
print(f"   Total Requests: {results['total_requests']:,}")
print(f"   Successful Requests: {results['successful_requests']:,}")
print(f"   Failed Requests: {results['failed_requests']:,}")
print(f"   Success Rate: {results['success_rate']:.1f}%")

# Performance metrics
metrics = results['performance_metrics']
print(f"\n⚡ Performance Metrics:")
print(f"   Avg Response Time: {metrics['avg_response_time']:.0f}ms")
print(f"   Min Response Time: {metrics['min_response_time']:.0f}ms")
print(f"   Max Response Time: {metrics['max_response_time']:.0f}ms")
print(f"   95th Percentile: {metrics['p95_response_time']:.0f}ms")
print(f"   99th Percentile: {metrics['p99_response_time']:.0f}ms")
print(f"   Requests/sec: {metrics['requests_per_second']:.1f}")
print(f"   Throughput: {metrics['throughput_mbps']:.1f} Mbps")

# Scenario breakdown
print(f"\n📋 Scenario Results:")
for scenario_name, scenario_results in results['scenarios'].items():
    print(f"   📄 {scenario_name}:")
    print(f"      Requests: {scenario_results['requests']:,}")
    print(f"      Avg Response: {scenario_results['avg_response_time']:.0f}ms")
    print(f"      Success Rate: {scenario_results['success_rate']:.1f}%")

# Resource utilization during test
if 'resource_usage' in results:
    usage = results['resource_usage']
    print(f"\n📊 Resource Usage During Test:")
    print(f"   Peak CPU: {usage['peak_cpu']:.1f}%")
    print(f"   Peak Memory: {usage['peak_memory']:.1f}%")
    print(f"   Avg CPU: {usage['avg_cpu']:.1f}%")
    print(f"   Avg Memory: {usage['avg_memory']:.1f}%")

# Performance recommendations
if results['recommendations']:
    print(f"\n💡 Performance Recommendations:")
    for rec in results['recommendations']:
        print(f"   • {rec}")
```

#### run_stress_test()

Run stress testing to find breaking points.

```python
def run_stress_test(
    self,
    project_name: str,
    start_users: int = 10,
    max_users: int = 1000,
    step_duration: int = 60
) -> Dict[str, Any]:
    """
    Run stress test to find system limits.
    
    Args:
        project_name: Name of project to test
        start_users: Starting number of concurrent users
        max_users: Maximum number of concurrent users
        step_duration: Duration of each step in seconds
    
    Returns:
        Stress test results with breaking point analysis
    """
```

**Example Usage:**

```python
# Run stress test to find breaking point
print("💥 Starting stress test...")
stress_results = benchmark_runner.run_stress_test(
    project_name="production-ecommerce",
    start_users=50,
    max_users=2000,
    step_duration=120  # 2 minutes per step
)

print(f"💥 Stress Test Results: {stress_results['project_name']}")
print(f"   Test Duration: {stress_results['total_duration']:.1f}s")
print(f"   Peak Users: {stress_results['peak_users']:,}")
print(f"   Breaking Point: {stress_results['breaking_point']:,} users")

# Performance degradation analysis
degradation = stress_results['performance_degradation']
print(f"\n📉 Performance Degradation:")
print(f"   Response Time Increase: +{degradation['response_time_increase']:.1f}%")
print(f"   Throughput Decrease: -{degradation['throughput_decrease']:.1f}%")
print(f"   Error Rate at Peak: {degradation['error_rate_at_peak']:.1f}%")

# Breaking point analysis
breaking_point = stress_results['breaking_point_analysis']
print(f"\n🚨 Breaking Point Analysis:")
print(f"   First Failure at: {breaking_point['first_failure_users']} users")
print(f"   System Overload at: {breaking_point['overload_users']} users")
print(f"   Primary Bottleneck: {breaking_point['primary_bottleneck']}")
print(f"   Resource Constraint: {breaking_point['resource_constraint']}")

# Step-by-step results
print(f"\n📊 Step Results:")
for step in stress_results['steps']:
    print(f"   👥 {step['users']} users:")
    print(f"      Avg Response: {step['avg_response_time']:.0f}ms")
    print(f"      Success Rate: {step['success_rate']:.1f}%")
    print(f"      Requests/sec: {step['requests_per_second']:.1f}")
    
    if step['errors']:
        print(f"      ❌ Errors: {len(step['errors'])}")
```

#### benchmark_comparison()

Compare performance between different configurations or versions.

```python
def benchmark_comparison(
    self,
    configurations: List[Dict[str, Any]],
    test_scenarios: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compare performance between configurations.
    
    Args:
        configurations: List of configurations to compare
        test_scenarios: Test scenarios to run
    
    Returns:
        Comparison results with performance differences
    """
```

**Example Usage:**

```python
# Compare different configurations
configurations = [
    {
        "name": "current_config",
        "project_name": "ecommerce-v1",
        "description": "Current production configuration"
    },
    {
        "name": "optimized_config", 
        "project_name": "ecommerce-v2-optimized",
        "description": "Optimized configuration with caching"
    },
    {
        "name": "scaled_config",
        "project_name": "ecommerce-v2-scaled",
        "description": "Horizontally scaled configuration"
    }
]

# Run comparison benchmark
comparison = benchmark_runner.benchmark_comparison(
    configurations=configurations,
    test_scenarios=test_scenarios
)

print(f"📊 Configuration Comparison Results:")
print(f"   Configurations Tested: {len(comparison['configurations'])}")
print(f"   Test Duration per Config: {comparison['test_duration']:.1f}s")

# Performance comparison table
print(f"\n📈 Performance Comparison:")
print(f"{'Configuration':<20} {'Req/sec':<10} {'Avg Response':<15} {'Success Rate':<12} {'Score'}")
print("=" * 75)

for config_name, results in comparison['results'].items():
    config_desc = next(c['name'] for c in configurations if c['name'] == config_name)
    req_per_sec = results['requests_per_second']
    avg_response = results['avg_response_time']
    success_rate = results['success_rate']
    score = results['performance_score']
    
    print(f"{config_desc:<20} {req_per_sec:<10.1f} {avg_response:<15.0f}ms {success_rate:<12.1f}% {score:.1f}")

# Winner and recommendations
winner = comparison['best_configuration']
print(f"\n🏆 Best Configuration: {winner['name']}")
print(f"   Performance Improvement: +{winner['improvement_percentage']:.1f}%")
print(f"   Key Advantages:")
for advantage in winner['advantages']:
    print(f"     • {advantage}")

# Detailed analysis
if comparison['detailed_analysis']:
    analysis = comparison['detailed_analysis']
    print(f"\n🔍 Detailed Analysis:")
    print(f"   Biggest Performance Gain: {analysis['biggest_gain']}")
    print(f"   Most Stable Configuration: {analysis['most_stable']}")
    print(f"   Best Resource Efficiency: {analysis['most_efficient']}")
```

## Advanced Performance Examples

### Automated Performance Pipeline

```python
from blastdock.performance import PerformanceOptimizer, BenchmarkRunner, CacheManager
import schedule
import time

def automated_performance_pipeline():
    """Automated performance optimization and monitoring pipeline."""
    
    optimizer = PerformanceOptimizer()
    benchmark_runner = BenchmarkRunner()
    cache_manager = CacheManager()
    
    projects = ["production-web", "production-api"]
    
    def daily_performance_check():
        """Daily performance analysis and optimization."""
        print("🔄 Starting daily performance check...")
        
        for project in projects:
            print(f"\n📊 Analyzing {project}...")
            
            # 1. Performance analysis
            analysis = optimizer.analyze_performance(project, "standard")
            current_score = analysis['performance_score']
            
            print(f"   Current Score: {current_score}/100")
            
            # 2. Apply optimizations if score is low
            if current_score < 80:
                print("   🚀 Applying optimizations...")
                optimization_result = optimizer.apply_optimizations(
                    project_name=project,
                    optimizations=["cache_optimization", "resource_optimization"]
                )
                
                if optimization_result['success']:
                    improvement = optimization_result['performance_improvement']
                    print(f"   ✅ Optimized: +{improvement:.1f}% improvement")
                else:
                    print(f"   ❌ Optimization failed: {optimization_result['error']}")
            
            # 3. Cache maintenance
            cache_stats = cache_manager.get_cache_stats()
            if cache_stats['hit_rate'] < 70:  # If hit rate is low
                print("   🧹 Performing cache maintenance...")
                cache_manager.optimize_cache()
            
            # 4. Quick performance test
            test_scenarios = [
                {"name": "health_check", "method": "GET", "path": "/health", "weight": 100}
            ]
            
            test_result = benchmark_runner.run_load_test(
                project_name=project,
                test_scenarios=test_scenarios,
                duration=60  # 1 minute test
            )
            
            avg_response = test_result['performance_metrics']['avg_response_time']
            success_rate = test_result['success_rate']
            
            print(f"   📈 Quick Test: {avg_response:.0f}ms avg, {success_rate:.1f}% success")
            
            # 5. Alert if performance is poor
            if avg_response > 1000 or success_rate < 95:
                send_performance_alert(project, avg_response, success_rate)
    
    def weekly_benchmark():
        """Weekly comprehensive benchmark."""
        print("📊 Starting weekly benchmark...")
        
        for project in projects:
            stress_result = benchmark_runner.run_stress_test(
                project_name=project,
                start_users=10,
                max_users=500,
                step_duration=60
            )
            
            breaking_point = stress_result['breaking_point']
            print(f"   {project} breaking point: {breaking_point} users")
            
            # Store benchmark history
            store_benchmark_history(project, stress_result)
    
    def send_performance_alert(project, response_time, success_rate):
        """Send performance alert."""
        print(f"🚨 Performance Alert: {project}")
        print(f"   Response Time: {response_time:.0f}ms")
        print(f"   Success Rate: {success_rate:.1f}%")
        # Implement actual alerting (Slack, email, etc.)
    
    def store_benchmark_history(project, results):
        """Store benchmark results for trend analysis."""
        # Implement benchmark history storage
        pass
    
    # Schedule tasks
    schedule.every().day.at("02:00").do(daily_performance_check)
    schedule.every().week.at("03:00").do(weekly_benchmark)
    
    print("📅 Performance pipeline scheduled:")
    print("   • Daily checks: 02:00")
    print("   • Weekly benchmarks: 03:00 (weekly)")
    
    # Run scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Start automated pipeline
automated_performance_pipeline()
```

### Performance Monitoring Dashboard

```python
from blastdock.performance import CacheManager, PerformanceOptimizer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
import time

def performance_dashboard():
    """Real-time performance monitoring dashboard."""
    
    console = Console()
    cache_manager = CacheManager()
    optimizer = PerformanceOptimizer()
    
    def create_dashboard():
        # Cache statistics
        cache_stats = cache_manager.get_cache_stats()
        
        cache_table = Table(title="🗄️ Cache Performance")
        cache_table.add_column("Metric", style="cyan")
        cache_table.add_column("Value", style="green")
        
        cache_table.add_row("Hit Rate", f"{cache_stats['hit_rate']:.1f}%")
        cache_table.add_row("Miss Rate", f"{cache_stats['miss_rate']:.1f}%")
        cache_table.add_row("Memory Usage", f"{cache_stats['memory_cache']['usage_percentage']:.1f}%")
        cache_table.add_row("Disk Usage", f"{cache_stats['disk_cache']['usage_percentage']:.1f}%")
        cache_table.add_row("Total Entries", f"{cache_stats['memory_cache']['entries'] + cache_stats['disk_cache']['entries']:,}")
        
        # Performance scores
        projects = ["production-web", "production-api"]
        perf_table = Table(title="⚡ Performance Scores")
        perf_table.add_column("Project", style="cyan")
        perf_table.add_column("Score", style="green")
        perf_table.add_column("Status", style="yellow")
        perf_table.add_column("Last Check", style="blue")
        
        for project in projects:
            try:
                analysis = optimizer.analyze_performance(project, "quick")
                score = analysis['performance_score']
                
                if score >= 80:
                    status = "🟢 Excellent"
                elif score >= 60:
                    status = "🟡 Good"
                else:
                    status = "🔴 Poor"
                
                last_check = time.strftime("%H:%M:%S")
                perf_table.add_row(project, f"{score}/100", status, last_check)
                
            except Exception as e:
                perf_table.add_row(project, "N/A", "❌ Error", time.strftime("%H:%M:%S"))
        
        # Layout
        layout = f"""
{cache_table}

{perf_table}

⏰ Last Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Press Ctrl+C to exit
        """
        
        return Panel(layout, title="🚀 BlastDock Performance Dashboard", border_style="blue")
    
    # Live dashboard
    with Live(create_dashboard(), refresh_per_second=0.5) as live:
        try:
            while True:
                time.sleep(5)
                live.update(create_dashboard())
        except KeyboardInterrupt:
            console.print("\n👋 Performance dashboard stopped")

# Run performance dashboard
performance_dashboard()
```

## Next Steps

- 🏗️ **[Templates API](../templates/)** - Template system and validation
- 💻 **[CLI API](../cli/)** - Command-line interface components
- 🔧 **[Utils API](../utils/)** - Utility functions and helpers
- 📊 **[Monitoring API](../monitoring/)** - Return to monitoring capabilities