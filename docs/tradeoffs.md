# Tradeoffs

- **Memory vs. Redis Caching**: In-memory is faster but doesn't persist across restarts or scale horizontally. Redis is preferred for production.
- **Semantic vs. Exact Cache**: Semantic cache saves more money but introduces embedding latency and potential accuracy issues.
- **Latency vs. Cost Routing**: Cheapest models are often slowest and least capable.
