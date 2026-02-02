import yaml
import os
from typing import Dict, Any, List

class Settings:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        return self.config.get("providers", {}).get(provider_name, {})

    @property
    def default_provider(self) -> str:
        return self.config.get("default_provider", "ollama")

    @property
    def fallback_order(self) -> List[str]:
        return self.config.get("fallback_order", ["ollama"])
