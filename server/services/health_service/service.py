import time
import math
from collections import deque
from typing import Dict, List, Optional
from server.services.base_service import BaseService
from server.state import ZoneReading

HISTORY_SIZE = 15
STUCK_TOLERANCE = 0.1
STUCK_THRESHOLD = 10
STUCK_SUSPECT_THRESHOLD = 6
SPIKE_MULTIPLIER = 5.0
SPIKE_MIN_STD = 1.0

TEMP_RANGE = (-40.0, 200.0)
SMOKE_RANGE = (0, 10000)
HUMIDITY_RANGE = (0.0, 100.0)

FLATLINE_VARIANCE_THRESHOLD = 0.001
FLATLINE_READINGS_REQUIRED = 10

class SensorHealthStatus:
    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self.status = 'HEALTHY'
        self.issues = []
        self.details = {}
        self.last_checked = time.time()

    def to_dict(self) -> dict:
        return {
            'zone_id': self.zone_id,
            'status': self.status,
            'issues': self.issues,
            'details': self.details,
            'last_checked': self.last_checked,
        }

class ZoneHealthTracker:
    def __init__(self, zone_id: str):
        self.zone_id = zone_id
        self._temp_history = deque(maxlen=HISTORY_SIZE)
        self._smoke_history = deque(maxlen=HISTORY_SIZE)
        self._humidity_history = deque(maxlen=HISTORY_SIZE)
        self._last_good_reading = None

    def feed(self, reading: ZoneReading):
        if reading.temp is not None:
            self._temp_history.append(reading.temp)
        if reading.smoke is not None:
            self._smoke_history.append(reading.smoke)
        if reading.humidity is not None:
            self._humidity_history.append(reading.humidity)

    def check_health(self, reading: ZoneReading) -> SensorHealthStatus:
        health = SensorHealthStatus(self.zone_id)
        issues = []

        # Out-of-range checks
        if reading.temp is not None and not (TEMP_RANGE[0] <= reading.temp <= TEMP_RANGE[1]):
            issues.append(('FAULTY', f"Temperature {reading.temp:.1f}°C out of physical range"))
            health.details['temp'] = 'OUT_OF_RANGE'

        if reading.smoke is not None and not (SMOKE_RANGE[0] <= reading.smoke <= SMOKE_RANGE[1]):
            issues.append(('FAULTY', f"Smoke {reading.smoke} PPM out of sensor range"))
            health.details['smoke'] = 'OUT_OF_RANGE'

        if reading.humidity is not None and not (HUMIDITY_RANGE[0] <= reading.humidity <= HUMIDITY_RANGE[1]):
            issues.append(('FAULTY', f"Humidity {reading.humidity:.1f}% out of physical range"))
            health.details['humidity'] = 'OUT_OF_RANGE'

        # Stuck sensor checks
        if len(self._temp_history) >= STUCK_SUSPECT_THRESHOLD and reading.temp is not None:
            stuck_count = self._count_stuck(self._temp_history, STUCK_TOLERANCE)
            if stuck_count >= STUCK_THRESHOLD:
                issues.append(('FAULTY', f"Temperature sensor STUCK at {reading.temp:.1f}°C"))
                health.details['temp'] = 'STUCK'
            elif stuck_count >= STUCK_SUSPECT_THRESHOLD:
                issues.append(('SUSPECT', f"Temperature sensor may be stuck at {reading.temp:.1f}°C"))
                health.details['temp'] = 'SUSPECT_STUCK'

        if len(self._smoke_history) >= STUCK_SUSPECT_THRESHOLD and reading.smoke is not None:
            stuck_count = self._count_stuck(self._smoke_history, STUCK_TOLERANCE)
            if stuck_count >= STUCK_THRESHOLD:
                issues.append(('FAULTY', f"Smoke sensor STUCK at {reading.smoke} PPM"))
                health.details['smoke'] = 'STUCK'
            elif stuck_count >= STUCK_SUSPECT_THRESHOLD:
                issues.append(('SUSPECT', f"Smoke sensor may be stuck at {reading.smoke} PPM"))
                health.details['smoke'] = 'SUSPECT_STUCK'

        # Spike detection
        if len(self._temp_history) >= 5 and reading.temp is not None:
            recent = list(self._temp_history)[:-1]
            if self._is_spike(reading.temp, recent):
                issues.append(('SUSPECT', f"Temperature spike detected: {reading.temp:.1f}°C"))
                health.details['temp'] = 'SPIKE'

        if len(self._smoke_history) >= 5 and reading.smoke is not None:
            recent = list(self._smoke_history)[:-1]
            if self._is_spike(reading.smoke, recent):
                issues.append(('SUSPECT', f"Smoke spike detected: {reading.smoke} PPM"))
                health.details['smoke'] = 'SPIKE'

        # Flatline checks
        if len(self._temp_history) >= FLATLINE_READINGS_REQUIRED:
            if self._is_flatline(self._temp_history):
                issues.append(('SUSPECT', "Temperature flatline variance suspect"))
                health.details['temp'] = 'FLATLINE'

        # Overall Status
        if any(severity == 'FAULTY' for severity, _ in issues):
            health.status = 'FAULTY'
        elif any(severity == 'SUSPECT' for severity, _ in issues):
            health.status = 'SUSPECT'
        else:
            health.status = 'HEALTHY'
            self._last_good_reading = reading

        health.issues = [msg for _, msg in issues]
        health.last_checked = time.time()
        return health

    def _count_stuck(self, history: deque, tolerance: float) -> int:
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

    def _is_spike(self, value: float, recent: list) -> bool:
        if len(recent) < 3:
            return False
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        std = max(math.sqrt(variance), SPIKE_MIN_STD)
        return abs(value - mean) > SPIKE_MULTIPLIER * std

    def _is_flatline(self, history: deque) -> bool:
        if len(history) < FLATLINE_READINGS_REQUIRED:
            return False
        recent = list(history)[-FLATLINE_READINGS_REQUIRED:]
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        return variance < FLATLINE_VARIANCE_THRESHOLD

    def get_last_good_reading(self) -> Optional[ZoneReading]:
        return self._last_good_reading

