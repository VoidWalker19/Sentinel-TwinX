"""
engine/recommender.py — Evacuation Route Recommender (Weighted Dijkstra)

This module knows the building layout and finds the safest exit for
anyone in a given zone. It uses risk-weighted Dijkstra's algorithm instead
of simple BFS — paths through high-risk zones cost more, so the system
naturally routes people away from danger even when multiple paths exist.

The algorithm respects blocked pathways detected by the HC-SR04 sensors
and zones marked as high-risk, penalizing traversal through dangerous areas
rather than binary avoid/allow.
"""

import heapq
from typing import Dict, List, Optional, Tuple
from server.state import RiskResult
from engine.config_loader import ZONE_GRAPH, EXIT_ZONES, ZONE_CONFIG

# Dynamic friendly names for exit zones loaded from config
EXIT_NAMES = {
    exit_id: ZONE_CONFIG.get(exit_id, {}).get('name', exit_id.replace('_', ' ').title())
    for exit_id in EXIT_ZONES
}



# ─────────────────────────────────────────────────────────────────────────────
# Risk-weighted Dijkstra pathfinding
# ─────────────────────────────────────────────────────────────────────────────

# Edge cost formula:
#   base_cost = 1.0 (one zone hop)
#   risk_penalty = (zone_risk_score / 100) * RISK_PENALTY_WEIGHT
#   total_edge_cost = base_cost + risk_penalty
#
# This means a zone at score 80 adds 4.0 extra cost,
# making the algorithm naturally prefer safer paths.

RISK_PENALTY_WEIGHT = 5.0     # How much risk score affects path cost
BLOCKED_COST = 999.0          # Effectively impassable


def find_safest_exit(
    origin_zone: str,
    blocked_zones: List[str],
    high_risk_zones: List[str],
    risk_scores: Dict[str, any] = None,
) -> Tuple[Optional[str], List[str], float]:
    """
    Dijkstra from origin_zone to find the safest (lowest-cost) exit.

    Unlike BFS which treats all paths equally, this weights edges by
    zone risk score — a path through a zone at score 80 costs much more
    than one through a zone at score 10, even though both are 1 hop.

    Args:
        origin_zone:     The zone the person is currently in.
        blocked_zones:   Zones with HC-SR04 blockage detected.
        high_risk_zones: Zones with score >= ORANGE (60).
        risk_scores:     Dict of zone_id → RiskResult or dict (for weighting).

    Returns:
        (exit_zone_id, path_list, total_cost)
        Returns (None, [], float('inf')) if no path exists.
    """
    # Exits that are not physically blocked
    active_exits = EXIT_ZONES - set(blocked_zones)
    if not active_exits:
        # If all exits are blocked, try to reach any exit as a last resort
        active_exits = EXIT_ZONES

    blocked_set = set(blocked_zones)

    # Build edge cost function using risk scores
    def edge_cost(target_zone: str) -> float:
        """Cost to move INTO target_zone."""
        if target_zone in blocked_set and target_zone not in active_exits:
            return BLOCKED_COST

        base = 1.0
        if risk_scores:
            score = _get_score(risk_scores.get(target_zone))
            risk_penalty = (score / 100.0) * RISK_PENALTY_WEIGHT
            return base + risk_penalty
        return base

    # Run Dijkstra with risk weighting
    result = _dijkstra(origin_zone, active_exits, edge_cost)
    if result[0] is not None:
        return result

    # Fallback: try with all exits if nothing reachable
    result = _dijkstra(origin_zone, EXIT_ZONES, edge_cost)
    if result[0] is not None:
        return result

    # Last resort: ignore costs entirely
    def unit_cost(z): return 1.0
    return _dijkstra(origin_zone, EXIT_ZONES, unit_cost)


