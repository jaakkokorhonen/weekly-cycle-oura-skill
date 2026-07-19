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


def test_compute_caffeine_window_no_caffeine():
    """Ei kofeiinia — palauttaa None."""
    sleep_start = datetime.datetime.fromisoformat("2026-07-18T22:00:00+03:00")
    gap = compute_caffeine_window([], sleep_start)
    assert gap is None


def test_compute_alcohol_window():
    sleep_start = datetime.datetime.fromisoformat("2026-07-18T22:00:00+03:00")
    events = [
        {"timestamp": "2026-07-18T20:00:00+03:00", "type": "alcohol", "amount": 2.0, "unit": "units"}
    ]
    gap, before_first_sleep = compute_alcohol_window(events, sleep_start)
    assert gap == 2.0
    assert before_first_sleep is True


def test_compute_alcohol_window_no_alcohol():
    """Ei alkoholia — palauttaa (None, False)."""
    sleep_start = datetime.datetime.fromisoformat("2026-07-18T22:00:00+03:00")
    gap, before_first_sleep = compute_alcohol_window([], sleep_start)
    assert gap is None
    assert before_first_sleep is False


def test_segment_sleep_night_returns_stub():
    """MVP: segment_sleep_night stubbattu — palauttaa aina monophasic."""
    sleep_phase_5_min = "222222221111111444444444444444222222333333"
    mode, gap_dur = segment_sleep_night(sleep_phase_5_min)
    assert mode == "monophasic"  # stub-arvo
    assert gap_dur == 0          # stub-arvo


def test_segment_sleep_night_standard_returns_stub():
    """MVP: myös normaali myönophasic-input palauttaa stubin."""
    sleep_phase_5_min = "44422211111122222222223333333222222222222111111111222222222211111111114444"
    mode, gap_dur = segment_sleep_night(sleep_phase_5_min)
    assert mode == "monophasic"
    assert gap_dur == 0


def test_detect_work_block_returns_stub():
    """MVP: detect_work_block stubbattu — palauttaa aina None."""
    result = detect_work_block(activity={}, events=[])
    assert result is None


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


def test_compute_recovery_cost_zero_delta():
    """HRV ja RHR täsmälleen baselinessa — recovery_cost lähellä nollaa."""
    sleep = {
        "average_hrv": 35,
        "lowest_heart_rate": 50,
        "efficiency": 95
    }
    readiness = {"temperature_deviation": 0.0}
    baselines = {"hrv_baseline": 35, "rhr_baseline": 50}
    cost = compute_recovery_cost(sleep, readiness, baselines)
    assert cost >= 0.0
