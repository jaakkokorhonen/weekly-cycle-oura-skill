import pytest
import json
from unittest.mock import MagicMock
from src.pipeline import Pipeline


def test_pipeline_run_success(
    tmp_path,
    mock_sleep_response,
    mock_readiness_response,
    mock_activity_response,
    mock_heartrate_response,
):
    records_dir = tmp_path / "records"
    raw_dir = tmp_path / "raw_inputs"
    events_file = tmp_path / "events.jsonl"
    events_file.write_text("")

    mock_client = MagicMock()
    mock_client.fetch_range.return_value = {
        "2026-07-18": {
            "sleep": mock_sleep_response["data"],
            "daily_readiness": mock_readiness_response["data"][0],
            "daily_activity": mock_activity_response["data"][0],
            "heartrate": mock_heartrate_response["data"],
        }
    }

    pipeline = Pipeline(
        oura_client=mock_client,
        records_dir=records_dir,
        raw_dir=raw_dir,
        events_filepath=events_file,
    )
    pipeline.run(date_str="2026-07-18")

    # record kirjoitettu
    record_file = records_dir / "2026-07-18.json"
    assert record_file.exists()

    with open(record_file) as f:
        data = json.load(f)

    assert data["date"] == "2026-07-18"
    assert "raw" in data
    assert "derived" in data
    assert "oura" in data
    assert "classification" in data
    assert "load_state" in data
    assert "recommendation" in data

    # raw-tiedosto kirjoitettu (pipeline-sopimus: _write_raw tallentaa raw_dir/YYYY-MM-DD.json)
    raw_file = raw_dir / "2026-07-18.json"
    assert raw_file.exists(), "pipeline._write_raw() ei kirjoittanut raw-tiedostoa"
    with open(raw_file) as f:
        raw = json.load(f)
    assert "sleep" in raw
    assert "daily_readiness" in raw


def test_pipeline_partial_baseline(
    tmp_path,
    mock_sleep_response,
    mock_readiness_response,
    mock_activity_response,
    mock_heartrate_response,
):
    """Alle 14 vrk historiadataa: partial_baseline: true merkitty tietueeseen (tiketti #28)."""
    records_dir = tmp_path / "records"  # tyhja - ei aiempaa historiaa
    raw_dir = tmp_path / "raw_inputs"
    events_file = tmp_path / "events.jsonl"
    events_file.write_text("")

    mock_client = MagicMock()
    mock_client.fetch_range.return_value = {
        "2026-07-18": {
            "sleep": mock_sleep_response["data"],
            "daily_readiness": mock_readiness_response["data"][0],
            "daily_activity": mock_activity_response["data"][0],
            "heartrate": mock_heartrate_response["data"],
        }
    }

    pipeline = Pipeline(
        oura_client=mock_client,
        records_dir=records_dir,
        raw_dir=raw_dir,
        events_filepath=events_file,
    )
    pipeline.run(date_str="2026-07-18")

    record_file = records_dir / "2026-07-18.json"
    with open(record_file) as f:
        data = json.load(f)

    assert data["partial_baseline"] is True, (
        "Alle 14 vrk historiadatalla partial_baseline pitaa olla True"
    )
