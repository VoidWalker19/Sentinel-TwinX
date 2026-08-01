"""
engine/chronos.py — CHRONOS Risk Engine

This is the "brain" of Sentinel Twin. It reads sensor values and computes
a risk score (0–100) for every building zone, plus human-readable reasons.

It is 100% deterministic (no randomness, no network) — it always works offline.
Think of it as a very smart set of if-statements trained by fire safety rules.

CHRONOS = CHemical, Heat, and Obstruction-based Numeric Scoring
"""

import time
import threading
from typing import Dict, List, Optional, Tuple
from server.state import ZoneReading, RiskResult
from engine.config_loader import ZONE_CONFIG, THRESHOLDS


# ─────────────────────────────────────────────────────────────────────────────
# Scoring thresholds — loaded dynamically from building.json config
# ─────────────────────────────────────────────────────────────────────────────

# Temperature thresholds (°C)
TEMP_CRITICAL   = THRESHOLDS.get('temp_critical', 65.0)
TEMP_HIGH       = THRESHOLDS.get('temp_high', 50.0)
TEMP_ELEVATED   = THRESHOLDS.get('temp_elevated', 38.0)
TEMP_WARM       = THRESHOLDS.get('temp_warm', 30.0)

# Smoke/gas thresholds (PPM — parts per million)
SMOKE_CRITICAL  = THRESHOLDS.get('smoke_critical', 600)
SMOKE_HIGH      = THRESHOLDS.get('smoke_high', 400)
SMOKE_MODERATE  = THRESHOLDS.get('smoke_moderate', 200)
SMOKE_LOW       = THRESHOLDS.get('smoke_low', 100)
SMOKE_TRACE     = THRESHOLDS.get('smoke_trace', 50)

# Humidity thresholds (%) — dry air accelerates fires
HUMIDITY_VERY_DRY = THRESHOLDS.get('humidity_very_dry', 15.0)
HUMIDITY_DRY      = THRESHOLDS.get('humidity_dry', 25.0)
HUMIDITY_LOW      = THRESHOLDS.get('humidity_low', 35.0)

# Risk score bands
SCORE_RED    = THRESHOLDS.get('score_red', 80)
SCORE_ORANGE = THRESHOLDS.get('score_orange', 60)
SCORE_YELLOW = THRESHOLDS.get('score_yellow', 30)
# Below 30 = Green (safe)


# ─────────────────────────────────────────────────────────────────────────────
# EMA Score Smoother (Point 3) — prevents false alarms from single spikes
# ─────────────────────────────────────────────────────────────────────────────

class EMAScoreSmoother:
    """
    Exponential Moving Average smoother for per-zone risk scores.

    Instead of using raw scores directly (which causes false alarms when
    a sensor briefly spikes), this applies EMA smoothing so that a score
    needs to stay elevated for 2-3 consecutive readings before the system
    responds — while still reacting fast enough for real emergencies.

    Formula: smoothed = alpha * raw + (1 - alpha) * prev_smoothed
    With alpha=0.35, the effective window is ~3 readings (~6 seconds).
    """

    def __init__(self, alpha: float = 0.35):
        self._alpha = alpha
        self._lock = threading.Lock()
        self._smoothed: Dict[str, float] = {}    # zone_id → smoothed score
        self._raw_history: Dict[str, List[float]] = {}  # zone_id → last few raw scores
        self._rate_of_change: Dict[str, float] = {}  # zone_id → points/tick

    def smooth(self, zone_id: str, raw_score: int) -> int:
        """
        Apply EMA smoothing to a raw risk score.

        Returns the smoothed score (still 0-100 int).
        """
        with self._lock:
            # Track raw history for rate-of-change calculation
            if zone_id not in self._raw_history:
                self._raw_history[zone_id] = []
            self._raw_history[zone_id].append(raw_score)
            if len(self._raw_history[zone_id]) > 5:
                self._raw_history[zone_id] = self._raw_history[zone_id][-5:]

            # Compute rate of change (points per tick)
            history = self._raw_history[zone_id]
            if len(history) >= 2:
                self._rate_of_change[zone_id] = history[-1] - history[-2]
            else:
                self._rate_of_change[zone_id] = 0.0

            if zone_id not in self._smoothed:
                # First reading — no smoothing possible
                self._smoothed[zone_id] = float(raw_score)
                return raw_score

            prev = self._smoothed[zone_id]
            smoothed = self._alpha * raw_score + (1 - self._alpha) * prev

            # Emergency override: if raw score is CRITICAL (>=90) and rising,
            # use higher alpha to respond faster to real emergencies
            if raw_score >= 90 and raw_score > prev:
                smoothed = 0.7 * raw_score + 0.3 * prev

            self._smoothed[zone_id] = smoothed
            return int(round(smoothed))

    def get_rate_of_change(self, zone_id: str) -> float:
        """Get the rate of change (points per tick) for a zone."""
        with self._lock:
            return self._rate_of_change.get(zone_id, 0.0)

    def reset(self, zone_id: str = None):
        """Reset smoothing state for one or all zones."""
        with self._lock:
            if zone_id:
                self._smoothed.pop(zone_id, None)
                self._raw_history.pop(zone_id, None)
                self._rate_of_change.pop(zone_id, None)
            else:
                self._smoothed.clear()
                self._raw_history.clear()
                self._rate_of_change.clear()


