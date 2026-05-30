import pytest

from routers.cost_aware import CostAwareRouter


@pytest.mark.asyncio
async def test_cost_router_orders_models_by_price_then_name(tmp_path):
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
models:
  - name: b-model
    cost_per_1k_tokens: 0.001
  - name: a-model
    cost_per_1k_tokens: 0.001
  - name: expensive-model
    cost_per_1k_tokens: 0.02
""".strip(),
        encoding="utf-8",
    )
    router = CostAwareRouter(str(config_path))

    models = await router.select_models({})

    assert models == ["a-model", "b-model", "expensive-model"]


@pytest.mark.asyncio
async def test_cost_router_filters_by_allowed_models_and_price_ceiling(tmp_path):
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
models:
  - name: cheap
    cost_per_1k_tokens: 0.0002
  - name: mid
    cost_per_1k_tokens: 0.002
  - name: expensive
    cost_per_1k_tokens: 0.02
""".strip(),
        encoding="utf-8",
    )
    router = CostAwareRouter(str(config_path))

    models = await router.select_models(
        {
            "allowed_models": ["mid", "expensive"],
            "max_cost_per_1k_tokens": 0.005,
        }
    )

    assert models == ["mid"]


@pytest.mark.asyncio
async def test_cost_router_falls_back_when_filters_remove_every_model(tmp_path):
    config_path = tmp_path / "models.yaml"
    config_path.write_text(
        """
models:
  - name: cheap
    cost_per_1k_tokens: 0.0002
  - name: expensive
    cost_per_1k_tokens: 0.02
""".strip(),
        encoding="utf-8",
    )
    router = CostAwareRouter(str(config_path))

    models = await router.select_models({"allowed_models": ["missing"]})

    assert models == ["cheap", "expensive"]
