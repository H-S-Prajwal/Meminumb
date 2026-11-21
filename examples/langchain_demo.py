"""
LangChain integration demo — Meminumb as a persistent chat memory backend.

Install:
    pip install meminumb[langchain] langchain-groq

Set env var:
    export GROQ_API_KEY="your-key-here"

Run:
    python examples/langchain_demo.py

Quit and run again — the full conversation history is restored from Meminumb.
"""

import os
import sys

try:
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.runnables.history import RunnableWithMessageHistory
    from langchain_groq import ChatGroq
except ImportError:
    print("Missing packages. Install with:")
    print("  pip install meminumb[langchain] langchain-groq")
    sys.exit(1)

from pathlib import Path

from meminumb.integrations.langchain import MeminumbChatHistory

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("Error: GROQ_API_KEY not set.")
    sys.exit(1)

# ── Setup ─────────────────────────────────────────────────────────────────────

DB_PATH = str(Path.home() / ".meminumb" / "langchain_demo.db")
SESSION_ID = "demo_session"

llm = ChatGroq(model="llama-3.1-8b-instant", api_key=api_key)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant with a good memory."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | llm

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: MeminumbChatHistory(
        user_id=session_id,
        db_path=DB_PATH,
    ),
    input_messages_key="input",
    history_messages_key="history",
)

config = {"configurable": {"session_id": SESSION_ID}}

# ── Chat loop ─────────────────────────────────────────────────────────────────

print("=" * 55)
print("  Meminumb + LangChain Demo")
print("  Type 'quit' to exit")
print("=" * 55)

history = MeminumbChatHistory(user_id=SESSION_ID, db_path=DB_PATH)
prior = history.messages
if prior:
    print(f"\n[Meminumb] Restored {len(prior)} message(s) from last session.\n")
else:
    print("\n[Meminumb] New session — no prior history.\n")

while True:
    try:
        user_input = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        break

    if not user_input:
        continue
    if user_input.lower() in ("quit", "exit"):
        print("Goodbye! Conversation saved for next time.")
        break

    response = chain_with_history.invoke(
        {"input": user_input},
        config=config,
    )
    print(f"\nBot: {response.content}\n")
