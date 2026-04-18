import asyncio
import random
import logging
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)

class ChaosMode(Enum):
    OFF = "off"
    LATENCY = "latency"
    FAILURE = "failure"
    SLOW_START = "slow_start"

class ChaosController:
    """Global chaos engineering controller."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.mode = ChaosMode.OFF
            cls._instance.config: Dict[str, Any] = {}
            cls._instance.provider_states: Dict[str, Dict] = {}
        return cls._instance
    
    def enable(self, mode: ChaosMode, **config):
        self.mode = mode
        self.config = config
        logger.warning(f"Chaos mode enabled: {mode} with config {config}")
    
    def disable(self):
        self.mode = ChaosMode.OFF
        logger.info("Chaos mode disabled")
    
    def should_fail(self, provider: str) -> bool:
        if self.mode != ChaosMode.FAILURE:
            return False
        rate = self.config.get("failure_rate", 0.1)
        return random.random() < rate
    
    async def inject_latency(self, provider: str) -> Optional[float]:
        if self.mode != ChaosMode.LATENCY:
            return None
        base_latency = self.config.get("base_latency_ms", 100)
        variance = self.config.get("variance_ms", 50)
        delay = (base_latency + random.uniform(-variance, variance)) / 1000
        if delay > 0:
            await asyncio.sleep(delay)
        return delay
    
    def get_mode(self) -> str:
        return self.mode.value

# Singleton access
chaos = ChaosController()
