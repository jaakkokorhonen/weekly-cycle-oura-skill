import pytest
from src.rule_engine import RuleEngine
from src.features import DayRecord


@pytest.fixture
def rule_engine():
    """Config-rakenne peilaa config.yaml.example:ia — kynnykset config["thresholds"]-aliavaimissa."""
    config = {
        "thresholds": {
            "high_load_kcal_hard": 1000,
            "high_load_kcal_soft": 800,
            "high_load_hrv_delta": -0.15,
            "integration_min_conditions": 3,
            "incomplete_reset_days": 3,
            "nap_sleep_threshold_h": 6.5,
            "nap_hrv_delta": -0.10,
            "low_output_hrv_delta": -0.10,
            "low_output_rhr_elevated_delta": 0.05,
        }
    }
    return RuleEngine(config=config)


def test_classify_day_high_load_hard(rule_engine):
    """Kalorit > hard threshold — HIGH_LOAD_DAY."""
    features = {"derived_active_kcal": 1100, "derived_hrv_delta_pct": -0.05}
    assert rule_engine.classify_day(features) == "HIGH_LOAD_DAY"


def test_classify_day_high_load_hybrid(rule_engine):
    """Hybriditapaus: kalorit 800-1000 + HRV suppressed — HIGH_LOAD_DAY."""
    features = {"derived_active_kcal": 850, "derived_hrv_delta_pct": -0.18}
    assert rule_engine.classify_day(features) == "HIGH_LOAD_DAY"


def test_classify_day_integration(rule_engine):
    """Matala aktiivisuus + kaikki palautumisehdot — INTEGRATION_DAY."""
    features = {
        "derived_active_kcal": 300,
        "derived_hrv_delta_pct": 0.05,       # >= 0
        "derived_deep_sleep_vs_30d": 100,    # > 0
        "derived_rhr_vs_30d": -0.05,         # < 0
    }
    assert rule_engine.classify_day(features) == "INTEGRATION_DAY"


def test_classify_day_integration_negative_hrv_is_not_integration(rule_engine):
    """Negatiivitesti: hrv_delta_pct < 0 ei saa tuottaa INTEGRATION_DAY:ta (#29 AC)."""
    features = {
        "derived_active_kcal": 300,
        "derived_hrv_delta_pct": -0.05,      # alle baselinen — ei integration
        "derived_deep_sleep_vs_30d": 100,
        "derived_rhr_vs_30d": -0.05,
    }
    assert rule_engine.classify_day(features) != "INTEGRATION_DAY"


def test_classify_day_baseline(rule_engine):
    features = {"derived_active_kcal": 400, "derived_hrv_delta_pct": 0.02}
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


def test_get_state_incomplete_reset_requires_3_days(rule_engine):
    """Insufficient evidence: 2 peräkkäistä HRV-suppressiota ei riitä — ei Incomplete Reset (#29 AC)."""
    history = [
        DayRecord(date="2026-07-16", classification="HIGH_LOAD_DAY",
                  hrv_delta_pct=-0.18, hrv_value=29, hrv_baseline_14d=35),
        DayRecord(date="2026-07-17", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.16, hrv_value=30, hrv_baseline_14d=35),
    ]
    assert rule_engine.get_state(history) != "Incomplete Reset"


def test_get_state_incomplete_reset(rule_engine):
    """3+ peräkkäistä HRV-suppressiota — Incomplete Reset (#29 AC)."""
    history = [
        DayRecord(date="2026-07-15", classification="HIGH_LOAD_DAY",
                  hrv_delta_pct=-0.18, hrv_value=29, hrv_baseline_14d=35),
        DayRecord(date="2026-07-16", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.16, hrv_value=30, hrv_baseline_14d=35),
        DayRecord(date="2026-07-17", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.20, hrv_value=28, hrv_baseline_14d=35),
    ]
    assert rule_engine.get_state(history) == "Incomplete Reset"


def test_get_state_partial_baseline_returns_neutral(rule_engine):
    """partial_baseline: true — get_state palauttaa Neutral, ei Incomplete Reset (#29 AC)."""
    history = [
        DayRecord(date="2026-07-15", classification="HIGH_LOAD_DAY",
                  hrv_delta_pct=-0.18, hrv_value=29, hrv_baseline_14d=35,
                  partial_baseline=True),
        DayRecord(date="2026-07-16", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.16, hrv_value=30, hrv_baseline_14d=35,
                  partial_baseline=True),
        DayRecord(date="2026-07-17", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.20, hrv_value=28, hrv_baseline_14d=35,
                  partial_baseline=True),
    ]
    assert rule_engine.get_state(history) == "Neutral"


def test_get_state_neutral_no_high_load(rule_engine):
    """Baseline-historia ilman HIGH_LOAD_DAYta — Neutral."""
    history = [
        DayRecord(date="2026-07-16", classification="BASELINE_DAY",
                  hrv_delta_pct=0.02, hrv_value=36, hrv_baseline_14d=35),
        DayRecord(date="2026-07-17", classification="BASELINE_DAY",
                  hrv_delta_pct=-0.02, hrv_value=34, hrv_baseline_14d=35),
    ]
    assert rule_engine.get_state(history) == "Neutral"
