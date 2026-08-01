from typing import Any
from server.services.base_service import BaseService
from server.services.logging_service import LoggingService
from server.services.configuration_service import ConfigurationService
from server.services.database_service import DatabaseService
from server.services.convex_service import ConvexService
from server.services.mqtt_service import MqttService
from server.services.sensor_service import SensorService
from server.services.health_service import HealthService
from server.services.alert_service import AlertService
from server.services.mission_service import MissionService
from server.services.navigation_service import NavigationService
from server.services.camera_service import CameraService
from server.services.vision_service import VisionService
from server.services.ai_service import AiService
from server.services.path_planner.service import PathPlannerService
from server.services.obstacle_manager.service import ObstacleManagerService
from server.services.history_service.service import HistoryService
from server.services.backup_service.service import BackupService
from server.services.health_monitor_service.service import HealthMonitorService
from server.services.diagnostics_service.service import DiagnosticsService
from server.services.analytics_service.service import AnalyticsService

class ServiceRegistry:
    """
    Registry that coordinates startup and teardown of all Sentinel Twin X modular services
    in topological order (dependencies first).
    """
    def __init__(self):
        self._services = {}

    def register(self, service: BaseService):
        self._services[service.name] = service

    def get(self, name: str) -> Any:
        return self._services.get(name)

    def start_all(self):
        # Specific dependency order for startup
        order = [
            "LoggingService",
            "ConfigurationService",
            "DatabaseService",
            "PathPlannerService",
            "ObstacleManagerService",
            "ConvexService",
            "HistoryService",
            "BackupService",
            "MqttService",
            "SensorService",
            "HealthService",
            "HealthMonitorService",
            "AlertService",
            "MissionService",
            "NavigationService",
            "CameraService",
            "VisionService",
            "AiService",
            "DiagnosticsService",
            "AnalyticsService",
        ]
        
        for name in order:
            srv = self._services.get(name)
            if srv:
                success = srv.start()
                if not success and name in ("LoggingService", "ConfigurationService"):
                    # Critical services
                    raise RuntimeError(f"Critical service {name} failed to initialize. Aborting backend startup.")

    def stop_all(self):
        # Stop in reverse order of dependencies
        for name in reversed(list(self._services.keys())):
            srv = self._services[name]
            if srv.is_running:
                srv.stop()

# Global registry instance
# Global registry instance
registry = ServiceRegistry()

# Initialize registry elements with default configs
registry.register(LoggingService())
registry.register(ConfigurationService())
registry.register(DatabaseService())
registry.register(PathPlannerService())
registry.register(ObstacleManagerService())
registry.register(HistoryService())
registry.register(BackupService())
registry.register(ConvexService())
registry.register(MqttService())
registry.register(SensorService())
registry.register(HealthService())
registry.register(HealthMonitorService())
registry.register(AlertService())
registry.register(MissionService())
registry.register(NavigationService())
registry.register(CameraService())
registry.register(VisionService())
registry.register(AiService())
registry.register(DiagnosticsService())
registry.register(AnalyticsService())
