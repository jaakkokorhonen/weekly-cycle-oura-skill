"""TDD skeletot: src/mcp_server.py (#33)

MCP-palvelinta ei käynnistetä testeissä — testataan työkalufunktiot
suoraan yksikkötesteillä ilman MCP-protokollaa.

Hyväksymiskriteerit (#33):
- get_status palauttaa vaaditut avaimet
- log_event kutsuu event_manageria oikeilla arvoilla
- run_pipeline palauttaa validin tietueen fixture-datalla
- run_pipeline palauttaa selkeän virheviestin API-virheessä, ei kaada palvelinta
- get_daily_report palauttaa tallennetun tietueen ilman API-kutsua
"""

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Apufunktio: minimaalinen mock-pipeline-tulos
# ---------------------------------------------------------------------------

def _mock_record(date: str = "2026-07-18") -> dict:
    return {
        "date": date,
        "classification": "BASELINE_DAY",
        "load_state": "Neutral",
        "recommendation": "Baseline range. No special action indicated.",
        "triggered_rule": None,
        "partial_baseline": False,
    }


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

def test_get_status_returns_expected_keys():
    """get_status() palauttaa dictionaryn jossa vaaditut avaimet (#33)."""
    with patch("src.mcp_server.Pipeline") as MockPipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.get_latest_record.return_value = _mock_record()
        MockPipeline.return_value = mock_pipeline

        from src.mcp_server import get_status  # noqa: PLC0415

        result = get_status()

    assert isinstance(result, dict)
    for key in ("date", "classification", "load_state", "recommendation"):
        assert key in result, f"Puuttuva avain: {key}"


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------

def test_log_event_caffeine_writes_to_events(tmp_path):
    """log_event() kutsuu event_manager.log_event() oikeilla arvoilla (#33)."""
    with patch("src.mcp_server.EventManager") as MockEM:
        mock_em = MagicMock()
        MockEM.return_value = mock_em

        from src.mcp_server import log_event  # noqa: PLC0415

        result = log_event(type="caffeine", amount=100.0, unit="mg", note="espresso")

    mock_em.log_event.assert_called_once()
    call_kwargs = mock_em.log_event.call_args[0][0]  # ensimmäinen positional arg (dict)
    assert call_kwargs["type"] == "caffeine"
    assert call_kwargs["amount"] == 100.0
    assert isinstance(result, str)  # vahvistusviesti


# ---------------------------------------------------------------------------
# run_pipeline
# ---------------------------------------------------------------------------

def test_run_pipeline_returns_valid_record():
    """run_pipeline() palauttaa classification + recommendation fixture-datalla (#33)."""
    with patch("src.mcp_server.Pipeline") as MockPipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = _mock_record()
        MockPipeline.return_value = mock_pipeline

        from src.mcp_server import run_pipeline  # noqa: PLC0415

        result = run_pipeline(date="2026-07-18")

    assert "classification" in result
    assert "recommendation" in result
    assert result["date"] == "2026-07-18"


def test_run_pipeline_api_error_returns_error_message():
    """run_pipeline() palauttaa selkeän virheviestin API-virheessä, ei kaada palvelinta (#33)."""
    with patch("src.mcp_server.Pipeline") as MockPipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.run.side_effect = Exception("API connection failed")
        MockPipeline.return_value = mock_pipeline

        from src.mcp_server import run_pipeline  # noqa: PLC0415

        result = run_pipeline(date="2026-07-18")

    assert "error" in result
    assert isinstance(result["error"], str)
    assert len(result["error"]) > 0


# ---------------------------------------------------------------------------
# get_daily_report
# ---------------------------------------------------------------------------

def test_get_daily_report_reads_record_without_api_call():
    """get_daily_report() lukee tallennetun tietueen — ei tee API-kutsua (#33)."""
    stored = _mock_record("2026-07-18")

    with patch("src.mcp_server.Pipeline") as MockPipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.get_record.return_value = stored
        mock_pipeline.run.side_effect = AssertionError("get_daily_report ei saa kutsua run()")
        MockPipeline.return_value = mock_pipeline

        from src.mcp_server import get_daily_report  # noqa: PLC0415

        result = get_daily_report(date="2026-07-18")

    mock_pipeline.run.assert_not_called()
    assert result["date"] == "2026-07-18"
    assert "classification" in result
