from server.services.base_service import BaseService

class ObstacleManagerService(BaseService):
    """
    Obstacle Manager Service responsible for processing HC-SR04 ultrasonic
    distance telemetry and managing real-time obstacle blockage state maps.
    """
    def __init__(self, config: dict = None):
        super().__init__("ObstacleManagerService", config)
        self._blocked_zones = set()
        self.obstacle_threshold_cm = 30.0

    def _on_start(self) -> bool:
        from server.services import registry
        cfg_srv = registry.get("ConfigurationService")
        if cfg_srv:
            nav_cfg = cfg_srv.config.get("navigation_config", {})
            self.obstacle_threshold_cm = nav_cfg.get("obstacle_threshold_cm", 30.0)
        self.logger.info("ObstacleManagerService started successfully.")
        return True

    def set_obstacle(self, zone_id: str, is_blocked: bool):
        if is_blocked:
            self._blocked_zones.add(zone_id)
        else:
            self._blocked_zones.discard(zone_id)

    def is_blocked(self, zone_id: str) -> bool:
        # Check local override from app_state or local sensors
        from server.state import app_state
        zone_reading = app_state.zones.get(zone_id)
        if zone_reading and zone_reading.blocked:
            return True
        return zone_id in self._blocked_zones

    def process_ultrasonic_reading(self, zone_id: str, distance_cm: float):
        """Dynamic evaluator for distance reports."""
        if 0.0 < distance_cm < self.obstacle_threshold_cm:
            if zone_id not in self._blocked_zones:
                self.logger.warning(
                    f"Obstacle detected in '{zone_id}'! Distance: {distance_cm:.1f}cm "
                    f"(threshold: {self.obstacle_threshold_cm:.1f}cm)"
                )
            self.set_obstacle(zone_id, True)
        else:
            self.set_obstacle(zone_id, False)

    def get_blocked_zones(self) -> list:
        return list(self._blocked_zones)
