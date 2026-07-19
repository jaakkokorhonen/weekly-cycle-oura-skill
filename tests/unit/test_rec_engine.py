import pytest
from src.recommendation_engine import RecommendationEngine

@pytest.fixture
def rec_engine():
    return RecommendationEngine()

def test_generate_high_load_expansion(rec_engine):
    features = {"derived_hrv_delta_pct": -0.12}
    text = rec_engine.generate(
        classification="HIGH_LOAD_DAY",
        load_state="Expansion",
        features=features,
        tactical=None
    )
    
    assert "high load" in text.lower()
    assert "-12" in text
    assert len(text.split(".")) <= 4  # max 3 sentences + optional punctuation split

def test_generate_tactical_nap(rec_engine):
    features = {"total_sleep_last_24h": 5.8}
    text = rec_engine.generate(
        classification="BASELINE_DAY",
        load_state="Neutral",
        features=features,
        tactical="nap"
    )
    
    assert "nap" in text.lower()
    assert "5.8 h" in text.lower()

def test_non_moral_constraints(rec_engine):
    features = {"derived_hrv_delta_pct": -0.20}
    text = rec_engine.generate(
        classification="HIGH_LOAD_DAY",
        load_state="Expansion",
        features=features,
        tactical=None
    )
    
    # Must not contain moralizing words
    moral_words = ["should", "must", "bad", "lazy", "discipline", "sinun pitäisi"]
    for word in moral_words:
        assert word not in text.lower()
