# status.py (Phase 4.75 - Advanced Dashboard)
import sqlite3
import logging
import json
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

DB_PATH = 'progress.db'
logging.basicConfig(level=logging.WARNING) # Keep logging quiet

# --- Data Structures for Time-Series ---
# Use deques to hold the last N minutes of data for sparklines
MAX_DATAPOINTS = 100
vjs_queue_history = deque(maxlen=MAX_DATAPOINTS)
analysis_success_history = deque(maxlen=MAX_DATAPOINTS)
ingestion_success_history = deque(maxlen=MAX_DATAPOINTS)

def get_db_data():
    """Fetches all necessary data from the database for the dashboard."""
    try:
        with sqlite3.connect(f'file:{DB_PATH}?mode=ro', uri=True) as conn:
            cursor = conn.cursor()
            
            # 1. Overall Summary
            cursor.execute("SELECT status, COUNT(*) FROM problems GROUP BY status")
            summary = dict(cursor.fetchall())
            
            # 2. Live Worker Status
            cursor.execute("SELECT worker_id, pool, problem_id, stage, status FROM live_workers ORDER BY worker_id")
            workers = cursor.fetchall()

            # 3. Dynamic Config (Optimizer Levers)
            cursor.execute("SELECT key, value FROM dynamic_config ORDER BY key")
            dynamic_config = cursor.fetchall()
            
            # --- NEW: Aggregate Metrics for Graphs ---
            # VJS Queue Size
            vjs_queue_size = summary.get('pending_vjs', 0)
            vjs_queue_history.append(vjs_queue_size)

            # Success Rates (EWMA would be better, but simple rolling average is good for display)
            since_timestamp = (datetime.now() - timedelta(minutes=10)).isoformat()
            cursor.execute("SELECT worker_pool, success FROM metrics WHERE timestamp > ?", (since_timestamp,))
            recent_metrics = cursor.fetchall()
            
            recent_analysis = [m[1] for m in recent_metrics if m[0] == 'ANALYSIS']
            if recent_analysis:
                analysis_success_history.append(sum(recent_analysis) / len(recent_analysis) * 100)

            recent_ingestion = [m[1] for m in recent_metrics if m[0] == 'INGESTION']
            if recent_ingestion:
                ingestion_success_history.append(sum(recent_ingestion) / len(recent_ingestion) * 100)

            return summary, workers, dynamic_config
            
    except sqlite3.Error as e:
        return {}, [], [], f"Database error: {e}"

def generate_layout() -> Layout:
    """Defines the new, expanded layout for the dashboard."""
    layout = Layout(name="root")
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=3, name="footer")
    )
    layout["main"].split_row(Layout(name="left_col", ratio=1), Layout(name="right_col", ratio=2))
    layout["left_col"].split(Layout(name="summary"), Layout(name="levers"))
    layout["right_col"].split(Layout(name="workers"), Layout(name="graphs"))
    return layout

def generate_summary_panel(summary_data) -> Panel:
    table = Table(show_header=False, box=None, padding=(0,1))
    table.add_column("Status")
    table.add_column("Count", justify="right")

    # More detailed status map
    status_map = {
        "pending_ingestion": "[cyan]📥 Ingestion[/cyan]",
        "pending_rescraping": "[cyan]🔄 Re-Scraping[/cyan]",
        "pending_analysis": "[magenta]🧠 Analysis[/magenta]",
        "pending_implementation": "[yellow]⌨️ Implementation[/yellow]",
        "pending_vjs": "[blue]⚖️ Verification[/blue]",
        "pending_data_assembly": "[green]📦 Assembly[/green]",
        "completed": "[bold green]✅ Completed[/bold green]",
    }
    
    for status, display in status_map.items():
        count = summary_data.get(status, 0)
        table.add_row(display, f"{count:,}")
    
    failed_count = sum(v for k, v in summary_data.items() if 'failed' in k)
    quarantined_count = summary_data.get('quarantined', 0)
    total = sum(summary_data.values())
    
    table.add_row("---", "---")
    table.add_row(f"[red]🔥 Failed[/red]", f"{failed_count:,}")
    table.add_row(f"[bold red] quarantined[/bold red]", f"{quarantined_count:,}")
    table.add_row("[bold]📊 Total Problems[/bold]", f"[bold]{total:,}[/bold]")
    return Panel(table, title="[bold cyan]Pipeline Queues[/bold cyan]", border_style="cyan")

def generate_levers_panel(config_data) -> Panel:
    """Displays the current values of the optimizer's control levers."""
    table = Table(show_header=False, box=None, padding=(0,1))
    table.add_column("Lever")
    table.add_column("Value", justify="right")
    for key, value in config_data:
        table.add_row(f"[yellow]{key}[/yellow]", str(value))
    return Panel(table, title="[bold yellow]Optimizer Levers[/bold yellow]", border_style="yellow")

def generate_graphs_panel() -> Panel:
    """Displays time-series sparkline graphs for key metrics."""
    vjs_graph = Sparkline(vjs_queue_history, " VJS Queue Size")
    analysis_graph = Sparkline(analysis_success_history, " Analysis Success %")
    ingestion_graph = Sparkline(ingestion_success_history, " Ingestion Success %")
    
    return Panel(
        Columns([vjs_graph, analysis_graph, ingestion_graph], expand=True),
        title="[bold magenta]Live Metrics (10 min)[/bold magenta]",
        border_style="magenta"
    )

def generate_workers_panel(workers_data) -> Panel:
    """Displays the status of all worker threads."""
    table = Table(header_style="bold blue", box=None, padding=(0,1))
    table.add_column("ID", justify="center")
    table.add_column("Pool")
    table.add_column("Status")
    table.add_column("Problem ID")
    table.add_column("Stage")

    for wid, pool, pid, stage, status in workers_data:
        style = "dim" if status == 'idle' else "default"
        table.add_row(
            f"[{style}]{wid}[/{style}]",
            f"[{style}]{pool}[/{style}]",
            f"[{style}]{status}[/{style}]",
            f"[cyan]{pid or '--'}[/cyan]",
            f"[{style}]{stage or '--'}[/{style}]",
        )
    return Panel(table, title="[bold blue]Live Worker Activity[/bold blue]", border_style="blue")

def main():
    console = Console()
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]Error:[/bold red] Database '{DB_PATH}' not found.")
        return
        
    layout = generate_layout()
    try:
        with Live(layout, console=console, screen=True, redirect_stderr=False) as live:
            while True:
                data = get_db_data()
                if isinstance(data, tuple) and len(data) == 4 and isinstance(data[3], str):
                    console.print(f"[bold red]Error:[/bold red] {data[3]}")
                    break
                
                summary, workers, dynamic_config = data

                layout["header"].update(Align.center(f"[bold]Project Synapse Dashboard[/bold] | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", vertical="middle"))
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
