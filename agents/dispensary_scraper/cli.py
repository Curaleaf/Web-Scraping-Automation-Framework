#!/usr/bin/env python3
"""Command-line interface for the Dispensary Scraper Agent."""

import asyncio
import sys
import click
from typing import List, Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
import json

try:
    # Try relative imports first (when run as module)
    from .agent import run_scraping_workflow, chat_with_scraper_agent
    from .dependencies import AgentDependencies
    from .settings import load_settings
except ImportError:
    # Fall back to absolute imports (when run directly)
    from agents.dispensary_scraper.agent import run_scraping_workflow, chat_with_scraper_agent
    from agents.dispensary_scraper.dependencies import AgentDependencies
    from agents.dispensary_scraper.settings import load_settings

console = Console()


def display_banner():
    """Display the application banner."""
    banner = Panel(
        "[bold blue]🏪 Dispensary Scraper Agent[/bold blue]\n\n"
        "[green]Automated web scraping for dispensary pricing data[/green]\n"
        "[dim]Powered by Playwright and PydanticAI[/dim]",
        style="blue",
        padding=(1, 2)
    )
    console.print(banner)
    console.print()


def display_categories():
    """Display available categories."""
    try:
        settings = load_settings()
        
        table = Table(title="Available Categories", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("URL Path", style="yellow")
        table.add_column("Output Prefix", style="green")
        
        for category in settings.categories:
            table.add_row(
                category["subcategory"],
                category["url"],
                category["prefix"]
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error loading categories: {e}[/red]")


def display_results_summary(result: dict):
    """Display scraping results in a formatted table."""
    if not result.get("success"):
        console.print(f"[red]❌ Scraping failed: {result.get('error_message', 'Unknown error')}[/red]")
        return
    
    # Main statistics
    stats_table = Table(title="Scraping Results", show_header=True, header_style="bold green")
    stats_table.add_column("Metric", style="cyan", no_wrap=True)
    stats_table.add_column("Value", style="yellow")
    
    stats_table.add_row("Products Scraped", str(result.get("products_scraped", 0)))
    stats_table.add_row("Categories Completed", str(result.get("categories_scraped", 0)))
    stats_table.add_row("Stores Processed", str(result.get("stores_scraped", 0)))
    
    duration_min = result.get("duration_seconds", 0) / 60
    stats_table.add_row("Duration", f"{duration_min:.1f} minutes")
    
    console.print(stats_table)
    
    # CSV files
    csv_files = result.get("csv_files_saved", [])
    if csv_files:
        console.print(f"\n[green]📄 CSV files saved ({len(csv_files)}):[/green]")
        for filepath in csv_files:
            console.print(f"  • {filepath}")
    
    # Snowflake uploads
    snowflake_results = result.get("snowflake_upload_results", {})
    if snowflake_results and not isinstance(snowflake_results, str):
        total_uploaded = sum(snowflake_results.values()) if isinstance(snowflake_results, dict) else 0
        console.print(f"\n[blue]❄️  Snowflake uploads: {total_uploaded} products[/blue]")
        if isinstance(snowflake_results, dict):
            for table, count in snowflake_results.items():
                console.print(f"  • {table}: {count} records")


@click.group()
@click.version_option()
def cli():
    """Dispensary Scraper Agent - Automated web scraping for dispensary pricing data."""
    pass


@cli.command()
@click.option("--categories", "-c", multiple=True, help="Categories to scrape (e.g., 'Whole Flower', 'Pre-Rolls')")
@click.option("--no-csv", is_flag=True, help="Skip CSV file generation")
@click.option("--no-snowflake", is_flag=True, help="Skip Snowflake upload")
@click.option("--dry-run", is_flag=True, help="Test configuration without scraping")
@click.option("--headless/--no-headless", default=True, help="Run browser in headless mode")
@click.option("--output", "-o", help="Output directory for CSV files")
def scrape(categories, no_csv, no_snowflake, dry_run, headless, output):
    """Run the dispensary scraping workflow."""
    
    display_banner()
    
    if dry_run:
        console.print("[yellow]🔍 Running in dry-run mode - testing configuration only[/yellow]\n")
    
    try:
        # Load settings and display info
        settings = load_settings()
        
        console.print("[cyan]Configuration:[/cyan]")
        console.print(f"  Base URL: {settings.base_url}")
        console.print(f"  Output Directory: {output or settings.output_directory}")
        console.print(f"  Headless Mode: {headless}")
        console.print(f"  CSV Export: {'No' if no_csv else 'Yes'}")
        console.print(f"  Snowflake Upload: {'No' if no_snowflake else 'Yes'}")
        console.print()
        
        # Show available categories if none specified
        if not categories:
            display_categories()
            
            if not dry_run:
                use_all = Confirm.ask("No categories specified. Scrape all categories?")
                if not use_all:
                    console.print("[yellow]Scraping cancelled[/yellow]")
                    return
        
        if dry_run:
            console.print("[green]✓ Configuration test passed[/green]")
            console.print("[dim]Use --no-dry-run to execute actual scraping[/dim]")
            return
        
        # Convert categories to list
        category_list = list(categories) if categories else None
        
        # Run scraping workflow
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Initializing scraper...", total=None)
            
            try:
                # Handle Windows async policy
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                
                # Run the workflow
                progress.update(task, description="Running scraping workflow...")
                
                async def run_with_progress():
                    return await run_scraping_workflow(
                        categories=category_list,
                        save_csv=not no_csv,
                        upload_snowflake=not no_snowflake
                    )
                
                result = asyncio.run(run_with_progress())
                
                progress.update(task, description="Processing results...", completed=True)
                
            except KeyboardInterrupt:
                progress.update(task, description="Cancelled by user", completed=True)
                console.print("\n[yellow]⚠️  Scraping cancelled by user[/yellow]")
                return
            except Exception as e:
                progress.update(task, description="Failed", completed=True)
                console.print(f"\n[red]❌ Error: {e}[/red]")
                return
        
        # Display results
        console.print()
        display_results_summary(result)
        
    except Exception as e:
        console.print(f"[red]❌ Configuration error: {e}[/red]")
        console.print("\n[dim]Make sure your .env file is properly configured.[/dim]")


@cli.command()
def categories():
    """List available scraping categories."""
    display_banner()
    display_categories()


@cli.command()
def test():
    """Test connections to external services."""
    display_banner()
    
    console.print("[cyan]Testing connections...[/cyan]\n")
    
    async def run_tests():
        deps = AgentDependencies()
        await deps.initialize()
        
        results = deps.test_connections()
        
        # Display results
        table = Table(title="Connection Tests", show_header=True, header_style="bold magenta")
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", style="yellow")
        table.add_column("Details", style="green")
        
        for service, status in results.items():
            status_icon = "✓" if status else "✗"
            status_color = "green" if status else "red"
            status_text = f"[{status_color}]{status_icon} {'Connected' if status else 'Failed'}[/{status_color}]"
            
            details = ""
            if service == "csv_storage":
                details = f"Directory: {deps.settings.output_directory}"
            elif service == "snowflake":
                details = f"Account: {deps.settings.snowflake_account}"
            
            table.add_row(service.replace("_", " ").title(), status_text, details)
        
        console.print(table)
        
        # Overall status
        all_healthy = all(results.values())
        overall_color = "green" if all_healthy else "red"
        overall_status = "All systems operational" if all_healthy else "Some connections failed"
        console.print(f"\n[{overall_color}]Overall Status: {overall_status}[/{overall_color}]")
        
        await deps.cleanup()
    
    try:
        asyncio.run(run_tests())
    except Exception as e:
        console.print(f"[red]❌ Test failed: {e}[/red]")


@cli.command()
@click.option("--limit", "-l", default=10, help="Number of recent files to show")
def status():
    """Show scraper status and recent files."""
    display_banner()
    
    try:
        settings = load_settings()
        
        # Show configuration
        console.print("[cyan]Current Configuration:[/cyan]")
        console.print(f"  Base URL: {settings.base_url}")
        console.print(f"  Output Directory: {settings.output_directory}")
        console.print(f"  Categories: {len(settings.categories)} configured")
        console.print(f"  Rate Limiting: {settings.scraping_delay_min}-{settings.scraping_delay_max}ms")
        console.print()
        
        # Show recent CSV files
        try:
            from .storage.csv_storage import CSVStorage
        except ImportError:
            from agents.dispensary_scraper.storage.csv_storage import CSVStorage
        csv_storage = CSVStorage(settings.output_directory)
        recent_files = csv_storage.list_csv_files()
        
        if recent_files:
            console.print(f"[green]📄 Recent CSV Files (showing {min(len(recent_files), limit)}):[/green]")
            
            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("File", style="yellow")
            table.add_column("Size", style="green")
            table.add_column("Modified", style="blue")
            
            for filepath in recent_files[:limit]:
                try:
                    stat = filepath.stat()
                    size_kb = stat.st_size / 1024
                    modified = stat.st_mtime
                    import datetime
                    mod_time = datetime.datetime.fromtimestamp(modified).strftime("%Y-%m-%d %H:%M")
                    
                    table.add_row(filepath.name, f"{size_kb:.1f} KB", mod_time)
                except Exception:
                    table.add_row(filepath.name, "Unknown", "Unknown")
            
            console.print(table)
        else:
            console.print("[dim]No CSV files found in output directory[/dim]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")


@cli.command()
def chat():
    """Start an interactive chat session with the scraper agent."""
    display_banner()
    
    console.print("[green]🤖 Starting interactive chat with Dispensary Scraper Agent[/green]")
    console.print("[dim]Type 'exit' to quit, 'help' for commands[/dim]\n")
    
    async def chat_session():
        deps = AgentDependencies()
        await deps.initialize()
        
        console.print("[green]✓ Agent initialized[/green]\n")
        
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]You")
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    console.print("\n[yellow]👋 Goodbye![/yellow]")
                    break
                
                if user_input.lower() == 'help':
                    console.print(Panel("""
[bold]Available Commands:[/bold]

• [cyan]categories[/cyan] - Show available scraping categories
• [cyan]test[/cyan] - Test connections to external services  
• [cyan]scrape whole flower[/cyan] - Example scraping request
• [cyan]status[/cyan] - Show current configuration and recent files
• [cyan]exit/quit[/cyan] - Exit the chat session

[bold]Example Requests:[/bold]
• "Can you scrape the Whole Flower category?"
• "Test my Snowflake connection"
• "Show me the results of the last scraping"
• "What categories are available?"
                    """, title="Help", border_style="cyan"))
                    continue
                
                if not user_input.strip():
                    continue
                
                # Get response from agent
                console.print(f"[bold blue]Agent:[/bold blue] ", end="")
                
                with console.status("[dim]Thinking...[/dim]"):
                    response = await chat_with_scraper_agent(user_input, context=deps)
                
                console.print(response)
                console.print()
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
                continue
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                continue
        
        await deps.cleanup()
    
    try:
        asyncio.run(chat_session())
    except KeyboardInterrupt:
        console.print("\n[yellow]Chat session ended[/yellow]")


if __name__ == "__main__":
    cli()