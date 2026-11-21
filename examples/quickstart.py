"""
Meminumb quickstart — copy-paste this after:  pip install meminumb

No API key, no config, no extra setup needed.
"""

from meminumb import Memory

print("=" * 50)
print("  Meminumb Quickstart")
print("=" * 50)

mem = Memory()

# ── 1. Store facts ────────────────────────────────
print("\n1. Storing facts...")
result = mem.add(
    [
        "Prajwal is a backend developer",
        "Prajwal loves jazz music",
        "Prajwal uses Python and Go",
        "Prajwal dislikes spicy food",
    ],
    user_id="prajwal",
)
print(f"   Stored  : {len(result.stored)}")
print(f"   Skipped : {len(result.skipped)}")
print(f"   Failed  : {len(result.failed)}")

# ── 2. Duplicate detection ────────────────────────
print("\n2. Adding the same fact again...")
result2 = mem.add(["Prajwal loves jazz music"], user_id="prajwal")
skip = result2.skipped[0]
print(f"   Reason      : {skip.reason}")
print(f"   Existing ID : {skip.existing_id}")

# ── 3. Search ─────────────────────────────────────
print("\n3. Searching: 'what does Prajwal do for work?'")
hits = mem.search("what does Prajwal do for work?", user_id="prajwal", top_k=2)
for h in hits:
    print(f"   → {h.content}")

# ── 4. Update ─────────────────────────────────────
print("\n4. Updating a fact...")
fid = result.stored[0].id
updated = mem.update(fid, content="Prajwal is a senior backend developer")
print("   Before : Prajwal is a backend developer")
print(f"   After  : {updated.content}")

# ── 5. Get all ────────────────────────────────────
print("\n5. All stored memories:")
for item in mem.get_all(user_id="prajwal"):
    print(f"   [{item.id}] {item.content}")

# ── 6. Delete ─────────────────────────────────────
print("\n6. Deleting one memory...")
deleted = mem.delete(fid)
print(f"   Deleted: {deleted}")
print(f"   Remaining: {len(mem.get_all(user_id='prajwal'))}")

print("\n" + "=" * 50)
print("  All features working. Meminumb is ready!")
print("=" * 50)
