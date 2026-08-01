"""
server/services/ai_service/modules/navigation_intelligence.py — Autonomous Navigation Intelligence & Stuck Recovery Engine

Manages hazard-weighted Dijkstra navigation, dynamically reroutes around newly detected obstacles,
and executes autonomous stuck rover recovery routines when position remains static despite active motor commands.
"""

import time
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

@dataclass
class NavigationPlan:
    start_zone: str
    target_zone: str
    waypoint_path: List[str]
    total_distance_px: float
    estimated_eta_sec: int
    is_rerouted: bool
    stuck_detected: bool
    recovery_action: Optional[str]
    reasons: List[str]

    def to_dict(self) -> dict:
        return {
            'start_zone': self.start_zone,
            'target_zone': self.target_zone,
            'waypoint_path': self.waypoint_path,
            'total_distance_px': round(self.total_distance_px, 1),
            'estimated_eta_sec': self.estimated_eta_sec,
            'is_rerouted': self.is_rerouted,
            'stuck_detected': self.stuck_detected,
            'recovery_action': self.recovery_action,
            'reasons': self.reasons,
        }


class NavigationIntelligenceEngine:
    """
    Intelligent pathfinding and stuck rover recovery module.
    """

    def __init__(self, stuck_time_threshold_sec: float = 8.0, position_stuck_radius_px: float = 5.0):
        self.stuck_threshold = stuck_time_threshold_sec
        self.stuck_radius = position_stuck_radius_px
        self._last_pos: Optional[Tuple[float, float]] = None
        self._last_move_time: float = time.time()

    def evaluate_navigation(
        self,
        rover_state: dict,
        risk_scores: Dict[str, dict],
        blocked_zones: List[str],
        zone_graph: Dict[str, List[str]],
        zone_positions: Dict[str, Tuple[float, float]],
    ) -> NavigationPlan:
        """
        Computes dynamic navigation pathing and checks for stuck rover conditions.
        """
        curr_zone = rover_state.get('current_zone', 'corridor')
        target_zone = rover_state.get('target_zone', 'corridor')
        status = rover_state.get('status', 'idle')
        curr_pos = tuple(rover_state.get('position', (385.0, 225.0)))

        now = time.time()
        stuck_detected = False
        recovery_action = None
        reasons = []

        # Stuck detection logic
        if status in ('en_route', 'moving') and target_zone and target_zone != curr_zone:
            if self._last_pos is not None:
                dist_moved = math.hypot(curr_pos[0] - self._last_pos[0], curr_pos[1] - self._last_pos[1])
                if dist_moved < self.stuck_radius:
                    if now - self._last_move_time >= self.stuck_threshold:
                        stuck_detected = True
                        recovery_action = "NUDGE_BACKWARD_AND_REROUTE"
                        reasons.append(f"Rover position static at {curr_pos} for {now - self._last_move_time:.1f}s despite active command.")
                else:
                    self._last_move_time = now
            else:
                self._last_move_time = now
            self._last_pos = curr_pos
        else:
            self._last_pos = curr_pos
            self._last_move_time = now

        # Compute dynamic hazard-weighted path
        # Temporarily mark current location as blocked if stuck to force alternate route
        effective_blocked = list(blocked_zones)
        if stuck_detected and curr_zone not in effective_blocked:
            effective_blocked.append(curr_zone)
            reasons.append(f"Temporarily avoiding {curr_zone} to un-stuck rover pathing.")

        from engine.recommender import find_safest_exit
        # Use risk-weighted pathfinder
        path = self._dijkstra(curr_zone, target_zone, effective_blocked, risk_scores, zone_graph)

        # Estimate distance and ETA
        dist_px = 0.0
        if len(path) >= 2:
            for i in range(len(path) - 1):
                p1 = zone_positions.get(path[i], (0, 0))
                p2 = zone_positions.get(path[i+1], (0, 0))
                dist_px += math.hypot(p2[0] - p1[0], p2[1] - p1[1])

        speed = float(rover_state.get('speed', 45.0) or 45.0)
        eta_sec = int(dist_px / speed) if speed > 0 else 0

        is_rerouted = len(effective_blocked) > len(blocked_zones) or any(z in blocked_zones for z in path)

        if not reasons:
            reasons.append(f"Optimal hazard-weighted route calculated from {curr_zone} to {target_zone}.")

        return NavigationPlan(
            start_zone=curr_zone,
            target_zone=target_zone,
            waypoint_path=path,
            total_distance_px=dist_px,
            estimated_eta_sec=eta_sec,
            is_rerouted=is_rerouted,
            stuck_detected=stuck_detected,
            recovery_action=recovery_action,
            reasons=reasons,
        )

    def _dijkstra(self, start: str, goal: str, blocked: List[str],
                  risk_scores: Dict[str, dict], graph: Dict[str, List[str]]) -> List[str]:
        import heapq
        if start == goal:
            return [start]

        b_set = set(blocked)
        heap = [(0.0, start, [start])]
        visited = set()

        while heap:
            cost, curr, path = heapq.heappop(heap)
            if curr in visited:
                continue
            visited.add(curr)

            if curr == goal:
                return path

            for nxt in graph.get(curr, []):
                if nxt in visited or (nxt in b_set and nxt != goal):
                    continue
                r_score = risk_scores.get(nxt, {}).get('score', 0)
                edge_cost = 1.0 + (r_score / 100.0) * 5.0
                heapq.heappush(heap, (cost + edge_cost, nxt, path + [nxt]))

        return []
