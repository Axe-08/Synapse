# status.py (The Stage-Centric Live Dashboard)
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

DB_PATH = 'progress.db'
logging.basicConfig(level=logging.WARNING)

def get_db_data():
    """Fetches all necessary data from the database for the dashboard."""
    try:
        with sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status, COUNT(*) FROM problems GROUP BY status")
            summary = cursor.fetchall()
            cursor.execute("SELECT worker_id, pool, problem_id, stage, status FROM live_workers ORDER BY worker_id")
            workers = cursor.fetchall()
            stuck_threshold = (datetime.now() - timedelta(minutes=15)).isoformat()
            cursor.execute("""
                SELECT id, name, rating, status, retry_count, notes 
                FROM problems 
                WHERE status LIKE 'failed_%' OR (status LIKE 'in_progress_%' AND last_updated < ?)
                ORDER BY last_updated DESC LIMIT 10
            """, (stuck_threshold,))
            issues = cursor.fetchall()
            return summary, workers, issues
    except sqlite3.Error as e:
        return None, None, f"Database error: {e}"

def generate_layout() -> Layout:
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=3, name="footer")
    )
    layout["main"].split_row(Layout(name="summary", ratio=1), Layout(name="workers", ratio=2))
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
    total = 0
    for status, display in status_map.items():
        count = data_dict.get(status, 0)
        color = status_colors.get(status.split('_')[-1], "white")
        table.add_row(f"[{color}]{display}[/{color}]", f"{count:,}")
    
    failed_count = sum(v for k, v in data_dict.items() if 'failed' in k)
    in_progress_count = sum(v for k, v in data_dict.items() if 'in_progress' in k)
    total = sum(data_dict.values())
    
    table.add_row("---", "---")
    table.add_row("[blue]⚙️ In Progress[/blue]", f"{in_progress_count:,}")
    table.add_row("[red]🔥 Failed[/red]", f"{failed_count:,}")
    table.add_row("[bold]📊 Total Problems[/bold]", f"[bold]{total:,}[/bold]")
    return Panel(table, title="[bold cyan]Pipeline Queues[/bold cyan]", border_style="cyan")

def generate_workers_panels(workers_data) -> Panel:
    pools = {'INGESTION': [], 'ARL': [], 'VJS': []}
    for worker in workers_data:
        if worker[1] in pools:
            pools[worker[1]].append(worker)

    panels = []
    stage_emojis = {"INITIALIZING": "🚀", "SCRAPING": "🔍", "SAVING": "💾", "ARL_ANALYST": "🧠", "ARL_IMPLEMENTER": "✍️", "VJS_VERIFYING": "⚖️"}

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

def main():
    console = Console()
    layout = generate_layout()
    
    try:
        with Live(layout, console=console, screen=True, redirect_stderr=False) as live:
            while True:
                summary, workers, issues = get_db_data()
                if summary is None:
                    console.print(f"[bold red]Error:[/bold red] Could not connect to '{DB_PATH}'.")
                    break
                layout["header"].update(Align.center(f"[bold]Project Synapse Dashboard[/bold] | {datetime.now().strftime('%H:%M:%S')}"))
                layout["summary"].update(generate_summary_panel(summary))
                layout["workers"].update(generate_workers_panels(workers))
                layout["footer"].update(Align.center("[dim]Press Ctrl+C to exit[/dim]"))
                time.sleep(2)
    except KeyboardInterrupt:
        print("\nExiting status monitor.")
    except Exception as e:
        logging.critical(f"Dashboard crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()