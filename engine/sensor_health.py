"""
engine/sensor_health.py — Sensor Health Validation Module

This module monitors sensor behavior patterns to detect faulty hardware
BEFORE the risk engine processes the data. This prevents false alarms
caused by stuck sensors, electrical spikes, or disconnected probes.

Detection methods:
  1. STUCK     — Same value (±tolerance) for N consecutive readings
  2. SPIKE     — Value jumps > K standard deviations in a single tick
  3. OUT_OF_RANGE — Physically impossible values (temp > 200°C, etc.)
  4. FLATLINE  — Zero variance over extended period (sensor power loss)

Health statuses:
  HEALTHY  — All checks pass, data is trustworthy
  SUSPECT  — Minor anomaly detected, data may be unreliable
  FAULTY   — Clear malfunction, data should be excluded from risk scoring
"""

import time
import math
import threading
from collections import deque
from typing import Dict, List, Optional, Tuple
from server.state import ZoneReading


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

HISTORY_SIZE = 15            # Rolling window for health analysis

# Stuck detection
STUCK_TOLERANCE = 0.1        # Values within ±0.1 of each other = "same"
STUCK_THRESHOLD = 10         # Consecutive identical readings before flagging
STUCK_SUSPECT_THRESHOLD = 6  # Flag as SUSPECT before full STUCK

# Spike detection
SPIKE_MULTIPLIER = 5.0       # Jump > 5× recent std_dev = spike
SPIKE_MIN_STD = 1.0          # Minimum std_dev floor to avoid false spike on stable data

# Out-of-range bounds (physical impossibility)
TEMP_RANGE = (-40.0, 200.0)     # °C — DHT22 range is -40 to 80, but allow some margin
SMOKE_RANGE = (0, 10000)        # PPM — MQ-2 max is ~10000
HUMIDITY_RANGE = (0.0, 100.0)   # % — physical limits

# Flatline detection
FLATLINE_VARIANCE_THRESHOLD = 0.001  # Variance below this = flatline
FLATLINE_READINGS_REQUIRED = 10      # Need this many readings of near-zero variance


class SensorHealthStatus:
    """Health assessment for a single zone's sensors."""

    HEALTHY = 'HEALTHY'
    SUSPECT = 'SUSPECT'
    FAULTY = 'FAULTY'

    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self.status: str = self.HEALTHY
        self.issues: List[str] = []
        self.details: Dict[str, str] = {}  # sensor_type → issue description
        self.last_checked: float = time.time()

    def to_dict(self) -> dict:
        return {
            'zone_id': self.zone_id,
            'status': self.status,
            'issues': self.issues,
            'details': self.details,
            'last_checked': self.last_checked,
        }


