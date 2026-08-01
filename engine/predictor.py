"""
engine/predictor.py — Predictive Trend Engine (Enhanced)

This module watches how risk scores change over time and predicts the future.
It keeps a rolling window of the last 30 readings per zone and fits a straight
line (linear regression) to find the trend direction and speed.

Enhanced with detailed risk bands, confidence levels, trend descriptions,
and actionable recommendations (Point 4 improvement).

Example output:
  "⬆️ Rising fast at +3.2 pts/sec — Score 72 (Danger). Projected CRITICAL
   in ~22s. Recommendation: Dispatch rover for investigation."
"""

import time
import numpy as np
from collections import deque
from typing import Dict, Optional
from server.state import PredictionResult
from engine.chronos import SCORE_RED, SCORE_ORANGE, SCORE_YELLOW


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

HISTORY_SIZE = 30         # Keep the last 30 readings per zone
SLOPE_STABLE_THRESHOLD = 0.05  # Risk points/sec — below this = "stable"
LOOKAHEAD_SECONDS = 30    # How far ahead to project (for the display)


# ─────────────────────────────────────────────────────────────────────────────
# Risk Band Definitions (Point 4)
# ─────────────────────────────────────────────────────────────────────────────

RISK_BANDS = [
    # (max_score, band_name, detail_template, color)
    (15,  'Safe',     'All readings within normal parameters. No action required.', 'green'),
    (30,  'Caution',  'Minor elevation detected. Continue routine monitoring.', 'teal'),
    (50,  'Warning',  'Moderate hazard indicators present. Increased monitoring advised.', 'yellow'),
    (70,  'Danger',   'Significant hazard detected. Active investigation required.', 'orange'),
    (100, 'Critical', 'Severe hazard confirmed. Immediate evacuation and emergency response required.', 'red'),
]

# Recommendation matrix: (risk_band, trend) → recommendation text
RECOMMENDATIONS = {
    ('Safe',     'stable'):  'No action needed. System operating normally.',
    ('Safe',     'rising'):  'Monitor — slight upward trend from baseline.',
    ('Safe',     'falling'): 'Conditions improving. No action needed.',
    ('Caution',  'stable'):  'Continue monitoring. Review sensor readings periodically.',
    ('Caution',  'rising'):  'Increasing trend detected. Prepare for possible escalation.',
    ('Caution',  'falling'): 'Conditions stabilizing. Continue observation.',
    ('Warning',  'stable'):  'Sustained warning levels. Consider visual inspection of the area.',
    ('Warning',  'rising'):  'Escalating hazard. Dispatch rover for automated investigation.',
    ('Warning',  'falling'): 'Hazard decreasing. Maintain monitoring until fully cleared.',
    ('Danger',   'stable'):  'Danger zone sustained. Rover investigation and staff alert recommended.',
    ('Danger',   'rising'):  'URGENT: Rapidly escalating danger. Initiate evacuation preparations.',
    ('Danger',   'falling'): 'Danger decreasing. Continue monitoring — do not cancel alerts prematurely.',
    ('Critical', 'stable'):  'CRITICAL: Sustained emergency. Execute full evacuation protocol NOW.',
    ('Critical', 'rising'):  'CRITICAL ESCALATION: Maximum emergency response. All personnel evacuate.',
    ('Critical', 'falling'): 'Critical conditions easing. Maintain evacuation until fully clear.',
}


def _get_risk_band(score: int) -> tuple:
    """Return (band_name, detail, color) for a given score."""
    for max_score, name, detail, color in RISK_BANDS:
        if score <= max_score:
            return name, detail, color
    return 'Critical', RISK_BANDS[-1][2], 'red'


def _get_recommendation(band: str, trend: str) -> str:
    """Get actionable recommendation based on risk band and trend combo."""
    return RECOMMENDATIONS.get((band, trend), 'Monitor situation and await further data.')


def _get_confidence(data_count: int, slope_consistency: float) -> str:
    """
    Determine prediction confidence based on data quality.

    Args:
        data_count: Number of readings in history
        slope_consistency: R² value from linear fit (0-1)
    """
    if data_count >= 20 and slope_consistency > 0.7:
        return 'high'
    elif data_count >= 10 and slope_consistency > 0.4:
        return 'medium'
    else:
        return 'low'


