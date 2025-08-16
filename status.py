# status.py
"""
A terminal-based live dashboard for monitoring the Project Synapse pipeline.

This script uses the 'rich' library to create a dynamic, full-screen display
that provides a real-time overview of the system's state. It reads data
from the `progress.db` in a read-only, non-blocking mode (thanks to WAL)
and refreshes every few seconds.

The dashboard includes:
-   Overall summary of problems in each pipeline stage (queue sizes).
-   Live status of every worker thread.
-   Current values of the optimizer's dynamic configuration levers.
-   Time-series sparkline graphs for key performance metrics.
"""
import sqlite3
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.columns import Columns
from rich.sparkline import Sparkline
from datetime import datetime, timedelta
import time
import os
from collections import deque
from typing import Tuple, List, Dict, Any, Deque, Optional

from config import PROGRESS_DB_NAME

logging.basicConfig(level=logging.WARNING)  # Keep dashboard-related logging quiet

# --- Data Structures for Time-Series ---
MAX_DATAPOINTS = 100
vjs_queue_history: Deque[int] = deque(maxlen=MAX_DATAPOINTS)
analysis_success_history: Deque[float] = deque(maxlen=MAX_DATAPOINTS)
ingestion_success_history: Deque[float] = deque(maxlen=MAX_DATAPOINTS)

def get_db_data() -> Optional[Tuple[Dict, List, List]]:
    """Fetches all necessary data from the database for the dashboard."""
    try:
        with sqlite3.connect(f'file:{PROGRESS_DB_NAME}?mode=ro', uri=True) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT status, COUNT(*) FROM problems GROUP BY status")
            summary = dict(cursor.fetchall())
            
            cursor.execute("SELECT worker_id, pool, problem_id, stage, status FROM live_workers ORDER BY worker_id")
            workers = cursor.fetchall()

            cursor.execute("SELECT key, value FROM dynamic_config ORDER BY key")
            dynamic_config = cursor.fetchall()
            
            vjs_queue_history.append(summary.get('pending_vjs', 0))

            since = (datetime.now() - timedelta(minutes=10)).isoformat()
            cursor.execute("SELECT worker_pool, success FROM metrics WHERE timestamp > ?", (since,))
            recent_metrics = cursor.fetchall()
            
            analysis = [m[1] for m in recent_metrics if m[0] == 'ANALYSIS']
            if analysis: analysis_success_history.append(sum(analysis) / len(analysis) * 100)

            ingestion = [m[1] for m in recent_metrics if m[0] == 'INGESTION']
            if ingestion: ingestion_success_history.append(sum(ingestion) / len(ingestion) * 100)

            return summary, workers, dynamic_config
    except sqlite3.Error as e:
        Console().print(f"[bold red]Database error:[/bold red] {e}")
        return None

def generate_layout() -> Layout:
    """Defines the rich layout for the dashboard."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=3, name="footer")
    )
    layout["main"].split_row(Layout(name="left", ratio=1), Layout(name="right", ratio=2))
    layout["left"].split(Layout(name="summary"), Layout(name="levers"))
    layout["right"].split(Layout(name="workers"), Layout(name="graphs"))
    return layout

def generate_summary_panel(summary_data: Dict[str, int]) -> Panel:
    """Creates the 'Pipeline Queues' panel."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Status"); table.add_column("Count", justify="right")
    status_map = {
        "pending_ingestion": "[cyan]📥 Ingestion[/cyan]", "pending_rescraping": "[cyan]🔄 Re-Scraping[/cyan]",
        "pending_analysis": "[magenta]🧠 Analysis[/magenta]", "pending_implementation": "[yellow]⌨️ Implementation[/yellow]",
        "pending_vjs": "[blue]⚖️ Verification[/blue]", "pending_data_assembly": "[green]📦 Assembly[/green]",
        "completed": "[bold green]✅ Completed[/bold green]",
    }
    for status, display in status_map.items():
        table.add_row(display, f"{summary_data.get(status, 0):,}")
    
    quarantined = summary_data.get('quarantined', 0)
    total = sum(summary_data.values())
    table.add_row("---", "---")
    table.add_row(f"[bold red]☣️ Quarantined[/bold red]", f"{quarantined:,}")
    table.add_row("[bold]📊 Total Problems[/bold]", f"[bold]{total:,}[/bold]")
    return Panel(table, title="[bold cyan]Pipeline Queues[/bold cyan]", border_style="cyan")

def generate_levers_panel(config_data: List[Tuple[str, str]]) -> Panel:
    """Creates the 'Optimizer Levers' panel."""
    table = Table(show_header=False, box=None, padding=(0,1))
    table.add_column("Lever"); table.add_column("Value", justify="right")
    for key, value in config_data:
        table.add_row(f"[yellow]{key}[/yellow]", str(value))
    return Panel(table, title="[bold yellow]Optimizer Levers[/bold yellow]", border_style="yellow")

def generate_graphs_panel() -> Panel:
    """Creates the 'Live Metrics' panel with sparklines."""
    vjs_graph = Sparkline(vjs_queue_history, " VJS Queue")
    analysis_graph = Sparkline(analysis_success_history, " Analysis Success %")
    ingestion_graph = Sparkline(ingestion_success_history, " Ingestion Success %")
    return Panel(
        Columns([vjs_graph, analysis_graph, ingestion_graph], expand=True),
        title="[bold magenta]Live Metrics (10 min)[/bold magenta]", border_style="magenta"
    )

def generate_workers_panel(workers_data: List[Tuple]) -> Panel:
    """Creates the 'Live Worker Activity' panel."""
    table = Table(header_style="bold blue", box=None, padding=(0, 1))
    table.add_column("ID", justify="center"); table.add_column("Pool"); table.add_column("Status")
    table.add_column("Problem ID"); table.add_column("Stage")
    for wid, pool, pid, stage, status in workers_data:
        style = "dim" if status == 'idle' else "default"
        table.add_row(f"[{style}]{wid}", f"[{style}]{pool}", f"[{style}]{status}",
                      f"[cyan]{pid or '--'}", f"[{style}]{stage or '--'}")
    return Panel(table, title="[bold blue]Live Worker Activity[/bold blue]", border_style="blue")

def main():
    console = Console()
    if not os.path.exists(PROGRESS_DB_NAME):
        console.print(f"[bold red]Error:[/bold red] Database '{PROGRESS_DB_NAME}' not found.")
        return
        
    layout = generate_layout()
    try:
        with Live(layout, console=console, screen=True, redirect_stderr=False) as live:
            while True:
                db_data = get_db_data()
                if db_data is None: break
                
                summary, workers, dynamic_config = db_data
                layout["header"].update(Align.center(f"[bold]Project Synapse Dashboard[/bold] | {datetime.now():%Y-%m-%d %H:%M:%S}"))
                layout["summary"].update(generate_summary_panel(summary))
                layout["levers"].update(generate_levers_panel(dynamic_config))
                layout["workers"].update(generate_workers_panel(workers))
                layout["graphs"].update(generate_graphs_panel())
                layout["footer"].update(Align.center("[dim]Watching for changes... (Press Ctrl+C to exit)[/dim]"))
                time.sleep(2)
    except KeyboardInterrupt:
        print("\nExiting status monitor.")
    except Exception as e:
        logging.critical(f"Dashboard crashed: {e}", exc_info=True)

if __name__ == "__main__":
    main()