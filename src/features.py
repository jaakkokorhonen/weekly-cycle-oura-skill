import datetime
from dataclasses import dataclass
from typing import Literal

@dataclass
class DerivedFeatures:
    # Recovery
    hrv_delta_pct: float          # (tonight_hrv - 14d_median) / 14d_median
    rhr_delta_pct: float          # (tonight_rhr - 30d_median) / 30d_median
    recovery_cost: float          # abs(hrv_delta_pct) + abs(rhr_delta_pct)

    # Sleep structure
    sleep_pattern: Literal["monophasic", "biphasic", "polyphasic"]
    total_sleep_last_24h: float   # hours

    # Behavioural windows — caffeine and alcohol
    caffeine_present: bool
    caffeine_hours_before_bed: float | None
    alcohol_present: bool
    alcohol_hours_before_bed: float | None
    alcohol_flag_before_first_sleep: bool

    # Work structure (stubbed)
    work_block_minutes: int | None

    # Baseline info
    hrv_baseline_14d: float | None
    rhr_baseline_30d: float | None
    deep_sleep_median_30d: float | None
    partial_baseline: bool

@dataclass
class DayRecord:
    date: str
    classification: Literal["HIGH_LOAD_DAY", "INTEGRATION_DAY", "BASELINE_DAY"]
    hrv_delta_pct: float
    hrv_value: float | None
    hrv_baseline_14d: float | None
    partial_baseline: bool = False

def compute_caffeine_window(events: list[dict], sleep_start: datetime.datetime) -> float | None:
    """Calculates hours between latest caffeine event and sleep_start."""
    caffeine_events = [e for e in events if e.get("type") == "caffeine"]
    if not caffeine_events:
        return None
    
    # Filter to events that happened before sleep_start
    valid_events = []
    for e in caffeine_events:
        ts = e.get("timestamp")
        if ts:
            dt = datetime.datetime.fromisoformat(ts)
            if dt <= sleep_start:
                valid_events.append(dt)
                
    if not valid_events:
        return None
        
    latest = max(valid_events)
    return (sleep_start - latest).total_seconds() / 3600.0

def compute_alcohol_window(events: list[dict], sleep_start: datetime.datetime) -> tuple[float | None, bool]:
    """Calculates hours between latest alcohol event and sleep_start, and if it's before first sleep (<3h)."""
    alcohol_events = [e for e in events if e.get("type") == "alcohol"]
    if not alcohol_events:
        return None, False
        
    valid_events = []
    for e in alcohol_events:
        ts = e.get("timestamp")
        if ts:
            dt = datetime.datetime.fromisoformat(ts)
            if dt <= sleep_start:
                valid_events.append(dt)
                
    if not valid_events:
        return None, False
        
    latest = max(valid_events)
    gap = (sleep_start - latest).total_seconds() / 3600.0
    before_first_sleep = gap < 3.0
    return gap, before_first_sleep

def segment_sleep_night(sleep_phase_5_min: str) -> tuple[str, int]:
    """MVP stub: returns monophasic and 0 gap."""
    return "monophasic", 0

def detect_work_block(activity: dict, events: list[dict]) -> dict | None:
    """MVP stub: returns None."""
    return None

def compute_recovery_cost(sleep: dict | None, readiness: dict | None, baselines: dict) -> float:
    """Calculates recovery cost based on HRV and RHR changes vs baseline."""
    if not sleep:
        return 0.0
        
    hrv = sleep.get("average_hrv")
    rhr = sleep.get("lowest_heart_rate")
    
    hrv_bl = baselines.get("hrv_baseline")
    rhr_bl = baselines.get("rhr_baseline")
    
    hrv_delta = 0.0
    if hrv is not None and hrv_bl:
        hrv_delta = (hrv - hrv_bl) / hrv_bl
        
    rhr_delta = 0.0
    if rhr is not None and rhr_bl:
        rhr_delta = (rhr - rhr_bl) / rhr_bl
        
    return abs(hrv_delta) + abs(rhr_delta)
