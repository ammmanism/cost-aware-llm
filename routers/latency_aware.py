import yaml
from typing import Dict, List, Any
from routers.base import BaseRouter

class LatencyAwareRouter(BaseRouter):
    """
    Router that prioritizes models based on their expected latency.
    
    This router loads expected response times (latency_ms) from a 
    configuration file and returns models in ascending order of latency, 
    allowing the gateway to minimize wait times for users.
    """
    def __init__(self, config_path: str = "configs/models.yaml"):
        self.config_path = config_path
        self.model_latency: Dict[str, int] = {}
        self.load_config()

    def load_config(self) -> None:
        """
        Load model configurations from a YAML file.
        
        Parses the 'models' section of the config to extract latency estimates.
        """
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                for model in config.get('models', []):
                    name = model.get('name')
                    latency = model.get('latency_ms')
                    if name and latency is not None:
                        self.model_latency[name] = int(latency)
        except FileNotFoundError:
            # Fallback to sensible defaults if config missing
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

    def select_models(self, request_data: Dict[str, Any]) -> List[str]:
        """
        Return model names prioritized by estimated latency in ascending order.

        Args:
            request_data: Contextual data for the request (not used in this router).

        Returns:
            A list of model names, with the fastest ones first.
        """
        if not self.model_latency:
            return ["gpt-3.5-turbo"]
        return sorted(self.model_latency.keys(), key=lambda m: self.model_latency[m])
