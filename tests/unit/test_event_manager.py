import pytest
import datetime
from src.event_manager import EventManager

def test_log_event_valid(tmp_path):
    events_file = tmp_path / "events.jsonl"
    manager = EventManager(filepath=events_file)
    
    event = {
        "timestamp": "2026-07-18T14:30:00+03:00",
        "type": "caffeine",
        "amount": 100.0,
        "unit": "mg",
        "note": "espresso"
    }
    manager.log_event(event)
    
    logged = manager.get_events_for_date("2026-07-18")
    assert len(logged) == 1
    assert logged[0]["amount"] == 100.0

def test_log_event_invalid_type(tmp_path):
    events_file = tmp_path / "events.jsonl"
    manager = EventManager(filepath=events_file)
    
    event = {
        "timestamp": "2026-07-18T14:30:00+03:00",
        "type": "invalid_type",
        "amount": 100.0
    }
    with pytest.raises(ValueError):
        manager.log_event(event)

def test_log_nap_requires_duration(tmp_path):
    events_file = tmp_path / "events.jsonl"
    manager = EventManager(filepath=events_file)
    
    event = {
        "timestamp": "2026-07-18T14:30:00+03:00",
        "type": "nap"
    }
    with pytest.raises(ValueError):
        manager.log_event(event)

def test_get_events_range(temp_events_file):
    manager = EventManager(filepath=temp_events_file)
    
    # 2026-07-18T10:30 and 2026-07-18T20:00 are in file
    start = datetime.datetime.fromisoformat("2026-07-18T00:00:00+03:00")
    end = datetime.datetime.fromisoformat("2026-07-18T12:00:00+03:00")
    
    events = manager.get_events_range(start, end)
    assert len(events) == 1
    assert events[0]["type"] == "caffeine"
