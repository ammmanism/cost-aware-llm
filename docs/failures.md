# Failure Management

- **Provider Outage**: Detected by Circuit Breaker, trips to OPEN state.
- **Rate Limits**: Handled by exponential backoff retry.
- **Cache Miss**: Failover to provider with background cache populate.
