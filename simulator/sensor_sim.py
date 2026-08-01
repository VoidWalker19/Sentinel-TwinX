"""
simulator/sensor_sim.py — Realistic Sensor Simulator

This module generates realistic-looking sensor data for all building zones
WITHOUT needing any physical hardware. It adds realistic noise (small random
variation), so the readings don't look fake.

Demo incidents can be injected at any time via inject_incident() — this is
what the one-tap demo buttons call. When you click "Simulate Lab Fire", this
module immediately ramps up temperature and smoke in the Chemistry Lab.

The ramp-up is gradual (like a real fire) so the pipeline can be seen
going through detect → analyze → investigate → verify → recommend.
"""

import random
import time
import threading
import math
from typing import Dict, Optional
from server.state import ZoneReading
from engine.chronos import ZONE_CONFIG


# ─────────────────────────────────────────────────────────────────────────────
# Baseline "safe" readings for each zone
# ─────────────────────────────────────────────────────────────────────────────

BASELINE: Dict[str, dict] = {
    'reception':   {'temp': 23.0, 'smoke': 14,  'humidity': 65.0, 'blocked': False},
    'office':      {'temp': 23.8, 'smoke': 8,   'humidity': 62.0, 'blocked': False},
    'server':      {'temp': 32.0, 'smoke': 22,  'humidity': 42.0, 'blocked': False},
    'storage':     {'temp': 22.0, 'smoke': 5,   'humidity': 70.0, 'blocked': False},
    'corridor':    {'temp': 25.1, 'smoke': 9,   'humidity': 60.0, 'blocked': False},
    'exit_a':      {'temp': 24.4, 'smoke': 6,   'humidity': 70.0, 'blocked': False},
    'classroom_a': {'temp': 23.5, 'smoke': 7,   'humidity': 62.0, 'blocked': False},
    'classroom_b': {'temp': 23.9, 'smoke': 11,  'humidity': 62.0, 'blocked': False},
    'chem_lab':    {'temp': 28.0, 'smoke': 45,  'humidity': 55.0, 'blocked': False},
    'exit_b':      {'temp': 24.2, 'smoke': 4,   'humidity': 70.0, 'blocked': False},
}

# ─────────────────────────────────────────────────────────────────────────────
# Incident definitions — what happens when a demo button is pressed
# ─────────────────────────────────────────────────────────────────────────────

# Each incident is applied on top of the baseline.
# The 'spread' key lists adjacent zones that get mildly elevated readings
# (smoke drifts through corridors — makes the demo realistic).
INCIDENTS: Dict[str, dict] = {
    'lab_fire': {
        'zone': 'chem_lab',
        'target': {'temp': 68.0, 'smoke': 650, 'humidity': 22.0, 'blocked': False},
        'spread': {
            'corridor': {'smoke': 280, 'temp': 32.0},
            'storage':    {'smoke': 95},
        },
    },
    'corridor_smoke': {
        'zone': 'corridor',
        'target': {'temp': 36.0, 'smoke': 420, 'humidity': 38.0, 'blocked': False},
        'spread': {
            'chem_lab':    {'smoke': 120},
            'classroom_a': {'smoke': 90},
            'classroom_b': {'smoke': 90},
        },
    },
    'exit_blocked': {
        'zone': 'exit_a',
        'target': {'temp': 23.0, 'smoke': 12, 'humidity': 68.0, 'blocked': True},
        'spread': {},
    },
    'server_overheat': {
        'zone': 'server',
        'target': {'temp': 55.0, 'smoke': 180, 'humidity': 28.0, 'blocked': False},
        'spread': {
            'corridor': {'temp': 28.0, 'smoke': 60},
        },
    },
    'gas_leak': {
        'zone': 'chem_lab',
        'target': {'temp': 29.5, 'smoke': 380, 'humidity': 52.0, 'blocked': False},
        'spread': {
            'corridor':    {'smoke': 160},
            'classroom_b': {'smoke': 80},
        },
    },
    'office_fire': {
        'zone': 'office',
        'target': {'temp': 58.0, 'smoke': 520, 'humidity': 18.0, 'blocked': False},
        'spread': {
            'reception':   {'smoke': 130, 'temp': 29.0},
            'corridor':    {'smoke': 200, 'temp': 31.0},
        },
    },
    'storage_smoke': {
        'zone': 'storage',
        'target': {'temp': 42.0, 'smoke': 310, 'humidity': 30.0, 'blocked': False},
        'spread': {
            'corridor':    {'smoke': 95},
        },
    },
    'exit_b_blocked': {
        'zone': 'exit_b',
        'target': {'temp': 24.0, 'smoke': 8, 'humidity': 68.0, 'blocked': True},
        'spread': {},
    },
    'multi_zone': {
        'zone': 'chem_lab',
        'target': {'temp': 61.0, 'smoke': 480, 'humidity': 25.0, 'blocked': False},
        'spread': {
            'corridor':    {'smoke': 250, 'temp': 33.0},
            'classroom_a': {'smoke': 160, 'temp': 29.0},
            'classroom_b': {'smoke': 140},
            'storage':     {'smoke': 70},
        },
    },
}

# Random event pool — picked randomly by inject_incident('random_event')
RANDOM_EVENT_POOL = [
    'lab_fire', 'corridor_smoke', 'exit_blocked',
    'server_overheat', 'gas_leak', 'office_fire',
    'storage_smoke', 'exit_b_blocked', 'multi_zone',
]



