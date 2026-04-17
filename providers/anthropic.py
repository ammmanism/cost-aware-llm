import os
import asyncio
import json
import logging
from typing import Dict, Any, AsyncIterator
from providers.base import BaseProvider
from failure_handling.retry import retry
from failure_handling.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

class AnthropicProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        self.default_model = "claude-3-haiku-20240307"

    @retry(max_retries=2, backoff_factor=1.0)
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        model = kwargs.get("model", self.default_model)
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker OPEN for Anthropic")

        try:
            if not self.api_key:
                await asyncio.sleep(0.15)
                output = f"[Anthropic Mock] {prompt[:50]}..."
                self.circuit_breaker.record_success()
                return {
                    "provider": "anthropic",
                    "model": model,
                    "output": output,
                    "status": "success"
                }

            import httpx
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": model,
                "max_tokens": kwargs.get("max_tokens", 1024),
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                output = data["content"][0]["text"]

            self.circuit_breaker.record_success()
            return {
                "provider": "anthropic",
                "model": model,
                "output": output,
                "status": "success"
            }
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Anthropic error: {e}")
            raise

    async def stream_generate(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        model = kwargs.get("model", self.default_model)
        if not self.circuit_breaker.allow_request():
            raise Exception("Circuit breaker OPEN for Anthropic")

        try:
            if not self.api_key:
                for word in ["Mock", " ", "streaming", " ", "response"]:
                    yield word
                    await asyncio.sleep(0.05)
                return

            import httpx
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            payload = {
                "model": model,
                "max_tokens": kwargs.get("max_tokens", 1024),
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                event = json.loads(data)
                                if event.get("type") == "content_block_delta":
                                    yield event["delta"]["text"]
                                elif event.get("type") == "message_stop":
                                    break
                            except json.JSONDecodeError:
                                continue

            self.circuit_breaker.record_success()
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(f"Anthropic streaming error: {e}")
            raise
