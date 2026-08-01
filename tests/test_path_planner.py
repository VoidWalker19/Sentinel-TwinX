import pytest
from server.services.path_planner.service import PathPlannerService

def test_path_planner_solver():
    """Verify Dijkstra solver finds optimal shortest path and handles blocks."""
    planner = PathPlannerService()
    
    # Configure simple graph
    graph = {
        "room_a": ["room_b", "room_c"],
        "room_b": ["room_a", "room_d"],
        "room_c": ["room_a", "room_d"],
        "room_d": ["room_b", "room_c"]
    }
    positions = {
        "room_a": (0.0, 0.0),
        "room_b": (10.0, 0.0),
        "room_c": (0.0, 10.0),
        "room_d": (10.0, 10.0)
    }
    floors = {
        "room_a": 1,
        "room_b": 1,
        "room_c": 1,
        "room_d": 1
    }
    names = {
        "room_a": "Room A",
        "room_b": "Room B",
        "room_c": "Room C",
        "room_d": "Room D"
    }
    
    planner.configure_map(graph, positions, floors, names)
    
    # 1. Simple path finding
    path = planner.find_path("room_a", "room_d")
    assert path[0] == "room_a"
    assert path[-1] == "room_d"
    
    # 2. Blocked path finding (block room_b -> force path via room_c)
    blocked_path = planner.find_path("room_a", "room_d", blocked_zones=["room_b"])
    assert blocked_path == ["room_a", "room_c", "room_d"]
    
    # 3. ETA and distance calculations
    dist = planner.calculate_path_distance(["room_a", "room_b"])
    assert dist == 10.0
    
    eta = planner.calculate_eta(10.0, 2.0)
    assert eta == 5
