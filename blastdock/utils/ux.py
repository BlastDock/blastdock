"""
Enhanced UX utilities for BlastDock CLI
Provides progress bars, status indicators, and improved user feedback
"""

import time
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from contextlib import contextmanager
from enum import Enum

from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn, 
    TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn,
    DownloadColumn, TransferSpeedColumn, MofNCompleteColumn
)
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.rule import Rule
from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
from rich.tree import Tree
from rich.columns import Columns
from rich.status import Status

from .logging import get_logger

logger = get_logger(__name__)


class TaskType(Enum):
    """Types of tasks for progress tracking"""
    GENERAL = "general"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    DEPLOYMENT = "deployment"
    BUILD = "build"
    ANALYSIS = "analysis"
    HEALTH_CHECK = "health_check"


@dataclass
class UXTask:
    """Task for UX progress tracking"""
    id: str
    name: str
    task_type: TaskType
    total: Optional[int] = None
    description: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    progress: int = 0
    status: str = "running"
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnhancedProgress:
    """Enhanced progress tracking with rich displays"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize enhanced progress tracker"""
        self.console = console or Console()
        self.logger = get_logger(__name__)
        
        # Active tasks
        self._tasks: Dict[str, UXTask] = {}
        self._task_lock = threading.RLock()
        
        # Progress instances for different types
        self._progress_instances: Dict[TaskType, Progress] = {}
        self._active_progress: Optional[Progress] = None
        
        # Live display
        self._live_display: Optional[Live] = None
        self._display_active = False
        
        self.logger.debug("Enhanced progress tracker initialized")
    
    def _get_progress_for_type(self, task_type: TaskType) -> Progress:
        """Get or create progress instance for task type"""
        if task_type not in self._progress_instances:
            if task_type == TaskType.DOWNLOAD:
                progress = Progress(
                    TextColumn("[bold blue]{task.description}", justify="right"),
                    BarColumn(bar_width=None),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    "•",
                    DownloadColumn(),
                    "•",
                    TransferSpeedColumn(),
                    "•",
                    TimeRemainingColumn(),
                    console=self.console,
                    transient=True
                )
            elif task_type == TaskType.BUILD:
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold green]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    "•",
                    TimeElapsedColumn(),
                    console=self.console,
                    transient=True
                )
            elif task_type == TaskType.DEPLOYMENT:
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.description}"),
                    BarColumn(),
                    MofNCompleteColumn(),
                    "•",
                    TimeElapsedColumn(),
                    console=self.console,
                    transient=True
                )
            elif task_type == TaskType.HEALTH_CHECK:
                progress = Progress(
                    SpinnerColumn("dots"),
                    TextColumn("[bold yellow]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=self.console,
                    transient=True
                )
            else:
                # General progress
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    "•",
                    TimeElapsedColumn(),
                    console=self.console,
                    transient=True
                )
            
            self._progress_instances[task_type] = progress
        
        return self._progress_instances[task_type]
    
    @contextmanager
    def task(self, task_id: str, name: str, task_type: TaskType = TaskType.GENERAL,
             total: Optional[int] = None, description: str = ""):
        """Context manager for tracking a task"""
        # Create task
        ux_task = UXTask(
            id=task_id,
            name=name,
            task_type=task_type,
            total=total,
            description=description or name
        )
        
        with self._task_lock:
            self._tasks[task_id] = ux_task
        
        # Get progress instance
        progress = self._get_progress_for_type(task_type)
        
        try:
            with progress:
                task = progress.add_task(ux_task.description, total=total)
                ux_task.metadata['progress_task_id'] = task
                
                yield TaskController(ux_task, progress, task, self)
        
        finally:
            # Mark as completed
            ux_task.completed_at = time.time()
            ux_task.status = "completed"
            
            with self._task_lock:
                if task_id in self._tasks:
                    del self._tasks[task_id]
    
    @contextmanager
    def multi_task_display(self, title: str = "BlastDock Operations"):
        """Context manager for displaying multiple tasks simultaneously"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="tasks"),
            Layout(name="footer", size=3)
        )
        
        # Header
        header = Panel(
            Align.center(Text(title, style="bold blue")),
            style="blue"
        )
        layout["header"].update(header)
        
        # Footer with timestamp
        footer = Panel(
            Align.center(Text(f"Started: {time.strftime('%H:%M:%S')}", style="dim")),
            style="dim"
        )
        layout["footer"].update(footer)
        
        try:
            with Live(layout, console=self.console, refresh_per_second=4) as live:
                self._live_display = live
                self._display_active = True
                
                yield MultiTaskController(self, layout, live)
        
        finally:
            self._live_display = None
            self._display_active = False
    
    def get_active_tasks(self) -> List[UXTask]:
        """Get list of active tasks"""
        with self._task_lock:
            return [task for task in self._tasks.values() if task.status == "running"]


class TaskController:
    """Controller for managing individual task progress"""
    
    def __init__(self, ux_task: UXTask, progress: Progress, 
                 progress_task_id: Any, parent: EnhancedProgress):
        self.ux_task = ux_task
        self.progress = progress
        self.progress_task_id = progress_task_id
        self.parent = parent
    
    def update(self, advance: int = 1, description: str = None, **kwargs):
        """Update task progress"""
        self.ux_task.progress += advance
        if description:
            self.ux_task.description = description
        
        self.progress.update(self.progress_task_id, advance=advance, 
                           description=description, **kwargs)
    
    def set_total(self, total: int):
        """Set or update the total for the task"""
        self.ux_task.total = total
        self.progress.update(self.progress_task_id, total=total)
    
    def complete(self, description: str = None):
        """Mark task as completed"""
        if description:
            self.ux_task.description = description
        
        if self.ux_task.total:
            remaining = self.ux_task.total - self.ux_task.progress
            if remaining > 0:
                self.update(advance=remaining, description=description)
        
        self.ux_task.status = "completed"
        self.ux_task.completed_at = time.time()
    
    def fail(self, error: str = "Task failed"):
        """Mark task as failed"""
        self.ux_task.status = "failed"
        self.ux_task.metadata['error'] = error
        self.ux_task.completed_at = time.time()
        
        self.progress.update(self.progress_task_id, description=f"❌ {error}")


class MultiTaskController:
    """Controller for managing multiple simultaneous tasks"""
    
    def __init__(self, parent: EnhancedProgress, layout: Layout, live: Live):
        self.parent = parent
        self.layout = layout
        self.live = live
        self._task_displays: Dict[str, Progress] = {}
    
    def add_task_display(self, task_type: TaskType, title: str = None) -> Progress:
        """Add a new task display panel"""
        progress = self.parent._get_progress_for_type(task_type)
        
        if title:
            display_title = title
        else:
            display_title = f"{task_type.value.title()} Tasks"
        
        # Create panel for this progress
        task_panel = Panel(progress, title=display_title, border_style="blue")
        
        # Update layout with new task panel
        current_tasks = len(self._task_displays)
        self._task_displays[task_type.value] = progress
        
        # Reorganize layout based on number of tasks
        if current_tasks == 0:
            self.layout["tasks"].update(task_panel)
        else:
            # Split tasks section
            task_layouts = [Panel(prog, title=f"{name.title()} Tasks") 
                          for name, prog in self._task_displays.items()]
            task_layouts.append(task_panel)
            
            if len(task_layouts) <= 2:
                self.layout["tasks"].split_row(*[Layout() for _ in task_layouts])
                for i, task_layout in enumerate(task_layouts):
                    self.layout["tasks"].children[i].update(task_layout)
            else:
                # Use columns for more than 2 tasks
                self.layout["tasks"].update(Columns(task_layouts, equal=True))
        
        return progress


class UXManager:
    """Main UX manager for enhanced CLI experience"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize UX manager"""
        self.console = console or Console()
        self.progress = EnhancedProgress(self.console)
        self.logger = get_logger(__name__)
        
        # UX preferences
        self.show_timestamps = True
        self.show_progress_bars = True
        self.animation_speed = "normal"  # slow, normal, fast
        self.color_theme = "auto"  # auto, light, dark
    
    def show_welcome(self, version: str = "1.0.0"):
        """Show welcome message with branding"""
        welcome_text = Text()
        welcome_text.append("🚀 ", style="bold red")
        welcome_text.append("BlastDock", style="bold blue")
        welcome_text.append(f" v{version}", style="bold green")
        welcome_text.append("\n")
        welcome_text.append("Enterprise Docker Deployment Platform", style="italic cyan")
        
        panel = Panel(
            Align.center(welcome_text),
            style="blue",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print()
    
    def show_success(self, message: str, details: List[str] = None):
        """Show success message with optional details"""
        success_text = Text()
        success_text.append("✅ ", style="bold green")
        success_text.append(message, style="bold green")
        
        if details:
            success_text.append("\n\n")
            for detail in details:
                success_text.append(f"  • {detail}\n", style="green")
        
        panel = Panel(success_text, border_style="green", title="Success")
        self.console.print(panel)
    
    def show_warning(self, message: str, suggestions: List[str] = None):
        """Show warning message with optional suggestions"""
        warning_text = Text()
        warning_text.append("⚠️ ", style="bold yellow")
        warning_text.append(message, style="bold yellow")
        
        if suggestions:
            warning_text.append("\n\n")
            warning_text.append("Suggestions:\n", style="bold yellow")
            for suggestion in suggestions:
                warning_text.append(f"  • {suggestion}\n", style="yellow")
        
        panel = Panel(warning_text, border_style="yellow", title="Warning")
        self.console.print(panel)
    
    def show_error(self, message: str, error_details: str = None, 
                   suggestions: List[str] = None):
        """Show error message with details and suggestions"""
        error_text = Text()
        error_text.append("❌ ", style="bold red")
        error_text.append(message, style="bold red")
        
        if error_details:
            error_text.append("\n\n")
            error_text.append("Details:\n", style="bold red")
            error_text.append(f"  {error_details}", style="red")
        
        if suggestions:
            error_text.append("\n\n")
            error_text.append("Suggestions:\n", style="bold yellow")
            for suggestion in suggestions:
                error_text.append(f"  • {suggestion}\n", style="yellow")
        
        panel = Panel(error_text, border_style="red", title="Error")
        self.console.print(panel)
    
    def show_info(self, title: str, data: Dict[str, Any], 
                  highlight_keys: List[str] = None):
        """Show information in a structured format"""
        info_text = Text()
        
        for key, value in data.items():
            key_style = "bold cyan" if highlight_keys and key in highlight_keys else "cyan"
            info_text.append(f"{key}: ", style=key_style)
            info_text.append(f"{value}\n", style="white")
        
        panel = Panel(info_text, title=title, border_style="blue")
        self.console.print(panel)
    
    def create_status_table(self, title: str, headers: List[str], 
                           rows: List[List[str]], styles: List[str] = None) -> Table:
        """Create a formatted status table"""
        table = Table(title=title, show_header=True, header_style="bold magenta")
        
        # Add columns
        for i, header in enumerate(headers):
            style = styles[i] if styles and i < len(styles) else "white"
            table.add_column(header, style=style)
        
        # Add rows
        for row in rows:
            table.add_row(*row)
        
        return table
    
    def prompt_choice(self, message: str, choices: List[str], 
                     default: str = None) -> str:
        """Enhanced choice prompt with validation"""
        if default and default in choices:
            choices_text = []
            for choice in choices:
                if choice == default:
                    choices_text.append(f"[bold green]{choice}[/bold green]")
                else:
                    choices_text.append(choice)
            
            choice_display = " / ".join(choices_text)
            prompt_text = f"{message} ({choice_display})"
        else:
            choice_display = " / ".join(choices)
            prompt_text = f"{message} ({choice_display})"
        
        while True:
            try:
                response = Prompt.ask(prompt_text, default=default)
                if response in choices:
                    return response
                else:
                    self.console.print(f"[red]Invalid choice. Please select from: {', '.join(choices)}[/red]")
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Operation cancelled[/yellow]")
                raise
    
    def prompt_confirm(self, message: str, default: bool = False) -> bool:
        """Enhanced confirmation prompt"""
        try:
            return Confirm.ask(message, default=default)
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]Operation cancelled[/yellow]")
            raise
    
    def prompt_text(self, message: str, default: str = None, 
                   password: bool = False) -> str:
        """Enhanced text prompt with validation"""
        try:
            return Prompt.ask(message, default=default, password=password)
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]Operation cancelled[/yellow]")
            raise
    
    def prompt_int(self, message: str, default: int = None, 
                  min_value: int = None, max_value: int = None) -> int:
        """Enhanced integer prompt with validation"""
        while True:
            try:
                value = IntPrompt.ask(message, default=default)
                
                if min_value is not None and value < min_value:
                    self.console.print(f"[red]Value must be at least {min_value}[/red]")
                    continue
                
                if max_value is not None and value > max_value:
                    self.console.print(f"[red]Value must be at most {max_value}[/red]")
                    continue
                
                return value
            
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[yellow]Operation cancelled[/yellow]")
                raise
    
    @contextmanager
    def status(self, message: str, spinner: str = "dots"):
        """Status context manager with spinner"""
        try:
            with Status(message, spinner=spinner, console=self.console) as status:
                yield status
        except (KeyboardInterrupt, EOFError):
            self.console.print("\n[yellow]Operation cancelled[/yellow]")
            raise
    
    @contextmanager
    def deployment_progress(self, project_name: str, services: List[str]):
        """Special progress context for deployments"""
        title = f"Deploying {project_name}"
        
        with self.progress.multi_task_display(title) as controller:
            # Add deployment progress display
            deploy_progress = controller.add_task_display(
                TaskType.DEPLOYMENT, 
                "Deployment Progress"
            )
            
            yield DeploymentProgressController(
                deploy_progress, services, self.console
            )
    
    def show_deployment_summary(self, project_name: str, 
                              services: Dict[str, str], duration: float):
        """Show deployment completion summary"""
        summary_text = Text()
        summary_text.append(f"🚀 Deployment Complete: ", style="bold green")
        summary_text.append(f"{project_name}\n", style="bold cyan")
        summary_text.append(f"Duration: {duration:.1f} seconds\n\n", style="green")
        
        # Service status
        summary_text.append("Services:\n", style="bold")
        for service, status in services.items():
            if status == "running":
                summary_text.append(f"  ✅ {service}: ", style="green")
                summary_text.append("Running\n", style="bold green")
            elif status == "failed":
                summary_text.append(f"  ❌ {service}: ", style="red")
                summary_text.append("Failed\n", style="bold red")
            else:
                summary_text.append(f"  ⚠️ {service}: ", style="yellow")
                summary_text.append(f"{status}\n", style="yellow")
        
        panel = Panel(summary_text, title="Deployment Summary", border_style="green")
        self.console.print(panel)


