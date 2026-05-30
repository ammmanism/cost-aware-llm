import pytest

from routers.latency_aware import LatencyAwareRouter


@pytest.mark.asyncio
async def test_latency_router_skips_models_without_latency(tmp_path):
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
models:
  - name: fast
    latency_ms: 100
  - name: missing-latency
    cost_per_1k_tokens: 0.001
  - name: slow
    latency_ms: 900
""".strip(),
        encoding="utf-8",
    )
    router = LatencyAwareRouter(str(config_path))

    models = await router.select_models({})

    assert models == ["fast", "slow"]


@pytest.mark.asyncio
async def test_latency_router_filters_allowed_models(tmp_path):
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
models:
  - name: fast
    latency_ms: 100
  - name: slow
    latency_ms: 900
""".strip(),
        encoding="utf-8",
    )
    router = LatencyAwareRouter(str(config_path))

    models = await router.select_models({"allowed_models": ["slow"]})

    assert models == ["slow"]
