from typing import Any, Dict, AsyncIterator
import time
import httpx
import json
import logging
from providers.abstract import BaseProvider

logger = logging.getLogger("cost_aware_llm.providers.vllm")

class VLLMProvider(BaseProvider):
    """
    Provider implementation for locally hosted vLLM inference servers.
    
    This provider uses the OpenAI-compatible API exposed by vLLM to route requests
    to local GPUs for cost-efficient and high-throughput inference.
    """
    def __init__(self, base_url: str = "http://localhost:8000/v1", timeout: int = 60):
        self.base_url = base_url
        self.timeout = timeout

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Generate a complete response using a local vLLM instance.
        """
        start_time = time.time()
        
        payload = {
            "model": kwargs.get("model", "local-model"),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
            
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                latency = int((time.time() - start_time) * 1000)
                
                return {
                    "provider": "vllm",
                    "model": payload["model"],
                    "output": data["choices"][0]["message"]["content"],
                    "latency_ms": latency,
                    "tokens": {
                        "prompt": data.get("usage", {}).get("prompt_tokens", 0),
                        "completion": data.get("usage", {}).get("completion_tokens", 0)
                    }
                }
            except Exception as e:
                logger.error(f"vLLM generation failed: {e}")
                raise

    async def stream_generate(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        """
        Stream a response from the local vLLM instance.
        """
        payload = {
            "model": kwargs.get("model", "local-model"),
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }
        
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                data = json.loads(line[6:])
                                delta = data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    yield delta["content"]
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"vLLM streaming failed: {e}")
                raise

    @property
    def name(self) -> str:
        """The identifier for this provider."""
        return "vllm"
