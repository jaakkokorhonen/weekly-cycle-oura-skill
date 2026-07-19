import click
import json
import datetime
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.oura_client import OuraClient
from src.pipeline import Pipeline
from src.event_manager import EventManager

load_dotenv()
console = Console()

def load_config() -> dict:
    """Loads configuration from config.yaml, or falls back to defaults."""
    config_path = Path("config.yaml")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
            
    # Try example config
    example_path = Path("config.yaml.example")
    if example_path.exists():
        try:
            with open(example_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
            
    # Hardcoded fallback defaults
    return {
        "oura_token": "",
        "data_dir": "data",
        "records_dir": "data/records",
        "raw_dir": "data/raw",
        "events_file": "data/events.jsonl",
        "timezone": "Europe/Helsinki",
        "thresholds": {
            "high_load_kcal_hard": 1000,
            "high_load_kcal_soft": 800,
            "high_load_hrv_delta": -0.15,
            "integration_min_conditions": 3,
            "incomplete_reset_days": 3,
            "nap_sleep_threshold_h": 6.5,
            "nap_hrv_delta": -0.10
        }
    }

@click.group()
def main_cli():
    """Weekly Cycle Oura Skill - CLI Tool."""
    pass

@main_cli.command()
@click.option("--date", default=None, help="Specific date to process (YYYY-MM-DD). Defaults to today.")
@click.option("--start", default=None, help="Start date of a range (YYYY-MM-DD).")
@click.option("--end", default=None, help="End date of a range (YYYY-MM-DD).")
def run(date, start, end):
    """Executes the analysis pipeline to fetch Oura data and update daily records."""
    config = load_config()
    token = config.get("oura_token")
    if not token or token == "YOUR_OURA_TOKEN_HERE":
        token = os.environ.get("OURA_TOKEN")
        
    if not token or token == "YOUR_OURA_TOKEN_HERE":
        console.print("[bold red]Error:[/] Oura token is missing in config.yaml or .env. Please configure OURA_TOKEN.")
        return



    # Setup pipeline dirs
    records_dir = Path(config.get("records_dir", "data/records"))
    raw_dir = Path(config.get("raw_dir", "data/raw"))
    events_file = Path(config.get("events_file", "data/events.jsonl"))

    client = OuraClient(token=token)
    pipeline = Pipeline(
        oura_client=client,
        records_dir=records_dir,
        raw_dir=raw_dir,
        events_filepath=events_file,
        config=config
    )

    if start and end:
        try:
            start_dt = datetime.date.fromisoformat(start)
            end_dt = datetime.date.fromisoformat(end)
            curr = start_dt
            while curr <= end_dt:
                console.print(f"Running pipeline for [cyan]{curr.isoformat()}[/]...")
                pipeline.run(curr.isoformat())
                curr += datetime.timedelta(days=1)
            console.print("[bold green]Success:[/] Date range pipeline executed successfully.")
        except Exception as e:
            console.print(f"[bold red]Pipeline Error:[/] {e}")
    else:
        target_date = date or datetime.date.today().isoformat()
        try:
            console.print(f"Running pipeline for [cyan]{target_date}[/]...")
            pipeline.run(target_date)
            console.print(f"[bold green]Success:[/] Pipeline executed successfully for {target_date}.")
        except Exception as e:
            console.print(f"[bold red]Pipeline Error:[/] {e}")

@main_cli.command()
@click.argument("event_type", type=click.Choice(["caffeine", "alcohol", "meal", "nap"]))
@click.option("--timestamp", default=None, help="Event ISO timestamp with timezone. Defaults to now.")
@click.option("--amount", type=float, default=None, help="Dose amount (e.g. caffeine mg, alcohol units).")
@click.option("--duration-min", type=int, default=None, help="Duration of nap in minutes (required for naps).")
@click.option("--note", default="", help="Optional text note.")
def log_event(event_type, timestamp, amount, duration_min, note):
    """Logs a manual event (caffeine, alcohol, meal, nap) to the local events file."""
    config = load_config()
    events_file = Path(config.get("events_file", "data/events.jsonl"))

    # Construct timestamp with local offset if not provided
    if not timestamp:
        # Determine local timezone offset (defaulting to +03:00 Helsinki summer time)
        local_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        timestamp = local_now.isoformat()

    event = {
        "timestamp": timestamp,
        "type": event_type,
        "source": "manual_event"
    }
    if amount is not None:
        event["amount"] = amount
    if duration_min is not None:
        event["duration_min"] = duration_min
    if note:
        event["note"] = note

    manager = EventManager(events_file)
    try:
        manager.log_event(event)
        console.print(f"[bold green]Success:[/] Logged [cyan]{event_type}[/] event at [magenta]{timestamp}[/].")
    except ValueError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")

@main_cli.command()
@click.option("--date", default=None, help="Date to query (YYYY-MM-DD). Defaults to today.")
def status(date):
    """Displays a beautiful, colorful status dashboard of physiology, classification, and recommendations."""
    config = load_config()
    target_date = date or datetime.date.today().isoformat()
    records_dir = Path(config.get("records_dir", "data/records"))
    record_file = records_dir / f"{target_date}.json"

    if not record_file.exists():
        console.print(f"[bold yellow]Warning:[/] No analysis record found for [cyan]{target_date}[/]. Run [bold]run[/] command first.")
        return

    try:
        with open(record_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        console.print(f"[bold red]Error reading record:[/] {e}")
        return

    # Extract info
    classification = data.get("classification", "BASELINE_DAY")
    load_state = data.get("load_state", "Neutral")
    recommendation = data.get("recommendation", "")
    derived = data.get("derived", {})
    oura = data.get("oura", {})

    # Define color scheme based on classification
    color_map = {
        "HIGH_LOAD_DAY": "bold red",
        "INTEGRATION_DAY": "bold green",
        "BASELINE_DAY": "bold blue"
    }
    class_color = color_map.get(classification, "bold white")

    # Render Header Panel
    console.print(Panel(
        f"[bold white]Date:[/] [cyan]{target_date}[/] | [bold white]Status:[/] [{class_color}]{classification}[/] | [bold white]Cycle State:[/] [magenta]{load_state}[/]",
        title="Weekly Cycle Oura Dashboard",
        border_style="cyan"
    ))

    # Metrics Table
    table = Table(title="Key Metrics Summary", border_style="dim")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold white")
    table.add_column("Baseline Comparison / Info", style="dim")

    # HRV
    hrv_val = derived.get("hrv_baseline_14d")
    hrv_delta = derived.get("hrv_delta_pct")
    hrv_delta_str = f"{int(round(hrv_delta * 100))}%" if hrv_delta is not None else "N/A"
    table.add_row(
        "HRV Delta", 
        hrv_delta_str, 
        f"14d Baseline Median: {hrv_val or 'N/A'}"
    )

    # RHR
    rhr_val = derived.get("rhr_baseline_30d")
    rhr_delta = derived.get("rhr_delta_pct")
    rhr_delta_str = f"{int(round(rhr_delta * 100))}%" if rhr_delta is not None else "N/A"
    table.add_row(
        "RHR Delta", 
        rhr_delta_str, 
        f"30d Baseline Median: {rhr_val or 'N/A'}"
    )

    # Active calories
    active_kcal = oura.get("oura_active_calories", 0)
    table.add_row(
        "Active Energy", 
        f"{active_kcal:.0f} kcal", 
        "Used for physical load classification"
    )

    # Sleep hours
    sleep_h = derived.get("total_sleep_last_24h", 0.0)
    table.add_row(
        "Sleep Duration", 
        f"{sleep_h:.1f} hours", 
        "Target sleep threshold is 6.5h"
    )

    console.print(table)

    # Recommendation Panel
    console.print(Panel(
        recommendation,
        title="[bold yellow]Tactical Suggestions[/]",
        border_style="yellow"
    ))

@main_cli.command()
@click.option("--start-1", required=True, help="Start of first range (YYYY-MM-DD)")
@click.option("--end-1", required=True, help="End of first range (YYYY-MM-DD)")
@click.option("--start-2", required=True, help="Start of second range (YYYY-MM-DD)")
@click.option("--end-2", required=True, help="End of second range (YYYY-MM-DD)")
def analyze(start_1, end_1, start_2, end_2):
    """Compares physiological outputs and behavioral statistics between two date blocks."""
    config = load_config()
    records_dir = Path(config.get("records_dir", "data/records"))

    def compute_range_stats(start, end):
        start_dt = datetime.date.fromisoformat(start)
        end_dt = datetime.date.fromisoformat(end)
        
        hrv_deltas = []
        sleep_durations = []
        caffeine_counts = 0
        alcohol_counts = 0
        total_days = 0
        
        curr = start_dt
        while curr <= end_dt:
            file_path = records_dir / f"{curr.isoformat()}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    derived = data.get("derived", {})
                    
                    hrv_val = derived.get("derived_hrv_delta_pct")
                    if hrv_val is not None:
                        hrv_deltas.append(hrv_val)
                        
                    sleep_val = derived.get("total_sleep_last_24h")
                    if sleep_val is not None:
                        sleep_durations.append(sleep_val)
                        
                    if derived.get("caffeine_present"):
                        caffeine_counts += 1
                    if derived.get("alcohol_present"):
                        alcohol_counts += 1
                except Exception:
                    pass
            total_days += 1
            curr += datetime.timedelta(days=1)
            
        avg_hrv_delta = sum(hrv_deltas) / len(hrv_deltas) if hrv_deltas else 0.0
        avg_sleep = sum(sleep_durations) / len(sleep_durations) if sleep_durations else 0.0
        
        return {
            "avg_hrv_delta_pct": avg_hrv_delta * 100,
            "avg_sleep": avg_sleep,
            "caffeine_days": caffeine_counts,
            "alcohol_days": alcohol_counts,
            "total_days": total_days
        }

    try:
        stats1 = compute_range_stats(start_1, end_1)
        stats2 = compute_range_stats(start_2, end_2)
    except Exception as e:
        console.print(f"[bold red]Analysis Error:[/] {e}")
        return

    table = Table(title="N-of-1 Range Comparison", border_style="cyan")
    table.add_column("Metric", style="cyan")
    table.add_column(f"Block 1 ({start_1} - {end_1})", style="bold white")
    table.add_column(f"Block 2 ({start_2} - {end_2})", style="bold white")
    table.add_column("Delta / Diff", style="bold yellow")

    table.add_row(
        "Avg HRV Delta", 
        f"{stats1['avg_hrv_delta_pct']:.1f}%", 
        f"{stats2['avg_hrv_delta_pct']:.1f}%", 
        f"{stats2['avg_hrv_delta_pct'] - stats1['avg_hrv_delta_pct']:.1f}%"
    )
    
    table.add_row(
        "Avg Sleep Duration", 
        f"{stats1['avg_sleep']:.1f} h", 
        f"{stats2['avg_sleep']:.1f} h", 
        f"{stats2['avg_sleep'] - stats1['avg_sleep']:.1f} h"
    )

    table.add_row(
        "Caffeine Days Count", 
        f"{stats1['caffeine_days']} / {stats1['total_days']}", 
        f"{stats2['caffeine_days']} / {stats2['total_days']}", 
        f"{stats2['caffeine_days'] - stats1['caffeine_days']}"
    )

    table.add_row(
        "Alcohol Days Count", 
        f"{stats1['alcohol_days']} / {stats1['total_days']}", 
        f"{stats2['alcohol_days']} / {stats2['total_days']}", 
        f"{stats2['alcohol_days'] - stats1['alcohol_days']}"
    )

    console.print(table)

if __name__ == "__main__":
    main_cli()
