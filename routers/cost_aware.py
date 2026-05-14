import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from routers.base import BaseRouter

logger = logging.getLogger(__name__)

class ModelPricing(BaseModel):
    name: str
    cost_per_1k_tokens: float = Field(..., ge=0)

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
                
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
                config = PricingConfig(**data)
                for model in config.models:
                    self.model_costs[model.name] = model.cost_per_1k_tokens
            
            logger.info(f"Loaded pricing for {len(self.model_costs)} models into CostAwareRouter")
            
        except Exception as e:
            logger.error(f"Failed to load CostAwareRouter config: {e}. Using resilient defaults.")
            self.model_costs = {
                "llama-3-8b": 0.0001,
                "claude-3-haiku": 0.00025,
                "gpt-3.5-turbo": 0.0005,
                "gpt-4-turbo": 0.01,
            }

    async def select_models(self, request_data: Dict[str, Any]) -> List[str]:
        """Return model names prioritized by cost in ascending order."""
        if not self.model_costs:
            return ["gpt-3.5-turbo"]
        return sorted(self.model_costs.keys(), key=lambda m: self.model_costs[m])

