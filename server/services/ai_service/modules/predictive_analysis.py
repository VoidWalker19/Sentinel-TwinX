"""
server/services/ai_service/modules/predictive_analysis.py — Hardware & Environmental Predictive AI Engine

Analyzes sensor trends, battery decay curves, WiFi RSSI signal strength, and hardware variance
to generate proactive warnings and maintenance recommendations BEFORE failures occur.
"""

import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

@dataclass
class PredictiveInsight:
    insight_type: str        # 'BATTERY_DECAY', 'WEAK_WIFI', 'SENSOR_FREEZE', 'HAZARD_RISING', 'MAINTENANCE_REQUIRED'
    severity: str            # 'CRITICAL', 'WARNING', 'ADVISORY'
    target_zone: Optional[str]
    target_zone_name: Optional[str]
    headline: str
    description: str
    recommendation: str
    confidence_score: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            'insight_type': self.insight_type,
            'severity': self.severity,
            'target_zone': self.target_zone,
            'target_zone_name': self.target_zone_name,
            'headline': self.headline,
            'description': self.description,
            'recommendation': self.recommendation,
            'confidence_score': round(self.confidence_score, 2),
            'confidence_pct': f"{round(self.confidence_score * 100)}%",
            'timestamp': self.timestamp,
        }


class PredictiveAnalysisEngine:
    """
    Predictive maintenance & environmental trend AI module.
    """

    def __init__(self):
        self._battery_history: List[Tuple[float, float]] = []  # (timestamp, battery_pct)
        self._sensor_history: Dict[str, List[dict]] = {}       # zone_id -> list of readings

    def analyze_system_trends(self, snapshot: dict) -> List[PredictiveInsight]:
        """
        Analyzes building snapshot to extract predictive maintenance insights.
        """
        insights: List[PredictiveInsight] = []
        now = time.time()

        rover = snapshot.get('rover', {})
        zones = snapshot.get('zones', {})
        predictions = snapshot.get('predictions', {})
        mqtt_status = snapshot.get('mqtt_status', {})

        from engine.config_loader import ZONE_CONFIG

        # 1. Analyze Rover Battery Decay Rate
        batt_pct = float(rover.get('battery_pct', 100.0) or 100.0)
        self._battery_history.append((now, batt_pct))
        if len(self._battery_history) > 30:
            self._battery_history = self._battery_history[-30:]

        if len(self._battery_history) >= 5:
            dt = self._battery_history[-1][0] - self._battery_history[0][0]
            dbatt = self._battery_history[0][1] - self._battery_history[-1][1]
            if dt > 10.0 and dbatt > 0:
                drain_per_min = (dbatt / dt) * 60.0
                if drain_per_min >= 2.5 and batt_pct < 40.0:
                    insights.append(PredictiveInsight(
                        insight_type='BATTERY_DECAY',
                        severity='WARNING',
                        target_zone=rover.get('current_zone'),
                        target_zone_name=ZONE_CONFIG.get(rover.get('current_zone', ''), {}).get('name', 'Rover Base'),
                        headline='Possible Battery Cell Degradation',
                        description=f"Rover battery discharging rapidly ({drain_per_min:.1f}% per minute). Current level: {batt_pct:.1f}%.",
                        recommendation="Recharge Rover Soon & Schedule Battery Inspection.",
                        confidence_score=0.89,
                    ))

        # 2. Analyze WiFi RSSI Signal Strength & Weak Link Areas
        node_statuses = mqtt_status.get('node_statuses', {})
        for zid, ninfo in node_statuses.items():
            rssi = ninfo.get('rssi')
            zname = ZONE_CONFIG.get(zid, {}).get('name', zid)
            if rssi is not None and rssi < -82:
                insights.append(PredictiveInsight(
                    insight_type='WEAK_WIFI',
                    severity='ADVISORY',
                    target_zone=zid,
                    target_zone_name=zname,
                    headline='Weak Signal Coverage Area',
                    description=f"WiFi signal strength in {zname} is severely attenuated ({rssi} dBm). Packet loss risk elevated.",
                    recommendation=f"Inspect WiFi Access Point signal coverage near {zname}.",
                    confidence_score=0.92,
                ))

        # 3. Analyze Sensor Health & Freeze Detection
        for zid, zdata in zones.items():
            if not zdata.get('online', True):
                continue

            zname = ZONE_CONFIG.get(zid, {}).get('name', zid)
            if zid not in self._sensor_history:
                self._sensor_history[zid] = []
            self._sensor_history[zid].append({'time': now, 'temp': zdata.get('temp'), 'smoke': zdata.get('smoke')})
            if len(self._sensor_history[zid]) > 20:
                self._sensor_history[zid] = self._sensor_history[zid][-20:]

            hist = self._sensor_history[zid]
            if len(hist) >= 10:
                temps = [h['temp'] for h in hist if h['temp'] is not None]
                if len(temps) >= 10 and len(set(temps)) == 1:
                    # Sensor value identical across 10 consecutive ticks (frozen ADC)
                    insights.append(PredictiveInsight(
                        insight_type='SENSOR_FREEZE',
                        severity='WARNING',
                        target_zone=zid,
                        target_zone_name=zname,
                        headline='Stuck / Frozen Sensor Output',
                        description=f"Temperature sensor in {zname} outputting identical static value ({temps[0]}°C) across 10 consecutive ticks.",
                        recommendation=f"Replace or recalibrate sensor module in {zname}.",
                        confidence_score=0.85,
                    ))

        # 4. Analyze Hazard Rising Trends
        for zid, pinfo in predictions.items():
            if pinfo.get('trend') == 'rising' and pinfo.get('slope', 0) > 0.5:
                zname = ZONE_CONFIG.get(zid, {}).get('name', zid)
                proj = pinfo.get('projected_score_30s', 0)
                insights.append(PredictiveInsight(
                    insight_type='HAZARD_RISING',
                    severity='WARNING' if proj >= 60 else 'ADVISORY',
                    target_zone=zid,
                    target_zone_name=zname,
                    headline='Escalating Risk Trend Detected',
                    description=f"Risk score in {zname} rising at +{pinfo.get('slope', 0):.1f} pts/sec. Projected 30s score: {proj}/100.",
                    recommendation=f"Increase Patrol Frequency & Focus Surveillance on {zname}.",
                    confidence_score=0.91,
                ))

        return insights
