import os
import logging
from logging.handlers import RotatingFileHandler
from server.services.base_service import BaseService

class LoggingService(BaseService):
    """
    Central logging service. Initializes rotating file loggers and stdout logs.
    """
    def __init__(self, config: dict = None):
        super().__init__("LoggingService", config)
        self.log_dir = self.config.get("log_dir", "logs")
        self.log_file = self.config.get("log_file", "sentinel.log")
        self.max_bytes = self.config.get("max_bytes", 5 * 1024 * 1024) # 5MB
        self.backup_count = self.config.get("backup_count", 5)
        self.log_level = self.config.get("level", logging.INFO)

    def _on_start(self) -> bool:
        try:
            # Create logs directory if not exists
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir)

            log_path = os.path.join(self.log_dir, self.log_file)
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            )

            # File handler (rotating)
            file_handler = RotatingFileHandler(
                log_path, maxBytes=self.max_bytes, backupCount=self.backup_count, encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(self.log_level)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(self.log_level)

            # Configure root logger
            root_logger = logging.getLogger()
            root_logger.setLevel(self.log_level)
            
            # Clear existing handlers to avoid duplicates
            root_logger.handlers = []
            root_logger.addHandler(file_handler)
            root_logger.addHandler(console_handler)

            self.logger.info(f"Logging initialized. Output file: {log_path}")
            return True
        except Exception as e:
            # Fallback to simple console config
            logging.basicConfig(level=logging.INFO)
            logging.error(f"Failed to initialize rotating file logger: {e}")
            return False

    def _on_stop(self) -> bool:
        self.logger.info("Shutdown logging service handlers.")
        # Do not close handlers completely as other processes might be exiting
        return True