# Module-level smoother singleton — shared across ticks
_score_smoother = EMAScoreSmoother(alpha=0.35)


# ─────────────────────────────────────────────────────────────────────────────
# Core scoring function
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk(reading: ZoneReading, settings: dict = None,
                 health_status=None, calibrated_thresholds: dict = None) -> RiskResult:
    """
    Compute a 0–100 risk score for a single zone.

    Each hazard type contributes points. Scores add up and are capped at 100.
    We also collect human-readable reasons so the UI can explain the score.
    Supports dynamic thresholds and overrides from the settings dict.

    Threshold priority: manual settings > calibrated values > hardcoded defaults

    If health_status is FAULTY, the affected sensor's contribution is excluded
    to prevent false alarms from malfunctioning hardware.
    """
    # ── 0. Check Offline / Missing readings (Honesty Rule) ─────────────────
    if not getattr(reading, 'online', True) or reading.temp is None or reading.smoke is None:
        return RiskResult(
            zone_id=reading.zone_id,
            score=0,
            status='offline',
            reasons=["🔌 Sensor offline (No Live Telemetry)"],
            timestamp=time.time(),
        )

    # ── 0. Check Overrides ─────────────────────────────────────────────────
    overrides = settings.get('overrides', {}) if settings else {}
    if reading.zone_id in overrides:
        status = overrides[reading.zone_id]
        if status == 'red':
            score = 100
        elif status == 'orange':
            score = 75
        elif status == 'yellow':
            score = 45
        else:
            score = 15
        return RiskResult(
            zone_id=reading.zone_id,
            score=score,
            status=status,
            reasons=[f"⚠️ Status overridden to {status.upper()} by Operator"],
            timestamp=time.time(),
        )

    reasons: List[str] = []

    # ── Determine thresholds (manual settings > calibrated > defaults) ──
    # Start with hardcoded defaults
    t_yellow = TEMP_ELEVATED
    t_red = TEMP_HIGH
    s_yellow = SMOKE_MODERATE
    s_red = SMOKE_HIGH

    # Layer 1: Apply calibrated thresholds if available
    if calibrated_thresholds:
        t_yellow = calibrated_thresholds.get('temp_yellow', t_yellow)
        t_red = calibrated_thresholds.get('temp_red', t_red)
        s_yellow = calibrated_thresholds.get('smoke_yellow', s_yellow)
        s_red = calibrated_thresholds.get('smoke_red', s_red)

    # Layer 2: Manual settings override everything
    if settings:
        if 'temp_threshold_yellow' in settings:
            t_yellow = settings['temp_threshold_yellow']
        if 'temp_threshold_red' in settings:
            t_red = settings['temp_threshold_red']
        if 'smoke_threshold_yellow' in settings:
            s_yellow = settings['smoke_threshold_yellow']
        if 'smoke_threshold_red' in settings:
            s_red = settings['smoke_threshold_red']

    # ── Sensor health check (Point 2) ──────────────────────────────────
    # Determine which sensors are trustworthy
    temp_healthy = True
    smoke_healthy = True
    humidity_healthy = True

    if health_status is not None:
        details = getattr(health_status, 'details', {})
        health_st = getattr(health_status, 'status', 'HEALTHY')

        if health_st == 'FAULTY':
            # Check which specific sensors are faulty
            if details.get('temp') in ('OUT_OF_RANGE', 'STUCK'):
                temp_healthy = False
                reasons.append(f"🔧 Temperature sensor FAULTY — reading excluded from scoring")
            if details.get('smoke') in ('OUT_OF_RANGE', 'STUCK'):
                smoke_healthy = False
                reasons.append(f"🔧 Smoke sensor FAULTY — reading excluded from scoring")
            if details.get('humidity') in ('OUT_OF_RANGE', 'STUCK'):
                humidity_healthy = False
                reasons.append(f"🔧 Humidity sensor FAULTY — reading excluded from scoring")
        elif health_st == 'SUSPECT':
            # Add warnings but still use the data
            for sensor, issue in details.items():
                if issue in ('SPIKE', 'SUSPECT_STUCK', 'FLATLINE'):
                    reasons.append(f"⚠️ {sensor.capitalize()} sensor data may be unreliable ({issue})")

    # ── Temperature scoring ─────────────────────────────────────────────
    temp_score = 0
    if temp_healthy:
        temp = reading.temp
        if temp >= t_red:
            temp_score = 80
            reasons.append(f"🟠 Critical/High temperature {temp:.1f}°C — limit {t_red}°C")
        elif temp >= t_yellow:
            temp_score = 45
            reasons.append(f"🟡 Elevated temperature {temp:.1f}°C — limit {t_yellow}°C")
        elif temp >= TEMP_WARM:
            temp_score = 20
            reasons.append(f"⚠️ Warm reading {temp:.1f}°C")

    # ── Smoke scoring ───────────────────────────────────────────────────
    smoke_score = 0
    if smoke_healthy:
        smoke = reading.smoke
        if smoke >= s_red:
            smoke_score = 80
            reasons.append(f"🟠 Critical/Heavy smoke {smoke} PPM — limit {s_red} PPM")
        elif smoke >= s_yellow:
            smoke_score = 45
            reasons.append(f"🟡 Moderate smoke {smoke} PPM — limit {s_yellow} PPM")
        elif smoke >= SMOKE_TRACE:
            smoke_score = 15
            reasons.append(f"ℹ️ Trace smoke {smoke} PPM")

    blocked_score = 0
    if reading.blocked:
        blocked_score = 40
        reasons.append("🚧 Evacuation path BLOCKED — obstacle detected by sonar")

    # Additive scoring with diminishing returns:
    # Primary hazard contributes fully, secondary adds 30% of its value
    # This ensures compound hazards (high temp + high smoke) score higher
    hazard_scores = sorted([temp_score, smoke_score, blocked_score], reverse=True)
    score = hazard_scores[0]
    if len(hazard_scores) > 1 and hazard_scores[1] > 0:
        score += int(hazard_scores[1] * 0.3)
    if len(hazard_scores) > 2 and hazard_scores[2] > 0:
        score += int(hazard_scores[2] * 0.15)

    # Humidity penalty / multiplier (dry air = fire accelerant)
    hum_points = 0
    if humidity_healthy and reading.humidity is not None:
        hum = reading.humidity
        if hum <= HUMIDITY_VERY_DRY:
            hum_points = 15
            reasons.append(f"🔴 Very dry air {hum:.0f}% — high fire spread risk")
        elif hum <= HUMIDITY_DRY:
            hum_points = 10
            reasons.append(f"🟡 Dry air {hum:.0f}% — elevated combustion risk")
        elif hum <= HUMIDITY_LOW:
            hum_points = 5
            reasons.append(f"⚠️ Low humidity {hum:.0f}%")

    score += hum_points

    # Combined hazard bonus / sensor fusion (only if both sensors healthy)
    if temp_healthy and smoke_healthy:
        temp = reading.temp
        smoke = reading.smoke
        if temp >= t_red and smoke >= s_red:
            score = max(score, 95)
            reasons.append("⚡ Combined heat + smoke escalation — possible active fire")
        elif (temp >= t_red and smoke >= s_yellow) or (temp >= t_yellow and smoke >= s_red):
            score = max(score, 85)
            reasons.append("⚡ Significant dual-sensor elevation detected")
        elif temp >= t_yellow and smoke >= s_yellow:
            score = max(score, 65)
            reasons.append("⚡ Moderate dual-sensor elevation detected")

    # High-risk zone baseline (chem lab, storage, server room)
    zone_cfg = ZONE_CONFIG.get(reading.zone_id, {})
    if zone_cfg.get('high_risk_baseline') and score > 0:
        score = int(score * 1.05)
        reasons.append("⚗️ High-risk zone multiplier applied")

    # Cap at 100
    score = min(100, score)

    # ── Determine status colour ────────────────────────────────────────────
    if score >= SCORE_RED:
        status = 'red'
    elif score >= SCORE_ORANGE:
        status = 'orange'
    elif score >= SCORE_YELLOW:
        status = 'yellow'
    else:
        status = 'green'

    # If no risks at all, add a "safe" reason
    if not reasons:
        reasons.append("✅ All readings normal — zone is safe")

    return RiskResult(
        zone_id=reading.zone_id,
        score=score,
        status=status,
        reasons=reasons,
        timestamp=time.time(),
    )


