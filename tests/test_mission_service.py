import pytest
from unittest.mock import MagicMock

from server.services.mission_service.service import MissionService, Mission, MissionType, MissionStatus

def test_mission_service_priority_queue():
    """Verify that missions are sorted and preempted according to priority guidelines."""
    service = MissionService()
    service._on_start()
    service.set_building_zones(["classroom_a", "reception", "corridor"])

    # 1. Enqueue routine patrol (prio = 1)
    patrol = Mission.create(MissionType.ROUTINE_PATROL, target_zones=["reception", "classroom_a"])
    success, msg = service.submit_mission(patrol)
    assert success is True
    assert service.active_mission == patrol

    # 2. Enqueue emergency inspection (prio = 3) -> should preempt routine patrol
    emergency = Mission.create(MissionType.EMERGENCY_INSPECTION, target_zones=["classroom_a"])
    success, msg = service.submit_mission(emergency)
    assert success is True
    assert service.active_mission == emergency
    assert patrol.status == MissionStatus.PAUSED
    assert patrol in service.paused_missions

    # 3. Enqueue battery return (prio = 4) -> should preempt emergency inspection
    battery = Mission.create(MissionType.BATTERY_RETURN)
    success, msg = service.submit_mission(battery)
    assert success is True
    assert service.active_mission == battery
    assert emergency.status == MissionStatus.QUEUED
    assert emergency in service.queue

    # 4. Complete battery return -> should promote emergency inspection next
    next_m = service.complete_active()
    assert next_m == emergency
    assert service.active_mission == emergency

    # 5. Complete emergency inspection -> should promote paused routine patrol next
    next_m2 = service.complete_active()
    assert next_m2 == patrol
    assert service.active_mission == patrol

def test_mission_service_automatic_dispatch_logic():
    """Verify that tick_queue schedules battery return and routine patrols properly."""
    service = MissionService()
    service._on_start()
    service.set_building_zones(["classroom_a", "reception", "corridor"])

    # Check that high risk zones spawn emergency inspections
    target = service.tick_queue(rover_status="idle", battery_pct=80.0, high_risk_zones=["classroom_a"])
    assert target == "classroom_a"
    assert service.active_mission.mission_type == MissionType.EMERGENCY_INSPECTION

    # Complete it
    service.complete_active()
    assert service.active_mission is None

    # Check battery return safety dispatch below 25%
    target_low_battery = service.tick_queue(rover_status="idle", battery_pct=20.0, high_risk_zones=[])
    assert target_low_battery == "corridor"
    assert service.active_mission.mission_type == MissionType.BATTERY_RETURN

def test_mission_service_fsm_transitions():
    """Verify that Mission FSM states transition correctly and update fsm_state."""
    service = MissionService()
    service._on_start()
    service.set_building_zones(["classroom_a", "reception", "corridor"])
    
    assert service.fsm_state == "IDLE"
    
    # 1. Start routine patrol -> PATROL state
    patrol = Mission.create(MissionType.ROUTINE_PATROL, target_zones=["reception"])
    service.submit_mission(patrol)
    service.tick_queue("idle", 80.0, [])
    assert service.fsm_state == "PATROL"
    
    # 2. Preempt with battery return -> RETURN_HOME state
    battery = Mission.create(MissionType.BATTERY_RETURN)
    service.submit_mission(battery)
    service.tick_queue("idle", 20.0, [])
    assert service.fsm_state == "RETURN_HOME"
    
    # Complete battery return to allow other missions
    service.complete_active()
    
    # 3. Start emergency inspection -> EMERGENCY state
    emergency = Mission.create(MissionType.EMERGENCY_INSPECTION, target_zones=["classroom_a"])
    service.submit_mission(emergency)
    service.tick_queue("idle", 50.0, ["classroom_a"])
    assert service.fsm_state == "EMERGENCY"
    
    # 4. Complete active -> promotes enqueued/paused
    service.complete_active() # completes emergency, active becomes patrol
    service.tick_queue("idle", 80.0, [])
    assert service.fsm_state == "PATROL"
