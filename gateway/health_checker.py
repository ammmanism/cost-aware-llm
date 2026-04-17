import asyncio
import time
from enum import Enum
from typing import Dict, List

class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"

class ProviderHealthChecker:
    """Mock Health Checker for LLM Providers."""
    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.status: Dict[str, HealthStatus] = {}
        self.last_check: Dict[str, float] = {}
        self._running = False

    async def start(self):
        self._running = True
        # Initialize all as healthy
        from providers.factory import ProviderFactory
        for name in ProviderFactory.get_all_providers():
            self.status[name] = HealthStatus.HEALTHY
            self.last_check[name] = time.time()

    async def stop(self):
        self._running = False

    def get_healthy_providers(self) -> List[str]:
        return [name for name, status in self.status.items() if status == HealthStatus.HEALTHY]