def compute_all_risks(zones: Dict[str, ZoneReading], settings: dict = None,
                      health_statuses: dict = None,
                      calibrator=None) -> Tuple[Dict[str, RiskResult], str, int]:
    """
    Run CHRONOS on all zones at once.

    Args:
        zones: Dict of zone_id → ZoneReading
        settings: Dynamic safety thresholds from the UI
        health_statuses: Dict of zone_id → SensorHealthStatus (from health checker)
        calibrator: SensorCalibrator instance for dynamic thresholds

    Returns:
        (risk_scores dict, system_status string, overall_risk int)

    System status is determined by the single highest-risk zone.
    Scores are EMA-smoothed to prevent false alarms from transient spikes.
    """
    if not zones:
        return {}, 'green', 0

    risk_scores: Dict[str, RiskResult] = {}
    for zone_id, reading in zones.items():
        # Get sensor health for this zone
        health = None
        if health_statuses:
            health = health_statuses.get(zone_id)

        # Get calibrated thresholds for this zone
        cal_thresholds = None
        if calibrator:
            cal_thresholds = calibrator.get_thresholds(zone_id)

        # Compute raw risk
        result = compute_risk(reading, settings, health, cal_thresholds)

        # Apply EMA smoothing (Point 3)
        if result.status == 'offline':
            smoothed_score = 0
            smoothed_status = 'offline'
            _score_smoother.reset(zone_id)
        else:
            smoothed_score = _score_smoother.smooth(zone_id, result.score)

            # Re-determine status based on smoothed score
            if smoothed_score >= SCORE_RED:
                smoothed_status = 'red'
            elif smoothed_score >= SCORE_ORANGE:
                smoothed_status = 'orange'
            elif smoothed_score >= SCORE_YELLOW:
                smoothed_status = 'yellow'
            else:
                smoothed_status = 'green'

        # Add smoothing info if raw and smoothed differ significantly
        reasons = list(result.reasons)
        diff = abs(result.score - smoothed_score)
        if diff >= 5:
            reasons.append(f"📊 EMA smoothed: raw {result.score} → smoothed {smoothed_score} "
                          f"(delta {diff:+d})")

        risk_scores[zone_id] = RiskResult(
            zone_id=zone_id,
            score=smoothed_score,
            status=smoothed_status,
            reasons=reasons,
            timestamp=result.timestamp,
        )

    # Overall system risk: worst zone + contribution from other elevated zones
    # This means 5 zones at 60 is worse than 1 zone at 80
    if risk_scores:
        sorted_scores = sorted((r.score for r in risk_scores.values()), reverse=True)
        max_score = sorted_scores[0]
        # Each additional elevated zone (score >= 30) adds 15% of its score to overall
        elevated_bonus = sum(
            int(s * 0.15) for s in sorted_scores[1:] if s >= SCORE_YELLOW
        )
        overall_risk = min(100, max_score + elevated_bonus)
    else:
        max_score = 0
        overall_risk = 0

    if max_score >= SCORE_RED:
        system_status = 'red'
    elif max_score >= SCORE_ORANGE:
        system_status = 'orange'
    elif max_score >= SCORE_YELLOW:
        system_status = 'yellow'
    else:
        system_status = 'green'

    return risk_scores, system_status, overall_risk



def get_high_risk_zones(risk_scores: Dict[str, RiskResult], threshold: int = SCORE_ORANGE) -> List[str]:
    """Return zone IDs whose score is at or above the given threshold."""
    return [zid for zid, r in risk_scores.items() if r.score >= threshold]


def get_score_smoother() -> EMAScoreSmoother:
    """Return the module-level EMA smoother instance (for external access)."""
    return _score_smoother
