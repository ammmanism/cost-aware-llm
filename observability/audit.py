import logging
import json
import time
from typing import Any, Dict

logger = logging.getLogger("gateway.audit")

class AuditLogger:
    """
    Logger for security and compliance auditing.
    
    Records every interaction with the gateway including the prompt (optional),
    the model used, costs, and tenant identifiers.
    """
    @staticmethod
    def log_event(event_type: str, tenant_id: str, metadata: Dict[str, Any]):
        """
        Record an audit event to the secure log.
        """
        audit_entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            "tenant_id": tenant_id,
            "metadata": metadata
        }
        logger.info(json.dumps(audit_entry))
