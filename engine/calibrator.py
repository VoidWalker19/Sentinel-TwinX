"""
engine/calibrator.py — Dynamic Sensor Calibration Module

Instead of relying on fixed hardcoded thresholds for every building,
this module learns what "normal" looks like for each zone by collecting
the first N readings and computing baseline statistics (mean + std dev).

Once calibrated, it provides per-zone dynamic thresholds that adapt to
the actual environment — e.g., a server room that normally runs at 32°C
won't trigger "warm" alerts that would be valid in a classroom at 23°C.

Calibration states:
  PENDING     → Not enough data yet (< 5 readings)
  CALIBRATING → Collecting data (5..CALIBRATION_WINDOW readings)
  CALIBRATED  → Baseline established, dynamic thresholds active

Threshold formula:
  yellow = baseline_mean + K_YELLOW * std_dev
  red    = baseline_mean + K_RED * std_dev
  (clamped to never exceed global safety maximums)
"""

import math
import threading
from collections import deque
from typing import Dict, Optional, Tuple
from server.state import ZoneReading


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

CALIBRATION_WINDOW = 20   # Readings needed for full calibration (~40s at 2s poll)
MIN_READINGS = 5          # Minimum readings before any calibration output

# How many standard deviations above baseline to set thresholds
K_YELLOW = 2.0            # Warning level
K_RED = 4.0               # Critical level

# Absolute safety ceilings — calibration can never push thresholds above these
MAX_TEMP_YELLOW = 45.0    # °C — no matter what, this is always concerning
MAX_TEMP_RED = 65.0       # °C — absolute fire danger
MAX_SMOKE_YELLOW = 200    # PPM
MAX_SMOKE_RED = 600       # PPM

# Minimum threshold floors — calibration can never set thresholds below these
MIN_TEMP_YELLOW = 30.0    # °C — below this would be too sensitive
MIN_TEMP_RED = 40.0       # °C
MIN_SMOKE_YELLOW = 50     # PPM
MIN_SMOKE_RED = 150       # PPM


class ZoneCalibration:
    """Calibration state for a single zone's sensors."""

    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self._temp_history: deque = deque(maxlen=CALIBRATION_WINDOW)
        self._smoke_history: deque = deque(maxlen=CALIBRATION_WINDOW)
        self._humidity_history: deque = deque(maxlen=CALIBRATION_WINDOW)

        # Computed baselines (None until calibrated)
        self.temp_mean: Optional[float] = None
        self.temp_std: Optional[float] = None
        self.smoke_mean: Optional[float] = None
        self.smoke_std: Optional[float] = None
        self.humidity_mean: Optional[float] = None
        self.humidity_std: Optional[float] = None

        # Dynamic thresholds (None until calibrated)
        self.temp_threshold_yellow: Optional[float] = None
        self.temp_threshold_red: Optional[float] = None
        self.smoke_threshold_yellow: Optional[int] = None
        self.smoke_threshold_red: Optional[int] = None

    @property
    def status(self) -> str:
        """Current calibration state."""
        count = len(self._temp_history)
        if count < MIN_READINGS:
            return 'pending'
        elif count < CALIBRATION_WINDOW:
            return 'calibrating'
        else:
            return 'calibrated'

    @property
    def progress(self) -> float:
        """Calibration progress as a 0.0–1.0 fraction."""
        return min(1.0, len(self._temp_history) / CALIBRATION_WINDOW)

    def feed(self, reading: ZoneReading):
        """Add a new reading and recompute baselines if enough data."""
        self._temp_history.append(reading.temp)
        self._smoke_history.append(reading.smoke)
        self._humidity_history.append(reading.humidity)

        # Recompute baselines once we have enough readings
        if len(self._temp_history) >= MIN_READINGS:
            self._recompute()

    def _recompute(self):
        """Recompute baseline statistics and dynamic thresholds."""
        # Temperature
        self.temp_mean = _mean(self._temp_history)
        self.temp_std = _std(self._temp_history, self.temp_mean)

        # Smoke
        self.smoke_mean = _mean(self._smoke_history)
        self.smoke_std = _std(self._smoke_history, self.smoke_mean)

        # Humidity
        self.humidity_mean = _mean(self._humidity_history)
        self.humidity_std = _std(self._humidity_history, self.humidity_mean)

        # Compute dynamic thresholds (clamped to safety bounds)
        # Ensure std_dev is at least 1.0 to avoid overly tight thresholds
        t_std = max(1.0, self.temp_std)
        s_std = max(5.0, self.smoke_std)

        self.temp_threshold_yellow = _clamp(
            self.temp_mean + K_YELLOW * t_std,
            MIN_TEMP_YELLOW, MAX_TEMP_YELLOW
        )
        self.temp_threshold_red = _clamp(
            self.temp_mean + K_RED * t_std,
            MIN_TEMP_RED, MAX_TEMP_RED
        )
        self.smoke_threshold_yellow = int(_clamp(
            self.smoke_mean + K_YELLOW * s_std,
            MIN_SMOKE_YELLOW, MAX_SMOKE_YELLOW
        ))
        self.smoke_threshold_red = int(_clamp(
            self.smoke_mean + K_RED * s_std,
            MIN_SMOKE_RED, MAX_SMOKE_RED
        ))

    def get_thresholds(self) -> Optional[dict]:
        """
        Return calibrated thresholds, or None if not yet calibrated.

        Returns dict with keys:
            temp_yellow, temp_red, smoke_yellow, smoke_red
        """
        if self.temp_threshold_yellow is None:
            return None
        return {
            'temp_yellow': round(self.temp_threshold_yellow, 1),
            'temp_red': round(self.temp_threshold_red, 1),
            'smoke_yellow': self.smoke_threshold_yellow,
            'smoke_red': self.smoke_threshold_red,
        }

    def to_dict(self) -> dict:
        """Serialise for UI/snapshot."""
        thresholds = self.get_thresholds()
        return {
            'zone_id': self.zone_id,
            'status': self.status,
            'progress': round(self.progress, 2),
            'baseline': {
                'temp_mean': round(self.temp_mean, 1) if self.temp_mean is not None else None,
                'smoke_mean': round(self.smoke_mean, 1) if self.smoke_mean is not None else None,
                'humidity_mean': round(self.humidity_mean, 1) if self.humidity_mean is not None else None,
            },
            'thresholds': thresholds,
        }