class DeploymentProgressController:
    """Controller for deployment-specific progress tracking"""
    
    def __init__(self, progress: Progress, services: List[str], console: Console):
        self.progress = progress
        self.services = services
        self.console = console
        
        # Create tasks for each service
        self.service_tasks = {}
        for service in services:
            task_id = self.progress.add_task(
                f"Preparing {service}...", 
                total=100
            )
            self.service_tasks[service] = task_id
    
    def update_service(self, service: str, progress: int, description: str = None):
        """Update progress for a specific service"""
        if service in self.service_tasks:
            task_id = self.service_tasks[service]
            
            # Calculate advance
            current_progress = self.progress.tasks[task_id].completed
            advance = max(0, progress - current_progress)
            
            update_kwargs = {'advance': advance}
            if description:
                update_kwargs['description'] = f"{description} {service}"
            
            self.progress.update(task_id, **update_kwargs)
    
    def complete_service(self, service: str, success: bool = True):
        """Mark service deployment as complete"""
        if service in self.service_tasks:
            task_id = self.service_tasks[service]
            
            if success:
                description = f"✅ {service} deployed"
                style = "green"
            else:
                description = f"❌ {service} failed"
                style = "red"
            
            self.progress.update(
                task_id, 
                completed=100, 
                description=description
            )


