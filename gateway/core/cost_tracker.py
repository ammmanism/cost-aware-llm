import yaml
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class NexusCostTracker:
    """
    Precision tracking of API expenditure across all providers.
    
    Provides real-time cost estimation based on model-specific 
    pricing configurations.
    """
    def __init__(self, config_path: str = "configs/models.yaml"):
        self.config_path = Path(config_path)
        self.model_prices: Dict[str, float] = {}
        self._load_prices()

    def _load_prices(self) -> None:
        """Load pricing data from config."""
        try:
            if not self.config_path.exists():
                return
            
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
                for model in data.get('models', []):
                    name = model.get('name')
                    price = model.get('cost_per_1k_tokens')
                    if name and price is not None:
                        self.model_prices[name] = float(price)
            
            logger.info(f"CostTracker initialized with {len(self.model_prices)} model prices")
        except Exception as e:
            logger.error(f"Failed to initialize CostTracker: {e}")

    def calculate_cost(self, model: str, total_tokens: int) -> float:
        """
        Calculate the cost of a request based on token count.
        
        Args:
            model: The name of the LLM model used.
            total_tokens: Sum of input and output tokens.
            
        Returns:
            Estimated cost in USD.
        """
        price_per_1k = self.model_prices.get(model, 0.001) # Default to 0.001 if unknown
        return (total_tokens / 1000.0) * price_per_1k

    def get_price_info(self, model: str) -> Optional[float]:
        """Get the price per 1k tokens for a model."""
        return self.model_prices.get(model)
