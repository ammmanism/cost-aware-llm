import yaml
import os
from typing import Dict, List, Any
from gateway.routers.base import BaseRouter

class CostAwareRouter(BaseRouter):
    def __init__(self, config_path: str = "configs/models.yaml"):
        self.config_path = config_path
        self.model_costs: Dict[str, float] = {}
        self.load_config()

    def load_config(self) -> None:
        """Load model configurations from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                for model in config.get('models', []):
                    name = model.get('name')
                    cost = model.get('cost_per_1k_tokens')
                    if name and cost is not None:
                        self.model_costs[name] = float(cost)
        except FileNotFoundError:
            # Fallback to sensible defaults if config missing
            self.model_costs = {
                "gpt-3.5-turbo": 0.002,
                "gpt-4": 0.03,
                "claude-3-haiku": 0.00025,
                "claude-3-sonnet": 0.003,
                "llama-3-8b": 0.0001,
            }
        except Exception as e:
            # Log error and use fallback
            import logging
            logging.error(f"Failed to load config from {self.config_path}: {e}")
            self.model_costs = {
                "gpt-3.5-turbo": 0.002,
                "gpt-4": 0.03,
            }

    def select_models(self, request: Dict[str, Any]) -> List[str]:
        """Return model names sorted by cost ascending."""
        if not self.model_costs:
            return ["gpt-3.5-turbo"]
        sorted_models = sorted(self.model_costs.keys(), key=lambda m: self.model_costs[m])
        return sorted_models