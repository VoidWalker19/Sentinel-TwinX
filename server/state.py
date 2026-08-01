"""
server/state.py — Shared application state (thread-safe singleton)

This module is the "memory" of Sentinel Twin.
Every background thread writes here; the FastAPI server/WebSocket reads and writes here.
A threading.Lock keeps things safe when multiple threads access data at the same time.
"""

import os
import io
import csv
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Data classes — simple containers that hold one piece of state each
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ZoneReading:
    """One sensor snapshot from a single building zone."""
    zone_id: str
    name: str
    temp: Optional[float] = None          # Temperature in °C (from DHT22)
    smoke: Optional[int] = None           # Smoke/gas level in PPM (from MQ-2)
    humidity: Optional[float] = None      # Relative humidity % (from DHT22)
    mq7: Optional[int] = None             # Carbon monoxide MQ-7
    mq135: Optional[int] = None           # Air Quality MQ-135
    blocked: bool = False                 # Is the evacuation path blocked? (from HC-SR04)
    timestamp: float = field(default_factory=time.time)
    online: bool = True

    def to_dict(self):
        return {
            'zone_id': self.zone_id, 'name': self.name,
            'temp': self.temp, 'smoke': self.smoke,
            'humidity': self.humidity, 'mq7': self.mq7, 'mq135': self.mq135,
            'blocked': self.blocked, 'timestamp': self.timestamp, 'online': self.online,
        }


@dataclass
class RiskResult:
    """Output of the CHRONOS risk engine for one zone."""
    zone_id: str
    score: int           # 0–100 (0=safe, 100=critical)
    status: str          # 'green', 'yellow', 'orange', 'red'
    reasons: List[str]   # Human-readable explanations
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            'zone_id': self.zone_id, 'score': self.score,
            'status': self.status, 'reasons': self.reasons,
            'timestamp': self.timestamp,
        }


@dataclass
class PredictionResult:
    """30-second lookahead trend for one zone."""
    zone_id: str
    trend: str                       # 'rising', 'stable', 'falling'
    slope: float                     # Risk points gained per second
    projected_score_30s: int         # Estimated score in 30 seconds
    projected_critical_in: Optional[int]  # Seconds until critical (or None)
    current_score: int
    # ── Detailed fields (Point 4) ──────────────────────────────────────
    risk_band: str = 'Safe'          # 'Safe','Caution','Warning','Danger','Critical'
    risk_band_detail: str = ''       # Detailed description of current risk level
    trend_description: str = ''      # Rich trend narrative
    confidence: str = 'low'          # 'high','medium','low' based on data quality
    recommendation: str = ''         # Suggested action based on score + trend

    def to_dict(self):
        return {
            'zone_id': self.zone_id, 'trend': self.trend,
            'slope': round(self.slope, 3),
            'projected_score_30s': self.projected_score_30s,
            'projected_critical_in': self.projected_critical_in,
            'current_score': self.current_score,
            'risk_band': self.risk_band,
            'risk_band_detail': self.risk_band_detail,
            'trend_description': self.trend_description,
            'confidence': self.confidence,
            'recommendation': self.recommendation,
        }


@dataclass
class RoverState:
    """Real-time position and status of the investigation rover."""
    status: str = 'idle'             # 'idle','en_route','arrived','verifying','done','returning','charging','resuming'
    target_zone: Optional[str] = None
    current_zone: Optional[str] = None
    position: Tuple[float, float] = (385.0, 225.0)   # (x, y) on the SVG map
    eta_seconds: int = 0
    dispatch_time: Optional[float] = None
    arrival_time: Optional[float] = None
    path: List[str] = field(default_factory=list)    # Zone IDs in travel order
    sensors: dict = field(default_factory=dict)
    current_mission: Optional[dict] = None
    battery_pct: float = 100.0
    is_charging: bool = False
    speed: float = 0.0

    def to_dict(self):
        return {
            'status': self.status, 'target_zone': self.target_zone,
            'current_zone': self.current_zone, 'position': list(self.position),
            'eta_seconds': self.eta_seconds, 'dispatch_time': self.dispatch_time,
            'arrival_time': self.arrival_time, 'path': self.path,
            'sensors': self.sensors, 'current_mission': self.current_mission,
            'battery_pct': round(self.battery_pct, 1), 'is_charging': self.is_charging,
            'speed': round(self.speed, 1),
        }


