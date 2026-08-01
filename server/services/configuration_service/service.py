import os
import json
from pathlib import Path
from server.services.base_service import BaseService

class ConfigurationService(BaseService):
    """
    Service responsible for loading building.json configuration and environment variables.
    Provides a unified query API for other services.
    """
    def __init__(self, config: dict = None):
        super().__init__("ConfigurationService", config)
        if config and "config_path" in config:
            self.config_path = Path(config["config_path"])
        else:
            self.config_path = self._find_config_path()
        self._building_config = {}

    def _find_config_path(self) -> Path:
        current = Path(__file__).resolve()
        for parent in current.parents:
            candidate = parent / 'config' / 'building.json'
            if candidate.exists():
                return candidate
        return current.parents[4] / 'config' / 'building.json'


    def _on_start(self) -> bool:
        try:
            self._building_config = self.load_building_json()
            self.logger.info(f"Configuration loaded from {self.config_path}")
            return True
        except Exception as e:
            self.logger.exception(f"Failed to load building.json: {e}")
            return False

    def load_building_json(self) -> dict:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found at: {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_building_config(self) -> dict:
        return self._building_config

    def get_env_var(self, key: str, default: str = None) -> str:
        return os.getenv(key, default)

    def get_zones(self) -> dict:
        return self._building_config.get("zones", {})

    def get_thresholds(self) -> dict:
        return self._building_config.get("thresholds", {})

    def get_hardware_config(self) -> dict:
        return self._building_config.get("hardware_config", {})

    def get_pin_map(self) -> dict:
        return self.get_hardware_config().get("pin_map", {})