class HealthService(BaseService):
    """
    Health check service that checks ranges, spikes, stuck sensors, and 
    staleness (automatically marks zones offline if silent for 10 seconds).
    """
    def __init__(self, config: dict = None):
        super().__init__("HealthService", config)
        self._trackers: Dict[str, ZoneHealthTracker] = {}
        self._latest_status: Dict[str, SensorHealthStatus] = {}
        self._last_update_times: Dict[str, float] = {}
        self.staleness_timeout = self.config.get("staleness_timeout", 10.0)

    def _on_start(self) -> bool:
        self.logger.info("Health service started.")
        return True

    def check_and_feed(self, reading: ZoneReading) -> SensorHealthStatus:
        zone_id = reading.zone_id
        if zone_id not in self._trackers:
            self._trackers[zone_id] = ZoneHealthTracker(zone_id)

        self._last_update_times[zone_id] = time.time()
        self._trackers[zone_id].feed(reading)
        
        status = self._trackers[zone_id].check_health(reading)
        self._latest_status[zone_id] = status
        return status

    def get_stale_zones(self, active_zones: List[str]) -> List[str]:
        """Returns zones that have exceeded the staleness timeout."""
        now = time.time()
        stale = []
        for zone_id in active_zones:
            last_time = self._last_update_times.get(zone_id, 0)
            # If never updated, or updated too long ago
            if last_time > 0 and (now - last_time) > self.staleness_timeout:
                stale.append(zone_id)
        return stale

    def get_status(self, zone_id: str) -> Optional[SensorHealthStatus]:
        return self._latest_status.get(zone_id)

    def get_all_status(self) -> Dict[str, dict]:
        return {zid: s.to_dict() for zid, s in self._latest_status.items()}

    def get_last_good_reading(self, zone_id: str) -> Optional[ZoneReading]:
        tracker = self._trackers.get(zone_id)
        return tracker.get_last_good_reading() if tracker else None
