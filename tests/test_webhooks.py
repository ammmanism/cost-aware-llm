import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from observability.webhooks import webhook_manager

@pytest.mark.asyncio
async def test_webhook_manager_registration():
    webhook_manager.register_endpoint("quota_exceeded", "http://example.com/webhook")
    assert "quota_exceeded" in webhook_manager.endpoints
    assert "http://example.com/webhook" in webhook_manager.endpoints["quota_exceeded"]

@pytest.mark.asyncio
@patch('httpx.AsyncClient.post', new_callable=AsyncMock)
async def test_webhook_manager_fire_event(mock_post):
    webhook_manager.endpoints = {} # reset
    webhook_manager.register_endpoint("test_event", "http://example.com/webhook")
    
    await webhook_manager.fire_event("test_event", {"key": "value"})
    
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://example.com/webhook"
    assert kwargs["json"] == {"key": "value", "event": "test_event"}
