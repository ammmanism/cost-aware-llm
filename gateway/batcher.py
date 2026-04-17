import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
import time
import logging

logger = logging.getLogger(__name__)

@dataclass
class BatchRequest:
    prompt: str
    tenant_id: str
    future: asyncio.Future
    timestamp: float

class RequestBatcher:
    """
    Batches multiple small requests to the same model to reduce API overhead.
    """
    
    def __init__(
        self,
        max_batch_size: int = 10,
        max_wait_ms: int = 100,
        min_prompt_length: int = 100  # Only batch small prompts
    ):
        self.max_batch_size = max_batch_size
        self.max_wait_seconds = max_wait_ms / 1000
        self.min_prompt_length = min_prompt_length
        
        self._batches: Dict[str, List[BatchRequest]] = {}  # model -> pending requests
        self._locks: Dict[str, asyncio.Lock] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        
    async def submit(
        self,
        model: str,
        prompt: str,
        tenant_id: str,
        generate_func: Callable[[str, str], Any]
    ) -> Any:
        """
        Submit a request. If batching is applicable, it may be delayed.
        Returns the generated response.
        """
        # Only batch if prompt is small
        if len(prompt) > self.min_prompt_length:
            # Process immediately
            return await generate_func(model, prompt)
        
        # Get or create lock for this model
        if model not in self._locks:
            self._locks[model] = asyncio.Lock()
        lock = self._locks[model]
        
        future = asyncio.Future()
        batch_req = BatchRequest(
            prompt=prompt,
            tenant_id=tenant_id,
            future=future,
            timestamp=time.time()
        )
        
        async with lock:
            if model not in self._batches:
                self._batches[model] = []
            self._batches[model].append(batch_req)
            
            # If batch reached size, process immediately
            if len(self._batches[model]) >= self.max_batch_size:
                if model in self._tasks and not self._tasks[model].done():
                    self._tasks[model].cancel()
                self._tasks[model] = asyncio.create_task(self._process_batch(model, generate_func))
            else:
                # Schedule processing after max wait
                if model not in self._tasks or self._tasks[model].done():
                    self._tasks[model] = asyncio.create_task(self._delayed_process(model, generate_func))
        
        return await future
    
    async def _delayed_process(self, model: str, generate_func: Callable):
        await asyncio.sleep(self.max_wait_seconds)
        async with self._locks[model]:
            if self._batches.get(model):
                await self._process_batch(model, generate_func)
    
    async def _process_batch(self, model: str, generate_func: Callable):
        batch = self._batches.pop(model, [])
        if not batch:
            return
        
        logger.info(f"Processing batch of {len(batch)} requests for model {model}")
        
        try:
            # For simplicity, process sequentially but could do true batching with some providers
            for req in batch:
                try:
                    result = await generate_func(model, req.prompt)
                    req.future.set_result(result)
                except Exception as e:
                    if not req.future.done():
                        req.future.set_exception(e)
        except Exception as e:
            for req in batch:
                if not req.future.done():
                    req.future.set_exception(e)
