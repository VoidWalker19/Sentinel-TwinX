"""
rover/verifier.py — Rover AI Verification Module

When the rover arrives at a zone, it "looks" at the scene with its camera
and runs a quick AI check to determine whether the alarm is REAL or a
FALSE ALARM. This reduces false alarm rates — a key innovation in the system.

In this demo version, we use a heuristic approach:
- We select a representative sample image for the zone
- We analyse pixel statistics (brightness, colour distribution, contrast)
- We output CONFIRMED or FALSE_ALARM with a confidence percentage

If an ESP32-CAM is present, a JPEG frame could be read from serial instead
of the sample image — the heuristic code would be identical.

Why this matters: fire detection sensors have false alarm rates of 5-20%.
Visual verification after sensor alarm reduces false evacuations dramatically.
"""

import random
import time
import math
from typing import Optional
from server.state import VerificationResult


# ─────────────────────────────────────────────────────────────────────────────
# Sample image profiles per zone and scenario
#
# Each profile describes what a camera would see in this zone:
#   'fire': bright warm colours, high contrast → fire confirmed
#   'smoke': grey haze, low contrast, low brightness → smoke confirmed
#   'normal': neutral colours, consistent brightness → false alarm
#   'blocked': dark, obstacle filling the frame
#
# In a real deployment, these would be actual JPEG frames from an ESP32-CAM.
# Here we use statistical profiles (brightness, red_ratio, contrast) that
# mimic what an image analysis algorithm would measure.
# ─────────────────────────────────────────────────────────────────────────────

# Profile: (brightness_mean 0-255, red_ratio 0-1, contrast_score 0-1)
# Higher brightness + high red_ratio = fire
# Low brightness + low contrast = smoke
# Mid brightness + low red_ratio = normal

_SCENE_PROFILES = {
    'fire':    {'brightness': (200, 255), 'red_ratio': (0.55, 0.80), 'contrast': (0.65, 0.95)},
    'smoke':   {'brightness': (60, 120),  'red_ratio': (0.28, 0.42), 'contrast': (0.10, 0.35)},
    'blocked': {'brightness': (15, 55),   'red_ratio': (0.25, 0.40), 'contrast': (0.05, 0.20)},
    'normal':  {'brightness': (120, 180), 'red_ratio': (0.28, 0.38), 'contrast': (0.30, 0.55)},
}

# Which scenario to use based on zone reading thresholds
def _choose_scene_profile(zone_id: str, zone_data: dict) -> str:
    """Select the most appropriate scene profile for a zone reading."""
    temp = zone_data.get('temp')
    if temp is None:
        temp = 25.0
    smoke = zone_data.get('smoke')
    if smoke is None:
        smoke = 20
    blocked = zone_data.get('blocked')
    blocked = bool(blocked) if blocked is not None else False

    if blocked:
        return 'blocked'
    if temp >= 50 and smoke >= 300:
        return 'fire'
    if smoke >= 200:
        return 'smoke'
    if temp >= 45:
        return 'fire'   # Hot but low smoke — glowing embers
    return 'normal'


def _sample_profile(profile_name: str) -> dict:
    """Sample a random point from the given profile's ranges."""
    profile = _SCENE_PROFILES[profile_name]
    return {
        'brightness': random.uniform(*profile['brightness']),
        'red_ratio':  random.uniform(*profile['red_ratio']),
        'contrast':   random.uniform(*profile['contrast']),
    }


def _analyse_image_stats(stats: dict, profile_name: str) -> tuple[str, int, str]:
    """
    Apply decision rules to image statistics and return a verdict.

    This is what a real computer vision model would compute,
    simplified to a rule-based heuristic for the demo.

    Returns:
        (verdict, confidence_percent, method_description)
    """
    brightness = stats['brightness']
    red_ratio  = stats['red_ratio']
    contrast   = stats['contrast']

    method = f"Brightness={brightness:.0f}/255, Red={red_ratio:.0%}, Contrast={contrast:.0%}"

    if profile_name == 'fire':
        # Fire signature: bright + warm red tones + high contrast
        fire_score = (
            (brightness / 255) * 0.35 +
            (red_ratio)        * 0.40 +
            (contrast)         * 0.25
        )
        if fire_score > 0.55:
            confidence = int(75 + fire_score * 25)
            return 'CONFIRMED', min(99, confidence), method
        else:
            confidence = int(60 + (1 - fire_score) * 30)
            return 'FALSE_ALARM', min(99, confidence), method

    elif profile_name == 'smoke':
        # Smoke signature: dim + grey (low red_ratio) + low contrast
        smoke_score = (
            (1 - brightness / 255) * 0.40 +
            (0.5 - abs(red_ratio - 0.33)) * 0.30 +
            (1 - contrast)         * 0.30
        )
        if smoke_score > 0.40:
            confidence = int(70 + smoke_score * 25)
            return 'CONFIRMED', min(99, confidence), method
        else:
            confidence = int(55 + (1 - smoke_score) * 35)
            return 'FALSE_ALARM', min(95, confidence), method

    elif profile_name == 'blocked':
        confidence = random.randint(88, 97)
        return 'CONFIRMED', confidence, method

    else:  # normal
        # Normal scene — probably a false alarm
        confidence = random.randint(78, 94)
        return 'FALSE_ALARM', confidence, method


# ─────────────────────────────────────────────────────────────────────────────
# Main verification entry point
# ─────────────────────────────────────────────────────────────────────────────

def verify_zone(zone_id: str, zone_data: dict) -> VerificationResult:
    """
    Simulate rover camera verification for a zone.

    Steps:
    1. Choose the scene profile based on sensor readings
    2. Sample "image statistics" from that profile
    3. Apply the decision heuristic
    4. Return a VerificationResult

    Args:
        zone_id:   The zone the rover is at.
        zone_data: The latest sensor snapshot dict for that zone.

    Returns:
        VerificationResult with CONFIRMED or FALSE_ALARM verdict.
    """
    # Step 1: Determine what the camera would see
    profile_name = _choose_scene_profile(zone_id, zone_data)

    # Step 2: Sample image statistics (simulating pixel analysis)
    stats = _sample_profile(profile_name)

    # Step 3: Apply decision rules
    verdict, confidence, method = _analyse_image_stats(stats, profile_name)

    return VerificationResult(
        verdict=verdict,
        confidence=confidence,
        method=method,
        zone_id=zone_id,
        timestamp=time.time(),
    )
