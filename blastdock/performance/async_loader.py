"""
Asynchronous template loading and processing system for BlastDock
Provides high-performance parallel template operations
"""

import asyncio
import aiofiles
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import yaml

from ..utils.logging import get_logger
from .cache import get_cache_manager
from .benchmarks import get_performance_benchmarks

logger = get_logger(__name__)


@dataclass
class LoadTask:
    """Template loading task"""
    template_name: str
    template_path: str
    priority: int = 1
    created_at: float = field(default_factory=time.time)
    dependencies: List[str] = field(default_factory=list)
    callback: Optional[Callable] = None


@dataclass
class LoadResult:
    """Template loading result"""
    template_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    load_time: float = 0.0
    memory_usage: float = 0.0


class AsyncTemplateLoader:
    """High-performance asynchronous template loader"""
    
    def __init__(self, max_workers: int = 8, max_queue_size: int = 1000):
        """Initialize async template loader"""
        self.logger = get_logger(__name__)
        self.cache_manager = get_cache_manager()
        self.benchmarks = get_performance_benchmarks()
        
        # Configuration
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        
        # Task management
        self._task_queue: asyncio.Queue = None
        self._active_tasks: Dict[str, LoadTask] = {}
        self._completed_tasks: Dict[str, LoadResult] = {}
        self._task_lock = threading.RLock()
        
        # Worker management
        self._workers: List[asyncio.Task] = []
        self._worker_stats: Dict[int, Dict[str, Any]] = {}
        self._is_running = False
        
        # Performance tracking
        self.stats = {
            'tasks_queued': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_load_time': 0.0,
            'avg_load_time': 0.0,
            'peak_queue_size': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Dependency tracking
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._dependents: Dict[str, Set[str]] = {}
        
        self.logger.info(f"Async template loader initialized with {max_workers} workers")
    
    async def start(self):
        """Start the async template loader"""
        if self._is_running:
            return
        
        self._is_running = True
        self._task_queue = asyncio.Queue(maxsize=self.max_queue_size)
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
            self._worker_stats[i] = {
                'tasks_processed': 0,
                'errors': 0,
                'total_time': 0.0,
                'avg_time': 0.0
            }
        
        self.logger.info(f"Started {len(self._workers)} async workers")
    
    async def stop(self):
        """Stop the async template loader"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel all workers
        for worker in self._workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        self._worker_stats.clear()
        
        self.logger.info("Async template loader stopped")
    
    async def load_template(self, template_name: str, template_path: str, 
                          priority: int = 1, 
                          dependencies: List[str] = None,
                          callback: Callable = None) -> LoadResult:
        """Load template asynchronously"""
        if not self._is_running:
            await self.start()
        
        dependencies = dependencies or []
        
        # Check cache first
        cached_result = await self._check_cache(template_name, template_path)
        if cached_result:
            self.stats['cache_hits'] += 1
            return cached_result
        
        self.stats['cache_misses'] += 1
        
        # Create load task
        task = LoadTask(
            template_name=template_name,
            template_path=template_path,
            priority=priority,
            dependencies=dependencies,
            callback=callback
        )
        
        # Add to dependency graph
        self._update_dependency_graph(template_name, dependencies)
        
        # Queue task
        await self._queue_task(task)
        
        # Wait for completion
        return await self._wait_for_completion(template_name)
    
    async def load_templates_batch(self, templates: List[Tuple[str, str]], 
                                 priority: int = 1) -> Dict[str, LoadResult]:
        """Load multiple templates in batch"""
        if not self._is_running:
            await self.start()
        
        # Analyze dependencies and optimize loading order
        optimized_order = await self._optimize_loading_order(templates)
        
        # Queue all tasks
        for template_name, template_path in optimized_order:
            task = LoadTask(
                template_name=template_name,
                template_path=template_path,
                priority=priority
            )
            await self._queue_task(task)
        
        # Wait for all completions
        results = {}
        for template_name, _ in templates:
            result = await self._wait_for_completion(template_name)
            results[template_name] = result
        
        return results
    
    async def preload_popular_templates(self, template_registry, top_n: int = 20) -> Dict[str, LoadResult]:
        """Preload most popular templates"""
        # Get popular templates from registry
        popular_templates = []
        
        with template_registry._registry_lock:
            # Sort by popularity score
            sorted_templates = sorted(
                template_registry._registry.values(),
                key=lambda e: e.metrics.popularity_score,
                reverse=True
            )[:top_n]
            
            for entry in sorted_templates:
                if entry.status.value == "active" and not entry.data:
                    popular_templates.append((entry.name, entry.path))
        
        if not popular_templates:
            return {}
        
        self.logger.info(f"Preloading {len(popular_templates)} popular templates")
        
        # Load templates with high priority
        return await self.load_templates_batch(popular_templates, priority=10)
    
    async def _worker(self, worker_id: int):
        """Async worker for processing template loading tasks"""
        stats = self._worker_stats[worker_id]
        
        self.logger.debug(f"Worker {worker_id} started")
        
        try:
            while self._is_running:
                try:
                    # Get task from queue
                    task = await asyncio.wait_for(self._task_queue.get(), timeout=1.0)
                    
                    start_time = time.time()
                    
                    # Process task
                    result = await self._process_task(task, worker_id)
                    
                    # Update stats
                    processing_time = time.time() - start_time
                    stats['tasks_processed'] += 1
                    stats['total_time'] += processing_time
                    stats['avg_time'] = stats['total_time'] / stats['tasks_processed']
                    
                    # Store result
                    with self._task_lock:
                        self._completed_tasks[task.template_name] = result
                        self._active_tasks.pop(task.template_name, None)
                    
                    # Update global stats
                    if result.success:
                        self.stats['tasks_completed'] += 1
                    else:
                        self.stats['tasks_failed'] += 1
                        stats['errors'] += 1
                    
                    self.stats['total_load_time'] += result.load_time
                    if self.stats['tasks_completed'] > 0:
                        self.stats['avg_load_time'] = self.stats['total_load_time'] / self.stats['tasks_completed']
                    
                    # Call callback if provided
                    if task.callback:
                        try:
                            if asyncio.iscoroutinefunction(task.callback):
                                await task.callback(result)
                            else:
                                task.callback(result)
                        except Exception as e:
                            self.logger.warning(f"Task callback error: {e}")
                    
                    # Mark task as done
                    self._task_queue.task_done()
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self.logger.error(f"Worker {worker_id} error: {e}")
                    stats['errors'] += 1
                    
        except asyncio.CancelledError:
            self.logger.debug(f"Worker {worker_id} cancelled")
        except Exception as e:
            self.logger.error(f"Worker {worker_id} fatal error: {e}")
        
        self.logger.debug(f"Worker {worker_id} stopped")
    
    async def _process_task(self, task: LoadTask, worker_id: int) -> LoadResult:
        """Process a template loading task"""
        start_time = time.time()
        
        try:
            # Check if dependencies are loaded
            await self._wait_for_dependencies(task)
            
            # Load template data
            template_data = await self._load_template_file(task.template_path)
            
            if template_data is None:
                return LoadResult(
                    template_name=task.template_name,
                    success=False,
                    error="Failed to parse template file",
                    load_time=time.time() - start_time
                )
            
            # Validate template structure
            validation_result = await self._validate_template_structure(template_data)
            
            if not validation_result['valid']:
                return LoadResult(
                    template_name=task.template_name,
                    success=False,
                    error=f"Template validation failed: {validation_result['error']}",
                    load_time=time.time() - start_time
                )
            
            # Process template (extract metadata, dependencies, etc.)
            processed_data = await self._process_template_data(template_data, task.template_path)
            
            load_time = time.time() - start_time
            
            # Cache the result
            await self._cache_result(task.template_name, processed_data, load_time)
            
            return LoadResult(
                template_name=task.template_name,
                success=True,
                data=processed_data,
                load_time=load_time,
                memory_usage=self._estimate_memory_usage(processed_data)
            )
            
        except Exception as e:
            return LoadResult(
                template_name=task.template_name,
                success=False,
                error=str(e),
                load_time=time.time() - start_time
            )
    
    async def _load_template_file(self, template_path: str) -> Optional[Dict[str, Any]]:
        """Load template file asynchronously"""
        try:
            async with aiofiles.open(template_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return yaml.safe_load(content)
        except Exception as e:
            self.logger.error(f"Failed to load template file {template_path}: {e}")
            return None
    
    async def _validate_template_structure(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate basic template structure"""
        required_sections = ['template_info', 'fields', 'compose']
        
        for section in required_sections:
            if section not in template_data:
                return {
                    'valid': False,
                    'error': f"Missing required section: {section}"
                }
        
        # Validate compose section has services
        compose = template_data.get('compose', {})
        if 'services' not in compose or not compose['services']:
            return {
                'valid': False,
                'error': "No services defined in compose section"
            }
        
        return {'valid': True}
    
    async def _process_template_data(self, template_data: Dict[str, Any], template_path: str) -> Dict[str, Any]:
        """Process template data to extract metadata and enhancements"""
        # Add metadata
        template_data['_metadata'] = {
            'loaded_at': time.time(),
            'source_path': template_path,
            'loader_version': '1.0'
        }
        
        # Extract service information
        compose = template_data.get('compose', {})
        services = compose.get('services', {})
        
        service_info = []
        for service_name, service_config in services.items():
            info = {
                'name': service_name,
                'image': service_config.get('image', ''),
                'ports': service_config.get('ports', []),
                'volumes': service_config.get('volumes', []),
                'environment': service_config.get('environment', [])
            }
            service_info.append(info)
        
        template_data['_services'] = service_info
        
        # Extract dependencies
        dependencies = []
        for service_config in services.values():
            if 'depends_on' in service_config:
                dependencies.extend(service_config['depends_on'])
        
        template_data['_dependencies'] = list(set(dependencies))
        
        return template_data
    
    async def _check_cache(self, template_name: str, template_path: str) -> Optional[LoadResult]:
        """Check if template is cached and still valid"""
        cache_key = f"async_template:{template_name}"
        
        cached_data = self.cache_manager.get(cache_key)
        if not cached_data:
            return None
        
        # Check if file has been modified
        try:
            current_mtime = Path(template_path).stat().st_mtime
            cached_mtime = cached_data.get('_metadata', {}).get('file_mtime', 0)
            
            if current_mtime > cached_mtime:
                # File has been modified, invalidate cache
                self.cache_manager.delete(cache_key)
                return None
            
            return LoadResult(
                template_name=template_name,
                success=True,
                data=cached_data,
                load_time=0.0  # Cache hit
            )
            
        except Exception:
            return None
    
    async def _cache_result(self, template_name: str, template_data: Dict[str, Any], load_time: float):
        """Cache template loading result"""
        cache_key = f"async_template:{template_name}"
        
        # Add cache metadata
        template_data['_metadata']['file_mtime'] = Path(template_data['_metadata']['source_path']).stat().st_mtime
        template_data['_metadata']['load_time'] = load_time
        
        # Cache with 1 hour TTL
        self.cache_manager.set(
            cache_key,
            template_data,
            ttl=3600,
            tags=['async_template', template_name]
        )
    
    async def _queue_task(self, task: LoadTask):
        """Queue a template loading task"""
        with self._task_lock:
            # Check if already queued or active
            if task.template_name in self._active_tasks:
                return
            
            self._active_tasks[task.template_name] = task
        
        # Add to queue
        await self._task_queue.put(task)
        
        self.stats['tasks_queued'] += 1
        current_queue_size = self._task_queue.qsize()
        if current_queue_size > self.stats['peak_queue_size']:
            self.stats['peak_queue_size'] = current_queue_size
    
    async def _wait_for_completion(self, template_name: str, timeout: float = 60.0) -> LoadResult:
        """Wait for template loading to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._task_lock:
                if template_name in self._completed_tasks:
                    result = self._completed_tasks.pop(template_name)
                    return result
            
            await asyncio.sleep(0.1)
        
        # Timeout
        return LoadResult(
            template_name=template_name,
            success=False,
            error="Loading timeout"
        )
    
    async def _wait_for_dependencies(self, task: LoadTask):
        """Wait for task dependencies to be loaded"""
        if not task.dependencies:
            return
        
        for dependency in task.dependencies:
            await self._wait_for_completion(dependency, timeout=30.0)
    
    def _update_dependency_graph(self, template_name: str, dependencies: List[str]):
        """Update dependency tracking graph"""
        self._dependency_graph[template_name] = set(dependencies)
        
        for dependency in dependencies:
            if dependency not in self._dependents:
                self._dependents[dependency] = set()
            self._dependents[dependency].add(template_name)
    
    async def _optimize_loading_order(self, templates: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """Optimize template loading order based on dependencies"""
        # For now, return original order
        # In future, implement topological sort based on dependencies
        return templates
    
    def _estimate_memory_usage(self, template_data: Dict[str, Any]) -> float:
        """Estimate memory usage of template data"""
        try:
            # Rough estimation based on string representation length
            import sys
            return sys.getsizeof(str(template_data)) / 1024 / 1024  # MB
        except Exception:
            return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get loader statistics"""
        worker_stats_summary = {
            'total_tasks': sum(stats['tasks_processed'] for stats in self._worker_stats.values()),
            'total_errors': sum(stats['errors'] for stats in self._worker_stats.values()),
            'avg_processing_time': sum(stats['avg_time'] for stats in self._worker_stats.values()) / len(self._worker_stats) if self._worker_stats else 0
        }
        
        return {
            'loader_stats': self.stats,
            'worker_stats': worker_stats_summary,
            'queue_size': self._task_queue.qsize() if self._task_queue else 0,
            'active_tasks': len(self._active_tasks),
            'completed_tasks': len(self._completed_tasks),
            'is_running': self._is_running,
            'workers': len(self._workers)
        }
    
    async def clear_cache(self):
        """Clear template cache"""
        self.cache_manager.invalidate_by_pattern("async_template:*")
        self.logger.info("Async template cache cleared")


# Global async loader instance
_async_loader = None


async def get_async_loader() -> AsyncTemplateLoader:
    """Get global async template loader instance"""
    global _async_loader
    if _async_loader is None:
        _async_loader = AsyncTemplateLoader()
        await _async_loader.start()
    return _async_loader