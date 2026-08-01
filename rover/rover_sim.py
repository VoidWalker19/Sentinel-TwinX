"""
rover/rover_sim.py — Autonomous Investigation Rover Simulator

This module simulates the physical rover's movement, battery charge levels,
and ultrasonic obstacle recovery behaviors. Decoupled from hardcoded zones
and routed through modular services.
"""

import time
import uuid
import threading
import logging
from typing import Dict, List, Optional, Tuple
from server.state import RoverState, TimelineEvent, ZoneReading, InspectionRecord, app_state
from rover.verifier import verify_zone

logger = logging.getLogger(__name__)

class RoverSimulator:
    """
    Simulates the investigation rover's movement and FSM behavior.
    Ticked by the Scheduler.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._status: str = 'idle'
        self._target_zone: Optional[str] = None
        self._current_zone: Optional[str] = None
        self._pos: Tuple[float, float] = (0.0, 0.0)
        self._target_pos: Tuple[float, float] = (0.0, 0.0)
        self._path: List[str] = []
        self._path_index: int = 0
        self._battery_pct: float = 100.0
        self._is_charging: bool = False

        self._dispatch_time: Optional[float] = None
        self._arrival_time: Optional[float] = None
        self._cooldown_until: Optional[float] = None
        self._latest_verification = None

        self._recently_visited: Dict[str, float] = {}
        self.REVISIT_COOLDOWN = 60.0
        self._sensors: dict = {}
        self._blocked_retries = 0

        # Lazy config bounds
        self._home_zone = "corridor"
        self._home_pos = (410.0, 129.0)

    def _resolve_home(self):
        from server.services import registry
        cfg_srv = registry.get("ConfigurationService")
        planner = registry.get("PathPlannerService")
        if cfg_srv:
            nav_cfg = cfg_srv.config.get("navigation_config", {})
            self._home_zone = nav_cfg.get("base_zone", "corridor")
        if planner:
            self._home_pos = planner.get_zone_position(self._home_zone)
        if self._current_zone is None:
            self._current_zone = self._home_zone
            self._pos = self._home_pos
            self._target_pos = self._home_pos

    def _find_path(self, start: str, target: str, blocked: Optional[List[str]] = None) -> List[str]:
        from server.services import registry
        nav_srv = registry.get("NavigationService")
        if nav_srv:
            return nav_srv.find_rover_path(start, target, blocked)
        return [start, target]

    def _interpolate(self, pos_a: Tuple[float, float], pos_b: Tuple[float, float], step: float):
        from server.services import registry
        nav_srv = registry.get("NavigationService")
        if nav_srv:
            return nav_srv.interpolate_position(pos_a, pos_b, step)
        return pos_b, True, 0.0

    def _calculate_path_distance(self, path: List[str], current_pos: Optional[Tuple[float, float]] = None) -> float:
        from server.services import registry
        nav_srv = registry.get("NavigationService")
        if nav_srv:
            return nav_srv.calculate_path_distance(path, current_pos)
        return 0.0

    def _calculate_eta(self, distance: float) -> int:
        from server.services import registry
        nav_srv = registry.get("NavigationService")
        if nav_srv:
            return nav_srv.calculate_eta(distance)
        return 0

    def tick(self, high_risk_zones: List[str], risk_scores: dict, zones: dict):
        with self._lock:
            self._resolve_home()
            now = time.time()

            # ── CHARGING / DOCKED LOGIC ─────────────────────────────────────
            if self._status == 'charging' or (self._status == 'idle' and self._current_zone == self._home_zone and self._battery_pct < 100.0):
                self._status = 'charging'
                self._is_charging = True
                self._battery_pct = min(100.0, self._battery_pct + 10.0)
                if self._battery_pct >= 99.9:
                    self._battery_pct = 100.0
                    self._is_charging = False
                    self._status = 'idle'
                    logger.info("[Rover] Battery fully recharged (100%). Ready for mission.")
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='reset',
                        description=f"🔋 Rover fully recharged at base (100%) — ready for patrol.",
                        severity='info',
                        zone_id=self._home_zone
                    ))
                    from server.services import registry
                    mission_srv = registry.get("MissionService")
                    if mission_srv:
                        mission_srv.complete_active()
                self._sensors = self._get_simulated_sensors(zones)
                return

            if self._status == 'idle':
                self._try_dispatch(high_risk_zones, now, zones)

            elif self._status in ['en_route', 'returning', 'resuming']:
                self._battery_pct = max(0.0, self._battery_pct - 0.25)
                self._update_travel(now, zones)

                # Low battery recall trigger
                if self._battery_pct <= 20.0 and self._status != 'returning' and self._target_zone != self._home_zone:
                    logger.warning("[Rover] Low battery (<=20%) — triggering auto BATTERY_RETURN mission!")
                    self._status = 'returning'
                    start_z = self._current_zone or self._home_zone
                    blocked = [z_id for z_id, z_obj in zones.items() if getattr(z_obj, 'blocked', False)]
                    self._path = self._find_path(start_z, self._home_zone, blocked)
                    self._path_index = 0
                    self._target_zone = self._home_zone
                    self._target_pos = self._home_pos
                    from server.services import registry
                    mission_srv = registry.get("MissionService")
                    if mission_srv:
                        from server.services.mission_service.service import Mission, MissionType
                        bm = Mission.create(MissionType.BATTERY_RETURN, all_zones=list(zones.keys()))
                        mission_srv.submit_mission(bm)
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='alert',
                        description="🪫 Low Battery (<=20%) — routine patrol preempted. Rover returning to base to charge.",
                        severity='warning',
                        zone_id=self._home_zone
                    ))

            elif self._status == 'arrived':
                if self._target_zone == self._home_zone:
                    self._status = 'charging'
                    self._is_charging = True
                    logger.info("[Rover] Docked at base — charging initiated.")
                else:
                    self._status = 'verifying'
                    logger.info(f"[Rover] Arrived at {self._target_zone}, starting verification")
                    self._arrival_time = now
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='arrival',
                        description=f"🤖 Rover arrived at {self._zone_name(self._target_zone)} — starting AI verification",
                        severity='info',
                        zone_id=self._target_zone,
                    ))

                    self._stamp_zone_with_rover_sensors(self._target_zone)

                    # Background verification thread execution
                    zone_id = self._target_zone
                    _zone_raw = zones.get(zone_id, {})
                    zone_data = _zone_raw.to_dict() if hasattr(_zone_raw, 'to_dict') else (_zone_raw if isinstance(_zone_raw, dict) else {})
                    threading.Thread(
                        target=self._run_verification,
                        args=(zone_id, zone_data),
                        daemon=True,
                        name='RoverVerifier',
                    ).start()

            elif self._status == 'verifying':
                self._battery_pct = max(0.0, self._battery_pct - 0.5)

            elif self._status == 'done':
                if self._cooldown_until and now >= self._cooldown_until:
                    if self._battery_pct <= 20.0:
                        self._status = 'returning'
                        self._target_pos = self._home_pos
                        self._target_zone = self._home_zone
                    else:
                        self._status = 'en_route'
                        self._target_pos = self._home_pos
                        self._target_zone = self._home_zone
                    
                    start_z = self._current_zone or self._home_zone
                    blocked = [z_id for z_id, z_obj in zones.items() if getattr(z_obj, 'blocked', False)]
                    self._path = self._find_path(start_z, self._home_zone, blocked)
                    self._path_index = 0
                    logger.info(f"[Rover] Returning to home position via route: {self._path}")

            self._sensors = self._get_simulated_sensors(zones)

    def _try_dispatch(self, high_risk_zones: List[str], now: float, zones: dict):
        if not high_risk_zones:
            return

        candidates = [
            z for z in high_risk_zones
            if (z not in self._recently_visited or
                now - self._recently_visited[z] > self.REVISIT_COOLDOWN)
        ]

        if not candidates:
            return

        target = candidates[0]
        start_z = self._current_zone or self._home_zone
        blocked = [z_id for z_id, z_obj in zones.items() if getattr(z_obj, 'blocked', False)]
        path = self._find_path(start_z, target, blocked)

        if not path:
            logger.warning(f"[Rover] Cannot dispatch to {target}: no unblocked path available")
            return

        from server.services import registry
        planner = registry.get("PathPlannerService")
        target_pos = planner.get_zone_position(target) if planner else self._home_pos

        self._status = 'en_route'
        self._target_zone = target
        self._target_pos = target_pos
        self._current_zone = start_z
        self._path = path
        self._path_index = 0
        self._dispatch_time = now
        self._latest_verification = None

        logger.info(f"[Rover] Dispatching to {target} via path: {path}")
        app_state.add_timeline_event(TimelineEvent(
            event_type='dispatch',
            description=f"🚀 Rover dispatched to {self._zone_name(target)} (Route: {' → '.join([self._zone_name(z) for z in path])})",
            severity='warning',
            zone_id=target,
        ))

    def _update_travel(self, now: float, zones: dict):
        from server.services import registry
        nav_srv = registry.get("NavigationService")
        obstacle_mgr = registry.get("ObstacleManagerService")
        planner = registry.get("PathPlannerService")
        
        speed = nav_srv.travel_speed if nav_srv else 45.0

        if not self._path or self._path_index >= len(self._path) - 1:
            if self._target_zone:
                t_pos = planner.get_zone_position(self._target_zone) if planner else self._home_pos
                self._pos, arrived, _ = self._interpolate(self._pos, t_pos, speed * 2.0)
                if arrived:
                    is_docking = self._status == 'returning' or (hasattr(app_state, 'mission_queue') and app_state.mission_queue.active_mission and app_state.mission_queue.active_mission.mission_type == 'BATTERY_RETURN')
                    if self._target_zone == self._home_zone and is_docking:
                        self._status = 'charging' if self._battery_pct < 100.0 else 'idle'
                        self._current_zone = self._home_zone
                        self._target_zone = None
                    else:
                        self._status = 'arrived'
                        self._current_zone = self._target_zone
                    self._path = []
            return

        next_zone = self._path[self._path_index + 1]
        next_pos = planner.get_zone_position(next_zone) if planner else self._home_pos

        # Check obstacle status via ObstacleManagerService
        is_blocked = False
        if obstacle_mgr:
            is_blocked = obstacle_mgr.is_blocked(next_zone)
        else:
            next_obj = zones.get(next_zone)
            is_blocked = getattr(next_obj, 'blocked', False) if next_obj else False

        if is_blocked and next_zone != self._target_zone:
            # Replan around blocked node
            logger.warning(f"[Rover] Obstacle detected at '{next_zone}'. Attempting Dijkstra replan...")
            start_z = self._path[self._path_index]
            blocked = [z_id for z_id, z_obj in zones.items() if getattr(z_obj, 'blocked', False)]
            if obstacle_mgr:
                blocked = list(set(blocked + obstacle_mgr.get_blocked_zones()))
            
            new_path = self._find_path(start_z, self._target_zone or self._home_zone, blocked)

            if new_path and len(new_path) > 1:
                logger.info(f"[Rover] Replanned successfully: {new_path}")
                self._path = new_path
                self._path_index = 0
                next_zone = self._path[self._path_index + 1]
                next_pos = planner.get_zone_position(next_zone) if planner else self._home_pos
                self._blocked_retries = 0
                app_state.add_timeline_event(TimelineEvent(
                    event_type='dispatch',
                    description=f"🚧 Obstacle at {self._zone_name(next_zone)} — rover replanned route: {' → '.join([self._zone_name(z) for z in new_path])}",
                    severity='warning',
                    zone_id=next_zone,
                ))
            else:
                # Recovery behaviors: wait in place up to 3 ticks, then backtrack return to base
                self._blocked_retries += 1
                if self._blocked_retries <= 3:
                    logger.warning(f"[Rover] Path blocked by '{next_zone}'. Recovery wait: {self._blocked_retries}/3 ticks...")
                    self._eta = 999
                    return
                else:
                    logger.warning(f"[Rover] Recovery: persistent obstacle at '{next_zone}'. Backtracking to base hub.")
                    self._blocked_retries = 0
                    self._status = 'returning'
                    self._target_zone = self._home_zone
                    self._target_pos = self._home_pos
                    
                    # Replan path home while ignoring the blocked zone
                    blocked = [next_zone]
                    if obstacle_mgr:
                        blocked.extend(obstacle_mgr.get_blocked_zones())
                    self._path = self._find_path(self._current_zone, self._home_zone, blocked)
                    self._path_index = 0
                    
                    app_state.add_timeline_event(TimelineEvent(
                        event_type='alert',
                        description=f"🔄 Obstacle recovery: Backtracking to base hub from {self._zone_name(self._current_zone)} due to persistent blockage at {self._zone_name(next_zone)}.",
                        severity='warning',
                        zone_id=next_zone
                    ))
                    
                    mission_srv = registry.get("MissionService")
                    if mission_srv:
                        mission_srv.complete_active(aborted=True)
                    return

        # Move smoothly toward next_pos
        self._pos, arrived, _ = self._interpolate(self._pos, next_pos, speed * 2.0)

        if arrived:
            self._path_index += 1
            self._current_zone = next_zone
            logger.debug(f"[Rover] Reached waypoint: {next_zone}")

            if next_zone == self._target_zone or self._path_index >= len(self._path) - 1:
                mission_srv = registry.get("MissionService")
                is_docking = self._status == 'returning' or (mission_srv and mission_srv.active_mission and mission_srv.active_mission.mission_type == 'BATTERY_RETURN')
                if self._target_zone == self._home_zone and is_docking:
                    self._status = 'charging' if self._battery_pct < 100.0 else 'idle'
                    self._current_zone = self._home_zone
                    self._target_zone = None
                    logger.info("[Rover] Back at home base — docked/charging")
                else:
                    self._status = 'arrived'
                    self._current_zone = self._target_zone
                self._path = []
                self._path_index = 0

        # Calculate exact ETA
        if self._path and self._path_index < len(self._path):
            remaining_path = self._path[self._path_index:]
            dist = self._calculate_path_distance(remaining_path, self._pos)
            self._eta = self._calculate_eta(dist)
        else:
            self._eta = 0

    def _run_verification(self, zone_id: str, zone_data: dict):
        try:
            time.sleep(1.5)
            # Run verifier Mock
            from rover.verifier import verify_zone
            result = verify_zone(zone_id, zone_data)

            with self._lock:
                self._latest_verification = result
                self._recently_visited[zone_id] = time.time()
                self._status = 'done'
                self._cooldown_until = time.time() + 8.0 # Cooldown seconds
                self._battery_pct = max(0.0, self._battery_pct - 1.5)

            msn_id = None
            from server.services import registry
            mission_srv = registry.get("MissionService")
            if mission_srv and mission_srv.active_mission:
                msn_id = mission_srv.active_mission.mission_id

            rec = InspectionRecord(
                id=f"insp_{uuid.uuid4().hex[:8]}",
                zone_id=zone_id,
                zone_name=self._zone_name(zone_id),
                timestamp=time.time(),
                verdict=result.verdict,
                confidence=result.confidence,
                method=result.method,
                mission_id=msn_id,
                sensors_snapshot=self._sensors.copy() if self._sensors else {}
            )
            app_state.add_inspection(rec)

            if mission_srv and mission_srv.active_mission:
                has_next = mission_srv.active_mission.advance_zone()
                if not has_next:
                    mission_srv.complete_active()

            verdict_emoji = '🔴' if result.verdict == 'CONFIRMED' else '✅'
            app_state.add_timeline_event(TimelineEvent(
                event_type='verification',
                description=(
                    f"{verdict_emoji} Rover verification at {self._zone_name(zone_id)}: "
                    f"{result.verdict} ({result.confidence}% confidence) — {result.method}"
                ),
                severity='critical' if result.verdict == 'CONFIRMED' else 'info',
                zone_id=zone_id,
            ))
        except Exception as e:
            logger.error(f"[Rover] Verification error: {e}")
            with self._lock:
                self._status = 'done'
                self._cooldown_until = time.time() + 8.0

    @staticmethod
    def _zone_name(zone_id: Optional[str]) -> str:
        if not zone_id:
            return 'Unknown'
        from server.services import registry
        planner = registry.get("PathPlannerService")
        if planner:
            return planner.get_zone_name(zone_id)
        try:
            from engine.chronos import ZONE_CONFIG
            return ZONE_CONFIG.get(zone_id, {}).get('name', zone_id)
        except ImportError:
            return zone_id

    def _stamp_zone_with_rover_sensors(self, zone_id: str):
        try:
            sensors = self._sensors
            if not sensors:
                return

            source = sensors.get('source', 'sim')

            reading = ZoneReading(
                zone_id=zone_id,
                name=self._zone_name(zone_id),
                temp=float(sensors.get('temp') or 25.0),
                smoke=int(sensors.get('smoke') or 20),
                humidity=float(sensors.get('humidity') or 60.0),
                blocked=bool(sensors.get('blocked', False)),
            )
            app_state.update_zone(reading)

            label = '📡 LIVE ESP32' if source == 'mqtt' else '🔬 Simulated'
            logger.info(
                f"[Rover] Stamped zone '{zone_id}' with rover readings "
                f"({label}): temp={reading.temp}°C smoke={reading.smoke}ppm"
            )
            app_state.add_timeline_event(TimelineEvent(
                event_type='detection',
                description=(
                    f"🔬 Rover scanned {self._zone_name(zone_id)}: "
                    f"Temp {reading.temp}°C · Smoke {reading.smoke} ppm · "
                    f"RH {reading.humidity}% · "
                    f"Exit {'⛔ BLOCKED' if reading.blocked else '✅ Clear'} "
                    f"[{label}]"
                ),
                severity='info',
                zone_id=zone_id,
            ))
        except Exception as e:
            logger.error(f"[Rover] Failed to stamp zone sensors: {e}")

    def _get_simulated_sensors(self, zones: dict) -> dict:
        home_readings = {
            'temp': 24.2,
            'humidity': 56.4,
            'smoke': 18,
            'blocked': False,
            'mq7': 35,
            'mq135': 78,
            'uptime': int(time.time() - (self._dispatch_time or time.time())) % 10000 + 100,
            'rssi': -48,
            'source': 'sim',
            'last_seen': time.time()
        }

        if self._status == 'idle' or self._current_zone == self._home_zone:
            return home_readings

        target_zone_id = self._target_zone or self._current_zone
        if not target_zone_id or target_zone_id not in zones:
            return home_readings

        target_zone = zones[target_zone_id]
        
        t_temp = getattr(target_zone, 'temp', None)
        t_hum = getattr(target_zone, 'humidity', None)
        t_smoke = getattr(target_zone, 'smoke', None)
        t_blocked = getattr(target_zone, 'blocked', None)

        temp_val = t_temp if t_temp is not None else 25.0
        hum_val = t_hum if t_hum is not None else 60.0
        smoke_val = t_smoke if t_smoke is not None else 20
        blocked_val = bool(t_blocked) if t_blocked is not None else False

        target_readings = {
            'temp': temp_val,
            'humidity': hum_val,
            'smoke': smoke_val,
            'blocked': blocked_val,
            'mq7': int(smoke_val * 1.5 + 20),
            'mq135': int(smoke_val * 1.8 + 50),
            'uptime': int(time.time() - (self._dispatch_time or time.time())) % 10000 + 100,
            'rssi': -65,
            'source': 'sim',
            'last_seen': time.time()
        }

        if self._status == 'en_route' and self._dispatch_time:
            px, py = self._pos
            hx, hy = self._home_pos
            tx, ty = self._target_pos
            
            total_dist = ((tx - hx)**2 + (ty - hy)**2) ** 0.5
            curr_dist = ((tx - px)**2 + (ty - py)**2) ** 0.5
            
            if total_dist > 0:
                ratio = max(0.0, min(1.0, 1.0 - (curr_dist / total_dist)))
            else:
                ratio = 1.0
                
            interpolated = {
                'temp': round(home_readings['temp'] + (target_readings['temp'] - home_readings['temp']) * ratio, 1),
                'humidity': round(home_readings['humidity'] + (target_readings['humidity'] - home_readings['humidity']) * ratio, 1),
                'smoke': int(home_readings['smoke'] + (target_readings['smoke'] - home_readings['smoke']) * ratio),
                'blocked': target_readings['blocked'] if ratio > 0.8 else False,
                'mq7': int(home_readings['mq7'] + (target_readings['mq7'] - home_readings['mq7']) * ratio),
                'mq135': int(home_readings['mq135'] + (target_readings['mq135'] - home_readings['mq135']) * ratio),
                'uptime': target_readings['uptime'],
                'rssi': int(home_readings['rssi'] + (target_readings['rssi'] - home_readings['rssi']) * ratio),
                'source': 'sim',
                'last_seen': time.time()
            }
            return interpolated
            
        return target_readings

    def get_state(self) -> RoverState:
        with self._lock:
            self._resolve_home()
            eta = getattr(self, '_eta', 0)
            remaining_path = self._path[self._path_index:] if getattr(self, '_path', None) and self._path_index < len(self._path) else []
            curr_msn = None
            from server.services import registry
            mission_srv = registry.get("MissionService")
            if mission_srv and mission_srv.active_mission:
                curr_msn = mission_srv.active_mission.to_dict()
            curr_speed = 45.0 if self._status == 'en_route' else 0.0
            return RoverState(
                status=self._status,
                target_zone=self._target_zone,
                current_zone=self._current_zone,
                position=(round(self._pos[0], 1), round(self._pos[1], 1)),
                eta_seconds=eta,
                dispatch_time=self._dispatch_time,
                arrival_time=self._arrival_time,
                path=remaining_path,
                sensors=getattr(self, '_sensors', {}),
                current_mission=curr_msn,
                battery_pct=getattr(self, '_battery_pct', 100.0),
                is_charging=getattr(self, '_is_charging', False),
                speed=curr_speed,
            )

    def get_latest_verification(self):
        with self._lock:
            result = self._latest_verification
            self._latest_verification = None
            return result

    def force_dispatch(self, zone_id: str):
        with self._lock:
            self._resolve_home()
            self._recently_visited.pop(zone_id, None)
            self._status = 'idle'
            now = time.time()
            start_z = self._current_zone or self._home_zone
            path = self._find_path(start_z, zone_id)
            if not path:
                path = [start_z, zone_id]
            from server.services import registry
            planner = registry.get("PathPlannerService")
            target_pos = planner.get_zone_position(zone_id) if planner else self._home_pos
            self._status = 'en_route'
            self._target_zone = zone_id
            self._target_pos = target_pos
            self._current_zone = start_z
            self._path = path
            self._path_index = 0
            self._dispatch_time = now
            self._latest_verification = None
        app_state.add_timeline_event(TimelineEvent(
            event_type='dispatch',
            description=f"🚀 Manual rover dispatch to {self._zone_name(zone_id)} (Route: {' → '.join([self._zone_name(z) for z in path])})",
            severity='warning',
            zone_id=zone_id,
        ))

    def recall(self):
        with self._lock:
            self._resolve_home()
            start_z = self._current_zone or self._home_zone
            path = self._find_path(start_z, self._home_zone)
            if not path:
                path = [start_z, self._home_zone]
            self._status = 'en_route'
            self._target_zone = self._home_zone
            self._target_pos = self._home_pos
            self._current_zone = start_z
            self._path = path
            self._path_index = 0
            self._dispatch_time = time.time()
            self._arrival_time = None
            self._latest_verification = None
        app_state.add_timeline_event(TimelineEvent(
            event_type='dispatch',
            description=f"🤖 Rover recalled to home base (Route: {' → '.join([self._zone_name(z) for z in path])})",
            severity='info',
            zone_id=self._home_zone,
        ))

rover_simulator = RoverSimulator()