class ZoneHealthTracker:
    """Tracks sensor health for a single zone over time."""

    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self._temp_history: deque = deque(maxlen=HISTORY_SIZE)
        self._smoke_history: deque = deque(maxlen=HISTORY_SIZE)
        self._humidity_history: deque = deque(maxlen=HISTORY_SIZE)
        self._last_good_reading: Optional[ZoneReading] = None

    def feed(self, reading: ZoneReading):
        """Add a new reading for health analysis."""
        self._temp_history.append(reading.temp)
        self._smoke_history.append(reading.smoke)
        self._humidity_history.append(reading.humidity)

    def check_health(self, reading: ZoneReading) -> SensorHealthStatus:
        """
        Run all health checks on the current reading.
        Returns a SensorHealthStatus with detected issues.
        """
        health = SensorHealthStatus(self.zone_id)
        issues = []

        # ── Check 1: Out-of-range (immediate FAULTY) ────────────────────
        if not (TEMP_RANGE[0] <= reading.temp <= TEMP_RANGE[1]):
            issues.append(('FAULTY', f"🔴 Temperature {reading.temp:.1f}°C out of physical range "
                          f"({TEMP_RANGE[0]}–{TEMP_RANGE[1]}°C)"))
            health.details['temp'] = 'OUT_OF_RANGE'

        if not (SMOKE_RANGE[0] <= reading.smoke <= SMOKE_RANGE[1]):
            issues.append(('FAULTY', f"🔴 Smoke {reading.smoke} PPM out of sensor range "
                          f"({SMOKE_RANGE[0]}–{SMOKE_RANGE[1]} PPM)"))
            health.details['smoke'] = 'OUT_OF_RANGE'

        if not (HUMIDITY_RANGE[0] <= reading.humidity <= HUMIDITY_RANGE[1]):
            issues.append(('FAULTY', f"🔴 Humidity {reading.humidity:.1f}% out of physical range "
                          f"({HUMIDITY_RANGE[0]}–{HUMIDITY_RANGE[1]}%)"))
            health.details['humidity'] = 'OUT_OF_RANGE'

        # ── Check 2: Stuck sensor detection ─────────────────────────────
        if len(self._temp_history) >= STUCK_SUSPECT_THRESHOLD:
            stuck_count = self._count_stuck(self._temp_history, STUCK_TOLERANCE)
            if stuck_count >= STUCK_THRESHOLD:
                issues.append(('FAULTY', f"🔴 Temperature sensor STUCK at {reading.temp:.1f}°C "
                              f"for {stuck_count} readings"))
                health.details['temp'] = 'STUCK'
            elif stuck_count >= STUCK_SUSPECT_THRESHOLD:
                issues.append(('SUSPECT', f"🟡 Temperature sensor may be stuck at {reading.temp:.1f}°C "
                              f"({stuck_count} identical readings)"))
                health.details['temp'] = health.details.get('temp', 'SUSPECT_STUCK')

        if len(self._smoke_history) >= STUCK_SUSPECT_THRESHOLD:
            stuck_count = self._count_stuck(self._smoke_history, STUCK_TOLERANCE)
            if stuck_count >= STUCK_THRESHOLD:
                issues.append(('FAULTY', f"🔴 Smoke sensor STUCK at {reading.smoke} PPM "
                              f"for {stuck_count} readings"))
                health.details['smoke'] = 'STUCK'
            elif stuck_count >= STUCK_SUSPECT_THRESHOLD:
                issues.append(('SUSPECT', f"🟡 Smoke sensor may be stuck at {reading.smoke} PPM "
                              f"({stuck_count} identical readings)"))
                health.details['smoke'] = health.details.get('smoke', 'SUSPECT_STUCK')

        # ── Check 3: Spike detection ────────────────────────────────────
        if len(self._temp_history) >= 5:
            # Check if latest reading is a spike relative to recent history
            recent = list(self._temp_history)[:-1]  # Everything except the latest
            if self._is_spike(reading.temp, recent):
                issues.append(('SUSPECT', f"🟡 Temperature spike detected: {reading.temp:.1f}°C "
                              f"(recent avg: {sum(recent)/len(recent):.1f}°C)"))
                health.details['temp'] = health.details.get('temp', 'SPIKE')

        if len(self._smoke_history) >= 5:
            recent = list(self._smoke_history)[:-1]
            if self._is_spike(reading.smoke, recent):
                issues.append(('SUSPECT', f"🟡 Smoke spike detected: {reading.smoke} PPM "
                              f"(recent avg: {sum(recent)/len(recent):.0f} PPM)"))
                health.details['smoke'] = health.details.get('smoke', 'SPIKE')

        # ── Check 4: Flatline detection ─────────────────────────────────
        if len(self._temp_history) >= FLATLINE_READINGS_REQUIRED:
            if self._is_flatline(self._temp_history):
                issues.append(('SUSPECT', f"🟡 Temperature shows zero variance — "
                              f"possible sensor power issue"))
                health.details['temp'] = health.details.get('temp', 'FLATLINE')

        # ── Determine overall status ────────────────────────────────────
        if any(severity == 'FAULTY' for severity, _ in issues):
            health.status = SensorHealthStatus.FAULTY
        elif any(severity == 'SUSPECT' for severity, _ in issues):
            health.status = SensorHealthStatus.SUSPECT
        else:
            health.status = SensorHealthStatus.HEALTHY
            # Store as last known good reading
            self._last_good_reading = reading

        health.issues = [msg for _, msg in issues]
        health.last_checked = time.time()
        return health

    def get_last_good_reading(self) -> Optional[ZoneReading]:
        """Return the last reading that passed all health checks."""
        return self._last_good_reading

    @staticmethod
    def _count_stuck(history: deque, tolerance: float) -> int:
        """Count consecutive identical values from the end of history."""
        if len(history) < 2:
            return 0
        latest = history[-1]
        count = 1
        for i in range(len(history) - 2, -1, -1):
            if abs(history[i] - latest) <= tolerance:
                count += 1
            else:
                break
        return count

    @staticmethod
    def _is_spike(value: float, recent: list) -> bool:
        """Check if a value is a statistical spike relative to recent data."""
        if len(recent) < 3:
            return False
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        std = max(math.sqrt(variance), SPIKE_MIN_STD)
        return abs(value - mean) > SPIKE_MULTIPLIER * std

    @staticmethod
    def _is_flatline(history: deque) -> bool:
        """Check if a sensor shows zero variance (flatline)."""
        if len(history) < FLATLINE_READINGS_REQUIRED:
            return False
        recent = list(history)[-FLATLINE_READINGS_REQUIRED:]
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        return variance < FLATLINE_VARIANCE_THRESHOLD


