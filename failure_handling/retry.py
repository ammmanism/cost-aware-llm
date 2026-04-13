import asyncio
from typing import Callable, Any, Type
import logging

logger = logging.getLogger(__name__)

async def retry_with_backoff(
    func: Callable,
    retries: int = 3,
    initial_delay: float = 1.0,
    factor: float = 2.0,
    exceptions: Type[Exception] = Exception
) -> Any:
    delay = initial_delay
    for i in range(retries):
        try:
            return await func()
        except exceptions as e:
            if i == retries - 1:
                raise e
            logger.warning(f"Retry {i+1} failing with error: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            delay *= factor# Retry logic 1
# Retry logic 2
# Retry logic 3
# Retry logic 4
# Retry logic 5
# Retry logic 6
# Retry logic 7
# Retry logic 8
# Retry logic 9
