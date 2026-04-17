import os
import asyncio
import json
import logging
from typing import Dict, Any, AsyncIterator
from providers.base import BaseProvider
from failure_handling.retry import retry
from failure_handling.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

class GeminiProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.default_model = "gemini-1.5-flash"

    @retry(max_retries=2, backoff_factor=1.0)
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        model = kwargs.get("model", self.default_model)
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker OPEN for Gemini")

        try:
            if not self.api_key:
                await asyncio.sleep(0.12)
                output = f"[Gemini Mock] {prompt[:50]}..."
                self.circuit_breaker.record_success()
                return {
                    "provider": "google",
                    "model": model,
                    "output": output,
                    "status": "success"
                }

            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": kwargs.get("max_tokens", 1024),
                    "temperature": kwargs.get("temperature", 0.7)
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                output = data["candidates"][0]["content"]["parts"][0]["text"]

            self.circuit_breaker.record_success()
            return {
                "provider": "google",
                "model": model,
                "output": output,
                "status": "success"
            }
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Gemini error: {e}")
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        model = kwargs.get("model", self.default_model)
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker OPEN for Gemini")

        try:
            if not self.api_key:
                for word in ["Mock", " ", "Gemini", " ", "stream"]:
                    yield word
                    await asyncio.sleep(0.05)
                return

            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?key={self.api_key}&alt=sse"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": kwargs.get("max_tokens", 1024),
                    "temperature": kwargs.get("temperature", 0.7)
                }
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                chunk = json.loads(data)
                                if "candidates" in chunk:
                                    for candidate in chunk["candidates"]:
                                        if "content" in candidate:
                                            for part in candidate["content"]["parts"]:
                                                if "text" in part:
                                                    yield part["text"]
                            except json.JSONDecodeError:
                                continue

            self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Gemini streaming error: {e}")
            raise
