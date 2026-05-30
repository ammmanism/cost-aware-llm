import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

from routers.base import BaseRouter

logger = logging.getLogger(__name__)


class ModelPricing(BaseModel):
    name: str
    cost_per_1k_tokens: float = Field(..., ge=0)
    provider: Optional[str] = None


class PricingConfig(BaseModel):
    models: List[ModelPricing]


class CostAwareRouter(BaseRouter):
    """
    Precision router that minimizes API expenditure.

    Prioritizes models by cost per 1k tokens using validated
    configuration models and async-ready selection.
    """

    def __init__(self, config_path: str = "configs/models.yaml"):
        self.config_path = Path(config_path)
        self.model_costs: Dict[str, float] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load model pricing with strict validation."""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(f"Config {self.config_path} not found")

            with self.config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            config = PricingConfig(**data)
            for model in config.models:
                self.model_costs[model.name] = model.cost_per_1k_tokens

            logger.info("Loaded pricing for %s models into CostAwareRouter", len(self.model_costs))

        except Exception as e:
            logger.error("Failed to load CostAwareRouter config: %s. Using resilient defaults.", e)
            self.model_costs = {
                "llama-3-8b": 0.0001,
                "claude-3-haiku": 0.00025,
                "gpt-3.5-turbo": 0.0005,
                "gpt-4-turbo": 0.01,
            }

    async def select_models(self, request_data: Dict[str, Any]) -> List[str]:
        """
        Return model names prioritized by cost in ascending order.

        Supported request filters:
        - allowed_models: optional list limiting the candidate set.
        - max_cost_per_1k_tokens: optional ceiling for model price.
        """
        if not self.model_costs:
            return ["gpt-3.5-turbo"]

        allowed_models = request_data.get("allowed_models")
        max_cost = request_data.get("max_cost_per_1k_tokens")
        candidates = dict(self.model_costs)

        if allowed_models:
            allowed = set(allowed_models)
            candidates = {name: cost for name, cost in candidates.items() if name in allowed}

        if max_cost is not None:
            candidates = {
                name: cost for name, cost in candidates.items() if cost <= float(max_cost)
            }

        if not candidates:
            logger.warning(
                "Cost filters removed every model; falling back to cheapest configured model"
            )
            candidates = dict(self.model_costs)

        return sorted(candidates.keys(), key=lambda model: (candidates[model], model))