class SensorCalibrator:
    """
    Manages calibration for all zones.

    Usage:
        calibrator = SensorCalibrator()
        calibrator.feed(zone_reading)               # each tick
        thresholds = calibrator.get_thresholds('chem_lab')  # returns dict or None
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._zones: Dict[str, ZoneCalibration] = {}

    def feed(self, reading: ZoneReading):
        """Feed a new sensor reading for calibration learning."""
        with self._lock:
            if reading.zone_id not in self._zones:
                self._zones[reading.zone_id] = ZoneCalibration(reading.zone_id)
            self._zones[reading.zone_id].feed(reading)

    def feed_all(self, zones: Dict[str, ZoneReading]):
        """Feed readings for all zones at once."""
        for reading in zones.values():
            self.feed(reading)

    def get_thresholds(self, zone_id: str) -> Optional[dict]:
        """Get calibrated thresholds for a zone, or None if not ready."""
        with self._lock:
            cal = self._zones.get(zone_id)
            if cal is None:
                return None
            return cal.get_thresholds()

    def get_status(self, zone_id: str) -> str:
        """Get calibration status for a zone."""
        with self._lock:
            cal = self._zones.get(zone_id)
            return cal.status if cal else 'pending'

    def get_all_status(self) -> Dict[str, dict]:
        """Get calibration info for all zones (for UI snapshot)."""
        with self._lock:
            return {zid: cal.to_dict() for zid, cal in self._zones.items()}

    def is_all_calibrated(self) -> bool:
        """Check if all known zones are fully calibrated."""
        with self._lock:
            if not self._zones:
                return False
            return all(c.status == 'calibrated' for c in self._zones.values())


# ─────────────────────────────────────────────────────────────────────────────
# Helper math functions (avoid numpy dependency for this simple module)
# ─────────────────────────────────────────────────────────────────────────────

def _mean(data) -> float:
    """Compute arithmetic mean of a sequence."""
    n = len(data)
    return sum(data) / n if n > 0 else 0.0


def _std(data, mean_val: float) -> float:
    """Compute population standard deviation given the mean."""
    n = len(data)
    if n < 2:
        return 0.0
    variance = sum((x - mean_val) ** 2 for x in data) / n
    return math.sqrt(variance)


def _clamp(value: float, low: float, high: float) -> float:
    """Clamp a value between low and high bounds."""
    return max(low, min(high, value))
