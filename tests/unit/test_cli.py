import pytest
from click.testing import CliRunner
from unittest.mock import patch
from src.cli import main_cli

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main_cli, ["--help"])
    assert result.exit_code == 0
    assert "show" in result.output
    assert "log-event" in result.output
    assert "status" in result.output
    assert "analyze" in result.output

@patch("src.cli.Pipeline")
def test_cli_run(mock_pipeline_class):
    mock_pipeline = mock_pipeline_class.return_value
    runner = CliRunner()
    result = runner.invoke(main_cli, ["run", "--date", "2026-07-18"])
    
    assert result.exit_code == 0
    mock_pipeline.run.assert_called_with("2026-07-18")

@patch("src.cli.EventManager")
def test_cli_log_event(mock_event_manager_class):
    mock_event_manager = mock_event_manager_class.return_value
    runner = CliRunner()
    result = runner.invoke(main_cli, [
        "log-event",
        "--type", "caffeine",
        "--amount", "100",
        "--unit", "mg",
        "--note", "espresso"
    ])
    
    assert result.exit_code == 0
    mock_event_manager.log_event.assert_called_once()
    event_arg = mock_event_manager.log_event.call_args[0][0]
    assert event_arg["type"] == "caffeine"
    assert event_arg["amount"] == 100.0
