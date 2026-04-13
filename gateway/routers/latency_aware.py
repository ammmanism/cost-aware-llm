from typing import List, Dict, Any
from gateway.routers.base import BaseRouter

class LatencyAwareRouter(BaseRouter):
    def __init__(self, model_configs: List[Dict[str, Any]]):
        self.configs = model_configs

    def route(self, request: Dict[str, Any]) -> str:
        # Sort by latency score and return fastest
        sorted_models = sorted(self.configs, key=lambda x: x["latency_score"])
        return sorted_models[0]["id"]
