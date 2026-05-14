import re
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class SentinelFirewall:
    """
    Provides input validation and sanitization for LLM prompts to ensure security.

    The firewall identifies and blocks common attack vectors, including:
    - Prompt Injection: Attempts to override system instructions.
    - PII Leakage: Accidental submission of sensitive personal data (SSN, Email, etc.).
    - Resource Exhaustion: Oversized prompts designed to cause latency or high cost.
    """

    # PII patterns (extend as needed for compliance e.g., GDPR, HIPAA)
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
        "phone_us": r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    }

    # Prompt injection patterns used to detect 'jailbreak' attempts
    INJECTION_PATTERNS = [
        r"ignore\s+(?:all\s+)?previous\s+instructions",
        r"system\s*:\s*",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"\[INST\]",
        r"\[/INST\]",
        r"you\s+are\s+a\s+",
        r"pretend\s+you\s+are",
        r"act\s+as\s+if",
        r"bypass\s+",
        r"jailbreak",
    ]

    # Global request limits
    MAX_PROMPT_LENGTH = 10000  # characters
    MAX_PROMPT_LINES = 500

    @classmethod
    def validate(cls, prompt: str, tenant_id: str = "default") -> Tuple[bool, Optional[str]]:
        """
        Validate a prompt for security and policy compliance.

        Args:
            prompt: The raw input string from the user.
            tenant_id: The ID of the tenant making the request.

        Returns:
            A tuple of (is_valid, error_message).
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Prompt must be a non-empty string"

        # 1. Length & Size validation
        if len(prompt) > cls.MAX_PROMPT_LENGTH:
            return False, f"Prompt exceeds maximum length of {cls.MAX_PROMPT_LENGTH} characters"

        if prompt.count("\n") > cls.MAX_PROMPT_LINES:
            return False, f"Prompt exceeds maximum of {cls.MAX_PROMPT_LINES} lines"

        # 2. PII detection (Privacy enforcement)
        for pii_type, pattern in cls.PII_PATTERNS.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning(f"PII detected in prompt from tenant '{tenant_id}': {pii_type}")
                return (
                    False,
                    f"Security violation: Prompt contains potential {pii_type.replace('_', ' ')}",
                )

        # 3. Injection detection (Model safety)
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning(f"Injection attempt detected from tenant '{tenant_id}': {pattern}")
                return False, "Security violation: Prompt contains suspicious instructions"

        return True, None

    @classmethod
    def sanitize(cls, prompt: str) -> str:
        """
        Sanitize a prompt by removing potentially harmful characters or normalizing format.

        Args:
            prompt: The raw input string.

        Returns:
            The sanitized string.
        """
        # Remove control characters except newline and tab to prevent terminal-escape attacks
        prompt = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", prompt)

        # Normalize whitespace (collapsing multiple spaces)
        prompt = re.sub(r"\s+", " ", prompt).strip()

        return prompt
