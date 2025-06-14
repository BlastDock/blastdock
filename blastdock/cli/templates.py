"""
CLI commands for template management and validation
"""

import click
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from ..utils.template_validator import TemplateValidator, ValidationLevel, TraefikCompatibility


console = Console()


@click.group()
def templates():
    """Template management and validation commands"""
    pass


@templates.command()
@click.option('--templates-dir', '-d', help='Templates directory path')
@click.option('--output', '-o', type=click.Choice(['table', 'detailed', 'json']), default='table', help='Output format')
@click.option('--filter', '-f', type=click.Choice(['all', 'errors', 'warnings', 'no-traefik']), default='all', help='Filter results')
@click.option('--save-report', help='Save detailed report to file')
def validate(templates_dir, output, filter, save_report):
    """Validate all templates for structure, security, and Traefik compatibility"""
    
    if templates_dir:
        validator = TemplateValidator(templates_dir)
    else:
        validator = TemplateValidator()
    
    console.print("\n[bold blue]🔍 Validating BlastDock Templates[/bold blue]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Validating templates...", total=100)
        
        # Get list of templates
        template_files = list(validator.templates_dir.glob('*.yml'))
        total_templates = len(template_files)
        
        if total_templates == 0:
            console.print("[red]❌ No template files found[/red]")
            return
        
        progress.update(task, total=total_templates)
        
        # Validate all templates
        analyses = {}
        for i, template_file in enumerate(template_files):
            template_name = template_file.stem
            progress.update(task, description=f"Validating {template_name}...", completed=i)
            
            analysis = validator.validate_template(str(template_file))
            analyses[template_name] = analysis
        
        progress.update(task, completed=total_templates, description="Validation complete!")
    
    # Filter results
    filtered_analyses = _filter_analyses(analyses, filter)
    
    # Display results
    if output == 'table':
        _display_table_output(filtered_analyses)
    elif output == 'detailed':
        _display_detailed_output(filtered_analyses)
    elif output == 'json':
        _display_json_output(filtered_analyses)
    
    # Generate and save report if requested
    if save_report:
        report = validator.generate_validation_report(analyses)
        Path(save_report).write_text(report)
        console.print(f"\n[green]📄 Detailed report saved to: {save_report}[/green]")
    
    # Summary
    _display_summary(analyses)


@templates.command()
@click.argument('template_name')
@click.option('--templates-dir', '-d', help='Templates directory path')
def analyze(template_name, templates_dir):
    """Analyze a specific template in detail"""
    
    if templates_dir:
        validator = TemplateValidator(templates_dir)
    else:
        validator = TemplateValidator()
    
    template_path = validator.templates_dir / f"{template_name}.yml"
    
    if not template_path.exists():
        console.print(f"[red]❌ Template '{template_name}' not found[/red]")
        return
    
    console.print(f"\n[bold blue]🔍 Analyzing Template: {template_name}[/bold blue]\n")
    
    with console.status("[bold green]Analyzing template..."):
        analysis = validator.validate_template(str(template_path))
    
    # Display detailed analysis
    _display_template_analysis(analysis)


