import os
import asyncio
import json
import logging
from typing import Dict, Any, AsyncIterator
from providers.base import BaseProvider
from failure_handling.retry import retry
from failure_handling.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

class OpenAIProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.default_model = "gpt-3.5-turbo"

    @retry(max_retries=3, backoff_factor=0.5)
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        model = kwargs.get("model", self.default_model)
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker is OPEN")

        try:
            if not self.api_key:
                await asyncio.sleep(0.1)
                output = f"[OpenAI Mock] Response to: {prompt[:50]}..."
                self.circuit_breaker.record_success()
                return {
                    "provider": "openai",
                    "model": model,
                    "output": output,
                    "status": "success"
                }

            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.7),
                "stream": False
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                output = data["choices"][0]["message"]["content"]

            self.circuit_breaker.record_success()
            return {
                "provider": "openai",
                "model": model,
                "output": output,
                "status": "success"
            }
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"OpenAI provider error: {e}")
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        model = kwargs.get("model", self.default_model)
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker is OPEN")

        try:
            if not self.api_key:
                # Mock streaming
                words = prompt.split()[:5] + ["...", "mock", "stream", "response"]
                for word in words:
                    yield word + " "
                    await asyncio.sleep(0.05)
                return

            import httpx
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": kwargs.get("max_tokens", 1024),
                "temperature": kwargs.get("temperature", 0.7),
                "stream": True
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                if chunk["choices"][0].get("delta", {}).get("content"):
                                    yield chunk["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                continue

            self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"OpenAI streaming error: {e}")
            raise