class ZoneHistory:
    """
    Rolling history of (timestamp, risk_score) pairs for one zone.
    We use a deque (double-ended queue) as an efficient ring buffer.
    """

    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        # Each entry is a (timestamp, risk_score) tuple
        self._history: deque = deque(maxlen=HISTORY_SIZE)

    def add(self, score: int):
        """Add the latest risk score with the current timestamp."""
        self._history.append((time.time(), score))

    def has_enough_data(self) -> bool:
        """We need at least 5 readings before the trend is meaningful."""
        return len(self._history) >= 5

    def compute(self) -> PredictionResult:
        """
        Fit a linear regression to the history and predict the future.

        The slope tells us:
        - Positive (e.g. +2.0): risk is rising 2 points per second
        - Negative (e.g. -1.5): risk is falling
        - Near zero: risk is stable

        We then ask: if the trend continues, how long until we hit CRITICAL (80)?

        Enhanced with risk bands, detailed descriptions, confidence levels,
        and actionable recommendations.
        """
        data = list(self._history)
        current_score = data[-1][1]
        data_count = len(data)

        # Get risk band info
        band_name, band_detail, band_color = _get_risk_band(current_score)
        risk_band_detail = f"Score {current_score}/100 — {band_name} zone. {band_detail}"

        if not self.has_enough_data():
            recommendation = _get_recommendation(band_name, 'stable')
            return PredictionResult(
                zone_id=self.zone_id,
                trend='stable',
                slope=0.0,
                projected_score_30s=current_score,
                projected_critical_in=None,
                current_score=current_score,
                risk_band=band_name,
                risk_band_detail=risk_band_detail,
                trend_description='Insufficient data for trend analysis — collecting readings.',
                confidence='low',
                recommendation=recommendation,
            )

        # Extract timestamps and scores as numpy arrays
        timestamps = np.array([d[0] for d in data])
        scores     = np.array([d[1] for d in data], dtype=float)

        # Normalise timestamps so t[0] = 0 (makes the math cleaner)
        t = timestamps - timestamps[0]

        # Fit y = slope * t + intercept using numpy's least-squares solver
        # np.polyfit(x, y, degree=1) returns [slope, intercept]
        r_squared = 0.0
        if t[-1] > 0:  # Avoid divide-by-zero if readings came in too fast
            coeffs = np.polyfit(t, scores, 1)
            slope = float(coeffs[0])  # Risk points per second

            # Compute R² for confidence estimation
            predicted = np.polyval(coeffs, t)
            ss_res = np.sum((scores - predicted) ** 2)
            ss_tot = np.sum((scores - np.mean(scores)) ** 2)
            r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        else:
            slope = 0.0

        # Projected score in 30 seconds
        projected_30 = int(np.clip(current_score + slope * LOOKAHEAD_SECONDS, 0, 100))

        # Determine trend label
        if slope > SLOPE_STABLE_THRESHOLD:
            trend = 'rising'
        elif slope < -SLOPE_STABLE_THRESHOLD:
            trend = 'falling'
        else:
            trend = 'stable'

        # Time until CRITICAL — only meaningful if score is rising towards 80
        projected_critical_in: Optional[int] = None
        if slope > SLOPE_STABLE_THRESHOLD and current_score < SCORE_RED:
            seconds_to_critical = (SCORE_RED - current_score) / slope
            if 0 < seconds_to_critical <= 300:  # Only show if within 5 minutes
                projected_critical_in = int(seconds_to_critical)

        # ── Build detailed trend description ────────────────────────────
        confidence = _get_confidence(data_count, max(0, r_squared))
        recommendation = _get_recommendation(band_name, trend)

        # Build rich trend narrative
        abs_slope = abs(slope)
        if trend == 'rising':
            speed = 'rapidly' if abs_slope > 2.0 else 'steadily' if abs_slope > 0.5 else 'slowly'
            trend_desc = f"⬆️ Rising {speed} at +{abs_slope:.1f} pts/sec."
            if projected_critical_in is not None:
                trend_desc += f" Projected CRITICAL in ~{projected_critical_in}s."
            else:
                trend_desc += f" Projected score: {projected_30} in 30s."

            # Add context about recent behavior
            if data_count >= 10:
                score_10_ago = data[-min(10, data_count)][1]
                delta = current_score - score_10_ago
                if delta > 0:
                    trend_desc += f" Score rose {delta} points over last {min(10, data_count)} readings."

        elif trend == 'falling':
            speed = 'rapidly' if abs_slope > 2.0 else 'steadily' if abs_slope > 0.5 else 'gradually'
            trend_desc = f"⬇️ Falling {speed} at -{abs_slope:.1f} pts/sec."
            trend_desc += f" Projected score: {projected_30} in 30s."

            # Time to safe
            if slope < -SLOPE_STABLE_THRESHOLD and current_score > 15:
                seconds_to_safe = current_score / abs_slope
                if 0 < seconds_to_safe <= 300:
                    trend_desc += f" Expected to reach safe levels in ~{int(seconds_to_safe)}s."

        else:
            trend_desc = f"➡️ Stable at {current_score}/100."
            if current_score > SCORE_YELLOW:
                trend_desc += " Sustained elevated readings — no improvement detected."
            else:
                trend_desc += " All parameters holding steady."

        # Add confidence note
        conf_labels = {'high': 'High confidence', 'medium': 'Moderate confidence', 'low': 'Low confidence'}
        trend_desc += f" ({conf_labels[confidence]} — {data_count} readings)"

        return PredictionResult(
            zone_id=self.zone_id,
            trend=trend,
            slope=slope,
            projected_score_30s=projected_30,
            projected_critical_in=projected_critical_in,
            current_score=current_score,
            risk_band=band_name,
            risk_band_detail=risk_band_detail,
            trend_description=trend_desc,
            confidence=confidence,
            recommendation=recommendation,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Predictor — manages histories for all zones
# ─────────────────────────────────────────────────────────────────────────────

class Predictor:
    """
    Maintains rolling history for all zones and computes predictions.

    Usage:
        predictor = Predictor()
        predictor.update('chem_lab', 75)          # add a reading
        result = predictor.get_prediction('chem_lab')  # get the trend
    """

    def __init__(self):
        self._histories: Dict[str, ZoneHistory] = {}

    def _get_history(self, zone_id: str) -> ZoneHistory:
        if zone_id not in self._histories:
            self._histories[zone_id] = ZoneHistory(zone_id)
        return self._histories[zone_id]

    def update(self, zone_id: str, score: int):
        """Feed in a new risk score reading for a zone."""
        self._get_history(zone_id).add(score)

    def get_prediction(self, zone_id: str) -> Optional[PredictionResult]:
        """Get the latest prediction for a zone (None if not enough data yet)."""
        if zone_id not in self._histories:
            return None
        return self._histories[zone_id].compute()

    def update_all(self, risk_scores: dict) -> Dict[str, PredictionResult]:
        """
        Update all zones at once and return all predictions.

        Args:
            risk_scores: dict of zone_id → RiskResult

        Returns:
            dict of zone_id → PredictionResult
        """
        predictions = {}
        for zone_id, risk_result in risk_scores.items():
            self.update(zone_id, risk_result.score)
            pred = self.get_prediction(zone_id)
            if pred is not None:
                predictions[zone_id] = pred
        return predictions


# ─────────────────────────────────────────────────────────────────────────────
# Friendly display helpers
# ─────────────────────────────────────────────────────────────────────────────

def format_prediction(pred: PredictionResult) -> str:
    """
    Turn a PredictionResult into a rich display string.

    Enhanced with risk band, confidence, and recommendation details.

    Examples:
        "⬆️ Rising fast at +3.2 pts/sec — [DANGER 72/100] → CRITICAL in ~22s
         | Confidence: HIGH | Action: Dispatch rover for investigation."
        "➡️ Stable — [SAFE 12/100] | All readings normal."
    """
    # Build status line
    parts = []

    if pred.trend == 'rising':
        speed = abs(pred.slope)
        if pred.projected_critical_in is not None:
            parts.append(f"⬆️ Rising (+{speed:.1f}/s) — [{pred.risk_band.upper()} {pred.current_score}/100]"
                        f" → CRITICAL in ~{pred.projected_critical_in}s")
        else:
            parts.append(f"⬆️ Rising (+{speed:.1f}/s) — [{pred.risk_band.upper()} {pred.current_score}/100]"
                        f" → projected {pred.projected_score_30s} in 30s")
    elif pred.trend == 'falling':
        speed = abs(pred.slope)
        parts.append(f"⬇️ Falling (-{speed:.1f}/s) — [{pred.risk_band.upper()} {pred.current_score}/100]"
                    f" → projected {pred.projected_score_30s} in 30s")
    else:
        parts.append(f"➡️ Stable — [{pred.risk_band.upper()} {pred.current_score}/100]")

    # Add confidence
    parts.append(f"Confidence: {pred.confidence.upper()}")

    # Add recommendation if not safe+stable
    if pred.risk_band != 'Safe' or pred.trend != 'stable':
        parts.append(f"Action: {pred.recommendation}")

    return " | ".join(parts)
