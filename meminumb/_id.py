from __future__ import annotations

import hashlib


def content_id(content: str, user_id: str = "", agent_id: str = "") -> str:
    """
    Deterministic 16-char hex ID derived from the content and its scope.

    The same fact for the same user/agent always produces the same ID, so
    re-adding an identical fact is detected as a duplicate without any DB
    round-trip beyond an existence check.
    """
    key = f"{user_id}:{agent_id}:{content.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
