import asyncio
import contextlib
import logging
from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)


class ProviderStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HeartbeatMonitor:
    """Monitor for LLM provider health."""

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.status: Dict[str, ProviderStatus] = {}
        self._running = False
        self._task = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("Heartbeat monitor started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Heartbeat monitor stopped")

    async def _run(self):
        while self._running:
            # Mock health check for now
            # In production, this would call /health or /models on each provider
            await asyncio.sleep(self.check_interval)
            logger.debug("Running provider health checks")
