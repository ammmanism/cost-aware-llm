from typing import Dict, Any


class CostAwareRouter:
    def __init__(self):
        self.cost_config = {
            "gpt-3.5-turbo": 0.0005,
            "gpt-4-turbo": 0.01,
        }

    def select_model(self, request: Dict[str, Any]) -> str:
        return min(self.cost_config, key=self.cost_config.get)