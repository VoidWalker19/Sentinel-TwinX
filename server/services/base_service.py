import logging
from typing import Dict, Any

class BaseService:
    """
    Base class for all modular services in the Sentinel Twin X backend.
    Enforces a standard lifecycle: init -> start() -> stop()
    """
    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"Service.{self.name}")
        self.is_running = False

    def start(self) -> bool:
        if self.is_running:
            self.logger.warning(f"Service '{self.name}' is already running.")
            return True
        self.logger.info(f"Starting service '{self.name}'...")
        try:
            self.is_running = self._on_start()
            if self.is_running:
                self.logger.info(f"Service '{self.name}' started successfully.")
            else:
                self.logger.error(f"Service '{self.name}' failed to start.")
            return self.is_running
        except Exception as e:
            self.logger.exception(f"Unhandled exception starting service '{self.name}': {e}")
            self.is_running = False
            return False

    def stop(self) -> bool:
        if not self.is_running:
            self.logger.warning(f"Service '{self.name}' is not running.")
            return True
        self.logger.info(f"Stopping service '{self.name}'...")
        try:
            success = self._on_stop()
            if success:
                self.is_running = False
                self.logger.info(f"Service '{self.name}' stopped successfully.")
            else:
                self.logger.error(f"Service '{self.name}' failed to stop cleanly.")
            return success
        except Exception as e:
            self.logger.exception(f"Unhandled exception stopping service '{self.name}': {e}")
            return False

    def _on_start(self) -> bool:
        """Override this method in subclasses to handle service initialization."""
        return True

    def _on_stop(self) -> bool:
        """Override this method in subclasses to handle service teardown."""
        return True
