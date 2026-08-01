import time
import uuid
import logging
from typing import List, Optional, Dict, Any, Tuple
from server.services.base_service import BaseService

class MissionStatus:
    QUEUED = 'QUEUED'
    ACTIVE = 'ACTIVE'
    PAUSED = 'PAUSED'
    DONE = 'DONE'
    ABORTED = 'ABORTED'

class MissionType:
    ROUTINE_PATROL = 'ROUTINE_PATROL'
    EMERGENCY_INSPECTION = 'EMERGENCY_INSPECTION'
    FIRE_VERIFICATION = 'FIRE_VERIFICATION'
    GAS_LEAK_INSPECTION = 'GAS_LEAK_INSPECTION'
    RESTRICTED_AREA_CHECK = 'RESTRICTED_AREA_CHECK'
    BATTERY_RETURN = 'BATTERY_RETURN'
    MISSION_RESUME = 'MISSION_RESUME'

MISSION_PRIORITY = {
    MissionType.BATTERY_RETURN: 4,
    MissionType.FIRE_VERIFICATION: 3,
    MissionType.GAS_LEAK_INSPECTION: 3,
    MissionType.EMERGENCY_INSPECTION: 3,
    MissionType.RESTRICTED_AREA_CHECK: 2,
    MissionType.ROUTINE_PATROL: 1,
    MissionType.MISSION_RESUME: 1,
}

class Mission:
    def __init__(self, mission_id: str, mission_type: str, status: str = MissionStatus.QUEUED,
                 target_zones: List[str] = None, current_zone_index: int = 0, priority: int = 1,
                 description: str = "", params: dict = None):
        self.mission_id = mission_id
        self.mission_type = mission_type
        self.status = status
        self.target_zones = target_zones or []
        self.current_zone_index = current_zone_index
        self.priority = priority
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.description = description
        self.params = params or {}

    @classmethod
    def create(cls, mission_type: str, target_zones: Optional[List[str]] = None, description: str = "",
               params: Optional[Dict[str, Any]] = None, all_zones: List[str] = None) -> 'Mission':
        mid = f"msn_{uuid.uuid4().hex[:8]}"
        prio = MISSION_PRIORITY.get(mission_type, 1)

        # Dynamic fallback base_zone loading from ConfigurationService
        from server.services import registry
        cfg_srv = registry.get("ConfigurationService")
        base_zone = "corridor"
        if cfg_srv:
            base_zone = cfg_srv.config.get("navigation_config", {}).get("base_zone", "corridor")

        if mission_type == MissionType.ROUTINE_PATROL and not target_zones:
            target_zones = all_zones or []
            if not description:
                description = "Routine building patrol across all zones"
        elif mission_type == MissionType.BATTERY_RETURN and not target_zones:
            target_zones = [base_zone]
            if not description:
                description = "Autonomous return to charging station (low battery)"

        return cls(
            mission_id=mid, mission_type=mission_type, status=MissionStatus.QUEUED,
            target_zones=target_zones, current_zone_index=0, priority=prio,
            description=description, params=params
        )

    def current_target_zone(self) -> Optional[str]:
        if 0 <= self.current_zone_index < len(self.target_zones):
            return self.target_zones[self.current_zone_index]
        return None

    def advance_zone(self) -> bool:
        self.current_zone_index += 1
        if self.current_zone_index >= len(self.target_zones):
            if self.mission_type == MissionType.ROUTINE_PATROL:
                self.current_zone_index = 0
                return True
            return False
        return True

    def to_dict(self) -> dict:
        return {
            'mission_id': self.mission_id,
            'mission_type': self.mission_type,
            'status': self.status,
            'target_zones': self.target_zones,
            'current_zone_index': self.current_zone_index,
            'current_target_zone': self.current_target_zone(),
            'priority': self.priority,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'description': self.description,
            'params': self.params,
        }

