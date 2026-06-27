import httpx
import json
import logging
import time
from typing import Dict, Any, AsyncIterator
from .abstract import BaseProvider

logger = logging.getLogger("cost_aware_llm.providers.ollama")

class OllamaProvider(BaseProvider):
    """
    Integration with local Ollama models.
    Supports completely free, localized inference.
    """
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434", timeout: int = 60):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    async def generate(self, prompt: str, **kwargs: Any) -> Dict[str, Any]:
        start_time = time.time()
        
        payload = {
            "model": kwargs.get("model", self.model),
            "prompt": prompt,
            "stream": False
        }
        
        # Apply temperature if provided
        if "temperature" in kwargs:
            payload["options"] = {"temperature": kwargs["temperature"]}
            
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.base_url}/api/generate", json=payload)
                response.raise_for_status()
                data = response.json()
                
                latency = int((time.time() - start_time) * 1000)
                
                return {
                    "provider": "ollama",
                    "model": payload["model"],
                    "output": data.get("response", ""),
                    "latency_ms": latency,
                    "tokens": {
                        "prompt": data.get("prompt_eval_count", 0),
                        "completion": data.get("eval_count", 0)
                    }
                }
            except Exception as e:
                logger.error(f"Ollama generation failed: {e}")
                raise

    async def stream_generate(self, prompt: str, **kwargs: Any) -> AsyncIterator[str]:
        payload = {
            "model": kwargs.get("model", self.model),
            "prompt": prompt,
            "stream": True
        }
        
        if "temperature" in kwargs:
            payload["options"] = {"temperature": kwargs["temperature"]}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"Ollama streaming failed: {e}")
                raise
