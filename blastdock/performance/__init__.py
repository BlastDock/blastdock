"""Performance optimization modules"""

from .cache_manager import get_cache_manager
from .template_cache import get_template_cache
from .deployment_optimizer import get_deployment_optimizer
from .memory_optimizer import get_memory_optimizer
from .parallel_processor import get_parallel_processor
from .benchmarks import get_performance_benchmarks

__all__ = [
    'get_cache_manager',
    'get_template_cache', 
    'get_deployment_optimizer',
    'get_memory_optimizer',
    'get_parallel_processor',
    'get_performance_benchmarks'
]
