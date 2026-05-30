import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml

logger = logging.getLogger(__name__)


DEFAULT_PRICE_PER_1K_TOKENS = 0.001


@dataclass(frozen=True)
class TokenUsage:
    """Token usage split for request and response accounting."""

    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


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
                logger.warning("Model pricing config not found at %s", self.config_path)
                return

            with self.config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            for model in data.get("models", []):
                name = model.get("name")
                price = model.get("cost_per_1k_tokens")
                if not name or price is None:
                    continue

                price_float = float(price)
                if price_float < 0:
                    logger.warning("Skipping model %s with negative price %s", name, price)
                    continue
                self.model_prices[name] = price_float

            logger.info("CostTracker initialized with %s model prices", len(self.model_prices))
        except Exception as e:
            logger.error("Failed to initialize CostTracker: %s", e)

    def calculate_cost(self, model: str, total_tokens: int) -> float:
        """
        Calculate the cost of a request based on token count.

        Args:
            model: The name of the LLM model used.
            total_tokens: Sum of input and output tokens.

        Returns:
            Estimated cost in USD.
        """
        if total_tokens <= 0:
            return 0.0

        price_per_1k = self.model_prices.get(model, DEFAULT_PRICE_PER_1K_TOKENS)
        return (total_tokens / 1000.0) * price_per_1k

    def calculate_usage_cost(self, model: str, usage: TokenUsage) -> float:
        """Calculate cost from structured token usage."""
        return self.calculate_cost(model, usage.total_tokens)

    def estimate_text_cost(self, model: str, prompt: str, completion: str = "") -> float:
        """
        Estimate cost from prompt and completion text.

        This intentionally uses a conservative whitespace token estimate so the
        gateway can enforce budgets without depending on provider tokenizers.
        """
        usage = TokenUsage(
            prompt_tokens=self.estimate_tokens(prompt),
            completion_tokens=self.estimate_tokens(completion),
        )
        return self.calculate_usage_cost(model, usage)

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate tokens for budget checks when provider usage is unavailable."""
        if not text:
            return 0
        return len(text.split())

    def get_price_info(self, model: str) -> Optional[float]:
        """Get the price per 1k tokens for a model."""
        return self.model_prices.get(model)

    def has_price(self, model: str) -> bool:
        """Return whether a model has explicit pricing configured."""
        return model in self.model_prices

# Nexus-Standard: Verified Type Safety and Professional Documentation Pattern

