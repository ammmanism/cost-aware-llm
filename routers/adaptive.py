import time
import random
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
import redis.asyncio as redis
import os
import json
import numpy as np
from routers.base import BaseRouter

logger = logging.getLogger(__name__)

class AdaptiveRouter(BaseRouter):
    """
    Adaptive router that learns from real-time performance metrics.
    Uses Thompson Sampling (Multi-Armed Bandit) to balance exploration/exploitation.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.environ.get("REDIS_URL")
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        
        # Fallback in-memory stats: alpha (successes), beta (failures)
        # We start with alpha=1, beta=1 for a uniform prior
        self._stats: Dict[str, Dict] = defaultdict(lambda: {
            "alpha": 1.0,
            "beta": 1.0,
            "total_latency": 0.0,
            "count": 0
        })
        
        # Weights for multi-objective optimization (future)
        self.latency_weight = 0.4
        self.cost_weight = 0.3
        self.success_weight = 0.3
        
    async def _ensure_redis_connected(self):
        if self.redis_url and not self._connected:
            try:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
                self._connected = True
                logger.info("AdaptiveRouter connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect Redis for AdaptiveRouter: {e}")
                self.redis_url = None
                
    async def record_result(self, model: str, success: bool, latency_ms: float, cost: float = 0.0):
        """Record the outcome of a request for a model."""
        await self._ensure_redis_connected()
        
        if self._redis:
            # Redis implementation uses hashes for alpha/beta
            key = f"router:bandit:{model}"
            field = "alpha" if success else "beta"
            await self._redis.hincrbyfloat(key, field, 1.0)
            # Store latency in a separate list for moving average
            await self._redis.lpush(f"router:latency:{model}", latency_ms)
            await self._redis.ltrim(f"router:latency:{model}", 0, 99) # Keep last 100
        else:
            # In-memory update
            stats = self._stats[model]
            if success:
                stats["alpha"] += 1.0
            else:
                stats["beta"] += 1.0
            stats["total_latency"] += latency_ms
            stats["count"] += 1

    async def _get_model_sample(self, model: str) -> float:
        """Sample from the model's performance distribution."""
        await self._ensure_redis_connected()
        
        alpha, beta = 1.0, 1.0
        
        if self._redis:
            key = f"router:bandit:{model}"
            stats = await self._redis.hgetall(key)
            alpha = float(stats.get("alpha", 1.0))
            beta = float(stats.get("beta", 1.0))
        else:
            stats = self._stats[model]
            alpha, beta = stats["alpha"], stats["beta"]
        
        # Thompson Sampling: sample from Beta distribution
        # This naturally handles exploration (wider distribution for new models)
        # and exploitation (narrower distribution around the mean for known models)
        return np.random.beta(alpha, beta)

    async def select_models(self, request_data: Dict[str, Any]) -> List[str]:
        """Return models ordered by Thompson samples (highest first)."""
        import yaml
        models = []
        try:
            config_path = os.environ.get("MODELS_CONFIG", "configs/models.yaml")
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                models = [m.get('name') for m in config.get('models', []) if m.get('name')]
        except Exception:
            models = ["gpt-3.5-turbo", "claude-3-haiku", "llama-3-8b"]
        
        if not models:
            return ["gpt-3.5-turbo"]

        # Sample for each model and sort
        samples = {}
        for model in models:
            samples[model] = await self._get_model_sample(model)
        
        # Sort by sample value descending (higher probability of success = better)
        sorted_models = sorted(models, key=lambda m: samples[m], reverse=True)
        
        # Log top choices for observability
        top_models = [f"{m}({samples[m]:.3f})" for m in sorted_models[:3]]
        logger.debug(f"Thompson Sampling choices: {', '.join(top_models)}")
        
        return sorted_models

