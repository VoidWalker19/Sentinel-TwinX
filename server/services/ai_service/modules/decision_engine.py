"""
server/services/ai_service/modules/decision_engine.py — AI Decision Engine & "WHY" Explainability Framework

Guarantees that EVERY autonomous decision or proposed action comes with complete
empirical justification, breakdown of sensor triggers, confidence score, and clear reasoning.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from server.services.ai_service.modules.hazard_detection import HazardClassification, SensorEvidence


@dataclass
class DecisionExplanation:
    """Structured 'WHY' explanation for an AI decision or action."""
    decision_title: str
    action_name: str
    params: dict
    target_zone: Optional[str]
    target_zone_name: Optional[str]
    hazard_type: str
    severity: str
    confidence: float
    confidence_pct: str
    reasons: List[str]
    sensor_breakdown: List[dict]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            'decision_title': self.decision_title,
            'action_name': self.action_name,
            'params': self.params,
            'target_zone': self.target_zone,
            'target_zone_name': self.target_zone_name,
            'hazard_type': self.hazard_type,
            'severity': self.severity,
            'confidence': self.confidence,
            'confidence_pct': self.confidence_pct,
            'reasons': self.reasons,
            'sensor_breakdown': self.sensor_breakdown,
            'timestamp': self.timestamp,
        }


class DecisionEngine:
    """
    Evaluates building state & classified hazards to construct explainable AI action proposals.
    """

    def evaluate_actions(self, snapshot: dict, hazards: Dict[str, HazardClassification]) -> List[DecisionExplanation]:
        """
        Generates fully justified decision proposals from building snapshot + hazard analysis.
        """
        explanations: List[DecisionExplanation] = []

        risk_scores = snapshot.get('risk_scores', {})
        system_status = snapshot.get('system_status', 'green')
        rover = snapshot.get('rover', {})
        predictions = snapshot.get('predictions', {})
        alert_active = snapshot.get('alert_active', False)
        layout_mode = snapshot.get('layout_mode', 'standard')
        focused_zone = snapshot.get('focused_zone')

        from engine.config_loader import ZONE_CONFIG

        # 1. Evaluate Alarm Activation / Crisis Layout Proposal
        if system_status == 'red' and not alert_active:
            explanations.append(DecisionExplanation(
                decision_title="Activate Building Emergency Alarm",
                action_name="set_alarm",
                params={'status': True, 'reason': "Overall building risk has breached CRITICAL threshold (>=80)."},
                target_zone=None,
                target_zone_name="All Zones",
                hazard_type="BUILDING_CRISIS",
                severity="CRITICAL",
                confidence=0.99,
                confidence_pct="99%",
                reasons=[
                    "System status evaluated as RED (CRITICAL).",
                    "Multiple sensor nodes report correlated emergency readings.",
                    "Immediate occupant notification and evacuation required."
                ],
                sensor_breakdown=[
                    {"sensor": "Overall Risk Index", "value": f"{snapshot.get('overall_risk', 0)}/100", "threshold": "80/100", "status": "CRITICAL"}
                ]
            ))

        # 2. Find Highest Hazard Zone for Rover Dispatch
        worst_zone = None
        worst_score = 0
        worst_hazard: Optional[HazardClassification] = None

        for zid, hclass in hazards.items():
            rscore = risk_scores.get(zid, {}).get('score', 0)
            if rscore > worst_score:
                worst_score = rscore
                worst_zone = zid
                worst_hazard = hclass

        # Propose Rover Dispatch if high risk detected and rover is available
        if worst_zone and worst_score >= 60 and worst_hazard:
            rover_status = rover.get('status', 'idle')
            rover_target = rover.get('target_zone')
            worst_name = ZONE_CONFIG.get(worst_zone, {}).get('name', worst_zone)

            if rover_status == 'idle' or (rover_status != 'idle' and rover_target != worst_zone and worst_score >= 80):
                # Build sensor breakdown
                breakdown = [
                    {"sensor": ev.sensor_name, "value": f"{ev.reading} {ev.unit}".strip(), "threshold": f"{ev.threshold} {ev.unit}".strip(), "status": ev.status}
                    for ev in worst_hazard.evidence
                ]
                breakdown.append({"sensor": "CHRONOS Score", "value": f"{worst_score}/100", "threshold": "60/100", "status": "EXCEEDED"})

                # Build reasons
                reasons = worst_hazard.description.split('. ')
                reasons.append(f"CHRONOS risk score reached {worst_score}/100.")
                reasons.extend(risk_scores.get(worst_zone, {}).get('reasons', []))

                explanations.append(DecisionExplanation(
                    decision_title=f"Deploy Rover Investigation to {worst_name}",
                    action_name="dispatch_rover",
                    params={'zone': worst_zone, 'reason': f"{worst_hazard.hazard_type} detected in {worst_name} (score {worst_score}/100)."},
                    target_zone=worst_zone,
                    target_zone_name=worst_name,
                    hazard_type=worst_hazard.hazard_type,
                    severity=worst_hazard.severity,
                    confidence=worst_hazard.confidence,
                    confidence_pct=worst_hazard.to_dict()['confidence_pct'],
                    reasons=list(set(reasons))[:4],
                    sensor_breakdown=breakdown,
                ))

        # 3. Propose Rover Recall if All Zones Safe
        elif rover.get('status') in ('done', 'verifying') and worst_score < 30:
            explanations.append(DecisionExplanation(
                decision_title="Recall Rover to Base Station",
                action_name="recall_rover",
                params={'reason': "All building zones have returned to nominal safety parameters."},
                target_zone=None,
                target_zone_name="Base Station",
                hazard_type="NOMINAL",
                severity="NONE",
                confidence=0.95,
                confidence_pct="95%",
                reasons=[
                    "Highest zone risk score is below advisory threshold (<30).",
                    "No active hazards detected in building snapshot.",
                    "Preserving rover battery by recalling to charging dock."
                ],
                sensor_breakdown=[
                    {"sensor": "Peak Building Risk", "value": f"{worst_score}/100", "threshold": "30/100", "status": "NOMINAL"}
                ]
            ))

        # 4. Propose UI Focus on Rising Risk Trend
        for zid, pinfo in predictions.items():
            if pinfo.get('trend') == 'rising' and pinfo.get('current_score', 0) >= 40:
                if focused_zone != zid:
                    zname = ZONE_CONFIG.get(zid, {}).get('name', zid)
                    explanations.append(DecisionExplanation(
                        decision_title=f"Focus Dashboard Viewport on {zname}",
                        action_name="focus_ui",
                        params={'zone': zid, 'reason': f"Predictive model detects rising risk trend (+{pinfo.get('slope', 0):.1f} pts/sec)."},
                        target_zone=zid,
                        target_zone_name=zname,
                        hazard_type="PREDICTIVE_RISING",
                        severity="ELEVATED",
                        confidence=0.85,
                        confidence_pct="85%",
                        reasons=[
                            f"Predictive engine indicates risk score rising in {zname}.",
                            f"Slope: +{pinfo.get('slope', 0):.1f} points/second.",
                            f"Projected 30s score: {pinfo.get('projected_score_30s', 0)}/100."
                        ],
                        sensor_breakdown=[
                            {"sensor": "Rate of Change", "value": f"+{pinfo.get('slope', 0):.1f} pts/s", "threshold": "+0.1 pts/s", "status": "RISING"},
                            {"sensor": "Projected 30s Score", "value": f"{pinfo.get('projected_score_30s', 0)}/100", "threshold": "60/100", "status": "WARNING"}
                        ]
                    ))
                    break

        # 5. UI Layout Adjustments
        if system_status == 'red' and layout_mode != 'crisis':
            explanations.append(DecisionExplanation(
                decision_title="Switch UI to Crisis Mode",
                action_name="set_layout",
                params={'layout_mode': 'crisis', 'reason': "Critical emergency detected. Expanding map and telemetry feeds."},
                target_zone=None,
                target_zone_name=None,
                hazard_type="UI_RECONFIG",
                severity="HIGH",
                confidence=1.0,
                confidence_pct="100%",
                reasons=["Building status is RED.", "Crisis layout prioritizes visual emergency camera stream."],
                sensor_breakdown=[]
            ))
        elif system_status == 'green' and layout_mode != 'standard':
            explanations.append(DecisionExplanation(
                decision_title="Restore Standard Dashboard Layout",
                action_name="set_layout",
                params={'layout_mode': 'standard', 'reason': "Building status restored to safe nominal state."},
                target_zone=None,
                target_zone_name=None,
                hazard_type="UI_RECONFIG",
                severity="NONE",
                confidence=1.0,
                confidence_pct="100%",
                reasons=["Building status returned to GREEN.", "Restoring full multi-card monitoring view."],
                sensor_breakdown=[]
            ))

        return explanations
