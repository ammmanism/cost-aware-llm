import re
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

class InputGuard:
    """
    Input validation and sanitization for LLM prompts.
    Prevents prompt injection, PII leakage, and oversized requests.
    """

    # PII patterns (extend as needed for compliance)
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
        "phone_us": r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    }

    # Prompt injection patterns
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

    # Default limits
    MAX_PROMPT_LENGTH = 10000  # characters
    MAX_PROMPT_LINES = 500

    @classmethod
    def validate(cls, prompt: str, tenant_id: str = "default") -> Tuple[bool, Optional[str]]:
        """
        Validate prompt for security and policy compliance.
        Returns (is_valid, error_message).
        """
        if not prompt or not isinstance(prompt, str):
            return False, "Prompt must be a non-empty string"

        # Length check
        if len(prompt) > cls.MAX_PROMPT_LENGTH:
            return False, f"Prompt exceeds maximum length of {cls.MAX_PROMPT_LENGTH} characters"

        # Line count check
        if prompt.count('\n') > cls.MAX_PROMPT_LINES:
            return False, f"Prompt exceeds maximum of {cls.MAX_PROMPT_LINES} lines"

        # PII detection
        for pii_type, pattern in cls.PII_PATTERNS.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning(f"PII detected in prompt from tenant {tenant_id}: {pii_type}")
                return False, f"Prompt contains potential {pii_type.replace('_', ' ')}"

        # Injection detection
        for pattern in cls.INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                logger.warning(f"Injection pattern detected in prompt from tenant {tenant_id}: {pattern}")
                return False, "Prompt contains suspicious instructions"

        return True, None

    @classmethod
    def sanitize(cls, prompt: str) -> str:
        """
        Sanitize prompt by removing or masking sensitive content.
        Currently a simple pass-through; extend for production needs.
        """
        # Remove control characters except newline and tab
        prompt = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', prompt)
        # Normalize whitespace
        prompt = re.sub(r'\s+', ' ', prompt).strip()
        return prompt
