"""
Configuration file watching and change detection
"""

import os
import time
import threading
from pathlib import Path
from typing import List, Callable, Dict, Any, Optional
from datetime import datetime, timedelta

from ..utils.logging import get_logger

logger = get_logger(__name__)


class ConfigWatcher:
    """Watch configuration files for changes"""
    
    def __init__(self, config_file: Path, check_interval: float = 1.0):
        self.config_file = config_file
        self.check_interval = check_interval
        
        # State tracking
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[Path], None]] = []
        
        # File state tracking
        self._last_modified: Optional[float] = None
        self._last_size: Optional[int] = None
        self._last_checksum: Optional[str] = None
        
        # Advanced watching options
        self._use_polling = True  # Use polling by default for cross-platform compatibility
        self._debounce_delay = 0.5  # Seconds to wait before triggering callbacks
        self._last_change_time: Optional[float] = None
        
        # Statistics
        self._change_count = 0
        self._last_change_detected: Optional[datetime] = None
        
        self._update_file_state()
    
    def add_callback(self, callback: Callable[[Path], None]) -> None:
        """Add callback for file changes"""
        self._callbacks.append(callback)
        logger.debug(f"Added file watcher callback: {callback.__name__}")
    
    def remove_callback(self, callback: Callable[[Path], None]) -> None:
        """Remove file change callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.debug(f"Removed file watcher callback: {callback.__name__}")
    
    def start(self) -> None:
        """Start watching for file changes"""
        if self._running:
            logger.warning("Config watcher is already running")
            return
        
        self._running = True
        
        if self._use_polling:
            self._thread = threading.Thread(target=self._polling_watch, daemon=True)
        else:
            # Try to use native file system events if available
            try:
                self._thread = threading.Thread(target=self._native_watch, daemon=True)
            except ImportError:
                logger.warning("Native file watching not available, falling back to polling")
                self._thread = threading.Thread(target=self._polling_watch, daemon=True)
        
        self._thread.start()
        logger.info(f"Started configuration file watcher for {self.config_file}")
    
    def stop(self) -> None:
        """Stop watching for file changes"""
        if not self._running:
            return
        
        self._running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        
        logger.info("Stopped configuration file watcher")
    
    def _polling_watch(self) -> None:
        """Watch file using polling"""
        while self._running:
            try:
                if self._check_file_changed():
                    self._handle_file_change()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in polling file watcher: {e}")
                time.sleep(self.check_interval)
    
    def _native_watch(self) -> None:
        """Watch file using native file system events"""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class ConfigFileHandler(FileSystemEventHandler):
                def __init__(self, watcher):
                    self.watcher = watcher
                
                def on_modified(self, event):
                    if not event.is_directory and Path(event.src_path) == self.watcher.config_file:
                        self.watcher._handle_file_change()
            
            observer = Observer()
            event_handler = ConfigFileHandler(self)
            observer.schedule(event_handler, str(self.config_file.parent), recursive=False)
            observer.start()
            
            try:
                while self._running:
                    time.sleep(0.1)
            finally:
                observer.stop()
                observer.join()
                
        except ImportError:
            logger.warning("watchdog package not available, using polling instead")
            self._polling_watch()
    
    def _check_file_changed(self) -> bool:
        """Check if file has changed using multiple methods"""
        if not self.config_file.exists():
            # Handle file deletion/recreation
            if self._last_modified is not None:
                logger.info(f"Configuration file was deleted: {self.config_file}")
                self._update_file_state()
                return True
            return False
        
        try:
            stat = self.config_file.stat()
            current_modified = stat.st_mtime
            current_size = stat.st_size
            
            # Check modification time
            if self._last_modified is None or current_modified != self._last_modified:
                self._last_modified = current_modified
                self._last_size = current_size
                return True
            
            # Check file size as additional verification
            if current_size != self._last_size:
                self._last_size = current_size
                return True
            
            # For critical changes, also check content checksum
            if self._should_check_checksum():
                current_checksum = self._get_file_checksum()
                if current_checksum != self._last_checksum:
                    self._last_checksum = current_checksum
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking file changes: {e}")
            return False
    
    def _should_check_checksum(self) -> bool:
        """Determine if we should check file checksum"""
        # Only check checksum occasionally to avoid performance impact
        return self._change_count % 10 == 0
    
    def _get_file_checksum(self) -> str:
        """Calculate file checksum"""
        import hashlib
        
        try:
            with open(self.config_file, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    def _update_file_state(self) -> None:
        """Update internal file state tracking"""
        if self.config_file.exists():
            try:
                stat = self.config_file.stat()
                self._last_modified = stat.st_mtime
                self._last_size = stat.st_size
                self._last_checksum = self._get_file_checksum()
            except Exception:
                self._last_modified = None
                self._last_size = None
                self._last_checksum = None
        else:
            self._last_modified = None
            self._last_size = None
            self._last_checksum = None
    
    def _handle_file_change(self) -> None:
        """Handle detected file change"""
        current_time = time.time()
        
        # Implement debouncing to avoid multiple rapid triggers
        if self._last_change_time and (current_time - self._last_change_time) < self._debounce_delay:
            return
        
        self._last_change_time = current_time
        self._change_count += 1
        self._last_change_detected = datetime.now()
        
        logger.info(f"Configuration file changed: {self.config_file}")
        
        # Trigger all callbacks
        for callback in self._callbacks:
            try:
                callback(self.config_file)
            except Exception as e:
                logger.error(f"Error in file change callback {callback.__name__}: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get watcher statistics"""
        return {
            'running': self._running,
            'config_file': str(self.config_file),
            'file_exists': self.config_file.exists(),
            'change_count': self._change_count,
            'last_change_detected': self._last_change_detected.isoformat() if self._last_change_detected else None,
            'callback_count': len(self._callbacks),
            'check_interval': self.check_interval,
            'debounce_delay': self._debounce_delay,
            'use_polling': self._use_polling
        }
    
    def force_check(self) -> bool:
        """Force check for file changes"""
        if self._check_file_changed():
            self._handle_file_change()
            return True
        return False
    
    def is_running(self) -> bool:
        """Check if watcher is running"""
        return self._running


