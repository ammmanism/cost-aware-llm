import random

class ChaosMonkey:
    """Simulate provider failures randomly."""
    def __init__(self, failure_rate: float = 0.2):
        self.failure_rate = failure_rate

    def maybe_fail(self, provider_name: str):
        if random.random() < self.failure_rate:
            raise Exception(f"Chaos Monkey killed {provider_name}")
