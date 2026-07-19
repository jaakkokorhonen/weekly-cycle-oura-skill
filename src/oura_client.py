"""Oura API v2 client — I/O layer only, no business logic.

Ref: oura-api-decisions.md (#14, #15, #16, #17, #19, #20, #21)
Ref: design.md §1 MVP-architecture
Ref: issue #26
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

BASE_URL = "https://api.ouraring.com"

# MVP endpoints — ordered by dependency (sleep first: contains HRV + RHR + naps)
MVP_ENDPOINTS: list[tuple[str, str]] = [
    ("sleep", "/v2/usercollection/sleep"),
    ("daily_readiness", "/v2/usercollection/daily_readiness"),
    ("daily_activity", "/v2/usercollection/daily_activity"),
    # heartrate endpoint reserved for post-MVP
]


class OuraClientError(Exception):
    """Raised on HTTP 4xx/5xx or unexpected API response."""


class OuraClient:
    """Fetches Oura API v2 data for a date range.

    Usage::

        client = OuraClient(token="...", raw_dir=Path("data/raw_inputs"))
        records = client.fetch_range("2026-06-19", "2026-07-19")
        # returns: dict[date_str, {"sleep": [...], "daily_readiness": {...}, "daily_activity": {...}}]
    """

    def __init__(self, token: str, raw_dir: Path | None = None) -> None:
        if not token:
            raise OuraClientError("OURA_TOKEN is empty — set it in config.yaml or env")
        self._token = token
        self._raw_dir = raw_dir or Path("data/raw_inputs")
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
        dict with keys "sleep" (list), "daily_readiness" (dict | None),
        "daily_activity" (dict | None).

        sleep items include long_sleep (night), short_sleep and rest (naps).
        Callers (pipeline.py) are responsible for separating them by type.
        """
        log.info("fetch_range %s .. %s", start_date, end_date)
        raw: dict[str, dict[str, list[Any]]] = {}

        for key, path in MVP_ENDPOINTS:
            items = self._fetch_paginated(path, start_date, end_date)
            for item in items:
                # sleep items are keyed by day derived from bedtime_start
                # readiness/activity items have a 'day' field directly
                day = self._extract_day(key, item)
                if day is None:
                    continue
                bucket = raw.setdefault(day, {"sleep": [], "daily_readiness": None, "daily_activity": None})
                if key == "sleep":
                    bucket["sleep"].append(item)
                elif key == "daily_readiness":
                    bucket["daily_readiness"] = item
                elif key == "daily_activity":
                    bucket["daily_activity"] = item

        self._write_raw(raw)
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
            # Replace start_date with cursor for subsequent pages
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
            # bedtime_start is ISO 8601 with tz offset — take date part only
            bedtime_start: str | None = item.get("bedtime_start")
            if not bedtime_start:
                return None
            # ISO 8601: '2026-07-18T22:30:00+03:00' or '2026-07-18T22:30:00Z'
            # We want the *local* date of when the person went to bed.
            # pipeline.py handles full tz conversion; here we use date prefix.
            return bedtime_start[:10]
        # daily_readiness and daily_activity have a plain 'day' field
        return item.get("day")

    def _write_raw(
        self, data: dict[str, dict[str, Any]]
    ) -> None:
        """Persist raw API responses to data/raw_inputs/YYYY-MM-DD.json.

        Does NOT overwrite an existing file — new data is merged at the
        endpoint key level so incremental runs preserve previous content.
        """
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        for day, payload in data.items():
            path = self._raw_dir / f"{day}.json"
            if path.exists():
                try:
                    existing = json.loads(path.read_text(encoding="utf-8"))
                    # Merge: append new sleep items, overwrite scalars
                    existing_sleep: list = existing.get("sleep", [])
                    new_sleep: list = payload.get("sleep", [])
                    merged_sleep = existing_sleep + [
                        s for s in new_sleep
                        if s.get("id") not in {e.get("id") for e in existing_sleep}
                    ]
                    merged = {**existing, **payload, "sleep": merged_sleep}
                except (json.JSONDecodeError, TypeError):
                    merged = payload
            else:
                merged = payload

            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)  # atomic rename
        log.info("Wrote raw_inputs for %d day(s)", len(data))
