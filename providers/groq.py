import httpx
import json
import logging
from typing import Dict, Any, AsyncIterator
from providers.base import BaseProvider
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class GroqProvider(BaseProvider):
    """
    Groq Provider for ultra-low latency inference using LPU tech.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or "your_groq_api_key"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def generate(self, prompt: str, model: str = "llama3-70b-8192", **kwargs) -> Dict[str, Any]:
        """Generate response via Groq API."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1024)
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(self.base_url, headers=self.headers, json=payload)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "provider": "groq",
                    "model": model,
                    "output": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                    "status": "success"
                }
            except Exception as e:
                logger.error(f"Groq API error: {e}")
                return {"status": "error", "error": str(e)}

    async def stream_generate(self, prompt: str, model: str = "llama3-70b-8192", **kwargs) -> AsyncIterator[str]:
        """Stream response via Groq API."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", self.base_url, headers=self.headers, json=payload) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            chunk = data["choices"][0]["delta"].get("content", "")
                            if chunk:
                                yield chunk
                        except:
                            continue
