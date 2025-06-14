"""
Marketplace CLI commands for BlastDock
Browse, search, and install templates from the marketplace
"""

import sys
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from ..marketplace import TemplateMarketplace, TemplateRepository, TemplateInstaller
from ..marketplace.marketplace import TemplateCategory
from ..utils.logging import get_logger

logger = get_logger(__name__)
console = Console()


@click.group(name='marketplace')
def marketplace():
    """Template marketplace commands"""
    pass


@marketplace.command('search')
@click.argument('query', required=False, default="")
@click.option('--category', '-c', type=click.Choice([c.value for c in TemplateCategory]), 
              help='Filter by category')
@click.option('--tag', '-t', multiple=True, help='Filter by tags')
@click.option('--traefik', is_flag=True, help='Only show Traefik-compatible templates')
@click.option('--source', type=click.Choice(['official', 'community', 'all']), 
              default='all', help='Filter by source')
@click.option('--limit', '-n', default=20, help='Maximum results to show')
def search_templates(query: str, category: Optional[str], tag: tuple, 
                    traefik: bool, source: str, limit: int):
    """Search for templates in the marketplace"""
    try:
        mp = TemplateMarketplace()
        
        # Convert category string to enum
        category_enum = None
        if category:
            category_enum = TemplateCategory(category)
        
        # Convert source filter
        source_filter = None if source == 'all' else source
        
        # Search templates
        results = mp.search(
            query=query,
            category=category_enum,
            tags=list(tag),
            traefik_only=traefik,
            source=source_filter
        )
        
        if not results:
            console.print("[yellow]No templates found matching your criteria[/yellow]")
            return
        
        # Show results
        console.print(f"\n[bold cyan]Found {len(results)} templates:[/bold cyan]\n")
        
        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan", width=25)
        table.add_column("Name", style="green")
        table.add_column("Category", style="yellow")
        table.add_column("Rating", justify="center")
        table.add_column("Downloads", justify="right")
        table.add_column("Traefik", justify="center")
        
        for template in results[:limit]:
            rating_stars = "⭐" * int(template.rating)
            traefik_icon = "✅" if template.traefik_compatible else "❌"
            
            table.add_row(
                template.id,
                template.display_name,
                template.category.value,
                f"{rating_stars} {template.rating:.1f}",
                str(template.downloads),
                traefik_icon
            )
        
        console.print(table)
        
        if len(results) > limit:
            console.print(f"\n[dim]Showing {limit} of {len(results)} results. Use --limit to see more.[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error searching marketplace: {e}[/red]")
        logger.exception("Marketplace search failed")
        sys.exit(1)


@marketplace.command('info')
@click.argument('template_id')
def template_info(template_id: str):
    """Show detailed information about a template"""
    try:
        mp = TemplateMarketplace()
        template = mp.get_template(template_id)
        
        if not template:
            console.print(f"[red]Template '{template_id}' not found[/red]")
            return
        
        # Create info panel
        info_content = f"""[bold]{template.display_name}[/bold]
{template.description}

[bold]Details:[/bold]
• Version: {template.version}
• Author: {template.author}
• Category: {template.category.value}
• Source: {template.source}

[bold]Metrics:[/bold]
• Rating: {"⭐" * int(template.rating)} {template.rating:.1f}/5.0
• Downloads: {template.downloads:,}
• Stars: {template.stars}

[bold]Technical:[/bold]
• Services: {', '.join(template.services)}
• Traefik: {"✅ Compatible" if template.traefik_compatible else "❌ Not compatible"}
• Validation Score: {template.validation_score}/100
• Security Score: {template.security_score}/100

[bold]Tags:[/bold]
{', '.join(f"[cyan]{tag}[/cyan]" for tag in template.tags)}"""
        
        if template.repository_url:
            info_content += f"\n\n[bold]Repository:[/bold] {template.repository_url}"
        
        if template.documentation_url:
            info_content += f"\n[bold]Documentation:[/bold] {template.documentation_url}"
        
        panel = Panel(info_content, title=f"Template: {template_id}", border_style="cyan")
        console.print(panel)
        
        # Show install command
        console.print(f"\n[dim]To install: blastdock marketplace install {template_id}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error getting template info: {e}[/red]")
        logger.exception("Template info failed")
        sys.exit(1)


