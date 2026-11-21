"""
Persistent storage example — memories survive across sessions.

By default Memory() uses db_path=":memory:" which is an in-process
SQLite database that disappears when your program exits.

Pass a real file path to db_path and the same memories will be there
the next time you run your program.

Run this script twice to see persistence in action:
  python examples/persistent_storage.py
  python examples/persistent_storage.py   ← same memories, no re-adding
"""

from pathlib import Path

from meminumb import Memory

DB_PATH = Path.home() / ".meminumb" / "demo.db"
first_run = not DB_PATH.exists()

mem = Memory(db_path=str(DB_PATH))

if first_run:
    print("First run — storing memories...\n")
    result = mem.add(
        [
            "Alice prefers dark mode",
            "Alice is a backend developer",
            "Alice uses Python and Go",
            "Alice dislikes spicy food",
        ],
        user_id="alice",
    )
    print(f"Stored : {len(result.stored)} memories")
    print(f"Skipped: {len(result.skipped)}")
    print(f"Failed : {len(result.failed)}")
else:
    print("Second run — memories already stored, trying to add same facts...\n")
    result = mem.add(
        [
            "Alice prefers dark mode",
            "Alice is a backend developer",
        ],
        user_id="alice",
    )
    print(f"Stored : {len(result.stored)}  ← 0 because they already exist")
    print(f"Skipped: {len(result.skipped)}  ← duplicates detected automatically")
    for item in result.skipped:
        print(f"  · '{item.content}' → {item.reason} (id={item.existing_id})")

print()

# Retrieve all stored memories regardless of run
all_memories = mem.get_all(user_id="alice")
print(f"Total memories for alice: {len(all_memories)}")
for m in all_memories:
    print(f"  [{m.id}] {m.content}")

print()

# Search works the same way with persistent storage
hits = mem.search("what programming languages does Alice know?", user_id="alice", top_k=2)
print("Search: 'what programming languages does Alice know?'")
for h in hits:
    print(f"  → {h.content}")

print(f"\nDatabase stored at: {DB_PATH}")
print("Run this script again to see that memories persist across sessions.")
