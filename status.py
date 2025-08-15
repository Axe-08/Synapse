# status.py (The Complete Live Dashboard)
import sqlite3
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.columns import Columns
from datetime import datetime, timedelta
import time
import os

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
            cursor.execute("SELECT worker_id, pool, problem_id, stage, status FROM live_workers ORDER BY worker_id")
            workers = cursor.fetchall()

            # 3. API Key Status
            cursor.execute("SELECT key_fingerprint, service, status, cooldown_until FROM key_status ORDER BY service, key_fingerprint")
            keys = cursor.fetchall()
            
            # 4. Problems needing attention (failed or stuck in_progress)
            stuck_threshold = (datetime.now() - timedelta(minutes=15)).isoformat()
            cursor.execute("""
                SELECT id, name, rating, status, retry_count, notes 
                FROM problems 
                WHERE status LIKE 'failed_%' OR (status LIKE 'in_progress_%' AND last_updated < ?)
                ORDER BY last_updated DESC LIMIT 10
            """, (stuck_threshold,))
            issues = cursor.fetchall()
            
            return summary, workers, issues, keys
            
    except sqlite3.Error as e:
        # Return empty lists and the error message for graceful failure
        return [], [], [], f"Database error: {e}"

def generate_layout() -> Layout:
    """Defines the overall layout for the dashboard."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=3, name="footer")
    )
    layout["main"].split_row(Layout(name="summary", ratio=1), Layout(name="details", ratio=2))
    layout["details"].split(Layout(name="workers"), Layout(name="bottom_row"))
    layout["bottom_row"].split_row(Layout(name="keys"), Layout(name="issues"))
    return layout

def generate_summary_panel(summary_data) -> Panel:
    table = Table(show_header=False, box=None, padding=(0,1))
    table.add_column("Status")
    table.add_column("Count", justify="right")

    status_map = {
        "pending_ingestion": "📥 Pending Ingestion",
        "pending_arl": "🧠 Pending ARL",
        "pending_vjs": "⚖️ Pending VJS",
        "completed": "✅ Completed",
    }
    status_colors = {"ingestion": "cyan", "arl": "magenta", "vjs": "yellow", "completed": "green"}
    
    data_dict = dict(summary_data)
    for status, display in status_map.items():
        count = data_dict.get(status, 0)
        color = status_colors.get(status.split('_')[-1], "white")
        table.add_row(f"[{color}]{display}[/{color}]", f"{count:,}")
    
    failed_count = sum(v for k, v in data_dict.items() if 'failed' in k)
    in_progress_count = sum(v for k, v in data_dict.items() if 'in_progress' in k)
    total = sum(data_dict.values())
    
    table.add_row("---", "---")
    table.add_row(f"[blue]⚙️ In Progress[/blue]", f"{in_progress_count:,}")
    table.add_row(f"[red]🔥 Failed[/red]", f"{failed_count:,}")
    table.add_row("[bold]📊 Total Problems[/bold]", f"[bold]{total:,}[/bold]")
    return Panel(table, title="[bold cyan]Pipeline Queues[/bold cyan]", border_style="cyan")

def generate_workers_panels(workers_data) -> Panel:
    pools = {'INGESTION': [], 'ARL': [], 'VJS': []}
    for worker in workers_data:
        if worker[1] in pools:
            pools[worker[1]].append(worker)

    panels = []
    stage_emojis = {
        "INITIALIZING": "🚀", "WARM-UP": "🔥", "SCRAPING": "🔍", "SAVING": "💾",
        "ARL_PLACEHOLDER": "🧠", "VJS_PLACEHOLDER": "⚖️"
    }

    for pool_name, workers in pools.items():
        table = Table(show_header=False, box=None, padding=(0,1), width=30)
        table.add_column("ID", justify="center", width=3)
        table.add_column("Info")
        for wid, _, pid, stage, status in workers:
            if status == 'idle':
                table.add_row(f"[dim]{wid}[/dim]", "[dim]-- idle --[/dim]")
            else:
                emoji = stage_emojis.get(stage, "⚙️")
                table.add_row(f"[bold blue]{wid}[/bold blue]", f"{emoji} [cyan]{pid}[/cyan]")
        panels.append(Panel(table, title=f"[bold]{pool_name} Pool[/bold]", border_style="blue", expand=True))
        
    return Panel(Columns(panels, expand=True), title="[bold blue]Live Worker Activity[/bold blue]", border_style="blue")

def generate_keys_panel(keys_data) -> Panel:
    table = Table(show_header=True, header_style="bold yellow", box=None, padding=(0,1))
    table.add_column("Service")
    table.add_column("Key")
    table.add_column("Status")
    table.add_column("Cooldown")

    status_colors = {"AVAILABLE": "green", "IN_USE": "blue", "RATE_LIMITED": "red", "INVALID": "red"}

    for fingerprint, service, status, cooldown in keys_data:
        color = status_colors.get(status, "white")
        cooldown_text = ""
        if status == "RATE_LIMITED":
            remaining = max(0, int(cooldown - time.time()))
            cooldown_text = f"{remaining}s"

        table.add_row(
            f"[{color}]{service}[/{color}]",
            fingerprint,
            f"[{color}]{status}[/{color}]",
            f"[dim]{cooldown_text}[/dim]"
        )
        
    return Panel(table, title="[bold yellow]API Key Status[/bold yellow]", border_style="yellow")

def generate_issues_panel(issues_data) -> Panel:
    table = Table(show_header=True, header_style="bold red", box=None, padding=(0,1))
    table.add_column("ID")
    table.add_column("Rating")
    table.add_column("Status")
    table.add_column("Retries")
    table.add_column("Notes")

    for pid, _, rating, status, retries, notes in issues_data:
        table.add_row(f"[cyan]{pid}[/cyan]", str(rating), f"[yellow]{status}[/yellow]", f"[red]{retries}[/red]", f"[dim]{(notes or '')[:30]}[/dim]")
        
    return Panel(table, title="[bold red]Attention Required[/bold red]", border_style="red")

def main():
    """Main function to display the live status dashboard."""
    console = Console()
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]Error:[/bold red] Database '{DB_PATH}' not found. Please run `create_database.py` first.")
        return
        
    layout = generate_layout()
    try:
        with Live(layout, console=console, screen=True, redirect_stderr=False) as live:
            while True:
                summary, workers, issues, keys = get_db_data()
                
                if isinstance(keys, str): # Check if get_db_data returned an error string
                    console.print(f"[bold red]Error:[/bold red] {keys}")
                    break

                layout["header"].update(Align.center(f"[bold]Project Synapse Dashboard[/bold] | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", vertical="middle"))
                layout["summary"].update(generate_summary_panel(summary))
                layout["workers"].update(generate_workers_panels(workers))
                layout["keys"].update(generate_keys_panel(keys))
                layout["issues"].update(generate_issues_panel(issues))
                layout["footer"].update(Align.center("[dim]Watching for changes... (Press Ctrl+C to exit)[/dim]"))
                
                time.sleep(2) # Refresh rate
    except KeyboardInterrupt:
        print("\nExiting status monitor.")
    except Exception as e:
        logging.critical(f"Dashboard crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
