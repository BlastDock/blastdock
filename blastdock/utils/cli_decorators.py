"""
CLI decorators and wrappers for enhanced user experience
"""

import time
import functools
from typing import Any, Callable, Dict, List, Optional
import click

from .ux import get_ux_manager, TaskType, task_progress, status_spinner
from .logging import get_logger

logger = get_logger(__name__)


def enhanced_command(show_welcome: bool = False, track_time: bool = True):
    """Decorator to enhance CLI commands with UX improvements"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ux = get_ux_manager()
            start_time = time.time()
            
            try:
                # Show welcome message for main commands
                if show_welcome:
                    from .._version import __version__
                    ux.show_welcome(__version__)
                
                # Execute the command
                result = func(*args, **kwargs)
                
                # Show timing information if requested
                if track_time:
                    duration = time.time() - start_time
                    if duration > 1.0:  # Only show for operations taking more than 1 second
                        ux.console.print(f"\n[dim]⏱️ Completed in {duration:.1f} seconds[/dim]")
                
                return result
                
            except click.exceptions.Abort:
                ux.console.print("\n[yellow]⚠️ Operation cancelled by user[/yellow]")
                raise
            except Exception as e:
                # Enhanced error display
                error_msg = str(e)
                suggestions = []
                
                # Add context-specific suggestions
                if "permission denied" in error_msg.lower():
                    suggestions.append("Check file permissions and user access rights")
                    suggestions.append("Try running with appropriate privileges")
                elif "connection" in error_msg.lower():
                    suggestions.append("Check network connectivity")
                    suggestions.append("Verify service is running and accessible")
                elif "not found" in error_msg.lower():
                    suggestions.append("Verify the resource exists")
                    suggestions.append("Check spelling and path")
                
                ux.show_error(f"Command failed: {func.__name__}", error_msg, suggestions)
                raise
        
        return wrapper
    return decorator


def with_progress(task_name: str = None, task_type: TaskType = TaskType.GENERAL):
    """Decorator to add progress tracking to CLI commands"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate task name if not provided
            name = task_name or f"Running {func.__name__}"
            task_id = f"{func.__name__}_{int(time.time())}"
            
            with task_progress(task_id, name, task_type) as progress:
                # Add progress controller to kwargs
                kwargs['_progress'] = progress
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_spinner(message: str = None, spinner: str = "dots"):
    """Decorator to add spinner to CLI commands"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            status_message = message or f"Running {func.__name__}..."
            
            with status_spinner(status_message, spinner) as status:
                kwargs['_status'] = status
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def interactive_command(confirm_destructive: bool = True):
    """Decorator for interactive commands with confirmation"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ux = get_ux_manager()
            
            # Check for destructive operations
            if confirm_destructive:
                destructive_keywords = ['remove', 'delete', 'destroy', 'stop', 'kill']
                if any(keyword in func.__name__.lower() for keyword in destructive_keywords):
                    if not ux.prompt_confirm(
                        f"⚠️ This is a destructive operation. Continue with {func.__name__}?",
                        default=False
                    ):
                        ux.console.print("[yellow]Operation cancelled[/yellow]")
                        return
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def deployment_command():
    """Special decorator for deployment commands with enhanced progress"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract project name from args/kwargs
            project_name = None
            if args:
                project_name = args[0] if isinstance(args[0], str) else "project"
            elif 'project_name' in kwargs:
                project_name = kwargs['project_name']
            else:
                project_name = "deployment"
            
            ux = get_ux_manager()
            start_time = time.time()
            
            try:
                # Show deployment start message
                ux.console.print(f"\n🚀 [bold blue]Starting deployment: {project_name}[/bold blue]\n")
                
                # Execute deployment
                result = func(*args, **kwargs)
                
                # Show success summary
                duration = time.time() - start_time
                ux.show_success(
                    f"Deployment completed: {project_name}",
                    [
                        f"Duration: {duration:.1f} seconds",
                        f"Status: Success",
                        f"Time: {time.strftime('%H:%M:%S')}"
                    ]
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                ux.show_error(
                    f"Deployment failed: {project_name}",
                    str(e),
                    [
                        "Check deployment logs for details",
                        "Verify all dependencies are available",
                        "Try rerunning the deployment"
                    ]
                )
                raise
        
        return wrapper
    return decorator


def template_command():
    """Special decorator for template-related commands"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ux = get_ux_manager()
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)
                suggestions = []
                
                if "template" in error_msg.lower() and "not found" in error_msg.lower():
                    suggestions.extend([
                        "Run 'blastdock templates list' to see available templates",
                        "Check template name spelling",
                        "Verify template repository is accessible"
                    ])
                elif "permission" in error_msg.lower():
                    suggestions.extend([
                        "Check file system permissions",
                        "Ensure templates directory is writable"
                    ])
                
                ux.show_error(f"Template operation failed", error_msg, suggestions)
                raise
        
        return wrapper
    return decorator