@templates.command()
@click.option('--templates-dir', '-d', help='Templates directory path')
@click.option('--filter', '-f', type=click.Choice(['none', 'basic', 'partial']), default='none', help='Filter by Traefik compatibility')
@click.option('--dry-run', is_flag=True, help='Show what would be enhanced without making changes')
@click.option('--backup', is_flag=True, help='Create backup before enhancing')
def enhance(templates_dir, filter, dry_run, backup):
    """Enhance templates with Traefik support"""
    
    if templates_dir:
        validator = TemplateValidator(templates_dir)
    else:
        validator = TemplateValidator()
    
    console.print("\n[bold blue]🚀 Enhancing Templates with Traefik Support[/bold blue]\n")
    
    # First validate to find templates needing enhancement
    with console.status("[bold green]Scanning templates..."):
        analyses = validator.validate_all_templates()
    
    # Filter templates that need enhancement
    to_enhance = []
    for name, analysis in analyses.items():
        if filter == 'none' and analysis.traefik_compatibility == TraefikCompatibility.NONE:
            to_enhance.append((name, analysis))
        elif filter == 'basic' and analysis.traefik_compatibility == TraefikCompatibility.BASIC:
            to_enhance.append((name, analysis))
        elif filter == 'partial' and analysis.traefik_compatibility == TraefikCompatibility.PARTIAL:
            to_enhance.append((name, analysis))
    
    if not to_enhance:
        console.print(f"[green]✅ No templates need enhancement for filter: {filter}[/green]")
        return
    
    console.print(f"[yellow]📋 Found {len(to_enhance)} templates to enhance[/yellow]\n")
    
    # Show what will be enhanced
    table = Table(title="Templates to Enhance")
    table.add_column("Template", style="cyan")
    table.add_column("Current Support", style="yellow")
    table.add_column("Score", style="magenta")
    table.add_column("Issues", style="red")
    
    for name, analysis in to_enhance:
        issues = f"{analysis.error_count}E, {analysis.warning_count}W"
        table.add_row(
            name,
            analysis.traefik_compatibility.value,
            f"{analysis.score}/100",
            issues
        )
    
    console.print(table)
    
    if dry_run:
        console.print("\n[blue]ℹ️  Dry run mode - no changes will be made[/blue]")
        return
    
    # Confirm enhancement
    if not click.confirm(f"\nEnhance {len(to_enhance)} templates?"):
        console.print("[yellow]❌ Enhancement cancelled[/yellow]")
        return
    
    # Enhance templates
    enhanced_count = 0
    failed_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        
        task = progress.add_task("Enhancing templates...", total=len(to_enhance))
        
        for i, (name, analysis) in enumerate(to_enhance):
            progress.update(task, description=f"Enhancing {name}...", completed=i)
            
            template_path = validator.templates_dir / f"{name}.yml"
            
            # Create backup if requested
            if backup:
                backup_path = template_path.with_suffix('.yml.backup')
                backup_path.write_text(template_path.read_text())
            
            # Enhance template
            success, message = validator.enhance_template_traefik_support(str(template_path))
            
            if success:
                enhanced_count += 1
            else:
                failed_count += 1
                console.print(f"[red]❌ Failed to enhance {name}: {message}[/red]")
        
        progress.update(task, completed=len(to_enhance), description="Enhancement complete!")
    
    console.print(f"\n[green]✅ Enhanced {enhanced_count} templates[/green]")
    if failed_count > 0:
        console.print(f"[red]❌ Failed to enhance {failed_count} templates[/red]")


@templates.command()
@click.option('--templates-dir', '-d', help='Templates directory path')
@click.option('--output', '-o', type=click.Choice(['table', 'json']), default='table', help='Output format')
def list(templates_dir, output):
    """List all available templates with basic info"""
    
    if templates_dir:
        validator = TemplateValidator(templates_dir)
    else:
        validator = TemplateValidator()
    
    template_files = list(validator.templates_dir.glob('*.yml'))
    
    if not template_files:
        console.print("[red]❌ No template files found[/red]")
        return
    
    console.print(f"\n[bold blue]📋 BlastDock Templates ({len(template_files)} found)[/bold blue]\n")
    
    if output == 'table':
        table = Table(title="Available Templates")
        table.add_column("Template", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Version", style="green")
        table.add_column("Traefik", style="yellow")
        table.add_column("Services", style="blue")
        
        for template_file in sorted(template_files):
            try:
                import yaml
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)
                
                template_info = template_data.get('template_info', {})
                name = template_file.stem
                description = template_info.get('description', 'No description')[:50]
                version = template_info.get('version', 'Unknown')
                traefik = '✅' if template_info.get('traefik_compatible') else '❌'
                services = ', '.join(template_info.get('services', []))[:30]
                
                table.add_row(name, description, version, traefik, services)
                
            except Exception:
                table.add_row(template_file.stem, "Error loading template", "-", "-", "-")
        
        console.print(table)
    
    elif output == 'json':
        import json
        templates_data = []
        
        for template_file in sorted(template_files):
            try:
                import yaml
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)
                
                templates_data.append({
                    'name': template_file.stem,
                    'info': template_data.get('template_info', {})
                })
                
            except Exception as e:
                templates_data.append({
                    'name': template_file.stem,
                    'error': str(e)
                })
        
        console.print(json.dumps(templates_data, indent=2))


def _filter_analyses(analyses, filter_type):
    """Filter analyses based on criteria"""
    if filter_type == 'all':
        return analyses
    elif filter_type == 'errors':
        return {k: v for k, v in analyses.items() if v.error_count > 0}
    elif filter_type == 'warnings':
        return {k: v for k, v in analyses.items() if v.warning_count > 0}
    elif filter_type == 'no-traefik':
        return {k: v for k, v in analyses.items() if v.traefik_compatibility == TraefikCompatibility.NONE}
    return analyses


def _display_table_output(analyses):
    """Display results in table format"""
    table = Table(title="Template Validation Results")
    table.add_column("Template", style="cyan")
    table.add_column("Valid", style="green")
    table.add_column("Score", style="magenta")
    table.add_column("Errors", style="red")
    table.add_column("Warnings", style="yellow")
    table.add_column("Traefik", style="blue")
    
    for name, analysis in sorted(analyses.items()):
        valid_icon = "✅" if analysis.is_valid else "❌"
        traefik_icon = {
            TraefikCompatibility.FULL: "🟢 Full",
            TraefikCompatibility.PARTIAL: "🟡 Partial", 
            TraefikCompatibility.BASIC: "🟠 Basic",
            TraefikCompatibility.NONE: "🔴 None"
        }[analysis.traefik_compatibility]
        
        table.add_row(
            name,
            valid_icon,
            f"{analysis.score}/100",
            str(analysis.error_count),
            str(analysis.warning_count),
            traefik_icon
        )
    
    console.print(table)


