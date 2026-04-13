import functools
import time
import logging

logger = logging.getLogger(__name__)

# Stub for OpenTelemetry tracing
def trace(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        logger.debug(f"Trace start: {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start
            logger.debug(f"Trace end: {func.__name__} took {duration:.3f}s")
    return wrapper
