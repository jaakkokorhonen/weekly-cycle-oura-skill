import re

class RecommendationEngine:
    def __init__(self):
        # List of moralizing words that must never appear in recommendations
        self.moral_words = ["should", "must", "bad", "lazy", "discipline", "sinun pitäisi"]

    def generate(self, classification: str, load_state: str, features: dict, tactical: str | list | None = None) -> str:
        """Generates a non-moralizing f-string text recommendation with combined sentences."""
        tactical_list = []
        if isinstance(tactical, str):
            tactical_list = [tactical]
        elif isinstance(tactical, list):
            tactical_list = tactical
            
        sentences = []

        # Handle HRV display percentage
        hrv_delta = features.get("derived_hrv_delta_pct")
        hrv_str = "N/A"
        if hrv_delta is not None:
            hrv_str = f"{int(round(hrv_delta * 100))}%"

        # 1. State/Classification sentence (combined)
        if classification == "HIGH_LOAD_DAY":
            sentences.append(f"Recorded high load cycle day with HRV currently at {hrv_str} relative to baseline.")
        elif classification == "INTEGRATION_DAY":
            sentences.append(f"System identifies recovery and sleep integration with HRV currently at {hrv_str} relative to baseline.")
        else:
            sentences.append(f"Standard baseline cycle day with HRV currently at {hrv_str} relative to baseline.")

        # 2. Cycle state sentence (combined)
        if load_state == "Expansion":
            sentences.append("Currently in cycle expansion stage with elevated physical load.")
        elif load_state == "Reset Confirmed":
            sentences.append("Reset confirmed with physiology returning to baseline levels.")
        elif load_state == "Incomplete Reset":
            sentences.append("Incomplete reset detected with fatigue signals persisting for 3 days.")
        else:
            sentences.append("Physiology is in a neutral cycle phase.")

        # 3. Tactical suggestion sentence
        if "nap" in tactical_list or "nap" == tactical:
            sleep_h = features.get("total_sleep_last_24h")
            sleep_str = f"{sleep_h:.1f} h" if sleep_h is not None else "N/A"
            sentences.append(f"Sleep duration was {sleep_str}, so a 15-minute nap is recommended to support recovery.")
        elif "CAFFEINE_LATE" in tactical_list:
            caffeine_gap = features.get("caffeine_hours_before_bed")
            caffeine_gap_str = f"{caffeine_gap:.1f}" if caffeine_gap is not None else "N/A"
            sentences.append(f"Late caffeine logged at {caffeine_gap_str} hours before bedtime start.")
        elif "ALCOHOL_RECENT" in tactical_list:
            alcohol_gap = features.get("alcohol_hours_before_bed")
            alcohol_gap_str = f"{alcohol_gap:.1f}" if alcohol_gap is not None else "N/A"
            sentences.append(f"Alcohol logged close to bedtime at {alcohol_gap_str} hours gap, expecting resting heart rate elevation.")

        text = " ".join(sentences)

        # Sanitize text to guarantee no moralizing language slips through
        for word in self.moral_words:
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            text = pattern.sub("recommended", text)

        return text
