"""
engine/config_loader.py — Unified Building Configuration Loader

This module acts as the single source of truth for the building layout,
sensor thresholds, graph adjacency, map coordinates, and hardware configuration.
Every other backend module imports its building data from here.
"""

import json
import os
from pathlib import Path

# Locate the config file path relative to this file
CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'building.json'

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Config file not found at: {CONFIG_PATH.resolve()}")
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

# Load the raw config dictionary
config_data = load_config()

# Expose parsed configuration elements
RAW_ZONES = config_data.get('zones', {})

# 1. ZONE_CONFIG maps zone_id -> metadata (matches v2 shape)
ZONE_CONFIG = {
    zone_id: {
        'name': z.get('name', zone_id),
        'floor': z.get('floor', 1),
        'high_risk_baseline': z.get('high_risk_baseline', False)
    }
    for zone_id, z in RAW_ZONES.items()
}

# 2. ZONE_GRAPH maps zone_id -> list of direct neighbors
ZONE_GRAPH = {
    zone_id: z.get('adjacencies', [])
    for zone_id, z in RAW_ZONES.items()
}

# 3. ZONE_MAP_POSITIONS maps zone_id -> (x, y) coordinate tuple
ZONE_MAP_POSITIONS = {
    zone_id: tuple(z.get('position', [0.0, 0.0]))
    for zone_id, z in RAW_ZONES.items()
}

# 4. EXIT_ZONES is a set of all exit zone identifiers
EXIT_ZONES = {
    zone_id for zone_id, z in RAW_ZONES.items() if z.get('is_exit', False)
}

# 5. Global thresholds and safety limits
THRESHOLDS = config_data.get('thresholds', {})

# 6. Hardware pin maps and motor settings
HARDWARE_CONFIG = config_data.get('hardware_config', {})
PIN_MAP = HARDWARE_CONFIG.get('pin_map', {})
MOTOR_PWM_MAX = HARDWARE_CONFIG.get('motor_pwm_max', 255)
MOTOR_PWM_PATROL = HARDWARE_CONFIG.get('motor_pwm_patrol', 180)
