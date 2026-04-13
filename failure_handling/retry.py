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
            delay *= factor