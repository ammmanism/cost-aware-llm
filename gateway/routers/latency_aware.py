from typing import Dict, List, Any
from gateway.routers.base import BaseRouter

class LatencyAwareRouter(BaseRouter):
    def __init__(self):
        # Mock latency in ms
        self.model_latency = {
            "gpt-3.5-turbo": 800,
            "gpt-4": 2000,
            "claude-3-haiku": 500,
            "claude-3-sonnet": 1200,
            "llama-3-8b": 300,
        }

    def select_models(self, request: Dict[str, Any]) -> List[str]:
        sorted_models = sorted(self.model_latency.keys(), key=lambda m: self.model_latency[m])
        return sorted_models
