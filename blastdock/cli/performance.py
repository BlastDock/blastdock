"""
CLI commands for performance monitoring and optimization
"""

import click
import json
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from ..performance import (
    get_cache_manager, get_template_cache, get_deployment_optimizer,
    get_memory_optimizer, get_parallel_processor, get_performance_benchmarks
)

console = Console()


@click.group()
def performance():
    """Performance monitoring and optimization commands"""
    pass


@performance.command()
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), 
              default='table', help='Output format')
@click.option('--detailed', is_flag=True, help='Show detailed metrics')
def status(output_format, detailed):
    """Show performance status and metrics"""
    
    console.print("\\n[bold blue]📊 BlastDock Performance Status[/bold blue]\\n")
    
    # Gather metrics from all performance components
    cache_manager = get_cache_manager()
    template_cache = get_template_cache()
    deployment_optimizer = get_deployment_optimizer()
    memory_optimizer = get_memory_optimizer()
    parallel_processor = get_parallel_processor()
    benchmarks = get_performance_benchmarks()
    
    cache_stats = cache_manager.get_stats()
    template_stats = template_cache.get_cache_stats()
    deployment_stats = deployment_optimizer.get_performance_metrics()
    memory_usage = memory_optimizer.get_memory_usage()
    parallel_stats = parallel_processor.get_performance_metrics()
    perf_summary = benchmarks.get_performance_summary()
    
    if output_format == 'json':
        all_stats = {
            'cache': cache_stats,
            'template_cache': template_stats,
            'deployment': deployment_stats,
            'memory': memory_usage,
            'parallel_processing': parallel_stats,
            'benchmarks': perf_summary
        }
        console.print(json.dumps(all_stats, indent=2, default=str))
        return
    
    # Display table format
    perf_table = Table(title="Performance Metrics", show_header=True, header_style="bold magenta")
    perf_table.add_column("Component", style="cyan", width=20)
    perf_table.add_column("Key Metric", style="green", width=15)
    perf_table.add_column("Value", style="white", width=15)
    perf_table.add_column("Status", style="yellow", width=10)
    
    # Cache metrics
    hit_rate = cache_stats.get('hit_rate', 0)
    cache_status = "🟢 Good" if hit_rate > 80 else "🟡 Fair" if hit_rate > 60 else "🔴 Poor"
    perf_table.add_row("Cache", "Hit Rate", f"{hit_rate:.1f}%", cache_status)
    
    memory_util = cache_stats.get('memory_utilization', 0)
    mem_status = "🟢 Good" if memory_util < 80 else "🟡 High" if memory_util < 95 else "🔴 Critical"
    perf_table.add_row("Cache", "Memory Usage", f"{memory_util:.1f}%", mem_status)
    
    # Template cache metrics
    template_hit_rate = template_stats.get('template_hit_rate', 0)
    template_status = "🟢 Good" if template_hit_rate > 70 else "🟡 Fair" if template_hit_rate > 50 else "🔴 Poor"
    perf_table.add_row("Templates", "Hit Rate", f"{template_hit_rate:.1f}%", template_status)
    
    avg_load_time = template_stats.get('avg_load_time', 0)
    load_status = "🟢 Fast" if avg_load_time < 1 else "🟡 Slow" if avg_load_time < 5 else "🔴 Very Slow"
    perf_table.add_row("Templates", "Avg Load Time", f"{avg_load_time:.2f}s", load_status)
    
    # Memory metrics
    memory_percent = memory_usage.get('percent', 0)
    memory_status = "🟢 Good" if memory_percent < 70 else "🟡 High" if memory_percent < 85 else "🔴 Critical"
    perf_table.add_row("Memory", "Usage", f"{memory_usage.get('rss_mb', 0):.1f}MB", memory_status)
    
    # Deployment metrics
    avg_deployment_time = deployment_stats.get('average_deployment_time', 0)
    deploy_status = "🟢 Fast" if avg_deployment_time < 30 else "🟡 Slow" if avg_deployment_time < 120 else "🔴 Very Slow"
    perf_table.add_row("Deployment", "Avg Time", f"{avg_deployment_time:.1f}s", deploy_status)
    
    # Parallel processing metrics
    success_rate = parallel_stats.get('success_rate', 0)
    parallel_status = "🟢 Good" if success_rate > 95 else "🟡 Fair" if success_rate > 90 else "🔴 Poor"
    perf_table.add_row("Parallel", "Success Rate", f"{success_rate:.1f}%", parallel_status)
    
    console.print(perf_table)
    
    if detailed:
        _show_detailed_metrics(cache_stats, template_stats, deployment_stats, 
                              memory_usage, parallel_stats, perf_summary)


