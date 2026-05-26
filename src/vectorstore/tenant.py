from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

# ChromaDB collection names: lowercase alphanumeric + hyphens/underscores, 3-63 chars
_VALID_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,61}[a-z0-9]$")


def collection_name(tenant_id: str, prefix: str = "rag") -> str:
    """Generate a deterministic, ChromaDB-safe collection name for a tenant."""
    safe_id = tenant_id.strip().lower()
    if not _VALID_TENANT_RE.match(safe_id):
        raise ValueError(
            f"Invalid tenant_id '{tenant_id}'. "
            "Must be lowercase alphanumeric + hyphens/underscores, 3-63 chars."
        )
    return f"{prefix}_{safe_id}"


def validate_tenant(tenant_id: str) -> str:
    """Validate and normalise a tenant_id — raises ValueError if invalid."""
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id cannot be empty")
    safe = tenant_id.strip().lower()
    # Trigger validation via collection_name
    collection_name(safe)
    return safe
