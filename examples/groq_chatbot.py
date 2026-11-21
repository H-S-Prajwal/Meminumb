"""
Groq-powered chatbot with persistent memory across sessions.

Demonstrates Meminumb's core value: an AI that extracts facts from your
conversation and recalls them the next time you talk to it.

Setup:
    pip install groq
    export GROQ_API_KEY="your-key-here"

Run:
    python examples/groq_chatbot.py

Quit and run again — the bot will remember what you told it.
Type 'quit' or 'exit' to end the session.
Type 'memory' to see everything the bot currently remembers about you.
Type 'clear' to wipe your memory and start fresh.
"""

import os
import sys
from pathlib import Path

try:
    from groq import Groq
except ImportError:
    print("groq package not found. Install it with:  pip install groq")
    sys.exit(1)

from meminumb import Memory

# ── Config ───────────────────────────────────────────────────────────────────

DB_PATH = str(Path.home() / ".meminumb" / "chat_demo.db")
MODEL = "llama-3.1-8b-instant"
USER_ID = "demo_user"

EXTRACT_PROMPT = """
You are a fact extractor. Given a user message, extract short factual statements
about the user (preferences, job, hobbies, dislikes, name, etc.).

Return ONLY a Python list of strings, one fact per item. If no facts about the
user are present, return an empty list [].

Examples:
User: "I'm Prajwal, I love jazz and work as a backend developer"
Output: ["User's name is Prajwal", "User loves jazz", "User works as a backend developer"]

User: "what's the weather like?"
Output: []

User message: "{message}"
Output:
"""

# ── Setup ────────────────────────────────────────────────────────────────────

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("Error: GROQ_API_KEY environment variable not set.")
    print("Get a free key at https://console.groq.com and run:")
    print('  export GROQ_API_KEY="your-key-here"')
    sys.exit(1)

client = Groq(api_key=api_key)
mem = Memory(db_path=DB_PATH)


# ── Helpers ──────────────────────────────────────────────────────────────────

def extract_facts(message: str) -> list[str]:
    """Ask the LLM to pull facts about the user from their message."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": EXTRACT_PROMPT.format(message=message)}],
        temperature=0,
        max_tokens=200,
    )
    raw = response.choices[0].message.content.strip()
    try:
        facts = eval(raw)  # noqa: S307
        return [f for f in facts if isinstance(f, str) and f.strip()]
    except Exception:
        return []


def recall_context(query: str) -> str:
    """Search stored memories relevant to the current message."""
    hits = mem.search(query, user_id=USER_ID, top_k=5)
    if not hits:
        return ""
    return "\n".join(f"- {h.content}" for h in hits)


def chat(history: list[dict], user_message: str) -> str:
    """Send message to the LLM with memory context injected into system prompt."""
    context = recall_context(user_message)
    system = "You are a helpful, friendly assistant with a good memory."
    if context:
        system += f"\n\nWhat you remember about this user:\n{context}"

    messages = [{"role": "system", "content": system}] + history
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=500,
    )
    return response.choices[0].message.content.strip()


# ── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 55)
    print("  Meminumb Chat Demo")
    print("  Commands: 'memory' | 'clear' | 'quit'")
    print("=" * 55)

    existing = mem.get_all(user_id=USER_ID)
    if existing:
        print(f"\n[Meminumb] I remember {len(existing)} fact(s) about you from last time.\n")
    else:
        print("\n[Meminumb] No memories yet — tell me about yourself!\n")

    history: list[dict] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye! Your memories are saved for next time.")
            break

        if user_input.lower() == "memory":
            memories = mem.get_all(user_id=USER_ID)
            if memories:
                print(f"\n[Meminumb] {len(memories)} stored memory/memories:")
                for m in memories:
                    print(f"  · {m.content}")
            else:
                print("[Meminumb] No memories stored yet.")
            print()
            continue

        if user_input.lower() == "clear":
            count = mem.clear(user_id=USER_ID)
            print(f"[Meminumb] Cleared {count} memory/memories.\n")
            history = []
            continue

        # Extract and store facts from the user's message
        facts = extract_facts(user_input)
        if facts:
            result = mem.add(facts, user_id=USER_ID)
            new = len(result.stored)
            dupes = len(result.skipped)
            if new:
                print(f"[Meminumb] Stored {new} new fact(s): {[f.content for f in result.stored]}")
            if dupes:
                print(f"[Meminumb] Already knew {dupes} of those.")

        # Get bot reply
        history.append({"role": "user", "content": user_input})
        reply = chat(history, user_input)
        history.append({"role": "assistant", "content": reply})
        print(f"\nBot: {reply}\n")


if __name__ == "__main__":
    main()
