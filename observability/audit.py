import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Configure audit logger separately
audit_logger = logging.getLogger("audit")
audit_logger.setLevel(logging.INFO)

# Prevent audit logs from propagating to root logger if needed
audit_logger.propagate = False
if not audit_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    audit_logger.addHandler(handler)

class AuditLogger:
    """Structured audit logging for compliance."""

    @staticmethod
    def log_request(
        tenant_id: str,
        request_id: str,
        endpoint: str,
        prompt_hash: str,
        prompt_length: int,
        model: str,
        status: str,
        latency_ms: float,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "llm_request",
            "tenant_id": tenant_id,
            "request_id": request_id,
            "endpoint": endpoint,
            "prompt_hash": prompt_hash,
            "prompt_length": prompt_length,
            "model": model,
            "status": status,  # success, error, cache_hit
            "latency_ms": round(latency_ms, 3),
        }
        if error:
            event["error"] = error
        if extra:
            event.update(extra)
        audit_logger.info(json.dumps(event))

    @staticmethod
    def log_admin_action(
        admin_user: str,
        action: str,
        target: str,
        details: Dict[str, Any],
        status: str = "success",
    ):
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "admin_action",
            "admin_user": admin_user,
            "action": action,
            "target": target,
            "status": status,
            "details": details,
        }
        audit_logger.info(json.dumps(event))
