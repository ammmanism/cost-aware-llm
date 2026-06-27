import httpx
from typing import Optional, Dict, Any, AsyncIterator

class Client:
    """Synchronous client for cost-aware-llm."""
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=120.0
        )

    def generate(
        self, 
        prompt: Optional[str] = None, 
        template_id: Optional[str] = None, 
        variables: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None, 
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate a response synchronously."""
        payload = {
            "use_cache": use_cache,
            "stream": False
        }
        if prompt:
            payload["prompt"] = prompt
        if template_id:
            payload["template_id"] = template_id
        if variables:
            payload["variables"] = variables
        if model:
            payload["model"] = model

        response = self.client.post(f"{self.base_url}/generate", json=payload)
        response.raise_for_status()
        return response.json()

class AsyncClient:
    """Asynchronous client for cost-aware-llm."""
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=120.0
        )

    async def generate(
        self, 
        prompt: Optional[str] = None, 
        template_id: Optional[str] = None, 
        variables: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None, 
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Generate a response asynchronously."""
        payload = {
            "use_cache": use_cache,
            "stream": False
        }
        if prompt:
            payload["prompt"] = prompt
        if template_id:
            payload["template_id"] = template_id
        if variables:
            payload["variables"] = variables
        if model:
            payload["model"] = model

        response = await self.client.post(f"{self.base_url}/generate", json=payload)
        response.raise_for_status()
        return response.json()
