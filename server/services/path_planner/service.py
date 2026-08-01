import math
import heapq
import logging
from typing import List, Dict, Tuple, Optional
from server.services.base_service import BaseService

class PathPlannerService(BaseService):
    """
    Path Planner Service responsible for Dijkstra shortest-path navigation solver,
    multi-floor transitions mapping, path distances, and ETA calculation.
    Fully driven by dynamic config layouts.
    """
    def __init__(self, config: dict = None):
        super().__init__("PathPlannerService", config)
        self._zone_graph: Dict[str, List[str]] = {}
        self._zone_positions: Dict[str, Tuple[float, float]] = {}
        self._zone_floors: Dict[str, int] = {}
        self._zone_names: Dict[str, str] = {}

    def _on_start(self) -> bool:
        from server.services import registry
        cfg_srv = registry.get("ConfigurationService")
        if cfg_srv:
            zones_raw = cfg_srv.get_zones()
            zone_graph = {zid: z.get("adjacencies", []) for zid, z in zones_raw.items()}
            zone_positions = {zid: tuple(z.get("position", [0.0, 0.0])) for zid, z in zones_raw.items()}
            zone_floors = {zid: int(z.get("floor", 1)) for zid, z in zones_raw.items()}
            zone_names = {zid: str(z.get("name", zid)) for zid, z in zones_raw.items()}
            
            self.configure_map(zone_graph, zone_positions, zone_floors, zone_names)
        self.logger.info("PathPlannerService started successfully.")
        return True

    def configure_map(self, zone_graph: dict, zone_positions: dict, zone_floors: dict, zone_names: dict):
        self._zone_graph = zone_graph
        self._zone_positions = zone_positions
        self._zone_floors = zone_floors
        self._zone_names = zone_names

    def find_path(self, start_zone: str, target_zone: str,
                  blocked_zones: Optional[List[str]] = None) -> List[str]:
        """Dijkstra solver over dynamic adjacency graph, supporting multi-floor linkages."""
        if not start_zone or not target_zone:
            return []
        if start_zone == target_zone:
            return [start_zone]
        if start_zone not in self._zone_graph or target_zone not in self._zone_graph:
            self.logger.warning(f"Unknown start '{start_zone}' or target '{target_zone}' in path graph")
            return []

        blocked = set(blocked_zones or [])
        pq: List[Tuple[float, str, List[str]]] = [(0.0, start_zone, [start_zone])]
        visited = set()

        while pq:
            dist, current, path = heapq.heappop(pq)
            if current == target_zone:
                return path
            if current in visited:
                continue
            visited.add(current)

            for neighbor in self._zone_graph.get(current, []):
                # Skip blocked nodes unless they are the direct target zone
                if neighbor in blocked and neighbor != target_zone:
                    continue

                pos_a = self._zone_positions.get(current, (0.0, 0.0))
                pos_b = self._zone_positions.get(neighbor, (0.0, 0.0))
                
                # Dynamic weight calculation: distance-based if same floor
                floor_a = self._zone_floors.get(current, 1)
                floor_b = self._zone_floors.get(neighbor, 1)
                
                if floor_a == floor_b:
                    edge_dist = math.dist(pos_a, pos_b)
                else:
                    # Multi-floor transitions (stairs/elevator) have a fixed penalty weight
                    edge_dist = 100.0 

                heapq.heappush(pq, (dist + edge_dist, neighbor, path + [neighbor]))

        self.logger.warning(f"Path solver: no path from {start_zone} to {target_zone} (blocked: {blocked})")
        return []

    def calculate_path_distance(self, path: List[str], current_pos: Optional[Tuple[float, float]] = None) -> float:
        if not path:
            return 0.0
        total = 0.0
        if current_pos and path[0] in self._zone_positions:
            total += math.dist(current_pos, self._zone_positions[path[0]])

        for i in range(len(path) - 1):
            pos_a = self._zone_positions.get(path[i], (0.0, 0.0))
            pos_b = self._zone_positions.get(path[i+1], (0.0, 0.0))
            
            floor_a = self._zone_floors.get(path[i], 1)
            floor_b = self._zone_floors.get(path[i+1], 1)
            if floor_a == floor_b:
                total += math.dist(pos_a, pos_b)
            else:
                total += 100.0
        return total

    def calculate_eta(self, distance: float, travel_speed: float) -> int:
        if travel_speed <= 0 or distance <= 0:
            return 0
        return int(math.ceil(distance / travel_speed))

    def get_zone_name(self, zone_id: str) -> str:
        return self._zone_names.get(zone_id, zone_id)

    def get_zone_position(self, zone_id: str) -> Tuple[float, float]:
        return self._zone_positions.get(zone_id, (0.0, 0.0))
