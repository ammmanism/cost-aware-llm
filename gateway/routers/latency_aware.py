import yaml
from typing import Dict, List, Any
from gateway.routers.base import BaseRouter

class LatencyAwareRouter(BaseRouter):
    def __init__(self, config_path: str = "configs/models.yaml"):
        self.config_path = config_path
        self.model_latency: Dict[str, int] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load model configurations from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                for model in config.get('models', []):
                    name = model.get('name')
                    latency = model.get('latency_ms')
                    if name and latency is not None:
                        self.model_latency[name] = int(latency)
        except FileNotFoundError:
            self.model_latency = {
                "gpt-3.5-turbo": 800,
                "gpt-4": 2000,
                "claude-3-haiku": 500,
                "claude-3-sonnet": 1200,
                "llama-3-8b": 300,
            }
        except Exception as e:
            import logging
            logging.error(f"Failed to load config from {self.config_path}: {e}")
            self.model_latency = {
                "gpt-3.5-turbo": 800,
                "gpt-4": 2000,
            }

    def select_models(self, request: Dict[str, Any]) -> List[str]:
        """Return model names sorted by latency ascending."""
        if not self.model_latency:
            return ["gpt-3.5-turbo"]
        sorted_models = sorted(self.model_latency.keys(), key=lambda m: self.model_latency[m])
        return sorted_models
