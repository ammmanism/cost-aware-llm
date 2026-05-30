# Cost Controls

The gateway protects tenant budgets before and after provider calls:

- `NexusCostTracker` loads model prices from `configs/models.yaml`.
- `CostAwareRouter` can filter candidates with `allowed_models` and `max_cost_per_1k_tokens`.
- `BudgetEnforcer` rejects requests that would exceed the tenant budget.
- Successful provider calls record actual spend through the budget enforcer and Prometheus metrics.

## Pricing Config

Each model should include a stable name and `cost_per_1k_tokens`:

```yaml
models:
  - name: claude-3-haiku
    provider: anthropic
    cost_per_1k_tokens: 0.00025
    latency_ms: 500
```

Models without pricing are ignored by the cost-aware router. Models without
latency are skipped by the latency-aware router instead of forcing the whole
router into defaults.

## Budget Settings

Set the default tenant budget in `.env`:

```bash
DEFAULT_BUDGET_USD=10.0
BUDGET_REDIS_TTL_SECONDS=2592000
```

If `REDIS_URL` is set, spend is tracked in Redis with `INCRBYFLOAT`. Without
Redis, the enforcer uses in-memory tracking for local development and tests.

## Request Lifecycle

1. The gateway sanitizes the prompt and selects candidate models.
2. It estimates prompt cost for the first model and checks remaining budget.
3. On success, it records actual request cost and updates tenant spend.
4. If the tenant is out of budget, the gateway returns `402`.