@dataclass
class VerificationResult:
    """Result of the rover's AI image-verification step."""
    verdict: str          # 'CONFIRMED' or 'FALSE_ALARM'
    confidence: int       # 0–100 %
    method: str           # Short description of what was checked
    zone_id: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            'verdict': self.verdict, 'confidence': self.confidence,
            'method': self.method, 'zone_id': self.zone_id,
            'timestamp': self.timestamp,
        }


@dataclass
class InspectionRecord:
    """Structured audit log record of a completed zone inspection."""
    id: str
    zone_id: str
    zone_name: str
    timestamp: float
    verdict: str
    confidence: int
    method: str
    mission_id: Optional[str] = None
    sensors_snapshot: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            'id': self.id, 'zone_id': self.zone_id, 'zone_name': self.zone_name,
            'timestamp': self.timestamp, 'verdict': self.verdict,
            'confidence': self.confidence, 'method': self.method,
            'mission_id': self.mission_id, 'sensors_snapshot': self.sensors_snapshot,
        }


@dataclass
class AIReport:
    """Structured incident report generated by the AI narrator."""
    summary: str
    analysis: str
    severity: str          # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    confidence: str        # e.g. '92%'
    recommendations: List[str]
    tier: str              # 'cloud_gemini', 'cloud_groq', 'local_fallback'
    tier_label: str        # Shown in the UI pill
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            'summary': self.summary, 'analysis': self.analysis,
            'severity': self.severity, 'confidence': self.confidence,
            'recommendations': self.recommendations,
            'tier': self.tier, 'tier_label': self.tier_label,
            'timestamp': self.timestamp,
        }


@dataclass
class TimelineEvent:
    """One entry in the incident log."""
    event_type: str        # 'detection','dispatch','arrival','verification','alert','reset'
    description: str
    severity: str          # 'info', 'warning', 'critical'
    zone_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            'event_type': self.event_type, 'description': self.description,
            'severity': self.severity, 'zone_id': self.zone_id,
            'timestamp': self.timestamp,
        }


@dataclass
class PendingAction:
    """An action proposed by the AI that is waiting for user approval."""
    id: str
    action: str
    params: dict
    reason: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'params': self.params,
            'reason': self.reason,
            'timestamp': self.timestamp
        }


@dataclass
class AuditLogEntry:
    """An entry in the immutable audit log recording executed/rejected/failed actions."""
    timestamp: float
    action: str
    params: dict
    source: str          # 'AI (Auto)', 'AI (Approved)', 'AI (Rejected)', 'Manual'
    reason: str
    status: str          # 'Executed', 'Approved', 'Rejected', 'Failed'

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'action': self.action,
            'params': self.params,
            'source': self.source,
            'reason': self.reason,
            'status': self.status
        }


# ─────────────────────────────────────────────────────────────────────────────
# AppState — the main shared state object
# ─────────────────────────────────────────────────────────────────────────────

