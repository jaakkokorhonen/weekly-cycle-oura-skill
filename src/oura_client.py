import requests
import datetime
from urllib.parse import urljoin

class OuraClientError(Exception):
    """Exception raised for Oura API client errors."""
    pass

class OuraClient:
    BASE_URL = "https://api.ouraring.com"

    def __init__(self, token: str):
        if not token:
            raise OuraClientError("Oura API personal access token is required.")
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    def _fetch_endpoint(self, endpoint: str, start_date: str, end_date: str) -> list[dict]:
        """Fetches data from an endpoint with start/end dates and handles pagination."""
        url = urljoin(self.BASE_URL, endpoint)
        
        # Prepare query parameters
        params = {"start_date": start_date}
        if end_date:
            params["end_date"] = end_date
            
        all_data = []
        page_count = 0
        max_pages = 10  # safety limit to prevent infinite loop

        while url and page_count < max_pages:
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
            except requests.RequestException as e:
                raise OuraClientError(f"HTTP request failed: {e}")

            if response.status_code >= 400:
                raise OuraClientError(f"Oura API returned error status {response.status_code}: {response.text}")

            try:
                payload = response.json()
            except ValueError:
                raise OuraClientError(f"Failed to parse JSON response from Oura API: {response.text}")

            all_data.extend(payload.get("data", []))
            
            # Check for pagination cursor
            next_token = payload.get("next_token")
            if next_token:
                params = {"next_token": next_token}
                page_count += 1
            else:
                break

        return all_data

    def fetch_range(self, start_date: str, end_date: str) -> dict[str, dict]:
        """Fetches sleep, daily_readiness, daily_activity, and heartrate for a date range.
        
        Returns:
            dict[date_str, {
                "sleep": list,
                "readiness": dict | None,
                "activity": dict | None,
                "heartrate": list
            }]
        """
        # Validate dates
        try:
            start_dt = datetime.date.fromisoformat(start_date)
            end_dt = datetime.date.fromisoformat(end_date)
            if start_dt > end_dt:
                raise ValueError("start_date must be before or equal to end_date")
        except ValueError as e:
            raise OuraClientError(f"Invalid date format: {e}")

        # Fetch endpoints
        sleep_data = self._fetch_endpoint("v2/usercollection/sleep", start_date, end_date)
        readiness_data = self._fetch_endpoint("v2/usercollection/daily_readiness", start_date, end_date)
        activity_data = self._fetch_endpoint("v2/usercollection/daily_activity", start_date, end_date)
        heartrate_data = self._fetch_endpoint("v2/usercollection/heartrate", start_date, end_date)

        # Structure by day
        records = {}
        
        # Initialize day records for every day in the range
        curr = start_dt
        while curr <= end_dt:
            day_str = curr.isoformat()
            records[day_str] = {
                "sleep": [],
                "readiness": None,
                "activity": None,
                "heartrate": []
            }
            curr += datetime.timedelta(days=1)

        # Distribute sleep sessions (can have multiple sessions per day)
        for s in sleep_data:
            day = s.get("day")
            if day in records:
                records[day]["sleep"].append(s)

        # Distribute readiness (typically one per day)
        for r in readiness_data:
            day = r.get("day")
            if day in records:
                records[day]["readiness"] = r

        # Distribute activity (typically one per day)
        for a in activity_data:
            day = a.get("day")
            if day in records:
                records[day]["activity"] = a

        # Distribute heartrate (many readings per day, we group by local calendar date)
        for hr in heartrate_data:
            ts = hr.get("timestamp")
            if ts:
                try:
                    # Oura heartrate timestamp is ISO format, e.g. 2026-07-18T10:00:00+03:00
                    dt = datetime.datetime.fromisoformat(ts)
                    day_str = dt.date().isoformat()
                    if day_str in records:
                        records[day_str]["heartrate"].append(hr)
                except ValueError:
                    continue

        return records
