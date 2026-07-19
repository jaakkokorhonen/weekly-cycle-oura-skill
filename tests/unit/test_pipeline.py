import pytest
import json
from unittest.mock import MagicMock
from src.pipeline import Pipeline

def test_pipeline_run_success(tmp_path, mock_sleep_response, mock_readiness_response, mock_activity_response, mock_heartrate_response):
    records_dir = tmp_path / "records"
    raw_dir = tmp_path / "raw_inputs"
    events_file = tmp_path / "events.jsonl"
    
    # Write empty events
    events_file.write_text("")
    
    # Mock clients
    mock_client = MagicMock()
    mock_client.fetch_range.return_value = {
        "2026-07-18": {
            "sleep": mock_sleep_response["data"],
            "readiness": mock_readiness_response["data"][0],
            "activity": mock_activity_response["data"][0],
            "heartrate": mock_heartrate_response["data"]
        }
    }
    
    pipeline = Pipeline(
        oura_client=mock_client,
        records_dir=records_dir,
        raw_dir=raw_dir,
        events_filepath=events_file
    )
    
    # Run
    pipeline.run(date_str="2026-07-18")
    
    # Check if files written
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