class SensorSimulator:
    """
    Thread-safe sensor data simulator.

    Each call to get_all_readings() returns fresh data with small random
    noise. When an incident is active, the affected zone's readings ramp
    toward the target values over several seconds (simulating a real fire
    spreading gradually, not popping into existence instantly).
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Current "effective" values per zone (start at baseline)
        self._current: Dict[str, dict] = {
            zid: dict(vals) for zid, vals in BASELINE.items()
        }

        # Target values when an incident is active (None = no incident)
        self._targets: Dict[str, Optional[dict]] = {zid: None for zid in BASELINE}

        # Incident name currently active (for UI display)
        self.active_incident: Optional[str] = None

        # Ramp speed — how quickly readings move toward the target
        # 1.0 = full step per tick (instant), 0.1 = 10% per tick (gradual)
        self.RAMP_RATE = 0.18   # ~18% per tick → reaches target in ~3-4 ticks

        self._start_time = time.time()

    def inject_incident(self, scenario: str):
        """
        Inject a demo incident. The readings will ramp toward the danger values
        over the next few refresh cycles, simulating real fire spread.

        Args:
            scenario: One of 'lab_fire', 'corridor_smoke', 'exit_blocked',
                      'server_overheat', or 'reset'.
        """
        with self._lock:
            if scenario == 'reset':
                # Clear all incidents and ramp back to baseline
                for zid in BASELINE:
                    self._targets[zid] = dict(BASELINE[zid])
                self.active_incident = None
                return

            # Random event — pick from pool
            if scenario == 'random_event':
                scenario = random.choice(RANDOM_EVENT_POOL)

            if scenario not in INCIDENTS:
                return

            inc = INCIDENTS[scenario]
            primary_zone = inc['zone']

            # Set primary zone target
            self._targets[primary_zone] = {**BASELINE[primary_zone], **inc['target']}

            # Set spread zone targets (smoke drift etc.)
            for spread_zone, overrides in inc.get('spread', {}).items():
                base = dict(BASELINE.get(spread_zone, {}))
                base.update(overrides)
                self._targets[spread_zone] = base

            self.active_incident = scenario

    def reset_all(self):
        """Return all zones to safe baseline readings."""
        self.inject_incident('reset')

    def _add_noise(self, key: str, value) -> float:
        """
        Add realistic random noise to a reading.
        Temperature: ±0.3°C, Smoke: ±8 PPM, Humidity: ±1.5%
        """
        if isinstance(value, bool):
            return value
        noise_params = {
            'temp':     ('gauss', 0, 0.3),
            'smoke':    ('gauss', 0, 8),
            'humidity': ('gauss', 0, 1.2),
        }
        if key not in noise_params:
            return value
        dist, mu, sigma = noise_params[key]
        if dist == 'gauss':
            noisy = value + random.gauss(mu, sigma)
            return max(0, noisy)
        return value

    def _ramp_toward_target(self, zone_id: str):
        """
        Move the current reading one step toward the target using linear interpolation.
        This creates the gradual ramp-up effect.
        """
        target = self._targets.get(zone_id)
        if target is None:
            return
        current = self._current[zone_id]
        new = {}
        for key, target_val in target.items():
            if isinstance(target_val, bool):
                # Booleans switch immediately (a door is either blocked or not)
                new[key] = target_val
            else:
                cur_val = current.get(key, target_val)
                # Linear interpolation: step 18% of the way toward target
                new[key] = cur_val + self.RAMP_RATE * (target_val - cur_val)
        self._current[zone_id] = new

        # If we've basically arrived at the target, stop ramping
        numeric_keys = [k for k in target if not isinstance(target[k], bool)]
        if numeric_keys:
            diffs = [abs(new[k] - target[k]) for k in numeric_keys]
            if max(diffs) < 1.0:
                self._targets[zone_id] = None  # Arrived — stop ramping

    def get_all_readings(self) -> Dict[str, ZoneReading]:
        """
        Return a fresh snapshot of all zone readings with noise applied.
        This is called by the DataBridge every 2 seconds.
        """
        with self._lock:
            # Ramp all active targets
            for zone_id in list(self._current.keys()):
                if self._targets.get(zone_id) is not None:
                    self._ramp_toward_target(zone_id)

            readings = {}
            for zone_id, vals in self._current.items():
                name = ZONE_CONFIG.get(zone_id, {}).get('name', zone_id)
                blocked = vals.get('blocked', False)

                readings[zone_id] = ZoneReading(
                    zone_id=zone_id,
                    name=name,
                    temp=round(self._add_noise('temp', vals['temp']), 1),
                    smoke=max(0, int(self._add_noise('smoke', vals['smoke']))),
                    humidity=round(max(0, min(100,
                        self._add_noise('humidity', vals['humidity']))), 1),
                    blocked=blocked,
                    timestamp=time.time(),
                )
            return readings

    def get_zone_reading(self, zone_id: str) -> Optional[ZoneReading]:
        """Get a reading for a single zone (used by serial parser for missing zones)."""
        all_readings = self.get_all_readings()
        return all_readings.get(zone_id)


# Module-level singleton — shared between data_bridge and demo button callbacks
sensor_simulator = SensorSimulator()
