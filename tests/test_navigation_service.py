import pytest
from server.services.navigation_service.service import NavigationService
from server.state import app_state

def test_navigation_service_dijkstra_and_interpolation():
    """Verify Dijkstra pathfinding, blocked detours, and interpolation."""
    app_state.reset_simulated_state()
    service = NavigationService()

    
    # 1. Simple layout configuration
    zone_graph = {
        "room_a": ["corridor"],
        "corridor": ["room_a", "room_b", "exit_zone"],
        "room_b": ["corridor"],
        "exit_zone": ["corridor"]
    }
    zone_positions = {
        "room_a": (100.0, 100.0),
        "corridor": (200.0, 100.0),
        "room_b": (300.0, 100.0),
        "exit_zone": (200.0, 200.0)
    }
    service.configure_map(zone_graph, zone_positions)

    # 2. Basic path check
    path = service.find_rover_path("room_a", "room_b")
    assert path == ["room_a", "corridor", "room_b"]

    # 3. Obstacle avoidance check: if corridor is blocked, cannot reach room_b from room_a
    blocked_path = service.find_rover_path("room_a", "room_b", blocked_zones=["corridor"])
    assert blocked_path == []

    # 4. Target override check: if room_b is blocked, can still inspect room_b directly
    inspect_blocked_target = service.find_rover_path("room_a", "room_b", blocked_zones=["room_b"])
    assert inspect_blocked_target == ["room_a", "corridor", "room_b"]

    # 5. Position Interpolation check
    new_pos, arrived, remaining = service.interpolate_position(
        pos_a=(100.0, 100.0), pos_b=(200.0, 100.0), step_pixels=40.0
    )
    assert new_pos == (140.0, 100.0)
    assert arrived is False
    assert remaining == 60.0

    # Over-step interpolation
    new_pos_arrived, arrived_flag, remaining_zero = service.interpolate_position(
        pos_a=(100.0, 100.0), pos_b=(200.0, 100.0), step_pixels=120.0
    )
    assert new_pos_arrived == (200.0, 100.0)
    assert arrived_flag is True
    assert remaining_zero == 0.0
