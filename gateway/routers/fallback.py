from typing import List, Dict, Any
from gateway.routers.base import BaseRouter

class FallbackRouter(BaseRouter):
    def __init__(self, fallback_chain: List[str]):
        self.chain = fallback_chain

    def route(self, request: Dict[str, Any]) -> str:
        # Return first model in chain, server logic handles actual fallback
        return self.chain[0]
