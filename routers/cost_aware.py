import yaml
import os
from typing import Dict, List, Any
from routers.base import BaseRouter


class CostAwareRouter(BaseRouter):
    """
    Router that prioritizes models based on their cost per 1k tokens.

    This router loads model pricing from a configuration file and returns
    models in ascending order of cost, allowing the gateway to minimize
    API expenses by trying cheaper models first.
    """

    def __init__(self, config_path: str = "configs/models.yaml"):
        self.config_path = config_path
        self.model_costs: Dict[str, float] = {}
        self.load_config()

    def load_config(self) -> None:
        """
        Load model configurations from a YAML file.

        Parses the 'models' section of the config to extract costs.
        """
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
                for model in config.get("models", []):
                    name = model.get("name")
                    cost = model.get("cost_per_1k_tokens")
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
            import logging

            logging.error(f"Failed to load config from {self.config_path}: {e}")
            self.model_costs = {
                "gpt-3.5-turbo": 0.002,
                "gpt-4": 0.03,
            }

    def select_models(self, request_data: Dict[str, Any]) -> List[str]:
        """
        Return model names prioritized by cost in ascending order.

        Args:
            request_data: Contextual data for the request (not used in this router).

        Returns:
            A list of model names, with the cheapest ones first.
        """
        if not self.model_costs:
            return ["gpt-3.5-turbo"]
        return sorted(self.model_costs.keys(), key=lambda m: self.model_costs[m])
