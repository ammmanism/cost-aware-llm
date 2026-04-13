# Architecture

The LLM Gateway is designed to provide a unified API layer over multiple LLM providers.

## Components

1. **FastAPI Server**: Handles incoming HTTP requests.
2. **Middleware**:
   - `AuthMiddleware`: Validates API keys.
   - `RateLimitMiddleware`: Prevents abuse.
   - `LoggingMiddleware`: Records request details.
3. **Routers**:
   - `CostAwareRouter`: Minimizes token costs.
   - `LatencyAwareRouter`: Minimizes response time.
   - `FallbackRouter`: Ensures high availability.
4. **Caching Layer**:
   - In-memory Exact Cache.
   - Semantic Cache (Redis/Vector Store).
5. **Resiliency Layer**:
   - `CircuitBreaker`: Stops requests to failing providers.
   - `Retry`: Exponential backoff for transient errors.
6. **Multi-tenancy**:
   - `QuotaManager`: Limits total requests per user.
   - `BudgetEnforcer`: Limits spend per user.
