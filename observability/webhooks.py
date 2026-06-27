import httpx
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("cost_aware_llm.webhooks")

class WebhookManager:
    def __init__(self):
        self.endpoints = {}
        # Assuming typical timeout
        self.client = httpx.AsyncClient(timeout=5.0)

    def register_endpoint(self, event_type: str, url: str):
        """Register a webhook URL for a specific event type."""
        if event_type not in self.endpoints:
            self.endpoints[event_type] = []
        self.endpoints[event_type].append(url)
        logger.info(f"Registered webhook for {event_type} at {url}")

    async def fire_event(self, event_type: str, payload: Dict[str, Any]):
        """Fire an event to all registered webhook endpoints."""
        if event_type not in self.endpoints:
            return
            
        urls = self.endpoints[event_type]
        if not urls:
            return

        payload["event"] = event_type
        
        async def send_webhook(url: str):
            try:
                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                logger.debug(f"Webhook {event_type} delivered to {url}")
            except Exception as e:
                logger.error(f"Failed to deliver webhook {event_type} to {url}: {e}")

        # Fire and forget
        tasks = [send_webhook(url) for url in urls]
        await asyncio.gather(*tasks, return_exceptions=True)

# Global webhook manager
webhook_manager = WebhookManager()
