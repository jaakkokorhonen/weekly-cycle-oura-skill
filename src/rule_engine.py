from typing import Literal
from src.features import DayRecord

class RuleEngine:
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        # Load thresholds from config, matching config.yaml.example structure
        self.thresholds = self.config.get("thresholds", {})
        
        self.high_load_kcal_hard = self.thresholds.get("high_load_kcal_hard", 1000)
        self.high_load_kcal_soft = self.thresholds.get("high_load_kcal_soft", 800)
        self.high_load_hrv_delta = self.thresholds.get("high_load_hrv_delta", -0.15)
        self.integration_min_conditions = self.thresholds.get("integration_min_conditions", 3)
        self.incomplete_reset_days = self.thresholds.get("incomplete_reset_days", 3)
        self.nap_sleep_threshold_h = self.thresholds.get("nap_sleep_threshold_h", 6.5)
        self.nap_hrv_delta = self.thresholds.get("nap_hrv_delta", -0.10)

    def classify_day(self, features: dict) -> Literal["HIGH_LOAD_DAY", "INTEGRATION_DAY", "BASELINE_DAY"]:
        """Classifies a day as HIGH_LOAD_DAY, INTEGRATION_DAY, or BASELINE_DAY."""
        kcal = features.get("derived_active_kcal", 0.0)
        hrv_delta = features.get("derived_hrv_delta_pct", 0.0)
        
        # HIGH_LOAD_DAY conditions
        if kcal >= self.high_load_kcal_hard:
            return "HIGH_LOAD_DAY"
        if kcal >= self.high_load_kcal_soft and hrv_delta <= self.high_load_hrv_delta:
            return "HIGH_LOAD_DAY"

        # INTEGRATION_DAY conditions
        if kcal < self.high_load_kcal_soft:
            deep_sleep_vs_30d = features.get("derived_deep_sleep_vs_30d", 0.0)
            rhr_vs_30d = features.get("derived_rhr_vs_30d", 0.0)
            
            # Conditions:
            # 1. HRV must be >= 0 (above or equal to baseline)
            # 2. Deep sleep must be > 0 (more than 30d baseline)
            # 3. RHR must be < 0 (lower than 30d baseline)
            cond1 = hrv_delta >= 0.0
            cond2 = deep_sleep_vs_30d > 0.0
            cond3 = rhr_vs_30d < 0.0
            
            if cond1 and cond2 and cond3:
                return "INTEGRATION_DAY"

        return "BASELINE_DAY"

    def get_state(self, history: list[DayRecord]) -> Literal["Neutral", "Expansion", "Incomplete Reset", "Reset Confirmed"]:
        """Calculates the current cycle state from history."""
        if not history:
            return "Neutral"

        # If any day has a partial baseline, the state defaults to Neutral to avoid noise
        if any(r.partial_baseline for r in history):
            return "Neutral"

        # Check for consecutive HRV suppression at the end of the history
        consecutive_suppression = 0
        for r in reversed(history):
            if r.hrv_delta_pct < 0.0:
                consecutive_suppression += 1
            else:
                break

        if consecutive_suppression >= self.incomplete_reset_days:
            # Verify we have at least one HIGH_LOAD_DAY in history to trigger cycle states
            if any(r.classification == "HIGH_LOAD_DAY" for r in history):
                return "Incomplete Reset"

        # Find the most recent HIGH_LOAD_DAY in history
        last_high_load_idx = -1
        for i in range(len(history) - 1, -1, -1):
            if history[i].classification == "HIGH_LOAD_DAY":
                last_high_load_idx = i
                break

        if last_high_load_idx == -1:
            return "Neutral"

        # Check if there is a reset confirmed (HRV >= baseline) after the last HIGH_LOAD_DAY
        has_reset = False
        for i in range(last_high_load_idx + 1, len(history)):
            r = history[i]
            # HRV >= baseline is confirmed if hrv_delta_pct >= 0 or hrv_value >= hrv_baseline
            if r.hrv_delta_pct >= 0.0:
                has_reset = True
                break
            if r.hrv_value is not None and r.hrv_baseline_14d is not None and r.hrv_value >= r.hrv_baseline_14d:
                has_reset = True
                break

        if has_reset:
            return "Reset Confirmed"

        # If we have a HIGH_LOAD_DAY but no reset yet, it's Expansion
        return "Expansion"

    def get_tactical_suggestion(self, features: dict) -> list[str]:
        """Identifies active tactical rules based on features."""
        rules = []
        # Late caffeine alert
        caffeine_gap = features.get("caffeine_hours_before_bed")
        if caffeine_gap is not None and caffeine_gap < 6.0:
            rules.append("CAFFEINE_LATE")

        # Recent alcohol alert
        alcohol_gap = features.get("alcohol_hours_before_bed")
        if alcohol_gap is not None and alcohol_gap < 3.0:
            rules.append("ALCOHOL_RECENT")

        # Sleep debt nap suggestion
        sleep_duration_h = features.get("total_sleep_last_24h")
        if sleep_duration_h is not None and sleep_duration_h < self.nap_sleep_threshold_h:
            rules.append("NAP_RECOMMENDED")

        return rules
