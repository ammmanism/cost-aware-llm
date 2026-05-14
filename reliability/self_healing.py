import asyncio
import logging
from typing import Dict, Set, Callable, Awaitable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SelfHealingManager:
    """
    Autonomous recovery system for failed LLM providers.
    
    Monitors 'quarantined' providers and orchestrates health probes 
    to re-integrate them into the active pool once stable.
    """
    def __init__(self, recovery_timeout_seconds: int = 300):
        self.recovery_timeout = recovery_timeout_seconds
        self.quarantine: Dict[str, datetime] = {}
        self.health_check_callback: Optional[Callable[[str], Awaitable[bool]]] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def quarantine_provider(self, provider_name: str):
        """Place a provider in quarantine after repeated failures."""
        self.quarantine[provider_name] = datetime.now()
        logger.warning(f"Provider {provider_name} quarantined for {self.recovery_timeout}s")

    async def start(self, health_check_callback: Callable[[str], Awaitable[bool]]):
        """Start the background self-healing loop."""
        self.health_check_callback = health_check_callback
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("SelfHealingManager started")

    async def stop(self):
        """Stop the background loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self):
        while self._running:
            try:
                await asyncio.sleep(60) # Check every minute
                now = datetime.now()
                to_recover = []

                for name, quarantine_time in self.quarantine.items():
                    if now - quarantine_time > timedelta(seconds=self.recovery_timeout):
                        to_recover.append(name)

                for name in to_recover:
                    logger.info(f"Attempting self-healing recovery for {name}...")
                    if self.health_check_callback:
                        is_healthy = await self.health_check_callback(name)
                        if is_healthy:
                            logger.info(f"Provider {name} successfully recovered and re-integrated.")
                            del self.quarantine[name]
                        else:
                            # Extend quarantine
                            self.quarantine[name] = now
                            logger.info(f"Recovery failed for {name}. Quarantine extended.")
            except Exception as e:
                logger.error(f"Error in SelfHealing loop: {e}")
