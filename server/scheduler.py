import time
import threading
import logging
from server.state import app_state, TimelineEvent
from server.services import registry
from rover.rover_sim import rover_simulator

logger = logging.getLogger(__name__)

class Scheduler(threading.Thread):
    """
    Background scheduler loop.
    Queries the registry to fetch the 12 modular services and ticks them
    according to the dynamic sensor_poll_rate setting.
    """
    def __init__(self):
        super().__init__(name='Scheduler', daemon=True)
        self._stop_event = threading.Event()
        self._prev_status = 'green'
        self._prev_high_risk = set()
        self._ai_requested_at = 0
        self.AI_RATE_LIMIT = 15.0
        self._calibration_logged = False
        self._last_fire_alert_at = 0.0
        self._last_person_alert_at = 0.0

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info("[Scheduler] Starting pipeline loop")
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:
                logger.error(f"[Scheduler] Tick error: {e}", exc_info=True)
            
            poll_rate = app_state.settings.get('sensor_poll_rate', 2.0)
            self._stop_event.wait(poll_rate)

    def _tick(self):
        # 1. Fetch services from registry
        sensor_srv = registry.get("SensorService")
        health_srv = registry.get("HealthService")
        alert_srv = registry.get("AlertService")
        db_srv = registry.get("DatabaseService")
        mission_srv = registry.get("MissionService")
        cfg_srv = registry.get("ConfigurationService")

        if not all([sensor_srv, health_srv, alert_srv, db_srv, mission_srv, cfg_srv]):
            logger.warning("[Scheduler] One or more modular services are not available in registry.")
            return

        zones = app_state.zones
        if not zones:
            return # Awaiting initial data feed

        # 2. Feed calibrations & check baseline complete
        for reading in zones.values():
            sensor_srv.process_reading(reading)

        # Update calibration UI snapshots
        app_state.calibration = sensor_srv.get_all_calibration_status()
        
        # Check if all zones are calibrated
        all_calib = all(c['status'] == 'calibrated' for c in app_state.calibration.values())
        if not self._calibration_logged and all_calib:
            self._calibration_logged = True
            app_state.add_timeline_event(TimelineEvent(
                event_type='info',
                description='📐 Sensor calibration complete — dynamic thresholds active',
                severity='info',
            ))

        # 3. Check health and mark stale zones offline (Honesty Rule)
        # Verify offline zones first
        active_zone_ids = list(zones.keys())
        stale_zone_ids = health_srv.get_stale_zones(active_zone_ids)
        for zone_id in stale_zone_ids:
            if zones[zone_id].online:
                zones[zone_id].online = False
                zones[zone_id].temp = None
                zones[zone_id].smoke = None
                zones[zone_id].humidity = None
                logger.warning(f"[Scheduler] Staleness timeout! Zone {zone_id} is offline.")

        health_statuses = {}
        for zone_id, reading in zones.items():
            health_statuses[zone_id] = health_srv.check_and_feed(reading)

        app_state.sensor_health = health_srv.get_all_status()

        # Log new faults
        for zone_id, health in health_statuses.items():
            if health.status == 'FAULTY':
                name = cfg_srv.get_zones().get(zone_id, {}).get('name', zone_id)
                for issue in health.issues:
                    if 'STUCK' in issue or 'OUT_OF_RANGE' in issue:
                        app_state.add_timeline_event(TimelineEvent(
                            event_type='alert',
                            description=f"🔧 Sensor fault in {name}: {issue}",
                            severity='warning',
                            zone_id=zone_id,
                        ))

        # 4. CHRONOS risk calculations
        risk_scores = {}
        overall_max_risk = 0
        system_status = 'green'

        for zone_id, reading in zones.items():
            cal_thresh = sensor_srv.get_thresholds(zone_id)
            h_status = health_statuses.get(zone_id)
            
            risk_res = alert_srv.compute_chronos_risk(
                reading=reading,
                settings=app_state.settings,
                health_status=h_status,
                calibrated_thresholds=cal_thresh
            )
            risk_scores[zone_id] = risk_res
            overall_max_risk = max(overall_max_risk, risk_res.score)
            
            # Elevate system status
            if risk_res.status == 'red':
                system_status = 'red'
            elif risk_res.status == 'orange' and system_status != 'red':
                system_status = 'orange'
            elif risk_res.status == 'yellow' and system_status not in ('red', 'orange'):
                system_status = 'yellow'

        app_state.update_risks(risk_scores, system_status, overall_max_risk)

        # 5. Trend Predictions
        predictions = {}
        for zone_id, risk_res in risk_scores.items():
            pred = sensor_srv.update_risk_trend(zone_id, risk_res.score)
            if pred:
                predictions[zone_id] = pred
        app_state.update_predictions(predictions)

        # 6. Event detection alerts
        self._detect_events(risk_scores, system_status, cfg_srv.get_zones())

        # 7. Evacuation Dijkstra recommendation routing
        recs = alert_srv.get_all_evac_recommendations(risk_scores, {zid: z.to_dict() for zid, z in zones.items()})
        app_state.recommendations = recs

        # 8. Rover Simulation & Queue
        dispatch_threshold = app_state.settings.get('rover_auto_dispatch_level', 70)
        high_risk_zones = [zid for zid, r in risk_scores.items() if r.score >= dispatch_threshold]

        mission_srv.set_building_zones(list(cfg_srv.get_zones().keys()))
        target_dispatch = mission_srv.tick_queue(
            rover_status=rover_simulator.get_state().status,
            battery_pct=rover_simulator.get_state().battery_pct,
            high_risk_zones=high_risk_zones
        )

        if target_dispatch:
            rover_simulator.force_dispatch(target_dispatch)

        # Tick simulator
        rover_simulator.tick(high_risk_zones, risk_scores, zones)
        app_state.update_rover(rover_simulator.get_state())

        # Log to SQLite DB & Convex Cloud DB
        convex_srv = registry.get("ConvexService")
        for zone_id, reading in zones.items():
            db_srv.log_sensor_reading(zone_id, reading.temp, reading.smoke, reading.humidity, reading.blocked)
            if convex_srv:
                convex_srv.sync_sensor_reading(zone_id, reading.temp, reading.smoke, reading.humidity, reading.blocked)
                
            r_res = risk_scores.get(zone_id)
            if r_res:
                db_srv.log_alert(zone_id, r_res.score, r_res.status, "; ".join(r_res.reasons))
                if convex_srv:
                    convex_srv.sync_alert(zone_id, r_res.score, r_res.status, "; ".join(r_res.reasons))
        
        r_state = rover_simulator.get_state()
        rx = r_state.position[0] if r_state.position else 0.0
        ry = r_state.position[1] if r_state.position else 0.0
        r_rssi = r_state.sensors.get('rssi') if r_state.sensors else None
        r_rssi = int(r_rssi) if r_rssi is not None else 0
        r_uptime = r_state.sensors.get('uptime') if r_state.sensors else None
        r_uptime = int(r_uptime) if r_uptime is not None else 0

        db_srv.log_rover_status(r_state.status, r_state.battery_pct, rx, ry, r_rssi, r_uptime)
        if convex_srv:
            convex_srv.sync_rover_status(r_state.status, r_state.battery_pct, rx, ry, r_rssi, r_uptime)
            
        db_srv.log_battery(4.0, int(r_state.battery_pct))
        if convex_srv:
            convex_srv.sync_battery_history(4.0, float(r_state.battery_pct))

        # 9. AI Agent Analysis calls
        now = time.time()
        if (now - self._ai_requested_at) >= self.AI_RATE_LIMIT:
            if overall_max_risk > 0 or system_status != 'green' or len(app_state.pending_actions) > 0:
                self._ai_requested_at = now
                snapshot = app_state.get_snapshot()
                ai_srv = registry.get("AiService")
                if ai_srv:
                    ai_srv.request_update(snapshot)

        # 10. Autonomous Background CV Safety Audits (Phase 2G)
        vision_srv = registry.get("VisionService")
        cam_srv = registry.get("CameraService")
        if vision_srv and cam_srv:
            frame = cam_srv.get_latest_frame()
            if frame is not None:
                cv_res = vision_srv.process_frame(frame)
                current_zone = rover_simulator.get_state().current_zone or 'corridor'
                
                # Check for verified fire signature
                if cv_res.get("fire_verified") or cv_res.get("fire_detected"):
                    if (now - self._last_fire_alert_at) >= 30.0:
                        self._last_fire_alert_at = now
                        app_state.add_timeline_event(TimelineEvent(
                            event_type='alert',
                            description="🔥 Roboflow AI Engine: Fire signature detected & verification active!",
                            severity='critical',
                            zone_id=current_zone
                        ))
                
                # Check for person detection
                if cv_res.get("person_detected"):
                    if (now - self._last_person_alert_at) >= 30.0:
                        self._last_person_alert_at = now
                        app_state.add_timeline_event(TimelineEvent(
                            event_type='alert',
                            description=f"👤 Roboflow AI Engine: Human detected in camera view! Count: {cv_res.get('person_count')}",
                            severity='warning',
                            zone_id=current_zone
                        ))

    def _detect_events(self, risk_scores, system_status, zone_config):
        dispatch_threshold = app_state.settings.get('rover_auto_dispatch_level', 70)
        now_high = set(zid for zid, r in risk_scores.items() if r.score >= dispatch_threshold)

        newly_alarmed = now_high - self._prev_high_risk
        for zone_id in newly_alarmed:
            r = risk_scores[zone_id]
            name = zone_config.get(zone_id, {}).get('name', zone_id)
            app_state.add_timeline_event(TimelineEvent(
                event_type='detection',
                description=f"⚠️ {name} entered high-risk state — score {r.score}/100",
                severity='warning' if r.score < 80 else 'critical',
                zone_id=zone_id,
            ))

        cleared = self._prev_high_risk - now_high
        for zone_id in cleared:
            name = zone_config.get(zone_id, {}).get('name', zone_id)
            app_state.add_timeline_event(TimelineEvent(
                event_type='info',
                description=f"✅ {name} returned to safe levels",
                severity='info',
                zone_id=zone_id,
            ))

        if system_status == 'red' and self._prev_status != 'red':
            app_state.add_timeline_event(TimelineEvent(
                event_type='alert',
                description="🚨 SYSTEM STATUS: RED — Evacuation required",
                severity='critical',
            ))
        elif system_status == 'green' and self._prev_status != 'green':
            app_state.add_timeline_event(TimelineEvent(
                event_type='info',
                description="🟢 SYSTEM STATUS: GREEN — Nominal clear",
                severity='info',
            ))

        self._prev_high_risk = now_high
        self._prev_status = system_status