@performance.command()
@click.option('--component', type=click.Choice(['cache', 'memory', 'templates', 'deployment', 'all']),
              default='all', help='Component to optimize')
@click.option('--aggressive', is_flag=True, help='Use aggressive optimization')
def optimize(component, aggressive):
    """Optimize performance components"""
    
    console.print("\\n[bold blue]⚡ Performance Optimization[/bold blue]\\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        
        if component in ['cache', 'all']:
            task = progress.add_task("Optimizing cache...", total=None)
            cache_manager = get_cache_manager()
            
            if aggressive:
                cache_manager.clear()
                console.print("  🗑️ Cleared all cache entries")
            else:
                # Just cleanup expired entries
                cache_manager._cleanup()
                console.print("  🧹 Cleaned up expired cache entries")
        
        if component in ['memory', 'all']:
            progress.update(task, description="Optimizing memory...")
            memory_optimizer = get_memory_optimizer()
            
            if aggressive:
                memory_optimizer.force_cleanup()
                console.print("  💾 Forced aggressive memory cleanup")
            else:
                memory_optimizer.optimize_memory()
                console.print("  🔄 Optimized memory usage")
        
        if component in ['templates', 'all']:
            progress.update(task, description="Optimizing template cache...")
            template_cache = get_template_cache()
            template_cache.optimize_memory()
            console.print("  📄 Optimized template cache")
        
        if component in ['deployment', 'all']:
            progress.update(task, description="Optimizing deployment settings...")
            deployment_optimizer = get_deployment_optimizer()
            deployment_optimizer.optimize_for_system()
            console.print("  🚀 Optimized deployment parallelism")
    
    console.print("\\n[green]✅ Performance optimization completed![/green]")


@performance.command()
@click.option('--suite', type=click.Choice(['quick', 'full', 'system']), 
              default='quick', help='Benchmark suite to run')
@click.option('--export', help='Export results to file')
def benchmark(suite, export):
    """Run performance benchmarks"""
    
    console.print(f"\\n[bold blue]🏃 Running {suite.title()} Benchmark Suite[/bold blue]\\n")
    
    benchmarks = get_performance_benchmarks()
    
    if suite == 'system':
        # Run comprehensive system benchmark
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Running system benchmarks...", total=5)
            
            results = benchmarks.run_system_benchmark()
            
            for i, (name, result) in enumerate(results.items()):
                progress.update(task, advance=1, description=f"Completed {name}")
        
        # Display results
        _display_benchmark_results(results)
        
        if export:
            benchmarks.export_benchmark_data(export)
            console.print(f"\\n[green]📁 Results exported to: {export}[/green]")
    
    elif suite == 'quick':
        # Quick benchmarks
        console.print("Running quick performance tests...")
        
        # Cache benchmark
        with benchmarks.benchmark('quick_cache_test', iterations=100) as ctx:
            cache_manager = get_cache_manager()
            for i in range(100):
                cache_manager.set(f'test_key_{i}', f'test_value_{i}')
                cache_manager.get(f'test_key_{i}')
        
        # Memory benchmark
        with benchmarks.benchmark('quick_memory_test', iterations=1000) as ctx:
            data = []
            for i in range(1000):
                data.append({'id': i, 'value': list(range(10))})
            data.clear()
        
        console.print("[green]✅ Quick benchmarks completed[/green]")
    
    elif suite == 'full':
        console.print("Running comprehensive benchmarks...")
        
        # Template loading benchmark
        from ..core.template_manager import TemplateManager
        
        with benchmarks.benchmark('template_manager_test', iterations=10) as ctx:
            template_manager = TemplateManager()
            for i in range(10):
                try:
                    templates = template_manager.list_templates()
                    for template in templates[:5]:  # Test first 5 templates
                        template_manager.template_exists(template)
                except Exception as e:
                    ctx.record_error()
        
        console.print("[green]✅ Full benchmarks completed[/green]")


@performance.command()
@click.option('--operation', help='Show trends for specific operation')
@click.option('--window', default=50, help='Window size for trend analysis')
def trends(operation, window):
    """Analyze performance trends"""
    
    console.print("\\n[bold blue]📈 Performance Trends Analysis[/bold blue]\\n")
    
    benchmarks = get_performance_benchmarks()
    
    if operation:
        # Analyze specific operation
        trend_data = benchmarks.analyze_performance_trends(operation, window)
        
        if trend_data['trend'] == 'insufficient_data':
            console.print(f"[yellow]Insufficient data for {operation} (need at least {window} samples)[/yellow]")
            return
        
        trend_color = {
            'improving': 'green',
            'stable': 'blue', 
            'degrading': 'red'
        }.get(trend_data['trend'], 'white')
        
        console.print(f"[bold]Operation:[/bold] {operation}")
        console.print(f"[bold]Trend:[/bold] [{trend_color}]{trend_data['trend'].title()}[/{trend_color}]")
        console.print(f"[bold]Performance Change:[/bold] {trend_data['performance_change_percent']:+.1f}%")
        console.print(f"[bold]Memory Change:[/bold] {trend_data['memory_change_percent']:+.1f}%")
        console.print(f"[bold]Sample Size:[/bold] {trend_data['sample_size']}")
    
    else:
        # Show trends for all operations
        profiles = benchmarks.get_all_profiles()
        
        if not profiles:
            console.print("[yellow]No performance profiles available[/yellow]")
            return
        
        trends_table = Table(title="Performance Trends", show_header=True, header_style="bold magenta")
        trends_table.add_column("Operation", style="cyan")
        trends_table.add_column("Trend", style="white")
        trends_table.add_column("Avg Duration", style="green")
        trends_table.add_column("Sample Count", style="blue")
        trends_table.add_column("Last Updated", style="yellow")
        
        for operation_name, profile in profiles.items():
            trend_data = benchmarks.analyze_performance_trends(operation_name, window)
            
            if trend_data['trend'] != 'insufficient_data':
                trend_display = {
                    'improving': '📈 Improving',
                    'stable': '➡️ Stable',
                    'degrading': '📉 Degrading'
                }.get(trend_data['trend'], '❓ Unknown')
            else:
                trend_display = '❓ Insufficient Data'
            
            last_updated = time.strftime('%H:%M:%S', time.localtime(profile.last_updated))
            
            trends_table.add_row(
                operation_name,
                trend_display,
                f"{profile.avg_duration:.3f}s",
                str(profile.sample_count),
                last_updated
            )
        
        console.print(trends_table)


@performance.command()
@click.option('--start-monitoring', is_flag=True, help='Start continuous monitoring')
@click.option('--stop-monitoring', is_flag=True, help='Stop continuous monitoring')
@click.option('--interval', default=60, help='Monitoring interval in seconds')
def monitor(start_monitoring, stop_monitoring, interval):
    """Control performance monitoring"""
    
    memory_optimizer = get_memory_optimizer()
    
    if start_monitoring:
        console.print(f"\\n[bold blue]📊 Starting Performance Monitoring[/bold blue]")
        console.print(f"Monitoring interval: {interval} seconds\\n")
        
        memory_optimizer.start_monitoring(interval)
        console.print("[green]✅ Performance monitoring started[/green]")
        console.print("[dim]Use 'blastdock performance monitor --stop-monitoring' to stop[/dim]")
    
    elif stop_monitoring:
        console.print("\\n[bold blue]⏹️ Stopping Performance Monitoring[/bold blue]\\n")
        
        memory_optimizer.stop_monitoring()
        console.print("[green]✅ Performance monitoring stopped[/green]")
    
    else:
        # Show current monitoring status
        metrics = memory_optimizer.get_performance_metrics()
        
        console.print("\\n[bold blue]📊 Performance Monitoring Status[/bold blue]\\n")
        
        status_table = Table(show_header=False)
        status_table.add_column("Setting", style="cyan")
        status_table.add_column("Value", style="white")
        
        status_table.add_row("Monitoring Enabled", "✅ Yes" if metrics['monitoring_enabled'] else "❌ No")
        status_table.add_row("Monitoring Interval", f"{metrics['monitoring_interval']}s")
        status_table.add_row("Snapshots Collected", str(metrics['snapshots_collected']))
        status_table.add_row("Cleanup Runs", str(metrics['cleanup_runs']))
        status_table.add_row("Objects Cleaned", str(metrics['objects_cleaned']))
        
        console.print(status_table)


@performance.command()
@click.option('--check-thresholds', is_flag=True, help='Check performance thresholds')
@click.option('--export-report', help='Export performance report to file')
def report(check_thresholds, export_report):
    """Generate performance report"""
    
    console.print("\\n[bold blue]📋 Performance Report[/bold blue]\\n")
    
    benchmarks = get_performance_benchmarks()
    
    if check_thresholds:
        threshold_results = benchmarks.check_performance_thresholds()
        
        if threshold_results['total_issues'] == 0:
            console.print("[green]✅ All performance metrics within acceptable thresholds[/green]")
        else:
            console.print(f"[yellow]⚠️ Found {threshold_results['total_issues']} performance issues[/yellow]\\n")
            
            # Show violations
            if threshold_results['violations']:
                console.print("[bold red]🚨 Threshold Violations:[/bold red]")
                for violation in threshold_results['violations']:
                    console.print(f"  • {violation['operation']}: {violation['type']} = {violation['value']:.1f} (threshold: {violation['threshold']})")
            
            # Show warnings
            if threshold_results['warnings']:
                console.print("\\n[bold yellow]⚠️ Performance Warnings:[/bold yellow]")
                for warning in threshold_results['warnings']:
                    console.print(f"  • {warning['operation']}: {warning['type']} = {warning['value']:.1f} (threshold: {warning['threshold']})")
    
    # Generate summary report
    summary = benchmarks.get_performance_summary()
    
    console.print("\\n[bold]📊 Performance Summary:[/bold]")
    console.print(f"  Total Benchmarks: {summary['total_benchmarks']}")
    console.print(f"  Operations Profiled: {summary['operations_profiled']}")
    console.print(f"  Cache Hit Rate: {summary['cache_hit_rate']:.1f}%")
    console.print(f"  Current Memory Usage: {summary['memory_usage_mb']:.1f}MB")
    console.print(f"  Recent Avg Duration: {summary['recent_avg_duration']:.3f}s")
    
    if export_report:
        # Export detailed report
        report_data = {
            'summary': summary,
            'timestamp': time.time(),
            'profiles': {name: prof.__dict__ for name, prof in benchmarks.get_all_profiles().items()}
        }
        
        if check_thresholds:
            report_data['threshold_check'] = threshold_results
        
        with open(export_report, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        console.print(f"\\n[green]📁 Report exported to: {export_report}[/green]")


def _show_detailed_metrics(cache_stats, template_stats, deployment_stats, 
                          memory_usage, parallel_stats, perf_summary):
    """Show detailed performance metrics"""
    
    console.print("\\n[bold]🔍 Detailed Metrics:[/bold]")
    
    # Cache details
    cache_panel_content = []
    cache_panel_content.append(f"Memory Entries: {cache_stats.get('memory_entries', 0)}")
    cache_panel_content.append(f"Disk Entries: {cache_stats.get('disk_entries', 0)}")
    cache_panel_content.append(f"Total Requests: {cache_stats.get('total_requests', 0)}")
    cache_panel_content.append(f"Memory Hits: {cache_stats.get('memory_hits', 0)}")
    cache_panel_content.append(f"Disk Hits: {cache_stats.get('disk_hits', 0)}")
    cache_panel_content.append(f"Evictions: {cache_stats.get('evictions', 0)}")
    
    console.print(Panel("\\n".join(cache_panel_content), title="Cache Statistics", border_style="blue"))
    
    # Memory details
    memory_panel_content = []
    memory_panel_content.append(f"RSS Memory: {memory_usage.get('rss_mb', 0):.1f}MB")
    memory_panel_content.append(f"Virtual Memory: {memory_usage.get('vms_mb', 0):.1f}MB")
    memory_panel_content.append(f"Python Objects: {memory_usage.get('python_objects', 0):,}")
    memory_panel_content.append(f"Tracked Objects: {memory_usage.get('tracked_objects', 0)}")
    memory_panel_content.append(f"Available Memory: {memory_usage.get('available_mb', 0):.1f}MB")
    
    console.print(Panel("\\n".join(memory_panel_content), title="Memory Statistics", border_style="green"))


def _display_benchmark_results(results):
    """Display benchmark results in a formatted table"""
    
    results_table = Table(title="Benchmark Results", show_header=True, header_style="bold magenta")
    results_table.add_column("Benchmark", style="cyan")
    results_table.add_column("Duration", style="green")
    results_table.add_column("Throughput", style="blue")
    results_table.add_column("Memory Usage", style="yellow")
    results_table.add_column("Status", style="white")
    
    for name, result in results.items():
        # Format duration
        if result.duration < 1:
            duration_str = f"{result.duration * 1000:.1f}ms"
        else:
            duration_str = f"{result.duration:.2f}s"
        
        # Format throughput
        if result.throughput:
            if result.throughput > 1000:
                throughput_str = f"{result.throughput / 1000:.1f}K/s"
            else:
                throughput_str = f"{result.throughput:.1f}/s"
        else:
            throughput_str = "N/A"
        
        # Format memory
        memory_str = f"{result.memory_usage_mb:.1f}MB"
        
        # Determine status
        if result.error_rate > 0.1:
            status = "🔴 Failed"
        elif result.duration > 10:
            status = "🟡 Slow"
        else:
            status = "🟢 Good"
        
        results_table.add_row(
            name.replace('_', ' ').title(),
            duration_str,
            throughput_str,
            memory_str,
            status
        )
    
    console.print(results_table)