import os
import sys
import yaml
import logging

logger = logging.getLogger(__name__)

CONFIG_FILENAME = "config.yaml"
EXAMPLE_CONFIG_FILENAME = "config.example.yaml"


class Config:
    def __init__(self, config_path=None):
        if config_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, CONFIG_FILENAME)
            if not os.path.exists(config_path):
                # Fallback to example if config.yaml doesn't exist yet
                example_path = os.path.join(base_dir, EXAMPLE_CONFIG_FILENAME)
                if os.path.exists(example_path):
                    config_path = example_path

        self.config_path = config_path
        self._data = self._load()

    def _load(self):
        if not os.path.exists(self.config_path):
            logger.error(f"Configuration file not found at: {self.config_path}")
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data or {}
        except Exception as e:
            logger.error(f"Failed to parse YAML configuration: {e}")
            return {}

    def reload(self):
        """Reload configuration from disk."""
        self._data = self._load()

    @property
    def bot_token(self) -> str:
        # Check environment variable first, then config file
        return os.environ.get("TELEGRAM_BOT_TOKEN") or self._data.get("bot", {}).get("token", "")

    @property
    def admin_chat_ids(self) -> list:
        ids = self._data.get("bot", {}).get("admin_chat_ids", [])
        return [int(cid) for cid in ids if str(cid).strip()]

    def is_admin(self, chat_id: int) -> bool:
        return chat_id in self.admin_chat_ids

    @property
    def send_startup_message(self) -> bool:
        return self._data.get("bot", {}).get("send_startup_message", True)

    @property
    def services(self) -> list:
        return self._data.get("services", [])

    def get_service(self, service_id: str) -> dict:
        for s in self.services:
            if s.get("id") == service_id:
                return s
        return {}

    @property
    def system_settings(self) -> dict:
        defaults = {
            "reboot_cmd": "sudo reboot",
            "shutdown_cmd": "sudo shutdown now",
            "preferred_interface": "wlan0",
        }
        user_sys = self._data.get("system", {})
        defaults.update(user_sys)
        return defaults

    @property
    def log_settings(self) -> dict:
        defaults = {
            "default_tail_lines": 50,
            "post_send_action": "none",  # "none", "truncate", "delete"
        }
        defaults.update(self._data.get("logs", {}))
        return defaults

    @property
    def java_settings(self) -> dict:
        defaults = {
            "enabled": False,
            "jps_path": "jps",
        }
        user_cfg = self._data.get("inspectors", {}).get("java") or self._data.get("java", {})
        defaults.update(user_cfg)
        return defaults

    @property
    def python_settings(self) -> dict:
        defaults = {
            "enabled": True,
            "exclude_self": True,
        }
        user_cfg = self._data.get("inspectors", {}).get("python") or self._data.get("python", {})
        defaults.update(user_cfg)
        return defaults

    @property
    def javascript_settings(self) -> dict:
        defaults = {
            "enabled": True,
            "pm2_enabled": True,
        }
        user_cfg = (
            self._data.get("inspectors", {}).get("javascript")
            or self._data.get("javascript", {})
            or self._data.get("node", {})
        )
        defaults.update(user_cfg)
        return defaults

    @property
    def periodic_status_settings(self) -> dict:
        defaults = {
            "enabled": True,
            "interval_minutes": 180,
        }
        user_cfg = self._data.get("periodic_status") or self._data.get("bot", {}).get("periodic_status") or {}
        defaults.update(user_cfg)
        return defaults


# Global singleton instance
cfg = Config()
