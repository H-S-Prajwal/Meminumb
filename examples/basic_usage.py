"""Basic Meminumb demo — no API key, no external services required."""

from meminumb import Memory

mem = Memory()  # uses DummyEmbedder by default — works offline

# ── Add some facts ──────────────────────────────────────────────────────────
result = mem.add(
    [
        "Alice prefers dark mode",
        "Alice is a backend developer",
        "Alice uses Python and Go",
    ],
    user_id="alice",
)
print(result)
# AddResult(stored=3, skipped=0, failed=0)

# ── Duplicate detection ─────────────────────────────────────────────────────
result2 = mem.add(["Alice prefers dark mode"], user_id="alice")
print(result2)
# AddResult(stored=0, skipped=1, failed=0)

skip = result2.skipped[0]
print(f"  skipped: '{skip.content}' — reason={skip.reason}, existing_id={skip.existing_id}")

# ── Search ──────────────────────────────────────────────────────────────────
hits = mem.search("what IDE theme does Alice use?", user_id="alice", top_k=2)
for h in hits:
    print(f"  → {h.content}")

# ── Get all ───────────────────────────────────────────────���─────────────────
all_items = mem.get_all(user_id="alice")
print(f"\nTotal stored for alice: {len(all_items)}")

# ── Delete ──────────────────────────────────────────────────────────────────
fid = result.stored[0].id
deleted = mem.delete(fid)
print(f"Deleted memory {fid}: {deleted}")
print(f"Remaining: {len(mem.get_all(user_id='alice'))}")
