from typing import List

class FallbackRouter:
    """Handles fallback ordering for models."""

    def get_fallback_chain(self, models: List[str]) -> List[str]:
        """
        Return a fallback chain. In simple case, just return the input list.
        Could be extended to add extra fallback models.
        """
        # Ensure we have at least one fallback model even if list empty
        if not models:
            return ["gpt-3.5-turbo"]
        # Add a default fallback at the end if not present
        chain = list(models)
        if "gpt-3.5-turbo" not in chain:
            chain.append("gpt-3.5-turbo")
        return chain
