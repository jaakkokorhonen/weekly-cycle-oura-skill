import pytest
from src.rule_engine import RuleEngine

@pytest.fixture
def rule_engine():
    config = {
        "high_load_kcal_threshold": 1000,
        "high_load_kcal_hybrid_threshold": 800,
        "high_load_hrv_suppression": -0.15,
        "integration_kcal_max": 500,
        "nap_sleep_max": 6.5,
        "nap_hrv_suppression": -0.10
    }
    return RuleEngine(config=config)

def test_classify_day_high_load(rule_engine):
    features = {"derived_active_kcal": 1100, "derived_hrv_delta_pct": -0.05}
    assert rule_engine.classify_day(features) == "HIGH_LOAD_DAY"
    
    features = {"derived_active_kcal": 850, "derived_hrv_delta_pct": -0.18}
    assert rule_engine.classify_day(features) == "HIGH_LOAD_DAY"

def test_classify_day_integration(rule_engine):
    features = {
        "derived_active_kcal": 300,
        "derived_hrv_delta_pct": 0.05,
        "derived_deep_sleep_vs_30d": 100,  # above median
        "derived_rhr_vs_30d": -2          # below median
    }
    assert rule_engine.classify_day(features) == "INTEGRATION_DAY"

def test_state_transitions(rule_engine):
    history = [
        {"classification": "BASELINE_DAY", "derived_hrv_delta_pct": 0.0},
        {"classification": "HIGH_LOAD_DAY", "derived_hrv_delta_pct": -0.20}
    ]
    # Day after HIGH_LOAD_DAY is Expansion
    assert rule_engine.get_state(history) == "Expansion"

def test_get_tactical_suggestion_nap(rule_engine):
    features = {
        "total_sleep_last_24h": 5.8,
        "derived_hrv_delta_pct": -0.12
    }
    assert rule_engine.get_tactical_suggestion(features) == "nap"

def test_insufficient_evidence(rule_engine):
    # Single bad night should not degrade state to Incomplete Reset
    history_1_bad = [
        {"derived_hrv_delta_pct": 0.0, "oura_resilience_level": "normal"},
        {"derived_hrv_delta_pct": -0.25, "oura_resilience_level": "normal"}
    ]
    assert rule_engine.get_capacity_trend(history_1_bad) == "Stable"
    
    # 3+ bad nights degrades trend
    history_3_bad = [
        {"derived_hrv_delta_pct": 0.0, "oura_resilience_level": "normal"},
        {"derived_hrv_delta_pct": -0.25, "oura_resilience_level": "normal"},
        {"derived_hrv_delta_pct": -0.22, "oura_resilience_level": "normal"},
        {"derived_hrv_delta_pct": -0.20, "oura_resilience_level": "normal"}
    ]
    assert rule_engine.get_capacity_trend(history_3_bad) == "Suppressed"
