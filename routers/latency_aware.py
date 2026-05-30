import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from routers.base import BaseRouter

logger = logging.getLogger(__name__)


class ModelConfig(BaseModel):
    name: str
    latency_ms: Optional[int] = Field(default=None, gt=0)
    provider: Optional[str] = None


class LatencyConfig(BaseModel):
    models: List[ModelConfig]


class LatencyAwareRouter(BaseRouter):
    """
    Elite-tier router prioritizing models by expected latency.

    Loads configuration via Pydantic for runtime safety and supports
    async selection for high-velocity gateway environments.
    """

    def __init__(self, config_path: str = "configs/models.yaml"):
        self.config_path = Path(config_path)
        self.model_latency: Dict[str, int] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load model configurations with strict validation."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Config {self.config_path} not found")

            with self.config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            config = LatencyConfig(**data)
            for model in config.models:
                if model.latency_ms is None:
                    logger.warning("Skipping %s in latency router: latency_ms missing", model.name)
                    continue
                self.model_latency[model.name] = model.latency_ms

            if not self.model_latency:
                raise ValueError("No models with latency_ms configured")

            logger.info("Loaded %s models into LatencyAwareRouter", len(self.model_latency))

        except Exception as e:
            logger.error(
                "Failed to load LatencyAwareRouter config: %s. Using resilient defaults.", e
            )
            self.model_latency = {
                "llama-3-8b": 150,
                "gpt-3.5-turbo": 600,
                "claude-3-haiku": 400,
                "gpt-4-turbo": 1500,
            }

    async def select_models(self, request_data: Dict[str, Any]) -> List[str]:
        """
        Return model names prioritized by estimated latency.

        Optimized for O(N log N) sorting where N is usually < 20 models.
        """
        if not self.model_latency:
            return ["gpt-3.5-turbo"]

        allowed_models = request_data.get("allowed_models")
        candidates = dict(self.model_latency)
        if allowed_models:
            allowed = set(allowed_models)
            candidates = {name: latency for name, latency in candidates.items() if name in allowed}

        if not candidates:
            logger.warning(
                "Latency filters removed every model; falling back to fastest configured model"
            )
            candidates = dict(self.model_latency)

        return sorted(candidates.keys(), key=lambda model: (candidates[model], model))

