import json
import datetime
import tempfile
import os
from pathlib import Path
from statistics import median
from src.oura_client import OuraClient, OuraClientError
from src.event_manager import EventManager
from src.features import DerivedFeatures, DayRecord, compute_caffeine_window, compute_alcohol_window, compute_recovery_cost
from src.rule_engine import RuleEngine
from src.recommendation_engine import RecommendationEngine

class Pipeline:
    def __init__(self, oura_client: OuraClient, records_dir: Path | str, raw_dir: Path | str, events_filepath: Path | str, config: dict | None = None):
        self.client = oura_client
        self.records_dir = Path(records_dir)
        self.raw_dir = Path(raw_dir)
        self.events_filepath = Path(events_filepath)
        self.config = config or {}
        
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        
        self.event_manager = EventManager(self.events_filepath)
        self.rule_engine = RuleEngine(self.config)
        self.rec_engine = RecommendationEngine()

    def _write_raw(self, date_str: str, day_data: dict) -> None:
        """Saves raw day data to raw_dir/YYYY-MM-DD.json atomically."""
        path = self.raw_dir / f"{date_str}.json"
        
        # Merge if exists
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                existing_sleep = existing.get("sleep", [])
                new_sleep = day_data.get("sleep", [])
                merged_sleep = existing_sleep + [
                    s for s in new_sleep
                    if s.get("id") not in {e.get("id") for e in existing_sleep}
                ]
                merged = {**existing, **day_data, "sleep": merged_sleep}
            except Exception:
                merged = day_data
        else:
            merged = day_data

        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.raw_dir), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise e

    def _load_historical_values(self, target_date: datetime.date, days_back: int, key_path: list[str]) -> list[float]:
        """Loads values from raw_dir files for preceding days to calculate medians."""
        values = []
        for i in range(1, days_back + 1):
            prev_date = target_date - datetime.timedelta(days=i)
            prev_file = self.raw_dir / f"{prev_date.isoformat()}.json"
            if prev_file.exists():
                try:
                    with open(prev_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    # Extract value based on key path (e.g. ["sleep", "average_hrv"])
                    curr = data
                    for key in key_path:
                        if isinstance(curr, list):
                            # For sleep list, get the first main sleep session
                            main_sleeps = [s for s in curr if s.get("type") in ("long_sleep", "short_sleep")]
                            if main_sleeps:
                                curr = main_sleeps[0].get(key)
                            else:
                                curr = None
                        elif isinstance(curr, dict):
                            curr = curr.get(key)
                        else:
                            curr = None
                            break
                            
                    if curr is not None:
                        values.append(float(curr))
                except Exception:
                    continue
        return values

    def _load_history_records(self, target_date: datetime.date, limit: int = 14) -> list[DayRecord]:
        """Loads parsed DayRecord objects chronologically from records_dir."""
        records = []
        for i in range(limit, 0, -1):
            prev_date = target_date - datetime.timedelta(days=i)
            prev_file = self.records_dir / f"{prev_date.isoformat()}.json"
            if prev_file.exists():
                try:
                    with open(prev_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    records.append(DayRecord(
                        date=data["date"],
                        classification=data["classification"],
                        hrv_delta_pct=data["derived"]["derived_hrv_delta_pct"],
                        hrv_value=data["raw"].get("sleep", [{}])[0].get("average_hrv") if data["raw"].get("sleep") else None,
                        hrv_baseline_14d=data["derived"].get("derived_hrv_baseline_14d_median"),
                        partial_baseline=data.get("partial_baseline", False)
                    ))
                except Exception:
                    continue
        return records

    def run(self, date_str: str) -> None:
        """Executes the pipeline for a single date_str."""
        # 1. Fetch range of data (fetch 30 days back if records are empty for bootstrapping, otherwise just fetch target)
        target_date = datetime.date.fromisoformat(date_str)
        
        # Check if we need to bootstrap history
        has_history = any(self.raw_dir.glob("*.json"))
        start_date = date_str
        if not has_history:
            start_date = (target_date - datetime.timedelta(days=30)).isoformat()

        try:
            fetched_data = self.client.fetch_range(start_date=start_date, end_date=date_str)
        except OuraClientError as e:
            # Fallback to local files if Oura API is offline, or raise
            fetched_data = {}

        # 2. Write raw payloads and sync tag events
        for day, day_payload in fetched_data.items():
            self._write_raw(day, day_payload)
            # Sync Oura tags to event_manager
            tags = day_payload.get("tag", [])
            for t in tags:
                label_list = t.get("tags", [])
                if label_list:
                    label = label_list[0].lower()
                    if label in ("caffeine", "alcohol", "meal", "nap"):
                        # Format tag as local manual event
                        event = {
                            "timestamp": t.get("timestamp"),
                            "type": label,
                            "amount": None,
                            "source": "manual_event"
                        }
                        try:
                            self.event_manager.log_event(event)
                        except ValueError:
                            # Already logged or validation error
                            pass

        # 3. Load target day raw data
        target_raw_file = self.raw_dir / f"{date_str}.json"
        if not target_raw_file.exists():
            # Create dummy raw data if missing
            day_raw = {"sleep": [], "daily_readiness": None, "daily_activity": None, "heartrate": [], "tag": []}
        else:
            with open(target_raw_file, "r", encoding="utf-8") as f:
                day_raw = json.load(f)

        # 4. Load baselines
        hrv_values = self._load_historical_values(target_date, 14, ["sleep", "average_hrv"])
        rhr_values = self._load_historical_values(target_date, 30, ["sleep", "lowest_heart_rate"])
        deep_sleep_values = self._load_historical_values(target_date, 30, ["sleep", "deep_sleep_duration"])

        # Baseline medians
        hrv_baseline = median(hrv_values) if hrv_values else None
        rhr_baseline = median(rhr_values) if rhr_values else None
        deep_sleep_baseline = median(deep_sleep_values) if deep_sleep_values else None

        # Determine partial baseline status
        partial_baseline = (len(hrv_values) < 14) or (len(rhr_values) < 30)

        # 5. Extract sleep features
        sleep_list = day_raw.get("sleep", [])
        main_sleep = [s for s in sleep_list if s.get("type") in ("long_sleep", "short_sleep")]
        sleep_session = main_sleep[0] if main_sleep else {}

        bedtime_start = None
        sleep_start_dt = None
        if sleep_session.get("bedtime_start"):
            bedtime_start = sleep_session.get("bedtime_start")
            sleep_start_dt = datetime.datetime.fromisoformat(bedtime_start)
        else:
            # Default to 23:00 local time of target date
            sleep_start_dt = datetime.datetime.fromisoformat(f"{date_str}T23:00:00+03:00")

        # Get events for target date
        day_events = self.event_manager.get_events_for_date(date_str)

        # Compute windows
        caffeine_gap = compute_caffeine_window(day_events, sleep_start_dt)
        alcohol_gap, alcohol_flag = compute_alcohol_window(day_events, sleep_start_dt)

        # Tonight HRV and RHR
        tonight_hrv = sleep_session.get("average_hrv")
        tonight_rhr = sleep_session.get("lowest_heart_rate")

        hrv_delta_pct = 0.0
        if tonight_hrv is not None and hrv_baseline:
            hrv_delta_pct = (tonight_hrv - hrv_baseline) / hrv_baseline

        rhr_delta_pct = 0.0
        if tonight_rhr is not None and rhr_baseline:
            rhr_delta_pct = (tonight_rhr - rhr_baseline) / rhr_baseline

        cost = compute_recovery_cost(sleep_session, day_raw.get("daily_readiness"), {"hrv_baseline": hrv_baseline, "rhr_baseline": rhr_baseline})

        # Sleep duration hours
        total_sleep_h = 0.0
        if sleep_session.get("total_sleep_duration"):
            total_sleep_h = sleep_session.get("total_sleep_duration") / 3600.0

        # Construct derived features dict
        deep_sleep_val = sleep_session.get("deep_sleep_duration", 0.0)
        deep_sleep_vs_30d = deep_sleep_val - deep_sleep_baseline if deep_sleep_baseline is not None else 0.0

        # Active kcal
        active_kcal = 0.0
        activity_payload = day_raw.get("daily_activity")
        if activity_payload and activity_payload.get("active_calories"):
            active_kcal = float(activity_payload.get("active_calories"))

        # Load history of records for rule engine
        history_records = self._load_history_records(target_date, 14)

        # Count days since last high load
        days_since_high_load = 99
        for i, rec in enumerate(reversed(history_records)):
            if rec.classification == "HIGH_LOAD_DAY":
                days_since_high_load = i + 1
                break

        # Calculate integration completeness conditions met (out of 3)
        integration_score = 0
        if hrv_delta_pct >= 0.0:
            integration_score += 1
        if deep_sleep_vs_30d > 0.0:
            integration_score += 1
        if rhr_delta_pct < 0.0:
            integration_score += 1

        derived_dict = {
            "derived_hrv_baseline_14d_median": hrv_baseline,
            "derived_hrv_delta_pct": hrv_delta_pct,
            "derived_deep_sleep_vs_30d": deep_sleep_vs_30d,
            "derived_rhr_vs_30d": rhr_delta_pct,
            "derived_active_kcal": active_kcal,
            "derived_high_load_flag": False,
            "derived_days_since_last_high_load": days_since_high_load,
            "derived_integration_completeness": integration_score,
            "hrv_delta_pct": hrv_delta_pct,
            "rhr_delta_pct": rhr_delta_pct,
            "recovery_cost": cost,
            "sleep_pattern": "monophasic",
            "total_sleep_last_24h": total_sleep_h,
            "caffeine_present": any(e["type"] == "caffeine" for e in day_events),
            "caffeine_hours_before_bed": caffeine_gap,
            "alcohol_present": any(e["type"] == "alcohol" for e in day_events),
            "alcohol_hours_before_bed": alcohol_gap,
            "alcohol_flag_before_first_sleep": alcohol_flag,
            "work_block_minutes": None,
            "hrv_baseline_14d": hrv_baseline,
            "rhr_baseline_30d": rhr_baseline,
            "deep_sleep_median_30d": deep_sleep_baseline,
            "partial_baseline": partial_baseline
        }

        # 6. Rule engine classification and state transition
        classification = self.rule_engine.classify_day(derived_dict)
        derived_dict["derived_high_load_flag"] = (classification == "HIGH_LOAD_DAY")

        # Create temporary current DayRecord to calculate state transitions
        current_record = DayRecord(
            date=date_str,
            classification=classification,
            hrv_delta_pct=hrv_delta_pct,
            hrv_value=tonight_hrv,
            hrv_baseline_14d=hrv_baseline,
            partial_baseline=partial_baseline
        )

        load_state = self.rule_engine.get_state(history_records + [current_record])
        tactical = self.rule_engine.get_tactical_suggestion(derived_dict)

        # 7. Recommendation Engine suggestions
        recommendation = self.rec_engine.generate(
            classification=classification,
            load_state=load_state,
            features=derived_dict,
            tactical=tactical
        )

        # 8. Extract Oura metrics for output
        readiness_payload = day_raw.get("daily_readiness")
        readiness_score = readiness_payload.get("score") if readiness_payload else None
        
        # Save merged record
        record_payload = {
            "date": date_str,
            "partial_baseline": partial_baseline,
            "classification": classification,
            "load_state": load_state,
            "recommendation": recommendation,
            "raw": day_raw,
            "derived": derived_dict,
            "oura": {
                "oura_readiness_score": readiness_score,
                "oura_recovery_index": readiness_payload.get("contributors", {}).get("recovery_index") if readiness_payload else None,
                "oura_active_calories": active_kcal
            }
        }

        record_file = self.records_dir / f"{date_str}.json"
        tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.records_dir), suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(record_payload, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, record_file)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise e
        return record_payload


    def get_record(self, date_str: str) -> dict:
        """Reads and returns the analysis record for a given date."""
        record_file = self.records_dir / f"{date_str}.json"
        if not record_file.exists():
            raise FileNotFoundError(f"Record for {date_str} not found.")
        with open(record_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_latest_record(self) -> dict:
        """Reads and returns the most recent analysis record in records_dir."""
        files = sorted(self.records_dir.glob("*.json"))
        if not files:
            raise FileNotFoundError("No analysis records found.")
        # Return the last (chronologically most recent) record file
        with open(files[-1], "r", encoding="utf-8") as f:
            return json.load(f)

