"""
Structured logging system for BlastDock
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .filesystem import paths
from ..exceptions import get_error_severity


class BlastDockFormatter(logging.Formatter):
    """Custom formatter for BlastDock logs with structured output"""
    
    def __init__(self, include_timestamp: bool = True, json_format: bool = False):
        self.include_timestamp = include_timestamp
        self.json_format = json_format
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        if self.json_format:
            return self._format_json(record)
        else:
            return self._format_text(record)
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields
        extra_fields = {k: v for k, v in record.__dict__.items() 
                       if k not in ('name', 'msg', 'args', 'levelname', 'levelno', 
                                  'pathname', 'filename', 'module', 'lineno', 'funcName',
                                  'created', 'msecs', 'relativeCreated', 'thread',
                                  'threadName', 'processName', 'process', 'getMessage',
                                  'exc_info', 'exc_text', 'stack_info')}
        
        if extra_fields:
            log_data['extra'] = extra_fields
        
        return json.dumps(log_data, ensure_ascii=False)
    
    def _format_text(self, record: logging.LogRecord) -> str:
        """Format log record as human-readable text"""
        parts = []
        
        if self.include_timestamp:
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            parts.append(f"[{timestamp}]")
        
        # Color-coded level
        level_colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset_color = '\033[0m'
        
        if sys.stderr.isatty():  # Only use colors in terminal
            color = level_colors.get(record.levelname, '')
            parts.append(f"{color}{record.levelname:8}{reset_color}")
        else:
            parts.append(f"{record.levelname:8}")
        
        # Logger name
        parts.append(f"[{record.name}]")
        
        # Message
        parts.append(record.getMessage())
        
        log_line = " ".join(parts)
        
        # Add exception info if present
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        
        return log_line


class BlastDockLogger:
    """Central logging manager for BlastDock"""
    
    def __init__(self):
        self._initialized = False
        self._loggers: Dict[str, logging.Logger] = {}
        self._log_level = logging.INFO
        self._log_to_file = True
        self._log_to_console = True
        self._json_format = False
    
    def initialize(self, 
                   log_level: str = "INFO",
                   log_to_file: bool = True,
                   log_to_console: bool = True,
                   json_format: bool = False,
                   max_log_size: int = 10 * 1024 * 1024,  # 10MB
                   backup_count: int = 5) -> None:
        """Initialize the logging system"""
        if self._initialized:
            return
        
        self._log_level = getattr(logging, log_level.upper(), logging.INFO)
        self._log_to_file = log_to_file
        self._log_to_console = log_to_console
        self._json_format = json_format
        
        # Ensure log directory exists
        if self._log_to_file:
            paths.ensure_directories()
        
        # Configure root logger
        root_logger = logging.getLogger('blastdock')
        root_logger.setLevel(self._log_level)
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Add console handler
        if self._log_to_console:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(self._log_level)
            console_formatter = BlastDockFormatter(
                include_timestamp=False, 
                json_format=self._json_format
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Add file handler
        if self._log_to_file:
            log_file = paths.log_dir / "blastdock.log"
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_log_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # Always log everything to file
            file_formatter = BlastDockFormatter(
                include_timestamp=True,
                json_format=self._json_format
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # Prevent propagation to avoid duplicate logs
        root_logger.propagate = False
        
        self._initialized = True
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger instance"""
        if not self._initialized:
            self.initialize()
        
        full_name = f"blastdock.{name}" if not name.startswith('blastdock') else name
        
        if full_name not in self._loggers:
            logger = logging.getLogger(full_name)
            self._loggers[full_name] = logger
        
        return self._loggers[full_name]
    
    def log_exception(self, 
                     logger: logging.Logger, 
                     exception: Exception, 
                     context: Optional[Dict[str, Any]] = None) -> None:
        """Log an exception with appropriate severity"""
        severity = get_error_severity(exception)
        
        # Map severity to log level
        level_map = {
            'critical': logging.CRITICAL,
            'error': logging.ERROR,
            'warning': logging.WARNING,
            'info': logging.INFO,
        }
        
        log_level = level_map.get(severity, logging.ERROR)
        
        # Create log message
        message = f"{type(exception).__name__}: {exception}"
        
        # Add context if provided
        extra = {}
        if context:
            extra.update(context)
        
        extra.update({
            'exception_type': type(exception).__name__,
            'severity': severity,
        })
        
        # Log with exception info
        logger.log(log_level, message, exc_info=True, extra=extra)
    
    def set_level(self, level: str) -> None:
        """Change log level for all loggers"""
        new_level = getattr(logging, level.upper(), logging.INFO)
        self._log_level = new_level
        
        # Update all existing loggers
        for logger in self._loggers.values():
            logger.setLevel(new_level)
        
        # Update root logger
        root_logger = logging.getLogger('blastdock')
        root_logger.setLevel(new_level)
    
    def get_log_file_path(self) -> Optional[Path]:
        """Get the current log file path"""
        if self._log_to_file:
            return paths.log_dir / "blastdock.log"
        return None


# Global logger instance
logger_manager = BlastDockLogger()


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance (convenience function)"""
    return logger_manager.get_logger(name)


def initialize_logging(**kwargs) -> None:
    """Initialize logging system (convenience function)"""
    logger_manager.initialize(**kwargs)


def log_exception(logger: logging.Logger, 
                 exception: Exception, 
                 context: Optional[Dict[str, Any]] = None) -> None:
    """Log an exception (convenience function)"""
    logger_manager.log_exception(logger, exception, context)