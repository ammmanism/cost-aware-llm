import asyncio
from enum import Enum
from typing import Callable, Any, Optional
import time

class State(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = State.CLOSED
        self.failures = 0
        self.last_failure_time: Optional[float] = None

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = State.OPEN

    def record_success(self):
        self.failures = 0
        self.state = State.CLOSED

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == State.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = State.HALF_OPEN
            else:
                raise Exception("Circuit is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == State.HALF_OPEN:
                self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            raise e# CB State 21
# CB State 22
# CB State 23
# CB State 24
# CB State 25
# CB State 26
# CB State 27
# CB State 28
# CB State 29
