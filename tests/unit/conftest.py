import pytest
import datetime

@pytest.fixture
def mock_sleep_response():
    """Mock Oura API v2 /v2/usercollection/sleep response data."""
    return {
        "data": [
            {
                "id": "sleep_session_1",
                "day": "2026-07-18",
                "type": "long_sleep",
                "bedtime_start": "2026-07-18T19:35:00+03:00",
                "bedtime_end": "2026-07-19T03:44:00+03:00",
                "total_sleep_duration": 27180,  # 7h 33m
                "time_in_bed": 29340,           # 8h 9m
                "efficiency": 93,
                "latency": 1080,                # 18m
                "deep_sleep_duration": 4380,    # 1h 13m
                "rem_sleep_duration": 6840,     # 1h 54m
                "light_sleep_duration": 15960,  # 4h 26m
                "awake_duration": 2160,         # 36m
                "average_heart_rate": 58.4,
                "lowest_heart_rate": 51.0,
                "average_hrv": 28,
                "sleep_phase_5_min": "44422211111122222222223333333222222222222111111111222222222211111111114444"
            }
        ]
    }

@pytest.fixture
def mock_readiness_response():
    """Mock Oura API v2 /v2/usercollection/daily_readiness response data."""
    return {
        "data": [
            {
                "id": "readiness_1",
                "day": "2026-07-18",
                "score": 78,
                "temperature_deviation": 0.0,
                "temperature_trend_deviation": 0.15,
                "contributors": {
                    "activity_balance": 59,
                    "body_temperature": 100,
                    "hrv_balance": 94,
                    "previous_day_activity": 75,
                    "previous_night": 98,
                    "recovery_index": 94,
                    "resting_heart_rate": 71,
                    "sleep_balance": 70
                }
            }
        ]
    }

@pytest.fixture
def mock_activity_response():
    """Mock Oura API v2 /v2/usercollection/daily_activity response data."""
    return {
        "data": [
            {
                "id": "activity_1",
                "day": "2026-07-18",
                "score": 97,
                "steps": 5266,
                "active_calories": 198,
                "total_calories": 2440,
                "equivalent_walking_distance": 2900,
                "low_activity_time": 6780,       # 1h 53m
                "medium_activity_time": 960,     # 16m
                "high_activity_time": 180,       # 3m
                "sedentary_time": 22980,         # 6h 23m
                "resting_time": 55440            # 15h 24m
            }
        ]
    }

@pytest.fixture
def mock_heartrate_response():
    """Mock Oura API v2 /v2/usercollection/heartrate response data."""
    return {
        "data": [
            {"bpm": 72, "source": "awake", "timestamp": "2026-07-18T10:00:00+03:00"},
            {"bpm": 55, "source": "rest", "timestamp": "2026-07-18T14:00:00+03:00"},
            {"bpm": 56, "source": "rest", "timestamp": "2026-07-18T14:15:00+03:00"},
            {"bpm": 54, "source": "rest", "timestamp": "2026-07-18T14:20:00+03:00"},
            {"bpm": 85, "source": "workout", "timestamp": "2026-07-18T16:00:00+03:00"},
            {"bpm": 52, "source": "sleep", "timestamp": "2026-07-18T23:30:00+03:00"}
        ]
    }

@pytest.fixture
def temp_events_file(tmp_path):
    """Creates a temporary events.jsonl file for testing event_manager."""
    events_file = tmp_path / "events.jsonl"
    events_file.write_text(
        '{"timestamp": "2026-07-18T10:30:00+03:00", "type": "caffeine", "amount": 100.0, "unit": "mg", "note": "coffee"}\n'
        '{"timestamp": "2026-07-18T20:00:00+03:00", "type": "alcohol", "amount": 2.0, "unit": "units", "note": "beer"}\n'
    )
    return events_file