@marketplace.command('featured')
@click.option('--limit', '-n', default=10, help='Number of templates to show')
def show_featured(limit: int):
    """Show featured/popular templates"""
    try:
        mp = TemplateMarketplace()
        featured = mp.get_featured_templates(limit)
        
        console.print("\n[bold cyan]🌟 Featured Templates[/bold cyan]\n")
        
        for i, template in enumerate(featured, 1):
            # Create template card
            card_content = f"""[bold green]{template.display_name}[/bold green]
{template.description[:80]}...

Rating: {"⭐" * int(template.rating)} {template.rating:.1f}
Downloads: {template.downloads:,} | Category: {template.category.value}
ID: [cyan]{template.id}[/cyan]"""
            
            card = Panel(card_content, width=40, box=box.ROUNDED)
            
            if i % 2 == 1:
                # Start a new row
                if i > 1:
                    console.print(columns)
                columns = [card]
            else:
                # Add to current row
                columns.append(card)
                console.print(Columns(columns, equal=True, expand=True))
        
        # Print last row if odd number
        if len(featured) % 2 == 1:
            console.print(columns[0])
        
    except Exception as e:
        console.print(f"[red]Error showing featured templates: {e}[/red]")
        logger.exception("Featured templates failed")
        sys.exit(1)


@marketplace.command('categories')
def show_categories():
    """Show available template categories"""
    try:
        mp = TemplateMarketplace()
        categories = mp.get_categories()
        
        console.print("\n[bold cyan]Template Categories[/bold cyan]\n")
        
        table = Table(box=box.SIMPLE)
        table.add_column("Category", style="yellow", width=20)
        table.add_column("Templates", justify="right")
        table.add_column("Description")
        
        category_descriptions = {
            TemplateCategory.WEB: "Web servers and applications",
            TemplateCategory.DATABASE: "Database systems",
            TemplateCategory.CMS: "Content Management Systems",
            TemplateCategory.ECOMMERCE: "E-commerce platforms",
            TemplateCategory.DEVELOPMENT: "Development tools and environments",
            TemplateCategory.MONITORING: "Monitoring and observability",
            TemplateCategory.ANALYTICS: "Analytics and data platforms",
            TemplateCategory.COMMUNICATION: "Chat and communication tools",
            TemplateCategory.PRODUCTIVITY: "Productivity and collaboration",
            TemplateCategory.MEDIA: "Media servers and streaming",
            TemplateCategory.SECURITY: "Security tools",
            TemplateCategory.INFRASTRUCTURE: "Infrastructure services"
        }
        
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            table.add_row(
                category.value,
                str(count),
                category_descriptions.get(category, "")
            )
        
        console.print(table)
        
        # Show marketplace stats
        stats = mp.get_stats()
        console.print(f"\n[dim]Total templates: {stats['total_templates']} | "
                     f"Total downloads: {stats['total_downloads']:,} | "
                     f"Traefik compatible: {stats['traefik_compatible']}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error showing categories: {e}[/red]")
        logger.exception("Categories display failed")
        sys.exit(1)


@marketplace.command('install')
@click.argument('template_id')
@click.option('--version', '-v', default='latest', help='Template version to install')
@click.option('--force', '-f', is_flag=True, help='Force reinstall if already installed')
def install_template(template_id: str, version: str, force: bool):
    """Install a template from the marketplace"""
    try:
        installer = TemplateInstaller()
        
        console.print(f"[cyan]Installing template '{template_id}'...[/cyan]")
        
        result = installer.install_template(template_id, version, force)
        
        if result['success']:
            console.print(f"\n[bold green]✅ Successfully installed '{result['template_name']}'![/bold green]")
            console.print(f"Version: {result['version']}")
            console.print(f"Path: {result['path']}")
            console.print(f"Validation score: {result['validation_score']}/100")
            
            if result['traefik_compatible']:
                console.print("[green]✅ Traefik compatible[/green]")
            
            if result.get('additional_files'):
                console.print(f"\nAdditional files installed:")
                for file_path in result['additional_files']:
                    console.print(f"  • {file_path}")
            
            console.print(f"\n[dim]Deploy with: blastdock deploy create my-{result['template_name']} "
                         f"--template {result['template_name']}[/dim]")
        else:
            console.print(f"\n[bold red]❌ Installation failed[/bold red]")
            console.print(f"Error: {result['error']}")
            
            if 'validation_errors' in result:
                console.print("\nValidation errors:")
                for error in result['validation_errors']:
                    console.print(f"  • {error}")
        
    except Exception as e:
        console.print(f"[red]Error installing template: {e}[/red]")
        logger.exception("Template installation failed")
        sys.exit(1)


