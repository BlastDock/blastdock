"""
High-performance caching system for BlastDock
"""

import os
import json
import pickle
import time
import hashlib
import threading
from typing import Any, Dict, Optional, Union, Callable, TypeVar, Generic
from dataclasses import dataclass, asdict
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from ..utils.logging import get_logger
from ..utils.filesystem import paths

logger = get_logger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    value: Any
    timestamp: float
    ttl: Optional[float] = None
    access_count: int = 0
    last_access: float = 0
    size_bytes: int = 0
    tags: list = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_access == 0:
            self.last_access = self.timestamp
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl
    
    def touch(self):
        """Update access statistics"""
        self.access_count += 1
        self.last_access = time.time()


class CacheManager:
    """High-performance multi-level cache manager"""
    
    def __init__(self, max_memory_size: int = 100 * 1024 * 1024,  # 100MB
                 max_disk_size: int = 1024 * 1024 * 1024,      # 1GB
                 default_ttl: Optional[float] = 3600,           # 1 hour
                 cleanup_interval: float = 300):                # 5 minutes
        """Initialize cache manager"""
        self.logger = get_logger(__name__)
        
        # Memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._memory_lock = threading.RLock()
        self._memory_size = 0
        self.max_memory_size = max_memory_size
        
        # Disk cache
        self.cache_dir = os.path.join(paths.data_dir, 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        self.max_disk_size = max_disk_size
        
        # Configuration
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()
        
        # Performance stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'memory_hits': 0,
            'disk_hits': 0,
            'evictions': 0,
            'size_evictions': 0
        }
        
        # Thread pool for async operations
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix='cache')
        
        self.logger.debug(f"Cache manager initialized: memory={max_memory_size//1024//1024}MB, disk={max_disk_size//1024//1024}MB")
    
    def get(self, key: str, default: T = None) -> Union[T, None]:
        """Get value from cache"""
        # Try memory cache first
        with self._memory_lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if not entry.is_expired():
                    entry.touch()
                    self.stats['hits'] += 1
                    self.stats['memory_hits'] += 1
                    self.logger.debug(f"Cache hit (memory): {key}")
                    return entry.value
                else:
                    # Expired, remove from memory
                    self._remove_from_memory(key)
        
        # Try disk cache
        disk_value = self._get_from_disk(key)
        if disk_value is not None:
            # Move back to memory cache if there's space
            self._set_in_memory(key, disk_value, self.default_ttl)
            self.stats['hits'] += 1
            self.stats['disk_hits'] += 1
            self.logger.debug(f"Cache hit (disk): {key}")
            return disk_value
        
        # Cache miss
        self.stats['misses'] += 1
        self.logger.debug(f"Cache miss: {key}")
        return default
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, 
            tags: Optional[list] = None, persist_to_disk: bool = True):
        """Set value in cache"""
        if ttl is None:
            ttl = self.default_ttl
        
        # Set in memory cache
        self._set_in_memory(key, value, ttl, tags)
        
        # Optionally persist to disk
        if persist_to_disk:
            self._executor.submit(self._set_on_disk, key, value, ttl, tags)
        
        # Periodic cleanup
        if time.time() - self._last_cleanup > self.cleanup_interval:
            self._executor.submit(self._cleanup)
    
    def delete(self, key: str):
        """Delete key from cache"""
        # Remove from memory
        with self._memory_lock:
            if key in self._memory_cache:
                self._remove_from_memory(key)
        
        # Remove from disk
        self._delete_from_disk(key)
    
    def clear(self, tags: Optional[list] = None):
        """Clear cache entries, optionally by tags"""
        if tags is None:
            # Clear all
            with self._memory_lock:
                self._memory_cache.clear()
                self._memory_size = 0
            
            # Clear disk cache
            try:
                import shutil
                shutil.rmtree(self.cache_dir)
                os.makedirs(self.cache_dir, exist_ok=True)
            except Exception as e:
                self.logger.error(f"Failed to clear disk cache: {e}")
        else:
            # Clear by tags
            keys_to_remove = []
            with self._memory_lock:
                for key, entry in self._memory_cache.items():
                    if any(tag in entry.tags for tag in tags):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    self._remove_from_memory(key)
    
    def invalidate_by_pattern(self, pattern: str):
        """Invalidate cache entries matching pattern"""
        import fnmatch
        
        keys_to_remove = []
        with self._memory_lock:
            for key in self._memory_cache:
                if fnmatch.fnmatch(key, pattern):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._remove_from_memory(key)
        
        # Also remove from disk
        for key in keys_to_remove:
            self._delete_from_disk(key)
    
    def _set_in_memory(self, key: str, value: Any, ttl: Optional[float], 
                      tags: Optional[list] = None):
        """Set value in memory cache"""
        if tags is None:
            tags = []
        
        # Calculate size
        try:
            size_bytes = len(pickle.dumps(value))
        except:
            size_bytes = len(str(value).encode())
        
        with self._memory_lock:
            # Remove existing entry if present
            if key in self._memory_cache:
                self._remove_from_memory(key)
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                size_bytes=size_bytes,
                tags=tags
            )
            
            # Check if we need to evict entries
            while (self._memory_size + size_bytes > self.max_memory_size and 
                   self._memory_cache):
                self._evict_lru()
            
            # Add new entry
            self._memory_cache[key] = entry
            self._memory_size += size_bytes
    
    def _remove_from_memory(self, key: str):
        """Remove entry from memory cache"""
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            self._memory_size -= entry.size_bytes
            del self._memory_cache[key]
    
    def _evict_lru(self):
        """Evict least recently used entry from memory"""
        if not self._memory_cache:
            return
        
        # Find LRU entry
        lru_key = min(self._memory_cache.keys(), 
                     key=lambda k: self._memory_cache[k].last_access)
        
        self._remove_from_memory(lru_key)
        self.stats['evictions'] += 1
        self.stats['size_evictions'] += 1
        self.logger.debug(f"Evicted LRU entry: {lru_key}")
    
    def _get_cache_file_path(self, key: str) -> str:
        """Get file path for cache key"""
        # Hash the key to create a safe filename
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.cache")
    
    def _get_from_disk(self, key: str) -> Any:
        """Get value from disk cache"""
        cache_file = self._get_cache_file_path(key)
        
        try:
            if not os.path.exists(cache_file):
                return None
            
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
            
            # Check if expired
            if cache_data.get('ttl') and time.time() - cache_data['timestamp'] > cache_data['ttl']:
                os.unlink(cache_file)
                return None
            
            return cache_data['value']
            
        except Exception as e:
            self.logger.debug(f"Failed to read from disk cache {key}: {e}")
            # Clean up corrupted cache file
            try:
                os.unlink(cache_file)
            except:
                pass
            return None
    
    def _set_on_disk(self, key: str, value: Any, ttl: Optional[float], 
                    tags: Optional[list] = None):
        """Set value in disk cache"""
        cache_file = self._get_cache_file_path(key)
        
        try:
            cache_data = {
                'key': key,
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl,
                'tags': tags or []
            }
            
            # Write atomically
            temp_file = cache_file + '.tmp'
            with open(temp_file, 'wb') as f:
                pickle.dump(cache_data, f)
            
            os.rename(temp_file, cache_file)
            
        except Exception as e:
            self.logger.debug(f"Failed to write to disk cache {key}: {e}")
    
    def _delete_from_disk(self, key: str):
        """Delete key from disk cache"""
        cache_file = self._get_cache_file_path(key)
        try:
            if os.path.exists(cache_file):
                os.unlink(cache_file)
        except Exception as e:
            self.logger.debug(f"Failed to delete from disk cache {key}: {e}")
    
    def _cleanup(self):
        """Cleanup expired entries and manage disk cache size"""
        self._last_cleanup = time.time()
        
        # Cleanup memory cache
        with self._memory_lock:
            expired_keys = [
                key for key, entry in self._memory_cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                self._remove_from_memory(key)
        
        # Cleanup disk cache
        try:
            cache_files = []
            total_size = 0
            
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    filepath = os.path.join(self.cache_dir, filename)
                    try:
                        stat = os.stat(filepath)
                        cache_files.append((filepath, stat.st_mtime, stat.st_size))
                        total_size += stat.st_size
                    except:
                        continue
            
            # Remove expired files
            current_time = time.time()
            for filepath, mtime, size in cache_files[:]:
                try:
                    with open(filepath, 'rb') as f:
                        cache_data = pickle.load(f)
                    
                    if (cache_data.get('ttl') and 
                        current_time - cache_data['timestamp'] > cache_data['ttl']):
                        os.unlink(filepath)
                        cache_files.remove((filepath, mtime, size))
                        total_size -= size
                except:
                    # Remove corrupted files
                    try:
                        os.unlink(filepath)
                        cache_files.remove((filepath, mtime, size))
                        total_size -= size
                    except:
                        pass
            
            # Remove oldest files if over disk limit
            if total_size > self.max_disk_size:
                cache_files.sort(key=lambda x: x[1])  # Sort by mtime
                
                while total_size > self.max_disk_size and cache_files:
                    filepath, mtime, size = cache_files.pop(0)
                    try:
                        os.unlink(filepath)
                        total_size -= size
                        self.stats['evictions'] += 1
                    except:
                        pass
        
        except Exception as e:
            self.logger.error(f"Cache cleanup failed: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._memory_lock:
            memory_entries = len(self._memory_cache)
            memory_size = self._memory_size
        
        # Count disk entries
        disk_entries = 0
        disk_size = 0
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.cache'):
                    filepath = os.path.join(self.cache_dir, filename)
                    try:
                        disk_entries += 1
                        disk_size += os.path.getsize(filepath)
                    except:
                        pass
        except:
            pass
        
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'memory_entries': memory_entries,
            'memory_size_mb': memory_size / 1024 / 1024,
            'memory_utilization': (memory_size / self.max_memory_size * 100) if self.max_memory_size > 0 else 0,
            'disk_entries': disk_entries,
            'disk_size_mb': disk_size / 1024 / 1024,
            'disk_utilization': (disk_size / self.max_disk_size * 100) if self.max_disk_size > 0 else 0,
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            **self.stats
        }
    
    def warm_up(self, keys_and_loaders: Dict[str, Callable[[], Any]]):
        """Warm up cache with specified keys and loader functions"""
        def load_key(key: str, loader: Callable[[], Any]):
            try:
                if self.get(key) is None:  # Only load if not in cache
                    value = loader()
                    self.set(key, value, tags=['warmup'])
                    self.logger.debug(f"Warmed up cache key: {key}")
            except Exception as e:
                self.logger.error(f"Failed to warm up cache key {key}: {e}")
        
        # Load keys in parallel
        futures = []
        for key, loader in keys_and_loaders.items():
            future = self._executor.submit(load_key, key, loader)
            futures.append(future)
        
        # Wait for completion
        for future in futures:
            try:
                future.result(timeout=30)  # 30 second timeout per key
            except Exception as e:
                self.logger.error(f"Cache warmup failed: {e}")
    
    def close(self):
        """Close cache manager and cleanup resources"""
        try:
            self._executor.shutdown(wait=True, timeout=10)
        except Exception as e:
            self.logger.error(f"Error shutting down cache executor: {e}")


# Decorator for caching function results
def cached(ttl: Optional[float] = None, tags: Optional[list] = None, 
          key_func: Optional[Callable] = None):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        cache_manager = get_cache_manager()
        
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl=ttl, tags=tags)
            return result
        
        return wrapper
    return decorator


# Global cache manager instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager