"""
server/services/ai_service/modules/mission_intelligence.py — Autonomous Mission Intelligence Engine

Evaluates mission priority, battery feasibility, estimated completion times,
alternative waypoint routing around hazardous zones, mission risk, and confidence metrics.
"""

import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

@dataclass
class MissionFeasibility:
    is_feasible: bool
    battery_required_pct: float
    battery_current_pct: float
    estimated_distance_m: float
    estimated_duration_sec: int
    risk_level: str               # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    confidence_score: float        # 0.0 - 1.0
    recommended_path: List[str]
    alternative_path: List[str]
    reasons: List[str]

    def to_dict(self) -> dict:
        return {
            'is_feasible': self.is_feasible,
            'battery_required_pct': round(self.battery_required_pct, 1),
            'battery_current_pct': round(self.battery_current_pct, 1),
            'estimated_distance_m': round(self.estimated_distance_m, 1),
            'estimated_duration_sec': self.estimated_duration_sec,
            'risk_level': self.risk_level,
            'confidence_score': round(self.confidence_score, 2),
            'confidence_pct': f"{round(self.confidence_score * 100)}%",
            'recommended_path': self.recommended_path,
            'alternative_path': self.alternative_path,
            'reasons': self.reasons,
        }


class MissionIntelligenceEngine:
    """
    Evaluates mission requests against physical rover constraints and building hazards.
    """

    def __init__(self, battery_consumption_per_meter: float = 0.4, safety_buffer_pct: float = 15.0):
        self.consumption_per_m = battery_consumption_per_meter
        self.safety_buffer_pct = safety_buffer_pct

    def evaluate_mission(
        self,
        mission_type: str,
        start_zone: str,
        target_zone: str,
        current_battery: float,
        risk_scores: Dict[str, dict],
        blocked_zones: List[str],
        zone_graph: Dict[str, List[str]],
        zone_positions: Dict[str, Tuple[float, float]],
    ) -> MissionFeasibility:
        """
        Evaluates battery feasibility, risk, and alternative routes for a target mission.
        """
        reasons = []

        # Find primary shortest path
        primary_path = self._dijkstra_path(start_zone, target_zone, blocked_zones, risk_scores, zone_graph, risk_weight=2.0)
        
        # Find alternative safest path (heavily avoiding risk)
        alt_path = self._dijkstra_path(start_zone, target_zone, blocked_zones, risk_scores, zone_graph, risk_weight=10.0)
        if alt_path == primary_path:
            alt_path = []

        # Estimate path distance (pixels -> meters conversion, ~20 pixels per meter)
        dist_px = self._calc_path_distance(primary_path, zone_positions)
        dist_m = dist_px / 20.0

        # Calculate return distance to corridor/base
        base_zone = "corridor"
        return_path = self._dijkstra_path(target_zone, base_zone, blocked_zones, risk_scores, zone_graph, risk_weight=2.0)
        return_dist_m = self._calc_path_distance(return_path, zone_positions) / 20.0

        total_dist_m = dist_m + return_dist_m
        est_duration = int(total_dist_m / 0.8) + 15  # 0.8 m/s rover speed + 15s inspection stay

        # Battery calculations
        req_battery = (total_dist_m * self.consumption_per_m) + self.safety_buffer_pct
        is_feasible = current_battery >= req_battery

        if not is_feasible:
            reasons.append(f"Insufficient battery ({current_battery:.1f}% available vs {req_battery:.1f}% required for roundtrip).")

        # Evaluate Mission Risk
        target_risk = risk_scores.get(target_zone, {}).get('score', 0)
        if target_risk >= 80:
            risk_level = 'CRITICAL'
            conf = 0.95
            reasons.append(f"Target zone {target_zone} is in CRITICAL hazard state ({target_risk}/100).")
        elif target_risk >= 60:
            risk_level = 'HIGH'
            conf = 0.88
            reasons.append(f"Target zone {target_zone} is in HIGH risk state ({target_risk}/100).")
        elif target_risk >= 30:
            risk_level = 'MEDIUM'
            conf = 0.80
        else:
            risk_level = 'LOW'
            conf = 0.99

        if is_feasible:
            reasons.append(f"Mission evaluated as feasible. Roundtrip battery requirement: {req_battery:.1f}%.")

        return MissionFeasibility(
            is_feasible=is_feasible,
            battery_required_pct=req_battery,
            battery_current_pct=current_battery,
            estimated_distance_m=total_dist_m,
            estimated_duration_sec=est_duration,
            risk_level=risk_level,
            confidence_score=conf,
            recommended_path=primary_path,
            alternative_path=alt_path,
            reasons=reasons,
        )

    def _calc_path_distance(self, path: List[str], zone_positions: Dict[str, Tuple[float, float]]) -> float:
        if len(path) < 2:
            return 0.0
        total = 0.0
        for i in range(len(path) - 1):
            p1 = zone_positions.get(path[i], (0, 0))
            p2 = zone_positions.get(path[i+1], (0, 0))
            total += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        return total

    def _dijkstra_path(self, start: str, goal: str, blocked: List[str],
                       risk_scores: Dict[str, dict], graph: Dict[str, List[str]], risk_weight: float) -> List[str]:
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
                edge_cost = 1.0 + (r_score / 100.0) * risk_weight
                heapq.heappush(heap, (cost + edge_cost, nxt, path + [nxt]))

        return []
