from typing import List, Dict, Any
from routers.base import BaseRouter

class FallbackRouter(BaseRouter):
    """
    Goat-tier fallback orchestrator.
    
    Ensures that every request has a viable path to completion by 
    appending resilient models to the selection chain.
    """

    async def select_models(self, request_data: Dict[str, Any]) -> List[str]:
        """
        Return a fallback chain.
        
        Args:
            request_data: Contains 'models' key with the initial selection.
        """
        models = request_data.get("models", [])
        if not models:
            return ["gpt-3.5-turbo"]
            
        # Ensure gpt-3.5-turbo is at the end as a final catch-all
        chain = list(models)
        if "gpt-3.5-turbo" not in chain:
            chain.append("gpt-3.5-turbo")
            
        return chain

