import json
import datetime
from pathlib import Path

class EventManager:
    VALID_TYPES = {"caffeine", "alcohol", "meal", "nap"}

    def __init__(self, filepath: str | Path):
        self.filepath = Path(filepath)

    def _ensure_file(self):
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self.filepath.write_text("")

    def log_event(self, event: dict) -> None:
        """Validates and appends an event to the events.jsonl file."""
        self._ensure_file()
        
        event_type = event.get("type")
        if event_type not in self.VALID_TYPES:
            raise ValueError(f"Invalid event type: {event_type}. Must be one of {self.VALID_TYPES}")

        if event_type == "nap" and "duration_min" not in event:
            raise ValueError("Nap events require a 'duration_min' field.")

        timestamp_str = event.get("timestamp")
        if not timestamp_str:
            raise ValueError("Events must contain a timestamp.")
        
        try:
            # Validate that it's a timezone-aware ISO string
            dt = datetime.datetime.fromisoformat(timestamp_str)
            if dt.tzinfo is None:
                raise ValueError("Timestamps must be timezone-aware.")
        except Exception as e:
            raise ValueError(f"Invalid timestamp format: {e}")

        # Store the event
        with open(self.filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def get_events_range(self, start: datetime.datetime, end: datetime.datetime) -> list[dict]:
        """Returns all events between start and end (inclusive)."""
        self._ensure_file()
        
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("Start and end datetimes must be timezone-aware.")

        results = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    evt_dt = datetime.datetime.fromisoformat(event["timestamp"])
                    if start <= evt_dt <= end:
                        results.append(event)
                except Exception:
                    continue
        return results

    def get_events_for_date(self, date_str: str) -> list[dict]:
        """Returns events that fall on the local calendar date (YYYY-MM-DD)."""
        self._ensure_file()
        
        try:
            target_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format.")

        results = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    evt_dt = datetime.datetime.fromisoformat(event["timestamp"])
                    # Convert to local date based on offset
                    evt_date = evt_dt.date()
                    if evt_date == target_date:
                        results.append(event)
                except Exception:
                    continue
        return results
