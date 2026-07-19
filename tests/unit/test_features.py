import pytest
import datetime
from src.features import (
    compute_caffeine_window,
    compute_alcohol_window,
    segment_sleep_night,
    detect_work_block,
    compute_recovery_cost
)

def test_compute_caffeine_window():
    sleep_start = datetime.datetime.fromisoformat("2026-07-18T22:00:00+03:00")
    events = [
        {"timestamp": "2026-07-18T10:30:00+03:00", "type": "caffeine", "amount": 100.0, "unit": "mg"}
    ]
    
    gap = compute_caffeine_window(events, sleep_start)
    assert gap == 11.5

def test_compute_alcohol_window():
    sleep_start = datetime.datetime.fromisoformat("2026-07-18T22:00:00+03:00")
    events = [
        {"timestamp": "2026-07-18T20:00:00+03:00", "type": "alcohol", "amount": 2.0, "unit": "units"}
    ]
    
    gap, before_first_sleep = compute_alcohol_window(events, sleep_start)
    assert gap == 2.0
    assert before_first_sleep is True

def test_segment_sleep_night_monophasic():
    # A standard sleep phase representation with brief awake periods
    sleep_phase_5_min = "444222111111222222222233333332222222222"
    
    mode, gap_dur = segment_sleep_night(sleep_phase_5_min)
    assert mode == "monophasic"
    assert gap_dur == 0

def test_segment_sleep_night_biphasic():
    # Long wake gap (coded as '4') in the middle
    sleep_phase_5_min = "222222221111111444444444444444222222333333"
    
    mode, gap_dur = segment_sleep_night(sleep_phase_5_min)
    assert mode == "biphasic"
    assert gap_dur == 75  # 15 intervals * 5 mins = 75 mins

def test_detect_work_block():
    activity = {
        "resting_time": 30000,
        "sedentary_time": 20000,
        "low_activity_time": 5000
    }
    events = [
        {"timestamp": "2026-07-18T09:00:00+03:00", "type": "work_start"},
        {"timestamp": "2026-07-18T17:00:00+03:00", "type": "work_end"}
    ]
    
    start, end, duration, score = detect_work_block(activity, events)
    assert start == "09:00"
    assert end == "17:00"
    assert duration == 8.0

def test_compute_recovery_cost():
    sleep = {
        "average_hrv": 30,
        "lowest_heart_rate": 55,
        "efficiency": 90
    }
    readiness = {
        "temperature_deviation": 0.2
    }
    baselines = {
        "hrv_baseline": 35,
        "rhr_baseline": 50
    }
    
    cost = compute_recovery_cost(sleep, readiness, baselines)
    assert cost > 0.0
