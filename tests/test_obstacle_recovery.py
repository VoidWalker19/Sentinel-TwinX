import pytest
from unittest.mock import MagicMock
from rover.rover_sim import RoverSimulator
from server.services.obstacle_manager.service import ObstacleManagerService
from server.services.path_planner.service import PathPlannerService
from server.services.navigation_service.service import NavigationService
from server.services.mission_service.service import MissionService
from server.state import ZoneReading

def test_rover_obstacle_replan_and_recovery():
    """Verify that the RoverSimulator replans around obstacles and backtracks if blocked."""
    from server.services import registry
    
    # Mock ConfigurationService for dynamic navigation config loading
    cfg_srv = MagicMock()
    cfg_srv.name = "ConfigurationService"
    cfg_srv.config = {
        "navigation_config": {
            "base_zone": "reception",
            "travel_speed": 45.0,
            "obstacle_threshold_cm": 30.0,
            "recovery_max_retries": 3
        }
    }
    registry.register(cfg_srv)
    
    planner = PathPlannerService()
    # Configure a layout with two alternate corridor paths:
    # reception <-> corridor_a <-> classroom_a  (distance = 200)
    # reception <-> corridor_b <-> classroom_a  (distance = 282.8)
    graph = {
        "reception": ["corridor_a", "corridor_b"],
        "corridor_a": ["reception", "classroom_a"],
        "corridor_b": ["reception", "classroom_a"],
        "classroom_a": ["corridor_a", "corridor_b"]
    }
    positions = {
        "reception": (100.0, 100.0),
        "corridor_a": (200.0, 100.0),
        "corridor_b": (200.0, 200.0),
        "classroom_a": (300.0, 100.0)
    }
    floors = {"reception": 1, "corridor_a": 1, "corridor_b": 1, "classroom_a": 1}
    names = {
        "reception": "Reception",
        "corridor_a": "Corridor A",
        "corridor_b": "Corridor B",
        "classroom_a": "Classroom A"
    }
    planner.configure_map(graph, positions, floors, names)
    registry.register(planner)
    
    obstacle_mgr = ObstacleManagerService()
    obstacle_mgr._on_start()
    registry.register(obstacle_mgr)
    
    nav_srv = NavigationService()
    nav_srv._on_start()
    registry.register(nav_srv)
    
    mission_srv = MissionService()
    mission_srv._on_start()
    mission_srv.set_building_zones(["reception", "corridor_a", "corridor_b", "classroom_a"])
    registry.register(mission_srv)
    
    # Initialize simulator
    sim = RoverSimulator()
    sim._home_zone = "reception"
    sim._home_pos = (100.0, 100.0)
    sim._current_zone = "reception"
    sim._pos = (100.0, 100.0)
    
    # 1. Dispatch rover from reception to classroom_a.
    # Shortest path should be reception -> corridor_a -> classroom_a.
    sim.force_dispatch("classroom_a")
    assert sim._status == "en_route"
    assert sim._path == ["reception", "corridor_a", "classroom_a"]
    
    # 2. Block Corridor A. Simulator should replan via Corridor B.
    obstacle_mgr.set_obstacle("corridor_a", True)
    
    zones_state = {
        "reception": ZoneReading(zone_id="reception", name="Reception", temp=20.0, smoke=10, humidity=50.0, online=True),
        "corridor_a": ZoneReading(zone_id="corridor_a", name="Corridor A", temp=20.0, smoke=10, humidity=50.0, online=True, blocked=True),
        "corridor_b": ZoneReading(zone_id="corridor_b", name="Corridor B", temp=20.0, smoke=10, humidity=50.0, online=True),
        "classroom_a": ZoneReading(zone_id="classroom_a", name="Classroom A", temp=20.0, smoke=10, humidity=50.0, online=True)
    }
    
    # Trigger travel tick - should detect blocked corridor_a and replan via corridor_b
    sim._update_travel(100.0, zones_state)
    assert sim._path == ["reception", "corridor_b", "classroom_a"]
    
    # 3. Block Corridor B too (no alternate path exists). Should start recovery waiting ticks.
    obstacle_mgr.set_obstacle("corridor_b", True)
    zones_state["corridor_b"].blocked = True
    
    # Wait ticks
    sim._update_travel(100.0, zones_state)
    assert sim._blocked_retries == 1
    sim._update_travel(100.0, zones_state)
    assert sim._blocked_retries == 2
    sim._update_travel(100.0, zones_state)
    assert sim._blocked_retries == 3
    
    # 4th tick - retries exhausted, should trigger backtracking recovery back to home (reception)
    sim._update_travel(100.0, zones_state)
    assert sim._status == "returning"
    assert sim._target_zone == "reception"
