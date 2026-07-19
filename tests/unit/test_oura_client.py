"""Unit tests for oura_client.py.

All HTTP calls are mocked — no real OURA_TOKEN required.
Ref: issue #24 (CI), #26 (oura_client spec)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses as rsps_lib
from responses import RequestsMock

from oura_client import OuraClient, OuraClientError

BASE = "https://api.ouraring.com"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path: Path) -> OuraClient:
    return OuraClient(token="test-token", raw_dir=tmp_path / "raw_inputs")


def _sleep_item(day: str, item_type: str = "long_sleep", item_id: str = "s1") -> dict:
    return {
        "id": item_id,
        "type": item_type,
        "bedtime_start": f"{day}T22:00:00+03:00",
        "bedtime_end": f"{day}T06:00:00+03:00",
        "total_sleep_duration": 25200,
        "average_hrv": 42.0,
        "lowest_heart_rate": 48,
    }


def _readiness_item(day: str) -> dict:
    return {"day": day, "score": 75, "hrv_balance": 3}


def _activity_item(day: str) -> dict:
    return {"day": day, "active_calories": 650, "steps": 8000}


# ---------------------------------------------------------------------------
# Basic fetch
# ---------------------------------------------------------------------------

@rsps_lib.activate
def test_fetch_range_basic(client: OuraClient) -> None:
    """fetch_range returns structured dict keyed by date."""
    day = "2026-07-18"
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep",
                 json={"data": [_sleep_item(day)], "next_token": None})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_readiness",
                 json={"data": [_readiness_item(day)], "next_token": None})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_activity",
                 json={"data": [_activity_item(day)], "next_token": None})

    result = client.fetch_range(day, day)

    assert day in result
    assert len(result[day]["sleep"]) == 1
    assert result[day]["sleep"][0]["type"] == "long_sleep"
    assert result[day]["daily_readiness"]["score"] == 75
    assert result[day]["daily_activity"]["active_calories"] == 650


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

@rsps_lib.activate
def test_pagination_next_token_followed(client: OuraClient) -> None:
    """next_token chain is followed until exhausted."""
    day1, day2 = "2026-07-17", "2026-07-18"

    # Sleep: page 1 returns next_token, page 2 is the last page
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep",
                 json={"data": [_sleep_item(day1, item_id="s1")], "next_token": "tok123"})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep",
                 json={"data": [_sleep_item(day2, item_id="s2")], "next_token": None})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_readiness",
                 json={"data": [], "next_token": None})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_activity",
                 json={"data": [], "next_token": None})

    result = client.fetch_range(day1, day2)

    assert day1 in result
    assert day2 in result
    assert result[day1]["sleep"][0]["id"] == "s1"
    assert result[day2]["sleep"][0]["id"] == "s2"


@rsps_lib.activate
def test_empty_page_stops_pagination(client: OuraClient) -> None:
    """Empty data list with no next_token stops gracefully."""
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep",
                 json={"data": [], "next_token": None})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_readiness",
                 json={"data": [], "next_token": None})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_activity",
                 json={"data": [], "next_token": None})

    result = client.fetch_range("2026-07-18", "2026-07-18")
    assert result == {}


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@rsps_lib.activate
def test_401_raises_clear_message(client: OuraClient) -> None:
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep", status=401)
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_readiness", status=401)
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_activity", status=401)

    with pytest.raises(OuraClientError, match="401 Unauthorized"):
        client.fetch_range("2026-07-18", "2026-07-18")


@rsps_lib.activate
def test_429_raises_clear_message(client: OuraClient) -> None:
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep", status=429)
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_readiness", status=429)
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_activity", status=429)

    with pytest.raises(OuraClientError, match="429 Too Many Requests"):
        client.fetch_range("2026-07-18", "2026-07-18")


@rsps_lib.activate
def test_500_raises_generic_message(client: OuraClient) -> None:
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep",
                 status=500, body="Internal Server Error")
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_readiness",
                 status=500, body="Internal Server Error")
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_activity",
                 status=500, body="Internal Server Error")

    with pytest.raises(OuraClientError, match="HTTP 500"):
        client.fetch_range("2026-07-18", "2026-07-18")


def test_empty_token_raises() -> None:
    with pytest.raises(OuraClientError, match="OURA_TOKEN is empty"):
        OuraClient(token="")


# ---------------------------------------------------------------------------
# Raw file writing
# ---------------------------------------------------------------------------

@rsps_lib.activate
def test_raw_file_written(client: OuraClient, tmp_path: Path) -> None:
    """Raw inputs are written atomically to data/raw_inputs/YYYY-MM-DD.json."""
    day = "2026-07-18"
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep",
                 json={"data": [_sleep_item(day)], "next_token": None})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_readiness",
                 json={"data": [_readiness_item(day)], "next_token": None})
    rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_activity",
                 json={"data": [_activity_item(day)], "next_token": None})

    client.fetch_range(day, day)

    raw_file = client._raw_dir / f"{day}.json"
    assert raw_file.exists()
    saved = json.loads(raw_file.read_text())
    assert saved["daily_readiness"]["score"] == 75


@rsps_lib.activate
def test_incremental_run_deduplicates_sleep(client: OuraClient) -> None:
    """Re-running fetch_range for the same day does not duplicate sleep items."""
    day = "2026-07-18"
    item = _sleep_item(day, item_id="s1")

    for _ in range(2):
        rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/sleep",
                     json={"data": [item], "next_token": None})
        rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_readiness",
                     json={"data": [_readiness_item(day)], "next_token": None})
        rsps_lib.add(rsps_lib.GET, f"{BASE}/v2/usercollection/daily_activity",
                     json={"data": [_activity_item(day)], "next_token": None})
        client.fetch_range(day, day)

    saved = json.loads((client._raw_dir / f"{day}.json").read_text())
    assert len(saved["sleep"]) == 1  # no duplicate
