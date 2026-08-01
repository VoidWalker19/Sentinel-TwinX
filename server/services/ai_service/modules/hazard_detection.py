"""
server/services/ai_service/modules/hazard_detection.py — Multi-Sensor Hazard Detection Engine

Correlates telemetry from DHT22 (temp/humidity), MQ-2 (smoke/combustible gas),
MQ-7 (CO), MQ-135 (air quality), and HC-SR04 (path obstruction) to accurately
classify hazard signatures and produce empirical sensor evidence.
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# Default thresholds (matched with building.json / CHRONOS defaults)
TEMP_CRITICAL = 65.0
TEMP_HIGH = 50.0
TEMP_ELEVATED = 38.0

SMOKE_CRITICAL = 600
SMOKE_HIGH = 400
SMOKE_MODERATE = 200

MQ7_HIGH = 150
MQ135_HIGH = 300


@dataclass
class SensorEvidence:
    """Empirical proof for a detected hazard condition."""
    sensor_name: str
    reading: Any
    unit: str
    threshold: Any
    status: str       # 'EXCEEDED', 'ELEVATED', 'ABNORMAL', 'NOMINAL', 'OFFLINE'
    impact_weight: float = 1.0

    def to_dict(self) -> dict:
        return {
            'sensor_name': self.sensor_name,
            'reading': self.reading,
            'unit': self.unit,
            'threshold': self.threshold,
            'status': self.status,
            'impact_weight': self.impact_weight,
        }


@dataclass
class HazardClassification:
    """Classified hazard signature for a single zone."""
    zone_id: str
    zone_name: str
    hazard_type: str    # 'FIRE', 'GAS_LEAK', 'THERMAL_OVERHEAT', 'CO_HAZARD', 'PATH_OBSTRUCTION', 'INTRUDER', 'NOMINAL', 'OFFLINE'
    severity: str       # 'CRITICAL', 'HIGH', 'ELEVATED', 'LOW', 'NONE'
    confidence: float   # 0.0 to 1.0 (0% - 100%)
    evidence: List[SensorEvidence] = field(default_factory=list)
    description: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            'zone_id': self.zone_id,
            'zone_name': self.zone_name,
            'hazard_type': self.hazard_type,
            'severity': self.severity,
            'confidence': round(self.confidence * 100, 1),
            'confidence_pct': f"{round(self.confidence * 100)}%",
            'evidence': [e.to_dict() for e in self.evidence],
            'description': self.description,
            'timestamp': self.timestamp,
        }


class HazardDetectionEngine:
    """
    Engine responsible for multi-sensor fusion correlation and empirical hazard classification.
    """

    def __init__(self, thresholds: dict = None):
        self.thresholds = thresholds or {}

    def classify_zone(self, zone_id: str, zone_name: str, zone_data: dict, risk_score: int = 0) -> HazardClassification:
        """
        Analyses multi-sensor telemetry for a zone and returns empirical evidence + classification.
        """
        # Check offline state (Honesty Rule)
        if not zone_data.get('online', True) or zone_data.get('temp') is None or zone_data.get('smoke') is None:
            return HazardClassification(
                zone_id=zone_id,
                zone_name=zone_name,
                hazard_type='OFFLINE',
                severity='NONE',
                confidence=1.0,
                evidence=[SensorEvidence("Link State", "Disconnected", "", "Online", "OFFLINE", 0.0)],
                description=f"Sensor node in {zone_name} is offline. No live telemetry available.",
            )

        temp = float(zone_data.get('temp', 0.0) or 0.0)
        smoke = int(zone_data.get('smoke', 0) or 0)
        humidity = float(zone_data.get('humidity', 50.0) or 50.0)
        mq7 = int(zone_data.get('mq7', 0) or 0)
        mq135 = int(zone_data.get('mq135', 0) or 0)
        blocked = bool(zone_data.get('blocked', False))

        t_crit = self.thresholds.get('temp_critical', TEMP_CRITICAL)
        t_high = self.thresholds.get('temp_high', TEMP_HIGH)
        t_elev = self.thresholds.get('temp_elevated', TEMP_ELEVATED)

        s_crit = self.thresholds.get('smoke_critical', SMOKE_CRITICAL)
        s_high = self.thresholds.get('smoke_high', SMOKE_HIGH)
        s_mod = self.thresholds.get('smoke_moderate', SMOKE_MODERATE)

        evidence_list: List[SensorEvidence] = []

        # 1. Active Combustion Fire (High Temp + High Smoke)
        if (temp >= t_high and smoke >= s_mod) or (smoke >= s_high and temp >= t_elev):
            evidence_list.append(SensorEvidence("Temperature", f"{temp:.1f}", "°C", t_high, "EXCEEDED" if temp >= t_high else "ELEVATED", 0.4))
            evidence_list.append(SensorEvidence("MQ2 Smoke/Gas", smoke, "PPM", s_mod, "EXCEEDED" if smoke >= s_high else "ELEVATED", 0.4))
            if humidity < 30.0:
                evidence_list.append(SensorEvidence("Humidity", f"{humidity:.0f}", "%", 30, "DRY_AIR", 0.2))

            conf = min(0.99, 0.70 + (smoke / 1000.0) * 0.15 + (temp / 100.0) * 0.15)
            sev = 'CRITICAL' if (temp >= t_crit or smoke >= s_crit or risk_score >= 80) else 'HIGH'
            return HazardClassification(
                zone_id=zone_id,
                zone_name=zone_name,
                hazard_type='FIRE',
                severity=sev,
                confidence=conf,
                evidence=evidence_list,
                description=f"Active combustion fire signature detected in {zone_name}. Temp: {temp:.1f}°C, Smoke: {smoke} PPM.",
            )

        # 2. Gas Leak / Chemical Vapor (High MQ-2 / MQ-135 + Normal Temp)
        if smoke >= s_high and temp < t_high:
            evidence_list.append(SensorEvidence("MQ2 Smoke/Gas", smoke, "PPM", s_high, "EXCEEDED", 0.5))
            evidence_list.append(SensorEvidence("Temperature", f"{temp:.1f}", "°C", t_high, "NOMINAL", 0.2))
            if mq135 > MQ135_HIGH:
                evidence_list.append(SensorEvidence("MQ135 Air Quality", mq135, "PPM", MQ135_HIGH, "EXCEEDED", 0.3))

            conf = min(0.95, 0.65 + (smoke / 1000.0) * 0.25)
            sev = 'CRITICAL' if smoke >= s_crit else 'HIGH'
            return HazardClassification(
                zone_id=zone_id,
                zone_name=zone_name,
                hazard_type='GAS_LEAK',
                severity=sev,
                confidence=conf,
                evidence=evidence_list,
                description=f"Gas leak / combustible vapor concentration detected in {zone_name} ({smoke} PPM). Ambient temp normal.",
            )

        # 3. Thermal Overheat / Equipment Fault (High Temp + Low Smoke)
        if temp >= t_high and smoke < s_mod:
            evidence_list.append(SensorEvidence("Temperature", f"{temp:.1f}", "°C", t_high, "EXCEEDED", 0.7))
            evidence_list.append(SensorEvidence("MQ2 Smoke/Gas", smoke, "PPM", s_mod, "NOMINAL", 0.3))

            conf = min(0.92, 0.60 + (temp / 100.0) * 0.3)
            sev = 'CRITICAL' if temp >= t_crit else 'HIGH'
            return HazardClassification(
                zone_id=zone_id,
                zone_name=zone_name,
                hazard_type='THERMAL_OVERHEAT',
                severity=sev,
                confidence=conf,
                evidence=evidence_list,
                description=f"Thermal anomaly recorded in {zone_name} ({temp:.1f}°C). Smoke levels nominal — probable equipment failure/overheating.",
            )

        # 4. Carbon Monoxide Hazard
        if mq7 >= MQ7_HIGH:
            evidence_list.append(SensorEvidence("MQ7 Carbon Monoxide", mq7, "PPM", MQ7_HIGH, "EXCEEDED", 0.8))
            return HazardClassification(
                zone_id=zone_id,
                zone_name=zone_name,
                hazard_type='CO_HAZARD',
                severity='HIGH',
                confidence=0.88,
                evidence=evidence_list,
                description=f"Dangerous Carbon Monoxide (CO) concentration in {zone_name} ({mq7} PPM).",
            )

        # 5. Egress Path Obstruction
        if blocked:
            evidence_list.append(SensorEvidence("HC-SR04 Proximity", "Blocked (<15cm)", "cm", 15, "EXCEEDED", 1.0))
            sev = 'CRITICAL' if risk_score >= 60 else 'HIGH'
            return HazardClassification(
                zone_id=zone_id,
                zone_name=zone_name,
                hazard_type='PATH_OBSTRUCTION',
                severity=sev,
                confidence=0.96,
                evidence=evidence_list,
                description=f"Physical obstruction detected blocking the evacuation corridor in {zone_name}.",
            )

        # 6. Moderate Advisory / Elevated Readings
        if temp >= t_elev or smoke >= s_mod:
            if temp >= t_elev:
                evidence_list.append(SensorEvidence("Temperature", f"{temp:.1f}", "°C", t_elev, "ELEVATED", 0.5))
            if smoke >= s_mod:
                evidence_list.append(SensorEvidence("MQ2 Smoke/Gas", smoke, "PPM", s_mod, "ELEVATED", 0.5))

            return HazardClassification(
                zone_id=zone_id,
                zone_name=zone_name,
                hazard_type='ELEVATED_READINGS',
                severity='ELEVATED',
                confidence=0.75,
                evidence=evidence_list,
                description=f"Elevated environmental readings in {zone_name}. Temp: {temp:.1f}°C, Smoke: {smoke} PPM.",
            )

        # 7. Nominal / Safe
        evidence_list.append(SensorEvidence("Temperature", f"{temp:.1f}", "°C", t_elev, "NOMINAL", 0.33))
        evidence_list.append(SensorEvidence("MQ2 Smoke/Gas", smoke, "PPM", s_mod, "NOMINAL", 0.33))
        evidence_list.append(SensorEvidence("Path State", "Clear", "", "Clear", "NOMINAL", 0.34))
        return HazardClassification(
            zone_id=zone_id,
            zone_name=zone_name,
            hazard_type='NOMINAL',
            severity='NONE',
            confidence=0.99,
            evidence=evidence_list,
            description=f"All sensor parameters in {zone_name} are within normal operating limits.",
        )

    def analyze_snapshot(self, snapshot: dict) -> Dict[str, HazardClassification]:
        """Classifies hazards across all zones in a building state snapshot."""
        zones = snapshot.get('zones', {})
        risk_scores = snapshot.get('risk_scores', {})
        results = {}

        from engine.config_loader import ZONE_CONFIG
        for zone_id, zdata in zones.items():
            zname = ZONE_CONFIG.get(zone_id, {}).get('name', zone_id)
            rscore = risk_scores.get(zone_id, {}).get('score', 0)
            results[zone_id] = self.classify_zone(zone_id, zname, zdata, rscore)

        return results
