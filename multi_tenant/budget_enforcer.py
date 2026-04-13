from typing import Dict

class BudgetEnforcer:
    def __init__(self):
        # tenant_id -> spent (USD)
        self._spending: Dict[str, float] = {}
        self.default_budget = 10.0  # USD per month

    def check_budget(self, tenant_id: str, estimated_cost: float) -> bool:
        current = self._spending.get(tenant_id, 0.0)
        return (current + estimated_cost) <= self.default_budget

    def add_cost(self, tenant_id: str, cost: float):
        if tenant_id not in self._spending:
            self._spending[tenant_id] = 0.0
        self._spending[tenant_id] += cost