class MultiConfigWatcher:
    """Watch multiple configuration files"""
    
    def __init__(self, check_interval: float = 1.0):
        self.check_interval = check_interval
        self._watchers: Dict[str, ConfigWatcher] = {}
        self._global_callbacks: List[Callable[[str, Path], None]] = []
        self._running = False
    
    def add_config_file(self, name: str, config_file: Path, 
                       callbacks: Optional[List[Callable[[Path], None]]] = None) -> None:
        """Add a configuration file to watch"""
        if name in self._watchers:
            logger.warning(f"Configuration file '{name}' is already being watched")
            return
        
        watcher = ConfigWatcher(config_file, self.check_interval)
        
        # Add individual callbacks
        if callbacks:
            for callback in callbacks:
                watcher.add_callback(callback)
        
        # Add global callback wrapper
        def global_callback_wrapper(file_path: Path):
            for global_callback in self._global_callbacks:
                try:
                    global_callback(name, file_path)
                except Exception as e:
                    logger.error(f"Error in global callback: {e}")
        
        watcher.add_callback(global_callback_wrapper)
        
        self._watchers[name] = watcher
        
        # Start watching if multi-watcher is running
        if self._running:
            watcher.start()
        
        logger.info(f"Added configuration file to watch: {name} -> {config_file}")
    
    def remove_config_file(self, name: str) -> None:
        """Remove a configuration file from watching"""
        if name not in self._watchers:
            logger.warning(f"Configuration file '{name}' is not being watched")
            return
        
        watcher = self._watchers[name]
        watcher.stop()
        del self._watchers[name]
        
        logger.info(f"Removed configuration file from watching: {name}")
    
    def add_global_callback(self, callback: Callable[[str, Path], None]) -> None:
        """Add global callback for all file changes"""
        self._global_callbacks.append(callback)
    
    def remove_global_callback(self, callback: Callable[[str, Path], None]) -> None:
        """Remove global callback"""
        if callback in self._global_callbacks:
            self._global_callbacks.remove(callback)
    
    def start_all(self) -> None:
        """Start watching all configuration files"""
        if self._running:
            logger.warning("Multi-config watcher is already running")
            return
        
        self._running = True
        
        for name, watcher in self._watchers.items():
            try:
                watcher.start()
                logger.debug(f"Started watcher for {name}")
            except Exception as e:
                logger.error(f"Failed to start watcher for {name}: {e}")
        
        logger.info(f"Started watching {len(self._watchers)} configuration files")
    
    def stop_all(self) -> None:
        """Stop watching all configuration files"""
        if not self._running:
            return
        
        self._running = False
        
        for name, watcher in self._watchers.items():
            try:
                watcher.stop()
                logger.debug(f"Stopped watcher for {name}")
            except Exception as e:
                logger.error(f"Error stopping watcher for {name}: {e}")
        
        logger.info("Stopped all configuration file watchers")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for all watchers"""
        stats = {
            'running': self._running,
            'total_watchers': len(self._watchers),
            'global_callbacks': len(self._global_callbacks),
            'watchers': {}
        }
        
        for name, watcher in self._watchers.items():
            stats['watchers'][name] = watcher.get_statistics()
        
        return stats
    
    def force_check_all(self) -> Dict[str, bool]:
        """Force check all watched files"""
        results = {}
        
        for name, watcher in self._watchers.items():
            try:
                results[name] = watcher.force_check()
            except Exception as e:
                logger.error(f"Error force checking {name}: {e}")
                results[name] = False
        
        return results
    
    def list_watched_files(self) -> Dict[str, str]:
        """List all watched configuration files"""
        return {name: str(watcher.config_file) for name, watcher in self._watchers.items()}
    
    def is_running(self) -> bool:
        """Check if multi-watcher is running"""
        return self._running


class ConfigChangeLogger:
    """Log configuration changes with detailed information"""
    
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file
        self._change_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
    
    def log_change(self, config_name: str, file_path: Path, 
                  change_type: str = "modified") -> None:
        """Log a configuration change"""
        change_record = {
            'timestamp': datetime.now().isoformat(),
            'config_name': config_name,
            'file_path': str(file_path),
            'change_type': change_type,
            'file_size': self._get_file_size(file_path),
            'file_exists': file_path.exists()
        }
        
        # Add to in-memory history
        self._change_history.append(change_record)
        
        # Trim history if it gets too large
        if len(self._change_history) > self._max_history_size:
            self._change_history = self._change_history[-self._max_history_size:]
        
        # Log to file if specified
        if self.log_file:
            self._write_to_log_file(change_record)
        
        # Log to standard logger
        logger.info(f"Configuration change logged: {config_name} ({change_type})")
    
    def _get_file_size(self, file_path: Path) -> Optional[int]:
        """Get file size safely"""
        try:
            return file_path.stat().st_size if file_path.exists() else None
        except Exception:
            return None
    
    def _write_to_log_file(self, change_record: Dict[str, Any]) -> None:
        """Write change record to log file"""
        try:
            import json
            
            if not self.log_file.parent.exists():
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(change_record) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write to change log file: {e}")
    
    def get_change_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get configuration change history"""
        if limit:
            return self._change_history[-limit:]
        return self._change_history.copy()
    
    def get_changes_since(self, since: datetime) -> List[Dict[str, Any]]:
        """Get changes since a specific time"""
        since_iso = since.isoformat()
        return [
            record for record in self._change_history
            if record['timestamp'] >= since_iso
        ]
    
    def clear_history(self) -> None:
        """Clear change history"""
        self._change_history.clear()
        logger.info("Configuration change history cleared")