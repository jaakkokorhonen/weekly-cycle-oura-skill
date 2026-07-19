import pytest
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
    event = {"timestamp": "2026-07-18T14:30:00+03:00", "type": "invalid_type", "amount": 100.0}
    with pytest.raises(ValueError):
        manager.log_event(event)


def test_log_event_missing_required_field(tmp_path):
    """caffeine ilman amount-kenttää — ValueError."""
    events_file = tmp_path / "events.jsonl"
    manager = EventManager(filepath=events_file)
    event = {"timestamp": "2026-07-18T14:30:00+03:00", "type": "caffeine"}
    with pytest.raises(ValueError):
        manager.log_event(event)


def test_log_event_amount_zero(tmp_path):
    """amount <= 0 — ValueError."""
    events_file = tmp_path / "events.jsonl"
    manager = EventManager(filepath=events_file)
    event = {"timestamp": "2026-07-18T14:30:00+03:00", "type": "caffeine", "amount": 0.0}
    with pytest.raises(ValueError):
        manager.log_event(event)


def test_log_nap_requires_duration(tmp_path):
    events_file = tmp_path / "events.jsonl"
    manager = EventManager(filepath=events_file)
    event = {"timestamp": "2026-07-18T14:30:00+03:00", "type": "nap"}
    with pytest.raises(ValueError):
        manager.log_event(event)


def test_get_events_range(temp_events_file):
    """Paluuarvo on dict[str, list] — avain aina läsnä."""
    manager = EventManager(filepath=temp_events_file)
    result = manager.get_events_range("2026-07-18", "2026-07-18")
    assert "2026-07-18" in result
    assert len(result["2026-07-18"]) == 2  # caffeine + alcohol fixture-tiedostossa


def test_get_events_range_empty_day(temp_events_file):
    """Päivä ilman tapahtumia palauttaa tyhjän listan — ei KeyError."""
    manager = EventManager(filepath=temp_events_file)
    result = manager.get_events_range("2026-07-17", "2026-07-19")
    assert result["2026-07-17"] == []
    assert result["2026-07-19"] == []


def test_get_events_range_timezone(tmp_path):
    """UTC+3-offsetilla kirjattu kofeiini löytyy oikealta lokaalilta päivältä."""
    events_file = tmp_path / "events.jsonl"
    events_file.write_text(
        '{"timestamp": "2026-07-18T10:30:00+03:00", "type": "caffeine",'
        ' "amount": 100.0, "unit": "mg", "note": "morning coffee"}\n'
    )
    manager = EventManager(filepath=events_file)
    result = manager.get_events_range("2026-07-18", "2026-07-18")
    assert len(result["2026-07-18"]) == 1
    assert result["2026-07-18"][0]["type"] == "caffeine"
