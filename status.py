# status.py (The Live Dashboard)
import sqlite3
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from datetime import datetime, timedelta
import time

DB_PATH = 'progress.db'
logging.basicConfig(level=logging.WARNING) # Keep logging quiet for this script

def get_db_data():
    """Fetches all necessary data from the database for the dashboard."""
    try:
        # Use read-only mode for safety
        with sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True) as conn:
            cursor = conn.cursor()
            
            # 1. Overall Summary
            cursor.execute("SELECT status, COUNT(*) FROM problems GROUP BY status")
            summary = cursor.fetchall()
            
            # 2. Live Worker Status
            cursor.execute("SELECT worker_id, problem_id, stage, status, last_heartbeat FROM live_workers ORDER BY worker_id")
            workers = cursor.fetchall()
            
            # 3. Problems needing attention (failed or stuck in_progress)
            stuck_threshold = (datetime.now() - timedelta(minutes=15)).isoformat()
            cursor.execute("""
                SELECT id, name, rating, status, retry_count, notes 
                FROM problems 
                WHERE status = 'failed' OR (status = 'in_progress' AND last_updated < ?)
                ORDER BY last_updated DESC LIMIT 10
            """, (stuck_threshold,))
            issues = cursor.fetchall()
            
            return summary, workers, issues
            
    except sqlite3.Error as e:
        return None, None, f"Database error: {e}"

def generate_layout() -> Layout:
    """Defines the overall layout for the dashboard."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=5, name="footer")
    )
    layout["main"].split_row(Layout(name="summary"), Layout(name="details"))
    layout["details"].split(Layout(name="workers"), Layout(name="issues"))
    return layout

def generate_summary_panel(summary_data) -> Panel:
    table = Table(show_header=True, header_style="bold magenta", box=None)
    table.add_column("Status", style="dim")
    table.add_column("Count", justify="right")

    status_map = {"completed": "✅ Completed", "pending": "⏳ Pending", "failed": "🔥 Failed", "in_progress": "⚙️ In Progress"}
    status_colors = {"completed": "green", "pending": "yellow", "failed": "red", "in_progress": "blue"}
    
    total = 0
    data_dict = dict(summary_data)
    for status, display in status_map.items():
        count = data_dict.get(status, 0)
        color = status_colors.get(status, "white")
        table.add_row(f"[{color}]{display}[/{color}]", f"{count:,}")
        total += count
    
    table.add_row("[bold]📊 Total Problems[/bold]", f"[bold]{total:,}[/bold]")
    return Panel(table, title="[bold cyan]Database Status[/bold cyan]", border_style="cyan")

def generate_workers_panel(workers_data) -> Panel:
    table = Table(show_header=True, header_style="bold blue", box=None)
    table.add_column("ID", justify="center")
    table.add_column("Problem ID")
    table.add_column("Current Stage")
    
    stage_emojis = {"INITIALIZING": "🚀", "SCRAPING": "🔍", "SAVING": "💾", "ARL_ANALYST": "🧠", "ARL_IMPLEMENTER": "✍️", "VJS_VERIFYING": "⚖️"}

    for wid, pid, stage, status, _ in workers_data:
        if status == 'idle':
            table.add_row(f"[dim]{wid}[/dim]", "[dim]-- idle --[/dim]", "[dim]----------------[/dim]")
        else:
            emoji = stage_emojis.get(stage, "⚙️")
            table.add_row(f"[bold blue]{wid}[/bold blue]", f"[cyan]{pid}[/cyan]", f"{emoji} {stage}")
            
    return Panel(table, title="[bold blue]Live Worker Activity[/bold blue]", border_style="blue")

def generate_issues_panel(issues_data) -> Panel:
    table = Table(show_header=True, header_style="bold red", box=None)
    table.add_column("ID")
    table.add_column("Rating")
    table.add_column("Status")
    table.add_column("Retries")
    table.add_column("Notes")

    for pid, _, rating, status, retries, notes in issues_data:
        table.add_row(f"[cyan]{pid}[/cyan]", str(rating), f"[yellow]{status}[/yellow]", f"[red]{retries}[/red]", f"[dim]{(notes or '')[:50]}[/dim]")
        
    return Panel(table, title="[bold red]Attention Required (Failed & Stuck)[/bold red]", border_style="red")

def main():
    console = Console()
    layout = generate_layout()
    
    try:
        with Live(layout, console=console, screen=True, redirect_stderr=False) as live:
            while True:
                summary, workers, issues = get_db_data()
                
                if summary is None:
                    console.print(f"[bold red]Error:[/bold red] Could not connect to or read '{DB_PATH}'. Please run `create_database.py` first.")
                    break

                layout["header"].update(Align.center(f"[bold]Project Synapse Dashboard[/bold]\nLast Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", vertical="middle"))
                layout["summary"].update(generate_summary_panel(summary))
                layout["workers"].update(generate_workers_panel(workers))
                layout["issues"].update(generate_issues_panel(issues))
                layout["footer"].update(Align.center("[dim]Watching for changes... (Press Ctrl+C to exit)[/dim]"))
                
                time.sleep(2) # Refresh rate
    except KeyboardInterrupt:
        print("\nExiting status monitor.")
    except Exception as e:
        logging.critical(f"Dashboard crashed: {e}")

if __name__ == "__main__":
    main()