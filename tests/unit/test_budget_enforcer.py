import pytest

from multi_tenant.budget_enforcer import BudgetEnforcer


@pytest.mark.asyncio
async def test_budget_enforcer_tracks_spend_in_memory(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    enforcer = BudgetEnforcer(default_budget=1.0)

    assert await enforcer.check_budget("tenant-a", 0.25)

    await enforcer.add_cost("tenant-a", 0.25)

    assert await enforcer.get_spend("tenant-a") == 0.25
    assert await enforcer.get_remaining_budget("tenant-a") == 0.75
    assert not await enforcer.check_budget("tenant-a", 0.80)


@pytest.mark.asyncio
async def test_budget_enforcer_rejects_negative_values(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    enforcer = BudgetEnforcer(default_budget=1.0)

    with pytest.raises(ValueError):
        await enforcer.check_budget("tenant-a", -0.01)

    with pytest.raises(ValueError):
        await enforcer.add_cost("tenant-a", -0.01)
