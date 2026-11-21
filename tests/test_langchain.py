"""Tests for the LangChain MeminumbChatHistory integration."""

import pytest

langchain_core = pytest.importorskip("langchain_core", reason="langchain-core not installed")

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402

from meminumb.integrations.langchain import MeminumbChatHistory  # noqa: E402


def make_history(user_id: str = "test_user") -> MeminumbChatHistory:
    return MeminumbChatHistory(user_id=user_id, db_path=":memory:")


def test_empty_history():
    h = make_history()
    assert h.messages == []


def test_add_human_message():
    h = make_history()
    h.add_user_message("Hello!")
    msgs = h.messages
    assert len(msgs) == 1
    assert isinstance(msgs[0], HumanMessage)
    assert msgs[0].content == "Hello!"


def test_add_ai_message():
    h = make_history()
    h.add_ai_message("Hi there!")
    msgs = h.messages
    assert len(msgs) == 1
    assert isinstance(msgs[0], AIMessage)
    assert msgs[0].content == "Hi there!"


def test_mixed_messages_order():
    h = make_history()
    h.add_user_message("What is 2+2?")
    h.add_ai_message("It's 4.")
    h.add_user_message("Thanks!")
    msgs = h.messages
    assert len(msgs) == 3
    assert isinstance(msgs[0], HumanMessage)
    assert isinstance(msgs[1], AIMessage)
    assert isinstance(msgs[2], HumanMessage)
    assert msgs[0].content == "What is 2+2?"
    assert msgs[1].content == "It's 4."
    assert msgs[2].content == "Thanks!"


def test_clear_removes_all_messages():
    h = make_history()
    h.add_user_message("Hello!")
    h.add_ai_message("Hi!")
    h.clear()
    assert h.messages == []


def test_add_message_with_langchain_objects():
    h = make_history()
    h.add_message(HumanMessage(content="Direct HumanMessage"))
    h.add_message(AIMessage(content="Direct AIMessage"))
    msgs = h.messages
    assert len(msgs) == 2
    assert msgs[0].content == "Direct HumanMessage"
    assert msgs[1].content == "Direct AIMessage"


def test_scoped_to_user_id():
    alice = make_history("alice")
    bob = make_history("bob")

    alice.add_user_message("I'm Alice")
    bob.add_user_message("I'm Bob")

    alice_msgs = alice.messages
    bob_msgs = bob.messages

    assert len(alice_msgs) == 1
    assert alice_msgs[0].content == "I'm Alice"
    assert len(bob_msgs) == 1
    assert bob_msgs[0].content == "I'm Bob"


def test_duplicate_messages_stored_separately():
    """Same content sent twice must both appear — timestamps make them distinct."""
    import time

    h = make_history()
    h.add_user_message("Hello!")
    time.sleep(0.001)  # ensure different time_ns
    h.add_user_message("Hello!")
    msgs = h.messages
    assert len(msgs) == 2


def test_shared_memory_instance():
    """Two MeminumbChatHistory objects sharing one Memory see the same data."""
    from meminumb.memory import Memory

    mem = Memory(db_path=":memory:")
    h1 = MeminumbChatHistory(user_id="shared", mem=mem)
    h2 = MeminumbChatHistory(user_id="shared", mem=mem)

    h1.add_user_message("Written via h1")
    msgs = h2.messages
    assert len(msgs) == 1
    assert msgs[0].content == "Written via h1"