class AppState:
    """
    Thread-safe shared state for the entire Sentinel Twin application.
    """

    def __init__(self):
        self._lock = threading.Lock()

        # Load building configuration
        from engine.config_loader import ZONE_CONFIG, THRESHOLDS

        # ── Sensor data (latest reading per zone) ──────────────────────────
        self.zones: Dict[str, ZoneReading] = {}
        # ── Risk engine outputs ─────────────────────────────────────────────
        self.risk_scores: Dict[str, RiskResult] = {}

        # Pre-initialize zones as offline (Honesty Rule)
        for zone_id, z in ZONE_CONFIG.items():
            self.zones[zone_id] = ZoneReading(
                zone_id=zone_id,
                name=z['name'],
                temp=None,
                smoke=None,
                humidity=None,
                blocked=False,
                timestamp=0.0,
                online=False
            )
            self.risk_scores[zone_id] = RiskResult(
                zone_id=zone_id,
                score=0,
                status='offline',
                reasons=["🔌 Sensor offline (Awaiting live telemetry)"],
                timestamp=0.0
            )

        self.system_status: str = 'green'   # Overall building status
        self.overall_risk: int = 0           # 0–100

        # ── Prediction (30-second lookahead) ───────────────────────────────
        self.predictions: Dict[str, PredictionResult] = {}

        # ── AI report (from narrator) ───────────────────────────────────────
        self.ai_report: Optional[AIReport] = None

        # ── Rover & Mission Queue ──────────────────────────────────────────
        self.rover = RoverState()
        self.verification: Optional[VerificationResult] = None
        self.inspections: List[InspectionRecord] = []

        # ── Incident timeline (most recent 200 events) ─────────────────────
        self.timeline: List[TimelineEvent] = []
        self.MAX_TIMELINE = 200

        # ── Action Queue & Approvals ───────────────────────────────────────
        self.pending_actions: List[PendingAction] = []
        self.autonomous_mode: bool = False

        # ── Immutable Audit Log ────────────────────────────────────────────
        self.audit_log: List[AuditLogEntry] = []

        # ── UI Reconfiguration & Focused Elements ──────────────────────────
        self.layout_mode: str = 'standard'  # 'standard' | 'crisis' | 'focus'
        self.focused_zone: Optional[str] = None
        self.highlight_element: Optional[str] = None  # Element key to flash in UI
        self.ai_thinking: bool = False

        # ── Dynamic Safety & System Settings (Tunable) ─────────────────────
        self.settings: Dict[str, any] = {
            'temp_threshold_yellow': THRESHOLDS.get('temp_elevated', 38.0),
            'temp_threshold_red': THRESHOLDS.get('temp_high', 50.0),
            'smoke_threshold_yellow': THRESHOLDS.get('smoke_moderate', 200),
            'smoke_threshold_red': THRESHOLDS.get('smoke_high', 400),
            'blocked_threshold': 15.0,
            'rover_auto_dispatch_level': THRESHOLDS.get('rover_auto_dispatch_level', 70),
            'sensor_poll_rate': THRESHOLDS.get('sensor_poll_rate', 2.0),
            'voice_enabled': True
        }

        # ── Sensor Health & Calibration ──────────────────────────────────
        self.sensor_health: Dict[str, dict] = {}    # zone_id → health status dict
        self.calibration: Dict[str, dict] = {}      # zone_id → calibration info dict

        # ── Operator Overrides (Debug Inject Endpoint) ───────────────────
        self.sensor_overrides: Dict[str, dict] = {}

        # ── Metadata ───────────────────────────────────────────────────────
        self.last_updated: Optional[float] = None
        self.mode: str = 'serial'             # Default demo mode is now 'serial'
        self.port: str = 'COM3'
        self.alert_active: bool = False    # True when status is RED

    def reset_simulated_state(self):
        """Resets simulated overrides, blocked states, and test flags back to nominal."""
        with self._lock:
            self.sensor_overrides.clear()
            for z in self.zones.values():
                z.blocked = False


    # ── Write helpers (call these from background threads) ─────────────────

    def update_zone(self, reading: ZoneReading):
        """Update sensor data for one zone."""
        with self._lock:
            # Apply debug sensor overrides if active (e.g. for hardware demo timing injection)
            if reading.zone_id in self.sensor_overrides:
                overrides = self.sensor_overrides[reading.zone_id]
                if 'temp' in overrides:
                    reading.temp = overrides['temp']
                if 'smoke' in overrides:
                    reading.smoke = overrides['smoke']
                if 'humidity' in overrides:
                    reading.humidity = overrides['humidity']
                if 'mq7' in overrides:
                    reading.mq7 = overrides['mq7']
                if 'mq135' in overrides:
                    reading.mq135 = overrides['mq135']
                if 'blocked' in overrides:
                    reading.blocked = overrides['blocked']
                reading.online = True
            
            self.zones[reading.zone_id] = reading
            self.last_updated = time.time()

    def update_risks(self, risks: Dict[str, RiskResult],
                     system_status: str, overall_risk: int):
        """Update risk scores for all zones at once."""
        with self._lock:
            self.risk_scores = risks
            self.system_status = system_status
            self.overall_risk = overall_risk
            self.alert_active = (system_status == 'red')

    def update_predictions(self, predictions: Dict[str, PredictionResult]):
        """Update trend predictions for all zones."""
        with self._lock:
            self.predictions = predictions

    def update_ai_report(self, report: AIReport):
        """Store the latest AI incident report."""
        with self._lock:
            self.ai_report = report

    def update_rover(self, rover: RoverState):
        """Update rover position/status."""
        with self._lock:
            if self.rover.sensors and self.rover.sensors.get('source') == 'mqtt':
                if rover.sensors.get('source') != 'mqtt':
                    rover.sensors = self.rover.sensors
            self.rover = rover

    def update_verification(self, result: VerificationResult):
        """Store the latest rover verification result."""
        with self._lock:
            self.verification = result

    def add_inspection(self, record: InspectionRecord):
        """Record a completed zone inspection log."""
        with self._lock:
            self.inspections.insert(0, record)
            if len(self.inspections) > 500:
                self.inspections.pop()

    def add_timeline_event(self, event: TimelineEvent):
        """Append an event to the incident log (newest first, capped at MAX)."""
        with self._lock:
            self.timeline.insert(0, event)
            if len(self.timeline) > self.MAX_TIMELINE:
                self.timeline = self.timeline[:self.MAX_TIMELINE]

    # ── AI Action & Policy Helpers ─────────────────────────────────────────

    def add_pending_action(self, action: str, params: dict, reason: str) -> str:
        """Add a pending proposed action, returning its unique ID."""
        with self._lock:
            action_id = str(uuid.uuid4())[:8]
            self.pending_actions.append(PendingAction(id=action_id, action=action, params=params, reason=reason))
            return action_id

    def remove_pending_action(self, action_id: str) -> Optional[PendingAction]:
        """Remove and return a pending action."""
        with self._lock:
            for idx, act in enumerate(self.pending_actions):
                if act.id == action_id:
                    return self.pending_actions.pop(idx)
            return None

    def log_audit(self, action: str, params: dict, source: str, reason: str, status: str):
        """Add an entry to the immutable audit log."""
        with self._lock:
            self.audit_log.append(AuditLogEntry(
                timestamp=time.time(),
                action=action,
                params=params,
                source=source,
                reason=reason,
                status=status
            ))

    def set_autonomous_mode(self, enabled: bool):
        """Toggle the master autonomous execution mode."""
        with self._lock:
            self.autonomous_mode = enabled
            self.highlight_element = 'autonomous_mode_toggle'

    def set_ai_thinking(self, thinking: bool):
        """Set the indicator showing if AI agent is generating decisions."""
        with self._lock:
            self.ai_thinking = thinking

    def set_alert_active(self, active: bool = True):
        """Set global alert active state."""
        with self._lock:
            self.alert_active = active

    # ── UI Layout Helpers ──────────────────────────────────────────────────

    def update_layout(self, mode: str, focused_zone: Optional[str] = None):
        """Change layout mode or active focused zone."""
        with self._lock:
            self.layout_mode = mode
            self.focused_zone = focused_zone
            self.highlight_element = 'layout_engine'

    def clear_highlight(self):
        """Clear the flash/highlight indicator for UI elements."""
        with self._lock:
            self.highlight_element = None

    # ── Tunable Settings Helpers ──────────────────────────────────────────

    def update_settings(self, key: str, value: any):
        """Tune a system safety or polling threshold."""
        with self._lock:
            if key in self.settings:
                # Typecast to avoid issues
                if isinstance(self.settings[key], float):
                    self.settings[key] = float(value)
                elif isinstance(self.settings[key], int):
                    self.settings[key] = int(value)
                elif isinstance(self.settings[key], bool):
                    self.settings[key] = bool(value)
                else:
                    self.settings[key] = value
                self.highlight_element = f"setting_{key}"

    # ── Read helper ────────────────────────────────────────────────────────

    def get_snapshot(self) -> dict:
        """Return a copy of the state suitable for WebSockets/UI rendering."""
        from server.services import registry
        mission_srv = registry.get("MissionService")
        cam_srv = registry.get("CameraService")
        mqtt_srv = registry.get("MqttService")

        # Resolve real MQTT broker connection status
        mqtt_connected = mqtt_srv.is_connected() if mqtt_srv else False
        mqtt_node_count = 0
        mqtt_last_heartbeat = 0.0
        if mqtt_srv:
            node_statuses = getattr(mqtt_srv, '_node_statuses', {})
            mqtt_node_count = sum(1 for v in node_statuses.values() if v.get('online', False))
            if hasattr(mqtt_srv, 'get_last_heartbeat'):
                mqtt_last_heartbeat = mqtt_srv.get_last_heartbeat()

        # Resolve camera source and status
        is_live_capture = cam_srv.is_live_capture if (cam_srv and hasattr(cam_srv, 'is_live_capture')) else False
        cam_active = is_live_capture
        camera_source = "live_hardware" if is_live_capture else "simulated_feed"

        with self._lock:
            return {
                'zones': {k: v.to_dict() for k, v in self.zones.items()},
                'risk_scores': {k: v.to_dict() for k, v in self.risk_scores.items()},
                'system_status': self.system_status,
                'overall_risk': self.overall_risk,
                'predictions': {k: v.to_dict() for k, v in self.predictions.items()},
                'ai_report': self.ai_report.to_dict() if self.ai_report else None,
                'rover': self.rover.to_dict(),
                'camera_online': cam_active,
                'camera_source': camera_source,
                'mqtt_connected': mqtt_connected,
                'mqtt_node_count': mqtt_node_count,
                'mqtt_last_heartbeat': mqtt_last_heartbeat,
                'mqtt_broker': mqtt_srv.broker_host if mqtt_srv else os.getenv('MQTT_BROKER', 'sentinelpi.local'),
                'mqtt_port': mqtt_srv.broker_port if mqtt_srv else int(os.getenv('MQTT_PORT', '1883')),
                'network_status': {
                    'ssid': os.getenv('WIFI_SSID', 'ATL LAB'),
                    'hostname': 'sentinelpi.local',
                    'ip': os.getenv('PI_IP', '10.10.0.22'),
                    'mqtt': mqtt_connected,
                    'websocket_port': 9001,
                    'network_connected': True
                },
                'mission_queue': mission_srv.get_state_dict() if mission_srv else None,
                'verification': self.verification.to_dict() if self.verification else None,
                'inspections': [r.to_dict() for r in self.inspections[:30]],
                'timeline': [e.to_dict() for e in self.timeline[:20]],
                'pending_actions': [a.to_dict() for a in self.pending_actions],
                'autonomous_mode': self.autonomous_mode,
                'audit_log': [log.to_dict() for log in self.audit_log[-30:]], # Last 30 in live snapshot
                'layout_mode': self.layout_mode,
                'focused_zone': self.focused_zone,
                'highlight_element': self.highlight_element,
                'ai_thinking': self.ai_thinking,
                'settings': self.settings,
                'sensor_health': self.sensor_health,
                'calibration': self.calibration,
                'last_updated': self.last_updated,
                'mode': self.mode,
                'port': self.port,
                'alert_active': self.alert_active,
            }


    def clear_alert(self):
        """Reset the alert flag."""
        with self._lock:
            self.alert_active = False

    def export_audit_csv(self) -> str:
        """Generates a CSV string of the complete audit log."""
        with self._lock:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Timestamp', 'Action', 'Parameters', 'Source', 'Reason', 'Status'])
            for entry in self.audit_log:
                writer.writerow([
                    time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(entry.timestamp)),
                    entry.action,
                    str(entry.params),
                    entry.source,
                    entry.reason,
                    entry.status
                ])
            return output.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton — import this everywhere
# ─────────────────────────────────────────────────────────────────────────────
app_state = AppState()