@marketplace.command('list')
@click.option('--installed', is_flag=True, help='Show only installed templates')
def list_templates(installed: bool):
    """List templates (all or installed only)"""
    try:
        if installed:
            installer = TemplateInstaller()
            templates = installer.list_installed_templates()
            
            if not templates:
                console.print("[yellow]No templates installed yet[/yellow]")
                console.print("\n[dim]Install templates with: blastdock marketplace install <template-id>[/dim]")
                return
            
            console.print("\n[bold cyan]Installed Templates[/bold cyan]\n")
            
            table = Table(box=box.ROUNDED)
            table.add_column("Name", style="green")
            table.add_column("Template ID", style="cyan")
            table.add_column("Version")
            table.add_column("Source")
            table.add_column("Score", justify="center")
            table.add_column("Traefik", justify="center")
            
            for template in templates:
                traefik_icon = "✅" if template['traefik_compatible'] else "❌"
                
                table.add_row(
                    template['name'],
                    template['template_id'],
                    template['version'],
                    template['source'],
                    f"{template['validation_score']}/100",
                    traefik_icon
                )
            
            console.print(table)
            
        else:
            # Show all marketplace templates
            mp = TemplateMarketplace()
            results = mp.search()  # Get all
            
            console.print(f"\n[bold cyan]All Marketplace Templates ({len(results)})[/bold cyan]\n")
            
            # Group by category
            by_category = {}
            for template in results:
                if template.category not in by_category:
                    by_category[template.category] = []
                by_category[template.category].append(template)
            
            for category, templates in sorted(by_category.items()):
                console.print(f"\n[bold yellow]{category.value.upper()}[/bold yellow]")
                
                for template in sorted(templates, key=lambda t: t.downloads, reverse=True)[:5]:
                    console.print(f"  • [cyan]{template.id}[/cyan] - {template.display_name} "
                                 f"(⭐{template.rating:.1f}, {template.downloads} downloads)")
            
            console.print(f"\n[dim]Use 'blastdock marketplace search' for detailed search[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error listing templates: {e}[/red]")
        logger.exception("Template listing failed")
        sys.exit(1)


@marketplace.command('uninstall')
@click.argument('template_name')
@click.confirmation_option(prompt='Are you sure you want to uninstall this template?')
def uninstall_template(template_name: str):
    """Uninstall an installed template"""
    try:
        installer = TemplateInstaller()
        
        result = installer.uninstall_template(template_name)
        
        if result['success']:
            console.print(f"[green]✅ Successfully uninstalled '{template_name}'[/green]")
        else:
            console.print(f"[red]❌ Failed to uninstall: {result['error']}[/red]")
        
    except Exception as e:
        console.print(f"[red]Error uninstalling template: {e}[/red]")
        logger.exception("Template uninstallation failed")
        sys.exit(1)


@marketplace.command('update')
@click.argument('template_name')
def update_template(template_name: str):
    """Update an installed template to the latest version"""
    try:
        installer = TemplateInstaller()
        
        console.print(f"[cyan]Checking for updates to '{template_name}'...[/cyan]")
        
        result = installer.update_template(template_name)
        
        if result['success']:
            console.print(f"[green]✅ Successfully updated '{template_name}' to v{result['version']}[/green]")
        else:
            console.print(f"[yellow]{result['error']}[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error updating template: {e}[/red]")
        logger.exception("Template update failed")
        sys.exit(1)


# Export the group for main CLI
marketplace_group = marketplace