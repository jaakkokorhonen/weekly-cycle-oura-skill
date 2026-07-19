import pytest
import responses
from src.oura_client import OuraClient, OuraClientError

@responses.activate
def test_fetch_range_success(mock_sleep_response, mock_readiness_response, mock_activity_response, mock_heartrate_response):
    # Setup mocks
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/sleep", json=mock_sleep_response, status=200)
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/daily_readiness", json=mock_readiness_response, status=200)
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/daily_activity", json=mock_activity_response, status=200)
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/heartrate", json=mock_heartrate_response, status=200)

    client = OuraClient(token="test_token")
    res = client.fetch_range(start_date="2026-07-18", end_date="2026-07-18")

    assert "2026-07-18" in res
    day_data = res["2026-07-18"]
    assert len(day_data["sleep"]) == 1
    assert day_data["readiness"]["score"] == 78
    assert day_data["activity"]["steps"] == 5266
    assert len(day_data["heartrate"]) == 6

@responses.activate
def test_fetch_range_pagination():
    mock_page_1 = {
        "data": [{"id": "s1", "day": "2026-07-18", "type": "long_sleep"}],
        "next_token": "token_page_2"
    }
    mock_page_2 = {
        "data": [{"id": "s2", "day": "2026-07-18", "type": "short_sleep"}]
    }
    
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/sleep", json=mock_page_1, status=200)
    # Match request with next_token parameter
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/sleep", json=mock_page_2, status=200, match=[responses.matchers.query_param_matcher({"next_token": "token_page_2"})])
    
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/daily_readiness", json={"data": []}, status=200)
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/daily_activity", json={"data": []}, status=200)
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/heartrate", json={"data": []}, status=200)

    client = OuraClient(token="test_token")
    res = client.fetch_range(start_date="2026-07-18", end_date="2026-07-18")
    
    assert len(res["2026-07-18"]["sleep"]) == 2

@responses.activate
def test_fetch_range_error():
    responses.add(responses.GET, "https://api.ouraring.com/v2/usercollection/sleep", status=401, json={"message": "Unauthorized"})

    client = OuraClient(token="invalid_token")
    with pytest.raises(OuraClientError):
        client.fetch_range(start_date="2026-07-18", end_date="2026-07-18")
