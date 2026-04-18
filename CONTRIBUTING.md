# Contributing to LLM Gateway Platform

First of all, thank you for investing your time in contributing to our high-performance AI infrastructure! 

## Engineering Philosophy
This project operates on **Goat Tier** backend standards. We prioritize:
1. **Mathematical Certainty**: No race conditions. Rate limiters use Redis Lua scripts. Budgets use atomic float ops.
2. **Resilience**: Assume upstream components fail. Every LLM provider API call must be wrapped in an adaptive circuit breaker and multi-armed bandit fallback policy.
3. **Zero-Trust Input**: Never pass a raw user prompt to a provider without streaming it through `security/input_guard.py`.

## Development Workflow

### 1. Branch Naming Conventions
*   `feat/` - for new features (e.g., `feat/milvus-vector-store`)
*   `fix/` - for bug fixes (e.g., `fix/redis-conn-timeout`)
*   `perf/` - for performance optimizations
*   `docs/` - for documentation

### 2. Linting & Typing
We use `ruff` for linting and `mypy` for static type checking. 
Before submitting a PR, ensure your code passes our strict checks:
```bash
make lint
make test
```

### 3. Adding New LLM Providers
All LLM providers must inherit from `BaseProvider` in `providers/base.py`.
You **must** implement both:
- `generate()`
- `stream_generate()` (Yielding SSE chunks)

Add your new provider to the `ProviderFactory` and ensure you have included chaos testing stubs via the global `ChaosController`.

## Pull Request Process
1. Update the `README.md` with details of changes to the interface or architecture, if applicable.
2. Ensure new metrics and OpenTelemetry spans are added for new functions.
3. Your PR requires at least 1 approval from a core maintainer before merging. All CI workflows (Bandit, Mypy, Ruff, Pytest) must pass.