# Global UX manager instance
_ux_manager = None


def get_ux_manager() -> UXManager:
    """Get global UX manager instance"""
    global _ux_manager
    if _ux_manager is None:
        _ux_manager = UXManager()
    return _ux_manager


# Convenience functions
def show_success(message: str, details: List[str] = None):
    """Show success message"""
    get_ux_manager().show_success(message, details)


def show_warning(message: str, suggestions: List[str] = None):
    """Show warning message"""
    get_ux_manager().show_warning(message, suggestions)


def show_error(message: str, error_details: str = None, suggestions: List[str] = None):
    """Show error message"""
    get_ux_manager().show_error(message, error_details, suggestions)


def show_info(title: str, data: Dict[str, Any], highlight_keys: List[str] = None):
    """Show information"""
    get_ux_manager().show_info(title, data, highlight_keys)


@contextmanager
def task_progress(task_id: str, name: str, task_type: TaskType = TaskType.GENERAL,
                 total: Optional[int] = None, description: str = ""):
    """Context manager for task progress"""
    with get_ux_manager().progress.task(task_id, name, task_type, total, description) as controller:
        yield controller


@contextmanager  
def status_spinner(message: str, spinner: str = "dots"):
    """Context manager for status spinner"""
    with get_ux_manager().status(message, spinner) as status:
        yield status