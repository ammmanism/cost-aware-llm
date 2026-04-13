# LLM Gateway

Production-grade LLM Gateway with intelligent routing, caching, fault tolerance, and multi-tenancy.

## Features

- **Routing**: Cost-aware, latency-aware, and fallback routing.
- **Caching**: In-memory TTL cache for exact prompt matches.
- **Fault Tolerance**: Retries with exponential backoff, circuit breaker pattern.
- **Multi-tenancy**: Quota management and budget enforcement.
- **Observability**: Prometheus metrics, OpenTelemetry tracing stub.
- **Load Balancing**: Round-robin and least-busy strategies.

## Architecture

```
Request → FastAPI → Router → Cache → Provider (with retry/CB) → Response
                 ↓
         Quota/Budget checks
```

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the gateway:
```bash
uvicorn gateway.server:app --reload
```

3. Send a request:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, world!", "tenant_id": "demo"}'
```

## API Usage

### POST `/generate`

Request body:
```json
{
  "prompt": "Your prompt here",
  "tenant_id": "optional-tenant-id",
  "use_cache": true
}
```

Response:
```json
{
  "model": "gpt-3.5-turbo",
  "output": "Generated response...",
  "provider": "openai",
  "latency_ms": 123.45
}
```

## Configuration

Edit `configs/models.yaml` to adjust model costs and latencies.

## Load Testing

Run Locust:
```bash
locust -f load_testing/locustfile.py --host=http://localhost:8000
```

## Observability

Prometheus metrics exposed at `/metrics` (add endpoint manually if desired).

## Testing Chaos

Import `ChaosMonkey` from `tests.chaos.kill_provider` to inject failures during testing.

## License

MIT
