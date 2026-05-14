import time
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class NexusROI:
    cost_saved: float = 0.0
    latency_penalty_ms: float = 0.0
    requests_optimized: int = 0

class NexusStatsManager:
    """
    Advanced observability for the Nexus Gateway ROI.
    
    Calculates cost efficiency by comparing the selected model's cost 
    against a hypothetical 'expensive-only' baseline (e.g., GPT-4).
    """
    def __init__(self, baseline_model: str = "gpt-4"):
        self.baseline_model = baseline_model
        self.stats = NexusROI()
        self._history: List[Dict[str, Any]] = []

    def record_optimization(self, selected_model: str, actual_cost: float, actual_latency: float, baseline_cost: float):
        """Record the impact of a routed request."""
        savings = max(0, baseline_cost - actual_cost)
        self.stats.cost_saved += savings
        self.stats.requests_optimized += 1
        
        # We track history for windowed analytics
        self._history.append({
            "timestamp": time.time(),
            "model": selected_model,
            "savings": savings,
            "latency": actual_latency
        })
        
        # Keep history manageable
        if len(self._history) > 1000:
            self._history.pop(0)

    def get_summary(self) -> Dict[str, Any]:
        """Return a high-level summary of gateway performance."""
        return {
            "total_cost_saved": round(self.stats.cost_saved, 6),
            "requests_optimized": self.stats.requests_optimized,
            "avg_savings_per_request": round(self.stats.cost_saved / max(1, self.stats.requests_optimized), 6),
            "efficiency_rating": "GOAT" if self.stats.cost_saved > 0 else "Baseline"
        }
