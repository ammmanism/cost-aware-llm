import asyncio
from typing import AsyncIterator, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class BackpressureStreamHandler:
    """
    Handles streaming with backpressure to prevent overwhelming slow clients.
    """
    
    def __init__(self, max_buffer_size: int = 100, check_interval: float = 0.01):
        self.max_buffer_size = max_buffer_size
        self.check_interval = check_interval
    
    async def process_stream(
        self,
        generator: AsyncIterator[str]
    ) -> AsyncIterator[str]:
        """
        Wraps a generator with backpressure control.
        Yields chunks only when buffer has space.
        """
        buffer = []
        async for chunk in generator:
            buffer.append(chunk)
            if len(buffer) >= self.max_buffer_size:
                # Flow control: yield the whole buffer
                for item in buffer:
                    yield item
                buffer.clear()
                # Yield to the event loop to prevent blocking
                await asyncio.sleep(0)
        
        # Yield remaining chunks
        for item in buffer:
            yield item
