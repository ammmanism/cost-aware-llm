from typing import Dict, List, Any
from gateway.routers.base import BaseRouter

class CostAwareRouter(BaseRouter):
    def __init__(self):
        # Cost per 1K tokens (mock values)
        self.model_costs = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.03,
            "claude-3-haiku": 0.00025,
            "claude-3-sonnet": 0.003,
            "llama-3-8b": 0.0001,
        }

    def select_models(self, request: Dict[str, Any]) -> List[str]:
        # Sort models by cost ascending
        sorted_models = sorted(self.model_costs.keys(), key=lambda m: self.model_costs[m])
        return sorted_models