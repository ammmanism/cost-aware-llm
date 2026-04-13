# LLM Gateway Platform

A production-grade LLM Gateway system designed for high availability, cost-efficiency, and observability.

## Architecture

The system acts as a unified entry point for multiple LLM providers (OpenAI, Anthropic, etc.).

- **Intelligent Routing**: Cost-aware, latency-aware, and fallback routing strategies.
- **Resiliency**: Circuit breakers and exponential backoff retries.
- **Caching**: Multi-level caching (exact and semantic).
- **Multi-tenancy**: Quota management and budget enforcement.
- **Observability**: Prometheus metrics and OpenTelemetry tracing.

## Quick Start

1. Install dependencies:
   ```bash
   make install
   ```
2. Configure environment:
   ```bash
   cp .env.example .env
   # Add your API keys
   ```
3. Run the gateway:
   ```bash
   make run
   ```

## API Usage

```bash
curl -X POST http://localhost:8000/generate \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "Hello, world!",
       "router": "cost_aware"
     }'
```