class SensorHealthChecker:
    """
    Manages health tracking for all zones.

    Usage:
        checker = SensorHealthChecker()
        checker.feed(reading)                    # each tick per zone
        health = checker.check(reading)          # get health status
        all_health = checker.get_all_status()    # for UI snapshot
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._trackers: Dict[str, ZoneHealthTracker] = {}
        self._latest_status: Dict[str, SensorHealthStatus] = {}

    def _get_tracker(self, zone_id: str) -> ZoneHealthTracker:
        """Get or create a health tracker for a zone."""
        if zone_id not in self._trackers:
            self._trackers[zone_id] = ZoneHealthTracker(zone_id)
        return self._trackers[zone_id]

    def check_and_feed(self, reading: ZoneReading) -> SensorHealthStatus:
        """Feed a reading and return its health status."""
        with self._lock:
            tracker = self._get_tracker(reading.zone_id)
            tracker.feed(reading)
            health = tracker.check_health(reading)
            self._latest_status[reading.zone_id] = health
            return health

    def check_all(self, zones: Dict[str, ZoneReading]) -> Dict[str, SensorHealthStatus]:
        """Check health for all zones at once."""
        results = {}
        for zone_id, reading in zones.items():
            results[zone_id] = self.check_and_feed(reading)
        return results

    def get_status(self, zone_id: str) -> Optional[SensorHealthStatus]:
        """Get the latest health status for a zone."""
        with self._lock:
            return self._latest_status.get(zone_id)

    def get_all_status(self) -> Dict[str, dict]:
        """Get all health statuses as dicts (for UI snapshot)."""
        with self._lock:
            return {zid: s.to_dict() for zid, s in self._latest_status.items()}

    def is_zone_healthy(self, zone_id: str) -> bool:
        """Quick check if a zone's sensors are healthy."""
        with self._lock:
            s = self._latest_status.get(zone_id)
            return s is None or s.status == SensorHealthStatus.HEALTHY

    def is_zone_faulty(self, zone_id: str) -> bool:
        """Quick check if a zone's sensors are faulty."""
        with self._lock:
            s = self._latest_status.get(zone_id)
            return s is not None and s.status == SensorHealthStatus.FAULTY

    def get_last_good_reading(self, zone_id: str) -> Optional[ZoneReading]:
        """Get the last healthy reading for a zone (fallback for faulty sensors)."""
        with self._lock:
            tracker = self._trackers.get(zone_id)
            return tracker.get_last_good_reading() if tracker else None