def health_check_command():
    """Special decorator for health check commands"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ux = get_ux_manager()
            
            with task_progress(
                "health_check", 
                "Running health checks", 
                TaskType.HEALTH_CHECK,
                total=100
            ) as progress:
                kwargs['_progress'] = progress
                
                try:
                    progress.update(20, "Initializing health check...")
                    result = func(*args, **kwargs)
                    progress.complete("Health check completed")
                    return result
                    
                except Exception as e:
                    progress.fail(f"Health check failed: {str(e)}")
                    ux.show_error(
                        "Health check failed",
                        str(e),
                        [
                            "Check service availability",
                            "Verify network connectivity",
                            "Review service logs"
                        ]
                    )
                    raise
        
        return wrapper
    return decorator


class ProgressSteps:
    """Helper class for multi-step operations with progress tracking"""
    
    def __init__(self, steps: List[str], task_type: TaskType = TaskType.GENERAL):
        self.steps = steps
        self.task_type = task_type
        self.current_step = 0
        self.total_steps = len(steps)
        self.progress_controller = None
    
    def __enter__(self):
        """Enter context manager"""
        task_id = f"multi_step_{int(time.time())}"
        self.context = task_progress(
            task_id, 
            "Multi-step operation", 
            self.task_type,
            total=self.total_steps * 100
        )
        self.progress_controller = self.context.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        if self.progress_controller:
            if exc_type is None:
                self.progress_controller.complete("All steps completed")
            else:
                self.progress_controller.fail(f"Failed at step: {self.get_current_step_name()}")
        
        return self.context.__exit__(exc_type, exc_val, exc_tb)
    
    def next_step(self, details: str = ""):
        """Move to next step"""
        if self.current_step < self.total_steps:
            step_name = self.steps[self.current_step]
            description = f"Step {self.current_step + 1}/{self.total_steps}: {step_name}"
            if details:
                description += f" - {details}"
            
            self.progress_controller.update(
                advance=100, 
                description=description
            )
            self.current_step += 1
    
    def get_current_step_name(self) -> str:
        """Get current step name"""
        if 0 <= self.current_step < self.total_steps:
            return self.steps[self.current_step]
        return "Unknown step"
    
    def update_current_step(self, details: str, progress_increment: int = 0):
        """Update current step with details"""
        if self.current_step < self.total_steps:
            step_name = self.steps[self.current_step]
            description = f"Step {self.current_step + 1}/{self.total_steps}: {step_name} - {details}"
            
            self.progress_controller.update(
                advance=progress_increment,
                description=description
            )


def multi_step_operation(steps: List[str], task_type: TaskType = TaskType.GENERAL):
    """Decorator for multi-step operations with progress tracking"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with ProgressSteps(steps, task_type) as progress_steps:
                kwargs['_steps'] = progress_steps
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Context managers for common UX patterns
@click.pass_context
def safe_execute(ctx, operation: Callable, error_message: str = "Operation failed"):
    """Safely execute an operation with enhanced error handling"""
    try:
        return operation()
    except click.exceptions.Abort:
        get_ux_manager().console.print("\n[yellow]Operation cancelled by user[/yellow]")
        ctx.exit(130)
    except Exception as e:
        get_ux_manager().show_error(error_message, str(e))
        ctx.exit(1)