def _dijkstra(
    origin: str,
    active_exits: set,
    cost_fn,
) -> Tuple[Optional[str], List[str], float]:
    """
    Dijkstra's shortest-path algorithm with custom edge cost function.

    Returns (exit_zone_id, path_list, total_cost) or (None, [], inf).
    """
    if origin in active_exits:
        return origin, [origin], 0.0

    # Priority queue: (total_cost, zone_id, path)
    heap = [(0.0, origin, [origin])]
    visited = set()

    while heap:
        cost, current, path = heapq.heappop(heap)

        if current in visited:
            continue
        visited.add(current)

        for neighbour in ZONE_GRAPH.get(current, []):
            if neighbour in visited:
                continue

            step_cost = cost_fn(neighbour)
            new_cost = cost + step_cost
            new_path = path + [neighbour]

            if neighbour in active_exits:
                return neighbour, new_path, round(new_cost, 2)

            heapq.heappush(heap, (new_cost, neighbour, new_path))

    return None, [], float('inf')


# ─────────────────────────────────────────────────────────────────────────────
# Evacuation message generator
# ─────────────────────────────────────────────────────────────────────────────

def _get_score(risk_entry) -> int:
    """Get score from either a RiskResult object or a dict."""
    if risk_entry is None:
        return 0
    if isinstance(risk_entry, dict):
        return risk_entry.get('score', 0)
    return getattr(risk_entry, 'score', 0)


def generate_evacuation_message(
    risk_scores: dict,
    zones_data: dict,
) -> str:
    """
    Generate a clear, actionable evacuation message for the whole building.

    Accepts risk_scores as either a dict of RiskResult objects OR dicts
    (the snapshot format). This message is spoken via Web Speech API.
    """
    if not risk_scores:
        return "All systems normal. No evacuation required."

    # Find blocked and high-risk zones
    blocked = [zid for zid, z in zones_data.items() if z.get('blocked')]
    high_risk = [zid for zid, r in risk_scores.items() if _get_score(r) >= 60]

    if not high_risk:
        return "No immediate danger detected. Continue monitoring."

    # Find the most dangerous zone
    worst_zone = max(risk_scores, key=lambda z: _get_score(risk_scores[z]))
    worst_score = _get_score(risk_scores[worst_zone])

    # Get zone names from config loader
    from engine.config_loader import ZONE_CONFIG
    worst_name = ZONE_CONFIG.get(worst_zone, {}).get('name', worst_zone)

    # Find best exit from the worst zone (now using Dijkstra)
    exit_id, path, path_cost = find_safest_exit(worst_zone, blocked, high_risk, risk_scores)
    exit_name = EXIT_NAMES.get(exit_id, exit_id) if exit_id else "nearest exit"

    # Build the message
    severity_word = "CRITICAL EMERGENCY" if worst_score >= 80 else "EMERGENCY"

    msg_parts = [f"{severity_word} detected in {worst_name}."]

    if blocked:
        from engine.chronos import ZONE_CONFIG as ZC
        b_names = [ZC.get(b, {}).get('name', b) for b in blocked]
        msg_parts.append(f"WARNING: {', '.join(b_names)} blocked.")

    msg_parts.append(f"Evacuate via {exit_name}.")

    if path and len(path) > 1:
        from engine.chronos import ZONE_CONFIG as ZC
        path_names = [ZC.get(p, {}).get('name', p) for p in path[:-1]]
        if path_names:
            msg_parts.append(f"Route: {' → '.join(path_names)} → {exit_name}.")

    msg_parts.append("Follow staff instructions.")

    return " ".join(msg_parts)


def get_all_recommendations(
    risk_scores: dict,
    zones_data: dict,
) -> Dict[str, dict]:
    """
    For every zone, compute the safest exit and evacuation route
    using risk-weighted Dijkstra.

    Returns a dict of zone_id → {'exit': str, 'path': list, 'clear': bool, 'cost': float}
    """
    blocked = [zid for zid, z in zones_data.items() if z.get('blocked')]
    high_risk = [zid for zid, r in risk_scores.items() if _get_score(r) >= 60]

    recommendations = {}
    for zone_id in risk_scores:
        exit_id, path, cost = find_safest_exit(zone_id, blocked, high_risk, risk_scores)
        recommendations[zone_id] = {
            'exit': exit_id,
            'exit_name': EXIT_NAMES.get(exit_id, exit_id) if exit_id else 'Unknown',
            'path': path,
            'clear': exit_id is not None,
            'cost': cost,
        }
    return recommendations
