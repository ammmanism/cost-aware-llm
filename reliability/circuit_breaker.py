import threading
import time
from enum import Enum


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Implements the Circuit Breaker pattern to prevent cascading failures.

    Monitors request failures and "trips" the circuit if a threshold is reached,
    blocking further requests for a recovery period. This allows the failing
    provider time to recover.
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.lock = threading.RLock()

    def allow_request(self) -> bool:
        """
        Check if a request is allowed based on the current circuit state.

        Returns:
            True if the request should proceed, False if it should be blocked.
        """
        with self.lock:
            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            else:  # HALF_OPEN
                return True

    def record_success(self) -> None:
        """
        Record a successful request. Resets the failure count and closes the circuit.
        """
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0

    def record_failure(self) -> None:
        """
        Record a failed request. May trip the circuit if the threshold is exceeded.
        """
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold or self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
