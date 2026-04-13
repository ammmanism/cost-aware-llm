import asyncio
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def retry(max_retries: int = 3, backoff_factor: float = 0.5, exceptions: tuple = (Exception,)):
    """
    Async retry decorator with exponential backoff.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Retry {attempt+1}/{max_retries} after error: {e}. Waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Max retries ({max_retries}) exceeded: {e}")
            raise last_exception
        return wrapper
    return decorator
