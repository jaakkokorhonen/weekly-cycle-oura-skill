import pytest
from src.rule_engine import RuleEngine
from src.features import DayRecord


@pytest.fixture
def rule_engine():
    config = {
        "high_load_kcal_hard": 1000,
        "high_load_kcal_soft": 800,
        "high_load_hrv_delta": -0.15,
        "integration_min_conditions": 3,
        "incomplete_reset_days": 3,
    }
    return RuleEngine(config=config)


def test_classify_day_high_load_hard(rule_engine):
    """Kalorit > hard threshold — HIGH_LOAD_DAY."""
    features = {"active_calories": 1100, "hrv_delta_pct": -0.05}
    assert rule_engine.classify_day(features) == "HIGH_LOAD_DAY"


def test_classify_day_high_load_hybrid(rule_engine):
    """Hybriditapaus: kalorit 800-1000 + HRV suppressed — HIGH_LOAD_DAY."""
    features = {"active_calories": 850, "hrv_delta_pct": -0.18}
    assert rule_engine.classify_day(features) == "HIGH_LOAD_DAY"


def test_classify_day_integration(rule_engine):
    """Matala aktiivisuus + 3/4 palautumisehtoa — INTEGRATION_DAY."""
    features = {
        "active_calories": 300,
        "hrv_delta_pct": 0.05,
        "deep_sleep_vs_30d_delta": 100,
        "rhr_delta_pct": -0.05,
    }
    assert rule_engine.classify_day(features) == "INTEGRATION_DAY"


def test_classify_day_baseline(rule_engine):
    features = {"active_calories": 400, "hrv_delta_pct": 0.02}
    assert rule_engine.classify_day(features) == "BASELINE_DAY"


def test_get_state_empty_history(rule_engine):
    """Tyhjä historia ei kaadu — palauttaa Neutral."""
    assert rule_engine.get_state([]) == "Neutral"


def test_get_state_expansion(rule_engine):
    """Päivä HIGH_LOAD_DAYn jälkeen — Expansion."""
    history = [
        DayRecord(date="2026-07-17", classification="HIGH_LOAD_DAY",
                  hrv_delta_pct=-0.20, hrv_value=28, hrv_baseline_14d=35),
    ]
    assert rule_engine.get_state(history) == "Expansion"


def test_get_state_reset_confirmed(rule_engine):
    """HIGH_LOAD_DAY + seuraava päivä HRV yli baselinen — Reset Confirmed."""
    history = [
        DayRecord(date="2026-07-16", classification="HIGH_LOAD_DAY",
                  hrv_delta_pct=-0.20, hrv_value=28, hrv_baseline_14d=35),
        DayRecord(date="2026-07-17", classification="BASELINE_DAY",
                  hrv_delta_pct=0.05, hrv_value=37, hrv_baseline_14d=35),
    ]
    assert rule_engine.get_state(history) == "Reset Confirmed"


def test_get_state_incomplete_reset(rule_engine):
    """3+ peräkkäistä HRV-suppressiota — Incomplete Reset."""
    history = [
        DayRecord(date="2026-07-15", classification="HIGH_LOAD_DAY",
                  hrv_delta_pct=-0.18, hrv_value=29, hrv_baseline_14d=35),
        DayRecord(date="2026-07-16", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.16, hrv_value=30, hrv_baseline_14d=35),
        DayRecord(date="2026-07-17", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.20, hrv_value=28, hrv_baseline_14d=35),
    ]
    assert rule_engine.get_state(history) == "Incomplete Reset"


def test_get_state_neutral_no_high_load(rule_engine):
    """Baseline-historia ilman HIGH_LOAD_DAYta — Neutral."""
    history = [
        DayRecord(date="2026-07-16", classification="BASELINE_DAY",
                  hrv_delta_pct=0.02, hrv_value=36, hrv_baseline_14d=35),
        DayRecord(date="2026-07-17", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.02, hrv_value=34, hrv_baseline_14d=35),
    ]
    assert rule_engine.get_state(history) == "Neutral"