class MissionService(BaseService):
    """
    Mission Service that manages active, queued, and paused rover missions,
    tracks Mission FSM states, and decides preemption strategies.
    """
    def __init__(self, config: dict = None):
        super().__init__("MissionService", config)
        self.active_mission: Optional[Mission] = None
        self.queue: List[Mission] = []
        self.paused_missions: List[Mission] = []
        self._all_zones = []
        self.fsm_state = 'IDLE'

    def _on_start(self) -> bool:
        self.logger.info("Mission service initialized successfully.")
        return True

    def set_building_zones(self, zone_ids: List[str]):
        self._all_zones = zone_ids

    def _sync_to_convex(self, mission: Mission):
        from server.services import registry
        convex_srv = registry.get("ConvexService")
        if convex_srv:
            convex_srv.sync_mission(
                mission_id=mission.mission_id,
                mission_type=mission.mission_type.value if hasattr(mission.mission_type, 'value') else str(mission.mission_type),
                status=mission.status.value if hasattr(mission.status, 'value') else str(mission.status),
                target_zones=mission.target_zones,
                priority=mission.priority
            )

    def submit_mission(self, mission: Mission) -> Tuple[bool, str]:
        if self.active_mission and self.active_mission.mission_type == mission.mission_type:
            if self.active_mission.current_target_zone() == mission.current_target_zone():
                return False, "Similar mission is already active."

        for qm in self.queue:
            if qm.mission_type == mission.mission_type and qm.target_zones == mission.target_zones:
                return False, "Similar mission is already queued."

        if not self.active_mission:
            self._activate(mission)
            return True, f"Activated mission: {mission.description}"

        if mission.priority > self.active_mission.priority:
            preempted = self.active_mission
            if preempted.mission_type == MissionType.ROUTINE_PATROL:
                preempted.status = MissionStatus.PAUSED
                self.paused_missions.append(preempted)
            else:
                preempted.status = MissionStatus.QUEUED
                self.queue.insert(0, preempted)

            self._sync_to_convex(preempted)
            self._activate(mission)
            return True, f"Preempted {preempted.mission_type} for {mission.mission_type}"

        mission.status = MissionStatus.QUEUED
        self.queue.append(mission)
        self.queue.sort(key=lambda m: (-m.priority, m.created_at))
        self._sync_to_convex(mission)
        return True, f"Enqueued mission (priority {mission.priority})"

    def _activate(self, mission: Mission):
        mission.status = MissionStatus.ACTIVE
        if not mission.started_at:
            mission.started_at = time.time()
        self.active_mission = mission
        self._sync_to_convex(mission)

    def complete_active(self, aborted: bool = False) -> Optional[Mission]:
        if not self.active_mission:
            return None

        finished = self.active_mission
        finished.status = MissionStatus.ABORTED if aborted else MissionStatus.DONE
        finished.completed_at = time.time()
        self._sync_to_convex(finished)
        self.active_mission = None

        if self.queue:
            next_m = self.queue.pop(0)
            self._activate(next_m)
            return next_m

        if self.paused_missions:
            paused = self.paused_missions.pop(0)
            paused.status = MissionStatus.ACTIVE
            self.active_mission = paused
            self._sync_to_convex(paused)
            return paused

        return None

    def tick_queue(self, rover_status: str, battery_pct: float, high_risk_zones: List[str]) -> Optional[str]:
        """Ticks queue, schedules inspections for high risk zones, returns target zone if dispatch needed."""
        # 1. Check emergency dispatches
        for z in high_risk_zones:
            already_covered = False
            if self.active_mission and self.active_mission.mission_type == MissionType.EMERGENCY_INSPECTION and z in self.active_mission.target_zones:
                already_covered = True
            for qm in self.queue:
                if qm.mission_type == MissionType.EMERGENCY_INSPECTION and z in qm.target_zones:
                    already_covered = True
            if not already_covered:
                em = Mission.create(MissionType.EMERGENCY_INSPECTION, target_zones=[z], description=f"Emergency check of {z}", all_zones=self._all_zones)
                self.submit_mission(em)

        # 2. Trigger automatic low-battery return
        if battery_pct < 25.0 and (not self.active_mission or self.active_mission.mission_type != MissionType.BATTERY_RETURN):
            bm = Mission.create(MissionType.BATTERY_RETURN, description="Low battery safety return", all_zones=self._all_zones)
            self.submit_mission(bm)

        # 3. Start routine patrols if idle and battery is healthy
        if rover_status == 'idle' and not self.active_mission and battery_pct >= 30.0:
            if self.queue or self.paused_missions:
                self.complete_active()
            else:
                rp = Mission.create(MissionType.ROUTINE_PATROL, all_zones=self._all_zones)
                self.submit_mission(rp)

        # 4. If rover is idle and there is an active mission (including return home), dispatch it
        target_zone = None
        if rover_status == 'idle' and self.active_mission:
            target_zone = self.active_mission.current_target_zone()

        # 5. Determine new FSM State
        new_state = 'IDLE'
        if self.active_mission:
            m_type = self.active_mission.mission_type
            if m_type == MissionType.BATTERY_RETURN:
                new_state = 'RETURN_HOME'
            elif m_type in (MissionType.FIRE_VERIFICATION, MissionType.GAS_LEAK_INSPECTION, MissionType.EMERGENCY_INSPECTION):
                new_state = 'EMERGENCY'
            elif m_type == MissionType.ROUTINE_PATROL:
                new_state = 'PATROL'
            elif m_type in (MissionType.RESTRICTED_AREA_CHECK, MissionType.MISSION_RESUME):
                new_state = 'INSPECTION'

        if new_state != self.fsm_state:
            prev_state = self.fsm_state
            self.fsm_state = new_state
            self.logger.info(f"[Mission FSM] State Transition: {prev_state} -> {new_state}")
            
            # Log transition to Operations Audit database
            from server.services import registry
            db_srv = registry.get("DatabaseService")
            if db_srv:
                db_srv.log_alert("system", 0, "info", f"Mission FSM Transition: {prev_state} -> {new_state}")
                
            from server.state import app_state, TimelineEvent
            app_state.add_timeline_event(TimelineEvent(
                event_type='info',
                description=f"🤖 Mission Manager FSM transition: {prev_state} ➔ {new_state}",
                severity='info'
            ))

        return target_zone

    def get_state_dict(self) -> dict:
        return {
            'active': self.active_mission.to_dict() if self.active_mission else None,
            'queue': [m.to_dict() for m in self.queue],
            'paused': [m.to_dict() for m in self.paused_missions],
            'fsm_state': self.fsm_state
        }
