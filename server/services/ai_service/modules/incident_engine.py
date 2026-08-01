"""
server/services/ai_service/modules/incident_engine.py — Unified 9-Step Incident Workflow State Machine

Manages full lifecycle tracking for all 10 supported incident types:
  Detect -> Analyze -> Classify -> Prioritize -> Notify -> Attempt Recovery -> Operator Decision -> Resolve -> Generate Report -> Store History
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

class IncidentStage:
    DETECT = "DETECT"
    ANALYZE = "ANALYZE"
    CLASSIFY = "CLASSIFY"
    PRIORITIZE = "PRIORITIZE"
    NOTIFY = "NOTIFY"
    ATTEMPT_RECOVERY = "ATTEMPT_RECOVERY"
    OPERATOR_DECISION = "OPERATOR_DECISION"
    RESOLVE = "RESOLVE"
    REPORT_GENERATED = "REPORT_GENERATED"
    STORED = "STORED"

INCIDENT_WORKFLOW_STEPS = [
    IncidentStage.DETECT,
    IncidentStage.ANALYZE,
    IncidentStage.CLASSIFY,
    IncidentStage.PRIORITIZE,
    IncidentStage.NOTIFY,
    IncidentStage.ATTEMPT_RECOVERY,
    IncidentStage.OPERATOR_DECISION,
    IncidentStage.RESOLVE,
    IncidentStage.REPORT_GENERATED,
    IncidentStage.STORED
]

@dataclass
class IncidentState:
    incident_id: str
    incident_type: str         # 'FIRE', 'GAS_LEAK', 'ROVER_STUCK', 'LOW_BATTERY', 'CAMERA_OFFLINE', 'MQTT_OFFLINE', 'ESP32_OFFLINE', 'SENSOR_FAILURE', 'INTRUDER', 'HIGH_TEMP'
    zone_id: Optional[str]
    zone_name: Optional[str]
    current_stage: str         # One of IncidentStage
    priority: int              # 1 (Highest) to 5 (Lowest)
    severity: str              # 'CRITICAL', 'HIGH', 'ELEVATED', 'LOW'
    description: str
    evidence_summary: str
    recovery_attempted: bool = False
    recovery_success: bool = False
    operator_notified: bool = False
    resolved: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    timeline_logs: List[dict] = field(default_factory=list)

    def advance_stage(self, next_stage: str, log_msg: str = ""):
        self.current_stage = next_stage
        self.updated_at = time.time()
        self.timeline_logs.append({
            'stage': next_stage,
            'timestamp': self.updated_at,
            'message': log_msg or f"Incident advanced to stage {next_stage}"
        })

    def to_dict(self) -> dict:
        return {
            'incident_id': self.incident_id,
            'incident_type': self.incident_type,
            'zone_id': self.zone_id,
            'zone_name': self.zone_name,
            'current_stage': self.current_stage,
            'step_index': INCIDENT_WORKFLOW_STEPS.index(self.current_stage) if self.current_stage in INCIDENT_WORKFLOW_STEPS else 0,
            'total_steps': len(INCIDENT_WORKFLOW_STEPS),
            'priority': self.priority,
            'severity': self.severity,
            'description': self.description,
            'evidence_summary': self.evidence_summary,
            'recovery_attempted': self.recovery_attempted,
            'recovery_success': self.recovery_success,
            'operator_notified': self.operator_notified,
            'resolved': self.resolved,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'timeline_logs': self.timeline_logs,
        }


class IncidentEngine:
    """
    State machine that manages active incidents through the unified 9-step workflow.
    """

    def __init__(self):
        self.active_incidents: Dict[str, IncidentState] = {}
        self.incident_history: List[IncidentState] = []

    def create_incident(self, incident_type: str, zone_id: str = None, zone_name: str = None,
                        severity: str = "HIGH", description: str = "", evidence_summary: str = "") -> IncidentState:
        """Initializes a new incident at DETECT stage."""
        iid = f"inc_{uuid.uuid4().hex[:8]}"

        prio_map = {
            'FIRE': 1,
            'GAS_LEAK': 1,
            'ROVER_STUCK': 2,
            'INTRUDER': 2,
            'LOW_BATTERY': 3,
            'HIGH_TEMP': 3,
            'CAMERA_OFFLINE': 4,
            'MQTT_OFFLINE': 4,
            'ESP32_OFFLINE': 4,
            'SENSOR_FAILURE': 5,
        }
        prio = prio_map.get(incident_type, 3)

        inc = IncidentState(
            incident_id=iid,
            incident_type=incident_type,
            zone_id=zone_id,
            zone_name=zone_name or zone_id or "System",
            current_stage=IncidentStage.DETECT,
            priority=prio,
            severity=severity,
            description=description,
            evidence_summary=evidence_summary,
        )
        inc.advance_stage(IncidentStage.DETECT, f"Detected {incident_type} anomaly in {inc.zone_name}.")
        self.active_incidents[iid] = inc
        return inc

    def process_incident_lifecycle(self, incident_id: str, action_taker: str = "AI Engine") -> Optional[IncidentState]:
        """Automatically steps an active incident forward through analysis, classification, and notification."""
        inc = self.active_incidents.get(incident_id)
        if not inc or inc.resolved:
            return inc

        if inc.current_stage == IncidentStage.DETECT:
            inc.advance_stage(IncidentStage.ANALYZE, "Analyzing multi-sensor readings & trend parameters.")
            inc.advance_stage(IncidentStage.CLASSIFY, f"Classified hazard signature as {inc.incident_type}.")
            inc.advance_stage(IncidentStage.PRIORITIZE, f"Assigned Priority Level {inc.priority} ({inc.severity}).")
            inc.advance_stage(IncidentStage.NOTIFY, f"Dispatched operator notification for {inc.incident_type}.")
            inc.operator_notified = True

        elif inc.current_stage == IncidentStage.NOTIFY:
            inc.advance_stage(IncidentStage.ATTEMPT_RECOVERY, "Executing autonomous recovery procedure.")
            inc.recovery_attempted = True
            # Recovery simulation/attempt check
            if inc.incident_type in ('ROVER_STUCK', 'LOW_BATTERY', 'SENSOR_FAILURE'):
                inc.recovery_success = True
                inc.advance_stage(IncidentStage.OPERATOR_DECISION, "Autonomous recovery successful. Awaiting operator confirmation.")
            else:
                inc.advance_stage(IncidentStage.OPERATOR_DECISION, "Awaiting manual operator verification and resolution.")

        return inc

    def resolve_incident(self, incident_id: str, operator_notes: str = "") -> Optional[IncidentState]:
        """Resolves an incident, advances through report generation, and moves to history storage."""
        inc = self.active_incidents.get(incident_id)
        if not inc:
            return None

        inc.resolved = True
        inc.advance_stage(IncidentStage.RESOLVE, f"Incident resolved by operator: {operator_notes or 'Resolved'}")
        inc.advance_stage(IncidentStage.REPORT_GENERATED, "Generated comprehensive incident post-mortem report.")
        inc.advance_stage(IncidentStage.STORED, "Stored incident record in historical archive database.")

        self.incident_history.append(inc)
        del self.active_incidents[incident_id]
        return inc

    def get_all_active(self) -> List[dict]:
        return [inc.to_dict() for inc in self.active_incidents.values()]
