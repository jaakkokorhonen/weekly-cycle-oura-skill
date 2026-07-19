import json
import datetime
from pathlib import Path
from mcp.server.fastmcp import FastMCP

from src.oura_client import OuraClient
from src.pipeline import Pipeline
from src.event_manager import EventManager
from src.cli import load_config

# Initialize FastMCP Server
mcp = FastMCP("Weekly Cycle Oura Skill")

@mcp.tool()
def get_status(date: str = "") -> dict:
    """Gets the latest calculated physiological status, classification, and recommendations."""
    config = load_config()
    token = config.get("oura_token", "")
    records_dir = Path(config.get("records_dir", "data/records"))
    raw_dir = Path(config.get("raw_dir", "data/raw"))
    events_file = Path(config.get("events_file", "data/events.jsonl"))

    client = OuraClient(token=token if token else "test_token")
    pipeline = Pipeline(
        oura_client=client,
        records_dir=records_dir,
        raw_dir=raw_dir,
        events_filepath=events_file,
        config=config
    )

    if date:
        try:
            return pipeline.get_record(date)
        except Exception:
            pass

    try:
        return pipeline.get_latest_record()
    except Exception as e:
        return {"error": f"No records found: {e}"}

@mcp.tool()
def get_daily_report(date: str = "") -> dict:
    """Retrieves a specific calendar day report by date (YYYY-MM-DD) without triggering a live run."""
    config = load_config()
    token = config.get("oura_token", "")
    records_dir = Path(config.get("records_dir", "data/records"))
    raw_dir = Path(config.get("raw_dir", "data/raw"))
    events_file = Path(config.get("events_file", "data/events.jsonl"))

    target_date = date or datetime.date.today().isoformat()
    client = OuraClient(token=token if token else "test_token")
    pipeline = Pipeline(
        oura_client=client,
        records_dir=records_dir,
        raw_dir=raw_dir,
        events_filepath=events_file,
        config=config
    )

    try:
        return pipeline.get_record(target_date)
    except Exception as e:
        return {"error": f"Failed to retrieve report for {target_date}: {e}"}

@mcp.tool()
def log_event(
    type: str,
    timestamp_str: str = "",
    amount: float = None,
    unit: str = None,
    note: str = ""
) -> str:
    """Logs a manual event (caffeine, alcohol, meal, or nap) to the local log."""
    config = load_config()
    events_file = Path(config.get("events_file", "data/events.jsonl"))

    if not timestamp_str:
        local_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
        timestamp_str = local_now.isoformat()

    event = {
        "timestamp": timestamp_str,
        "type": type,
        "source": "manual_event"
    }
    if amount is not None:
        event["amount"] = amount
    if unit is not None:
        event["unit"] = unit
    if note:
        event["note"] = note

    manager = EventManager(events_file)
    manager.log_event(event)
    return f"Successfully logged {type} event."

@mcp.tool()
def run_pipeline(date: str = "") -> dict:
    """Runs the full fetch, processing, and enrichment pipeline for a calendar date (YYYY-MM-DD)."""
    config = load_config()
    token = config.get("oura_token", "")
    records_dir = Path(config.get("records_dir", "data/records"))
    raw_dir = Path(config.get("raw_dir", "data/raw"))
    events_file = Path(config.get("events_file", "data/events.jsonl"))

    target_date = date or datetime.date.today().isoformat()
    client = OuraClient(token=token if token else "test_token")
    pipeline = Pipeline(
        oura_client=client,
        records_dir=records_dir,
        raw_dir=raw_dir,
        events_filepath=events_file,
        config=config
    )

    try:
        return pipeline.run(target_date)
    except Exception as e:
        return {"error": f"Pipeline failed: {e}"}

@mcp.tool()
def compare_ranges(start_1: str, end_1: str, start_2: str, end_2: str) -> str:
    """Compares average physiology and event logs between two calendar date ranges (N-of-1 trial comparison)."""
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
        
        comparison = {
            "block_1": {
                "range": f"{start_1} to {end_1}",
                "stats": stats1
            },
            "block_2": {
                "range": f"{start_2} to {end_2}",
                "stats": stats2
            },
            "deltas": {
                "hrv_delta_pct_diff": stats2["avg_hrv_delta_pct"] - stats1["avg_hrv_delta_pct"],
                "avg_sleep_hours_diff": stats2["avg_sleep"] - stats1["avg_sleep"],
                "caffeine_days_diff": stats2["caffeine_days"] - stats1["caffeine_days"],
                "alcohol_days_diff": stats2["alcohol_days"] - stats1["alcohol_days"]
            }
        }
        return json.dumps(comparison, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to compare ranges: {e}"})

if __name__ == "__main__":
    mcp.run()
