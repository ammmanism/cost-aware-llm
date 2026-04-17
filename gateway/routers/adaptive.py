import time
import random
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
import redis.asyncio as redis
import os
import json
from gateway.routers.base import BaseRouter

logger = logging.getLogger(__name__)

class AdaptiveRouter(BaseRouter):
    """
    Adaptive router that learns from real-time performance metrics.
    Uses a multi-armed bandit approach (epsilon-greedy) to balance exploration/exploitation.
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.environ.get("REDIS_URL")
        self._redis: Optional[redis.Redis] = None
        self._connected = False
        
        # Fallback in-memory stats
        self._stats: Dict[str, Dict] = defaultdict(lambda: {
            "success_count": 0,
            "failure_count": 0,
            "total_latency": 0.0,
            "cost_per_request": 0.0,
        })
        
        # Configuration
        self.exploration_rate = 0.1  # 10% exploration
        self.latency_weight = 0.4
        self.cost_weight = 0.3
        self.success_weight = 0.3
        self.decay_factor = 0.95  # Weight recent performance more
        
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
        key = f"router:stats:{model}"
        
        if self._redis:
            # Use Redis sorted set with timestamps for sliding window
            now = time.time()
            data = {
                "success": 1 if success else 0,
                "latency": latency_ms,
                "cost": cost,
                "timestamp": now
            }
            await self._redis.zadd(key, {json.dumps(data): now})
            # Trim old data (keep last hour)
            await self._redis.zremrangebyscore(key, 0, now - 3600)
        else:
            # In-memory with decay
            stats = self._stats[model]
            stats["success_count"] = stats["success_count"] * self.decay_factor + (1 if success else 0)
            stats["failure_count"] = stats["failure_count"] * self.decay_factor + (0 if success else 1)
            stats["total_latency"] = stats["total_latency"] * self.decay_factor + latency_ms
            stats["cost_per_request"] = cost
    
    async def _get_model_score(self, model: str) -> float:
        """Calculate score for a model based on recent performance."""
        await self._ensure_redis_connected()
        
        if self._redis:
            key = f"router:stats:{model}"
            # Get recent records (last 5 minutes)
            now = time.time()
            records = await self._redis.zrangebyscore(key, now - 300, now)
            if not records:
                return 0.5  # Neutral score for unknown models
            
            successes = 0
            total_latency = 0
            total_cost = 0
            count = len(records)
            
            for rec_json in records:
                rec = json.loads(rec_json)
                successes += rec["success"]
                total_latency += rec["latency"]
                total_cost += rec["cost"]
            
            success_rate = successes / count if count > 0 else 0
            avg_latency = total_latency / count if count > 0 else 1000
            
            # Normalize scores (inverted latency: lower is better)
            max_latency = 5000
            latency_score = max(0, 1 - (avg_latency / max_latency))
            cost_score = max(0, 1 - total_cost)  # Assume cost normalized
            
            score = (
                self.success_weight * success_rate +
                self.latency_weight * latency_score +
                self.cost_weight * cost_score
            )
            return score
        else:
            stats = self._stats[model]
            total = stats["success_count"] + stats["failure_count"]
            if total == 0:
                return 0.5
            success_rate = stats["success_count"] / total
            avg_latency = stats["total_latency"] / total if total > 0 else 1000
            latency_score = max(0, 1 - (avg_latency / 5000))
            return 0.7 * success_rate + 0.3 * latency_score
    
    async def select_models(self, request: Dict[str, Any]) -> List[str]:
        """Return models ordered by adaptive score (highest first)."""
        # Improved model discovery
        import yaml
        models = []
        try:
            with open("configs/models.yaml", 'r') as f:
                config = yaml.safe_load(f)
                models = [m.get('name') for m in config.get('models', []) if m.get('name')]
        except:
            models = ["gpt-3.5-turbo", "claude-3-haiku", "llama-3-8b"]
        
        if not models:
            return ["gpt-3.5-turbo"]
        
        # Epsilon-greedy: sometimes explore randomly
        if random.random() < self.exploration_rate:
            logger.debug("Adaptive router exploring")
            random.shuffle(models)
            return models
        
        # Calculate scores for all models
        scores = {}
        for model in models:
            scores[model] = await self._get_model_score(model)
        
        # Sort by score descending
        sorted_models = sorted(models, key=lambda m: scores[m], reverse=True)
        logger.debug(f"Adaptive router scores: { {m: round(scores[m],3) for m in sorted_models[:3]} }")
        return sorted_models
