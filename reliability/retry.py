import asyncio
import functools
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def retry(max_retries: int = 3, backoff_factor: float = 0.5, exceptions: tuple = (Exception,)):
    """
    Async retry decorator with exponential backoff for resilient LLM calls.

    Args:
        max_retries: Maximum number of retry attempts.
        backoff_factor: Base factor for exponential backoff calculation.
        exceptions: Tuple of exception classes that should trigger a retry.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            """Executes the decorated function with retry logic."""
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2**attempt)
                        logger.warning(
                            f"Retrying '{func.__name__}' ({attempt + 1}/{max_retries}) "
                            f"due to {type(e).__name__}: {e}. Waiting {wait_time:.2f}s"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) reached for '{func.__name__}': {e}"
                        )
            raise last_exception

        return wrapper

    return decorator
