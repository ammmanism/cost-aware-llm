from pathlib import Path

from gateway.core.cost_tracker import DEFAULT_PRICE_PER_1K_TOKENS, NexusCostTracker, TokenUsage


def write_models_config(path: Path) -> None:
    path.write_text(
        """
models:
  - name: cheap-model
    cost_per_1k_tokens: 0.002
  - name: free-model
    cost_per_1k_tokens: 0
  - name: broken-model
    cost_per_1k_tokens: -1
""".strip(),
        encoding="utf-8",
    )


def test_cost_tracker_loads_valid_prices_and_skips_negative_values(tmp_path):
    config_path = tmp_path / "models.yaml"
    write_models_config(config_path)

    tracker = NexusCostTracker(str(config_path))

    assert tracker.get_price_info("cheap-model") == 0.002
    assert tracker.get_price_info("free-model") == 0
    assert tracker.get_price_info("broken-model") is None


def test_cost_tracker_uses_default_price_for_unknown_models(tmp_path):
    tracker = NexusCostTracker(str(tmp_path / "missing.yaml"))

    assert tracker.calculate_cost("unknown-model", 1000) == DEFAULT_PRICE_PER_1K_TOKENS


def test_cost_tracker_handles_zero_and_negative_token_counts(tmp_path):
    tracker = NexusCostTracker(str(tmp_path / "missing.yaml"))

    assert tracker.calculate_cost("unknown-model", 0) == 0
    assert tracker.calculate_cost("unknown-model", -10) == 0


def test_cost_tracker_estimates_text_usage(tmp_path):
    config_path = tmp_path / "models.yaml"
    write_models_config(config_path)
    tracker = NexusCostTracker(str(config_path))

    assert tracker.estimate_tokens("one two three") == 3
    assert tracker.calculate_usage_cost("cheap-model", TokenUsage(10, 15)) == 0.00005
    assert tracker.estimate_text_cost("cheap-model", "hello world", "done") == 0.000006
