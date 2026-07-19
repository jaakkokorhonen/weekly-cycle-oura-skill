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

        # Caffeine and alcohol require 'amount' and it must be > 0.0
        if event_type in ("caffeine", "alcohol"):
            if "amount" not in event:
                raise ValueError(f"'{event_type}' events require an 'amount' field.")
            amount = event.get("amount")
            try:
                amount_val = float(amount)
                if amount_val <= 0.0:
                    raise ValueError()
            except (TypeError, ValueError):
                raise ValueError(f"'{event_type}' amount must be greater than 0.")

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

    def get_events_range(self, start_date: str, end_date: str) -> dict[str, list[dict]]:
        """Returns all events between start_date and end_date (calendar date strings) grouped by day.
        
        Returns:
            dict[date_str, list[dict]]
        """
        self._ensure_file()
        
        try:
            start_dt = datetime.date.fromisoformat(start_date)
            end_dt = datetime.date.fromisoformat(end_date)
            if start_dt > end_dt:
                raise ValueError("start_date must be before or equal to end_date")
        except ValueError as e:
            raise ValueError(f"Invalid date format: {e}")

        # Initialize results dictionary for every day in the range
        results = {}
        curr = start_dt
        while curr <= end_dt:
            results[curr.isoformat()] = []
            curr += datetime.timedelta(days=1)

        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    evt_dt = datetime.datetime.fromisoformat(event["timestamp"])
                    evt_date_str = evt_dt.date().isoformat()
                    if evt_date_str in results:
                        results[evt_date_str].append(event)
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
                    evt_date = evt_dt.date()
                    if evt_date == target_date:
                        results.append(event)
                except Exception:
                    continue
        return results
