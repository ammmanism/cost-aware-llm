import yaml
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, RootModel
from routers.base import BaseRouter

logger = logging.getLogger(__name__)

class ModelConfig(BaseModel):
    name: str
    latency_ms: int = Field(..., gt=0)
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
                
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
                config = LatencyConfig(**data)
                for model in config.models:
                    self.model_latency[model.name] = model.latency_ms
            
            logger.info(f"Loaded {len(self.model_latency)} models into LatencyAwareRouter")
            
        except Exception as e:
            logger.error(f"Failed to load LatencyAwareRouter config: {e}. Using resilient defaults.")
            # Resilient Goat-tier defaults
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
            
        # Sort by latency value ascending
        return sorted(self.model_latency.keys(), key=lambda m: self.model_latency[m])

