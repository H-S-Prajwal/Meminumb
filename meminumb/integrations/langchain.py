"""
LangChain integration for Meminumb.

Provides MeminumbChatHistory — a drop-in replacement for any
LangChain chat message history backend.

Install:
    pip install meminumb[langchain]

Usage::

    from meminumb.integrations.langchain import MeminumbChatHistory
    from langchain.chains import ConversationChain
    from langchain_openai import ChatOpenAI

    history = MeminumbChatHistory(user_id="alice", db_path="~/.meminumb/alice.db")

    # Use with any LangChain chain
    from langchain_core.runnables.history import RunnableWithMessageHistory
    chain = RunnableWithMessageHistory(your_chain, lambda sid: history)
"""

from __future__ import annotations

from typing import Optional

try:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
except ImportError as exc:
    raise ImportError(
        "LangChain integration requires langchain-core. "
        "Install it with:  pip install meminumb[langchain]"
    ) from exc

from meminumb.memory import Memory


class MeminumbChatHistory(BaseChatMessageHistory):
    """
    LangChain-compatible chat message history backed by Meminumb.

    Stores every human and AI message as a memory, scoped to a user_id.
    Messages survive across sessions — restart your agent and the full
    conversation history is still there.

    Args:
        user_id:  Scope messages to a specific user or session.
        db_path:  Path to the SQLite file. Defaults to in-memory.

    Example::

        history = MeminumbChatHistory(user_id="alice", db_path="~/.meminumb/alice.db")
        history.add_user_message("Hi, I'm Alice")
        history.add_ai_message("Hello Alice!")
        print(history.messages)
    """

    def __init__(
        self,
        user_id: str = "default",
        db_path: str = ":memory:",
        mem: Optional[Memory] = None,
    ) -> None:
        self.user_id = user_id
        self._mem = mem or Memory(db_path=db_path)
        self._message_prefix = "__msg__"

    @property
    def messages(self) -> list[BaseMessage]:
        """Return all messages for this user in insertion order."""
        items = self._mem.get_all(user_id=self.user_id)
        # Filter only message items and sort by creation order via ID
        msg_items = [i for i in items if i.content.startswith(self._message_prefix)]
        result = []
        for item in msg_items:
            raw = item.content[len(self._message_prefix):]
            role, _, rest = raw.partition(":")
            _, _, text = rest.partition(":")  # strip timestamp
            if role == "human":
                result.append(HumanMessage(content=text))
            elif role == "ai":
                result.append(AIMessage(content=text))
        return result

    def add_message(self, message: BaseMessage) -> None:
        """Store a LangChain message in Meminumb."""
        if isinstance(message, HumanMessage):
            role = "human"
        elif isinstance(message, AIMessage):
            role = "ai"
        else:
            return

        # Prefix + role + text makes each message uniquely content-addressed
        import time
        content = f"{self._message_prefix}{role}:{time.time_ns()}:{message.content}"
        self._mem.add([content], user_id=self.user_id)

    def clear(self) -> None:
        """Delete all messages for this user."""
        self._mem.clear(user_id=self.user_id)
