"""
Meminumb — reliable memory layer for AI agents.

Public API:
    Memory       — main class
    AddResult    — returned by Memory.add()
    SkipReason   — why a fact was not stored
    MemoryItem   — a stored memory
    SkippedItem  — a fact that was not stored, with reason
"""

from meminumb.memory import Memory
from meminumb.result import AddResult, MemoryItem, SkippedItem, SkipReason

__all__ = ["Memory", "AddResult", "MemoryItem", "SkipReason", "SkippedItem"]
__version__ = "0.3.0"
