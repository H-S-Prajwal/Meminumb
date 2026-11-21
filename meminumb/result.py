from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SkipReason(str, Enum):
    """Why a fact was not stored."""

    DUPLICATE = "duplicate"
    EMBED_FAILED = "embed_failed"
    INSERT_FAILED = "insert_failed"


@dataclass
class MemoryItem:
    """A successfully stored memory."""

    id: str
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SkippedItem:
    """A fact that was not stored, with a machine-readable reason."""

    content: str
    reason: SkipReason
    existing_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AddResult:
    """
    The full outcome of a Memory.add() call.

    Every fact ends up in exactly one of the three lists:
      - stored:  written to the store successfully
      - skipped: intentionally not written (e.g. duplicate)
      - failed:  write attempted but raised an error

    Nothing is ever silently dropped.
    """

    stored: list[MemoryItem] = field(default_factory=list)
    skipped: list[SkippedItem] = field(default_factory=list)
    failed: list[SkippedItem] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return len(self.failed) == 0

    def __repr__(self) -> str:
        return (
            f"AddResult(stored={len(self.stored)}, "
            f"skipped={len(self.skipped)}, "
            f"failed={len(self.failed)})"
        )
