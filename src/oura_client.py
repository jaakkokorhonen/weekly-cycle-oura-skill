"""Oura API v2 client — I/O layer only, no business logic.

Ref: oura-api-decisions.md (#14, #15, #16, #17, #19, #20, #21)
Ref: design.md §1 MVP-architecture
Ref: issue #26

Tallennusvastuu: tämä moduuli EI kirjoita data/-kansioon.
fetch_range() palauttaa raakadatan pipeline.py:lle, joka persistoi sen
ennen rikastusvaihetta (data/raw_inputs/YYYY-MM-DD.json).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.ouraring.com"

# MVP endpoints — ordered by dependency (sleep first: contains HRV + RHR + naps)
MVP_ENDPOINTS: list[tuple[str, str]] = [
    ("sleep", "/v2/usercollection/sleep"),
    ("daily_readiness", "/v2/usercollection/daily_readiness"),
    ("daily_activity", "/v2/usercollection/daily_activity"),
    ("heartrate", "/v2/usercollection/heartrate"),  # MVP: lepotilojen tunnistus (source == 'rest')
]


class OuraClientError(Exception):
    """Raised on HTTP 4xx/5xx or unexpected API response."""


class OuraClient:
    """Fetches Oura API v2 data for a date range.

    Pure I/O layer — no file writes, no business logic.

    Usage::

        client = OuraClient(token="...")
        records = client.fetch_range("2026-06-19", "2026-07-19")
        # returns: dict[date_str, {
        #   "sleep": list,
        #   "daily_readiness": dict | None,
        #   "daily_activity": dict | None,
        #   "heartrate": list,
        # }]

    Caller (pipeline.py) is responsible for persisting raw data and
    all subsequent enrichment steps.
    """

    def __init__(self, token: str) -> None:
        if not token:
            raise OuraClientError("OURA_TOKEN is empty — set it in config.yaml or env")
        self._token = token
        self._session = requests.Session()
        self._session.headers.update(
            {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch_range(
        self, start_date: str, end_date: str
    ) -> dict[str, dict[str, Any]]:
        """Fetch all MVP endpoints for [start_date, end_date] inclusive.

        Returns a dict keyed by date string (YYYY-MM-DD). Each value is a
        dict with keys:
          "sleep"           — list (long_sleep, short_sleep, rest/nap items)
          "daily_readiness" — dict | None
          "daily_activity"  — dict | None
          "heartrate"       — list (all HR samples for the day)

        sleep items include long_sleep (night), short_sleep and rest (naps).
        heartrate items with source == 'rest' can be used to detect naps.
        pipeline.py is responsible for separating and persisting all data.
        """
        log.info("fetch_range %s .. %s", start_date, end_date)
        raw: dict[str, dict[str, Any]] = {}

        for key, path in MVP_ENDPOINTS:
            items = self._fetch_paginated(path, start_date, end_date)
            for item in items:
                day = self._extract_day(key, item)
                if day is None:
                    continue
                bucket = raw.setdefault(
                    day,
                    {
                        "sleep": [],
                        "daily_readiness": None,
                        "daily_activity": None,
                        "heartrate": [],
                    },
                )
                if key == "sleep":
                    bucket["sleep"].append(item)
                elif key == "daily_readiness":
                    bucket["daily_readiness"] = item
                elif key == "daily_activity":
                    bucket["daily_activity"] = item
                elif key == "heartrate":
                    bucket["heartrate"].append(item)

        return raw

    def fetch_baseline_range(self, days: int = 30) -> dict[str, dict[str, Any]]:
        """Fetch the last `days` days as baseline window (first-run helper)."""
        today = date.today()
        start = (today - timedelta(days=days)).isoformat()
        end = today.isoformat()
        log.info("fetch_baseline_range: %d days (%s .. %s)", days, start, end)
        return self.fetch_range(start, end)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_paginated(
        self, path: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Fetch all pages for a single endpoint, following next_token cursors."""
        items: list[dict[str, Any]] = []
        params: dict[str, str] = {"start_date": start_date, "end_date": end_date}

        while True:
            response = self._get(path, params)
            data = response.get("data", [])
            items.extend(data)
            next_token = response.get("next_token")
            if not next_token:
                break
            params = {"next_token": next_token}
            log.debug("%s: fetched %d items, following next_token", path, len(data))

        log.debug("%s: total %d items", path, len(items))
        return items

    def _get(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        """Execute a single GET request and return parsed JSON."""
        url = f"{BASE_URL}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            raise OuraClientError(f"Network error fetching {path}: {exc}") from exc

        if resp.status_code == 401:
            raise OuraClientError(
                "Oura API: 401 Unauthorized — check OURA_TOKEN in config.yaml"
            )
        if resp.status_code == 429:
            raise OuraClientError(
                "Oura API: 429 Too Many Requests — back off and retry later"
            )
        if not resp.ok:
            raise OuraClientError(
                f"Oura API: HTTP {resp.status_code} for {path} — {resp.text[:200]}"
            )

        try:
            return resp.json()
        except ValueError as exc:
            raise OuraClientError(
                f"Oura API: invalid JSON from {path}: {exc}"
            ) from exc

    @staticmethod
    def _extract_day(endpoint_key: str, item: dict[str, Any]) -> str | None:
        """Extract the canonical YYYY-MM-DD date from an API item."""
        if endpoint_key == "sleep":
            bedtime_start: str | None = item.get("bedtime_start")
            if not bedtime_start:
                return None
            # ISO 8601: '2026-07-18T22:30:00+03:00' — take date prefix.
            # pipeline.py handles full tz conversion.
            return bedtime_start[:10]
        if endpoint_key == "heartrate":
            # heartrate items have a 'timestamp' field: '2026-07-18T06:00:00+03:00'
            timestamp: str | None = item.get("timestamp")
            if not timestamp:
                return None
            return timestamp[:10]
        # daily_readiness and daily_activity have a plain 'day' field
        return item.get("day")