def _display_detailed_output(analyses):
    """Display detailed validation results"""
    for name, analysis in sorted(analyses.items()):
        console.print(f"\n[bold cyan]📄 {name}[/bold cyan]")
        console.print(f"Score: {analysis.score}/100")
        console.print(f"Traefik: {analysis.traefik_compatibility.value}")
        
        if analysis.results:
            for result in analysis.results[:5]:  # Show first 5 results
                level_icon = {
                    ValidationLevel.ERROR: "❌",
                    ValidationLevel.WARNING: "⚠️",
                    ValidationLevel.INFO: "ℹ️",
                    ValidationLevel.SUCCESS: "✅"
                }[result.level]
                
                console.print(f"  {level_icon} [{result.category}] {result.message}")
                if result.suggestion:
                    console.print(f"    💡 {result.suggestion}")


def _display_json_output(analyses):
    """Display results in JSON format"""
    import json
    
    output_data = {}
    for name, analysis in analyses.items():
        output_data[name] = {
            'valid': analysis.is_valid,
            'score': analysis.score,
            'traefik_compatibility': analysis.traefik_compatibility.value,
            'error_count': analysis.error_count,
            'warning_count': analysis.warning_count,
            'results': [
                {
                    'level': r.level.value,
                    'category': r.category,
                    'message': r.message,
                    'suggestion': r.suggestion
                }
                for r in analysis.results
            ]
        }
    
    console.print(json.dumps(output_data, indent=2))


def _display_template_analysis(analysis):
    """Display detailed analysis for a single template"""
    # Header
    status_icon = "✅" if analysis.is_valid else "❌"
    console.print(Panel(
        f"[bold]{analysis.template_name}[/bold]\n"
        f"Status: {status_icon} {'Valid' if analysis.is_valid else 'Invalid'}\n"
        f"Quality Score: {analysis.score}/100\n"
        f"Traefik Support: {analysis.traefik_compatibility.value}\n"
        f"Issues: {analysis.error_count} errors, {analysis.warning_count} warnings",
        title="Template Analysis",
        title_align="left"
    ))
    
    # Group results by category
    results_by_category = {}
    for result in analysis.results:
        category = result.category
        if category not in results_by_category:
            results_by_category[category] = []
        results_by_category[category].append(result)
    
    # Display results by category
    for category, results in results_by_category.items():
        console.print(f"\n[bold blue]📋 {category.title()}[/bold blue]")
        
        for result in results:
            level_icon = {
                ValidationLevel.ERROR: "❌",
                ValidationLevel.WARNING: "⚠️",
                ValidationLevel.INFO: "ℹ️",
                ValidationLevel.SUCCESS: "✅"
            }[result.level]
            
            level_color = {
                ValidationLevel.ERROR: "red",
                ValidationLevel.WARNING: "yellow",
                ValidationLevel.INFO: "blue",
                ValidationLevel.SUCCESS: "green"
            }[result.level]
            
            console.print(f"  {level_icon} [{level_color}]{result.message}[/{level_color}]")
            if result.suggestion:
                console.print(f"    [dim]💡 {result.suggestion}[/dim]")


def _display_summary(analyses):
    """Display validation summary"""
    total = len(analyses)
    valid = sum(1 for a in analyses.values() if a.is_valid)
    avg_score = sum(a.score for a in analyses.values()) / total if total > 0 else 0
    
    traefik_counts = {
        TraefikCompatibility.FULL: 0,
        TraefikCompatibility.PARTIAL: 0,
        TraefikCompatibility.BASIC: 0,
        TraefikCompatibility.NONE: 0
    }
    
    for analysis in analyses.values():
        traefik_counts[analysis.traefik_compatibility] += 1
    
    console.print(Panel(
        f"[bold green]📊 Validation Summary[/bold green]\n\n"
        f"Templates: {total}\n"
        f"Valid: {valid} ({valid/total*100:.1f}%)\n"
        f"Average Score: {avg_score:.1f}/100\n\n"
        f"[bold blue]Traefik Support:[/bold blue]\n"
        f"🟢 Full: {traefik_counts[TraefikCompatibility.FULL]}\n"
        f"🟡 Partial: {traefik_counts[TraefikCompatibility.PARTIAL]}\n"
        f"🟠 Basic: {traefik_counts[TraefikCompatibility.BASIC]}\n"
        f"🔴 None: {traefik_counts[TraefikCompatibility.NONE]}",
        title="Summary",
        title_align="left"
    ))