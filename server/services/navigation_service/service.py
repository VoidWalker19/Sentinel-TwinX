import math
import logging
from typing import List, Tuple, Optional
from server.services.base_service import BaseService

class NavigationService(BaseService):
    """
    Navigation Service responsible for coordinate interpolation (along straight segments on the SVG blueprint),
    delegating pathfinding to PathPlannerService, and fetching configuration-driven speeds.
    """
    def __init__(self, config: dict = None):
        super().__init__("NavigationService", config)
        self.travel_speed = 45.0
        self.base_zone = "corridor"

    def _on_start(self) -> bool:
        from server.services import registry
        cfg_srv = registry.get("ConfigurationService")
        if cfg_srv:
            nav_cfg = cfg_srv.config.get("navigation_config", {})
            self.travel_speed = nav_cfg.get("travel_speed", 45.0)
            self.base_zone = nav_cfg.get("base_zone", "corridor")
        self.logger.info("Navigation service started successfully.")
        return True

    def _get_planner(self):
        from server.services import registry
        planner = registry.get("PathPlannerService")
        if not planner:
            from server.services.path_planner.service import PathPlannerService
            planner = PathPlannerService()
            registry.register(planner)
        return planner

    def configure_map(self, zone_graph: dict, zone_positions: dict, zone_floors: dict = None, zone_names: dict = None):
        """Backwards compatible mapper for legacy code / unit testing."""
        planner = self._get_planner()
        floors = zone_floors or {zid: 1 for zid in zone_graph}
        names = zone_names or {zid: zid for zid in zone_graph}
        planner.configure_map(zone_graph, zone_positions, floors, names)

    def find_rover_path(self, start_zone: str, target_zone: str,
                        blocked_zones: Optional[List[str]] = None) -> List[str]:
        """Queries PathPlannerService to perform shortest path calculation."""
        from server.services import registry
        diag = registry.get("DiagnosticsService")
        if diag and diag.get_simulation("navigation_blockage"):
            if blocked_zones is None:
                blocked_zones = []
            blocked_zones = list(blocked_zones)
            if target_zone:
                blocked_zones.append(target_zone)
            blocked_zones.extend(["lobby", "corridor", "server_room"])
        planner = self._get_planner()
        return planner.find_path(start_zone, target_zone, blocked_zones)


    def calculate_path_distance(self, path: List[str], current_pos: Optional[Tuple[float, float]] = None) -> float:
        """Queries PathPlannerService to compute path metrics."""
        planner = self._get_planner()
        return planner.calculate_path_distance(path, current_pos)

    def calculate_eta(self, distance: float) -> int:
        """Queries PathPlannerService to compute flight time estimates."""
        planner = self._get_planner()
        return planner.calculate_eta(distance, self.travel_speed)

    def interpolate_position(self, pos_a: Tuple[float, float], pos_b: Tuple[float, float],
                             step_pixels: float) -> Tuple[Tuple[float, float], bool, float]:
        """Moves pos_a toward pos_b by step_pixels."""
        x1, y1 = pos_a
        x2, y2 = pos_b
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)

        if dist <= step_pixels or dist < 1.0:
            return pos_b, True, 0.0

        ratio = step_pixels / dist
        new_pos = (x1 + dx * ratio, y1 + dy * ratio)
        return new_pos, False, dist - step_pixels
