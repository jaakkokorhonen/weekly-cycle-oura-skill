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
def get_daily_status(date_str: str = "") -> str:
    """Gets the calculated physiological status, classification, and recommendations for a target date (YYYY-MM-DD).
    
    If date_str is empty, defaults to today.
    """
    config = load_config()
    target_date = date_str or datetime.date.today().isoformat()
    records_dir = Path(config.get("records_dir", "data/records"))
    record_file = records_dir / f"{target_date}.json"

    if not record_file.exists():
        return json.dumps({
            "error": f"No analysis record found for {target_date}. Please run the pipeline for this date first."
        })

    try:
        with open(record_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Failed to read record file: {e}"})

@mcp.tool()
def log_manual_event(
    event_type: str,
    timestamp_str: str = "",
    amount: float = None,
    duration_min: int = None,
    note: str = ""
) -> str:
    """Logs a manual event (caffeine, alcohol, meal, or nap) with optional amount and duration.
    
    event_type must be one of: caffeine, alcohol, meal, nap.
    timestamp_str: ISO format with timezone (e.g. 2026-07-18T14:30:00+03:00). Defaults to current time.
    amount: quantity (mg for caffeine, units for alcohol).
    duration_min: duration of nap in minutes (required for naps).
    """
    config = load_config()
    events_file = Path(config.get("events_file", "data/events.jsonl"))

    if not timestamp_str:
        # Default to Europe/Helsinki offset +03:00
        timestamp_str = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3))).isoformat()

    event = {
        "timestamp": timestamp_str,
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
        return json.dumps({
            "success": True,
            "message": f"Successfully logged {event_type} event at {timestamp_str}."
        })
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)})

@mcp.tool()
def run_analysis_pipeline(date_str: str = "") -> str:
    """Runs the data fetch and enrichment pipeline for a target date (YYYY-MM-DD).
    
    If date_str is empty, defaults to today. Runs bootstrapping (30 days history) on first execution.
    """
    config = load_config()
    token = config.get("oura_token")
    if not token or token == "YOUR_OURA_TOKEN_HERE":
        return json.dumps({"error": "Oura API token is missing in config.yaml."})

    records_dir = Path(config.get("records_dir", "data/records"))
    raw_dir = Path(config.get("raw_dir", "data/raw"))
    events_file = Path(config.get("events_file", "data/events.jsonl"))

    target_date = date_str or datetime.date.today().isoformat()
    client = OuraClient(token=token)
    pipeline = Pipeline(
        oura_client=client,
        records_dir=records_dir,
        raw_dir=raw_dir,
        events_filepath=events_file,
        config=config
    )

    try:
        pipeline.run(target_date)
        # Load and return the newly created record
        record_file = records_dir / f"{target_date}.json"
        if record_file.exists():
            with open(record_file, "r", encoding="utf-8") as f:
                return json.dumps(json.load(f), ensure_ascii=False, indent=2)
        return json.dumps({"success": True, "message": f"Pipeline executed successfully for {target_date}."})
    except Exception as e:
        return json.dumps({"success": False, "error": f"Pipeline execution failed: {e}"})

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
