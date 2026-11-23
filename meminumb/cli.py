"""
Meminumb CLI — inspect and manage memories from the terminal.

Usage:
    meminumb add    FACT  --db PATH [--user USER] [--agent AGENT] [--ttl SECONDS]
    meminumb delete ID    --db PATH
    meminumb recent [N]   --db PATH [--user USER] [--agent AGENT]
    meminumb list         --db PATH [--user USER]
    meminumb search QUERY --db PATH [--user USER] [--top-k N]
    meminumb stats        --db PATH
    meminumb clear-expired --db PATH
    meminumb clear        --db PATH [--user USER]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime


def _mem(db: str):
    from meminumb import Memory
    return Memory(db_path=db)


def _fmt_time(ts: float | None) -> str:
    if ts is None:
        return "never"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def cmd_add(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    result = mem.add(
        [args.fact],
        user_id=args.user or "",
        agent_id=args.agent or "",
        ttl_seconds=args.ttl,
    )
    if result.stored:
        item = result.stored[0]
        print(f"Stored [{item.id}]: {item.content}")
    elif result.skipped:
        skip = result.skipped[0]
        print(f"Skipped ({skip.reason.value}): already stored as [{skip.existing_id}]")
    else:
        print(f"Failed: {result.failed[0].error}")


def cmd_delete(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    if mem.delete(args.memory_id):
        print(f"Deleted [{args.memory_id}].")
    else:
        print(f"Not found: [{args.memory_id}].")


def cmd_recent(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    items = mem.get_recent(args.n, user_id=args.user or "", agent_id=args.agent or "")
    if not items:
        scope = f"user '{args.user}'" if args.user else "all users"
        print(f"No memories found for {scope}.")
        return

    scope = f"user '{args.user}'" if args.user else "all users"
    print(f"{len(items)} most recent memory/memories for {scope}:\n")
    for item in items:
        expiry = f"  expires {_fmt_time(item.expires_at)}" if item.expires_at else ""
        print(f"  [{item.id}] {item.content}{expiry}")


def cmd_list(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    items = mem.get_all(user_id=args.user or "")
    if not items:
        scope = f"user '{args.user}'" if args.user else "all users"
        print(f"No memories found for {scope}.")
        return

    scope = f"user '{args.user}'" if args.user else "all users"
    print(f"{len(items)} memory/memories for {scope} in {args.db}\n")
    for item in items:
        expiry = f"  expires {_fmt_time(item.expires_at)}" if item.expires_at else ""
        print(f"  [{item.id}] {item.content}{expiry}")


def cmd_search(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    hits = mem.search(args.query, user_id=args.user or "", top_k=args.top_k)
    if not hits:
        print(f"No results for '{args.query}'.")
        return

    print(f"Top {len(hits)} result(s) for '{args.query}':\n")
    for i, item in enumerate(hits, 1):
        print(f"  {i}. [{item.id}] {item.content}")


def cmd_stats(args: argparse.Namespace) -> None:
    import time

    from meminumb import Memory
    from meminumb.store import SQLiteStore

    store = SQLiteStore(args.db)
    mem = Memory(store=store)

    all_items = mem.get_all()
    now = time.time()

    # Count expired rows directly via the connection
    cur = store._conn.execute(
        "SELECT COUNT(*) FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
        (now,),
    )
    expired_count = cur.fetchone()[0]

    cur2 = store._conn.execute("SELECT COUNT(*) FROM memories")
    total_rows = cur2.fetchone()[0]

    cur3 = store._conn.execute(
        "SELECT MIN(created_at), MAX(created_at) FROM memories"
    )
    oldest_ts, newest_ts = cur3.fetchone()

    cur4 = store._conn.execute(
        "SELECT DISTINCT json_extract(metadata, '$.user_id') FROM memories"
    )
    users = [r[0] for r in cur4.fetchall() if r[0]]

    print(f"Database : {args.db}")
    print(f"Total    : {total_rows} row(s)  ({expired_count} expired, {len(all_items)} active)")
    print(f"Users    : {len(users)}  {users if users else ''}")
    print(f"Oldest   : {_fmt_time(oldest_ts)}")
    print(f"Newest   : {_fmt_time(newest_ts)}")


def cmd_clear_expired(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    removed = mem.clear_expired()
    print(f"Removed {removed} expired memory/memories from {args.db}.")


def cmd_export(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    count = mem.export(args.output, user_id=args.user or "", agent_id=args.agent or "")
    scope = f"user '{args.user}'" if args.user else "all users"
    print(f"Exported {count} memory/memories for {scope} → {args.output}")


def cmd_import(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    if args.dry_run:
        import json

        with open(args.input, encoding="utf-8") as fh:
            data = json.load(fh)
        total = len(data.get("memories", []))
        print(f"[dry-run] Would import up to {total} memory/memories from {args.input}")
        return
    result = mem.import_from(args.input)
    print(
        f"Imported from {args.input}: "
        f"{result['stored']} stored, {result['skipped']} skipped, {result['failed']} failed."
    )


def cmd_clear(args: argparse.Namespace) -> None:
    mem = _mem(args.db)
    scope = f"user '{args.user}'" if args.user else "ALL users"

    # Confirm before wiping everything
    if not args.user:
        answer = input(f"This will delete ALL memories in {args.db}. Type 'yes' to confirm: ")
        if answer.strip().lower() != "yes":
            print("Aborted.")
            return

    removed = mem.clear(user_id=args.user or "")
    print(f"Cleared {removed} memory/memories for {scope}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="meminumb",
        description="Inspect and manage Meminumb memory databases.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ── add ───────────────────────────────────────────────────────────────────
    p_add = sub.add_parser("add", help="store a new memory fact")
    p_add.add_argument("fact", help="the fact text to store")
    p_add.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_add.add_argument("--user", metavar="USER", help="user_id to scope the memory")
    p_add.add_argument("--agent", metavar="AGENT", help="agent_id to scope the memory")
    p_add.add_argument("--ttl", type=int, metavar="SECONDS", help="seconds until expiry")
    p_add.set_defaults(func=cmd_add)

    # ── delete ────────────────────────────────────────────────────────────────
    p_del = sub.add_parser("delete", help="delete a memory by its ID")
    p_del.add_argument("memory_id", help="the memory ID to delete")
    p_del.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_del.set_defaults(func=cmd_delete)

    # ── recent ────────────────────────────────────────────────────────────────
    p_recent = sub.add_parser("recent", help="list the most recently added memories")
    p_recent.add_argument(
        "n", type=int, nargs="?", default=10, metavar="N", help="how many to show (default: 10)"
    )
    p_recent.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_recent.add_argument("--user", metavar="USER", help="filter by user_id")
    p_recent.add_argument("--agent", metavar="AGENT", help="filter by agent_id")
    p_recent.set_defaults(func=cmd_recent)

    # ── list ──────────────────────────────────────────────────────────────────
    p_list = sub.add_parser("list", help="list stored memories")
    p_list.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_list.add_argument("--user", metavar="USER", help="filter by user_id")
    p_list.set_defaults(func=cmd_list)

    # ── search ────────────────────────────────────────────────────────────────
    p_search = sub.add_parser("search", help="search memories by similarity")
    p_search.add_argument("query", help="search query text")
    p_search.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_search.add_argument("--user", metavar="USER", help="filter by user_id")
    p_search.add_argument(
        "--top-k", type=int, default=5, metavar="N", help="number of results (default: 5)"
    )
    p_search.set_defaults(func=cmd_search)

    # ── stats ─────────────────────────────────────────────────────────────────
    p_stats = sub.add_parser("stats", help="show database statistics")
    p_stats.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_stats.set_defaults(func=cmd_stats)

    # ── clear-expired ─────────────────────────────────────────────────────────
    p_ce = sub.add_parser("clear-expired", help="delete all expired memories")
    p_ce.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_ce.set_defaults(func=cmd_clear_expired)

    # ── clear ─────────────────────────────────────────────────────────────────
    p_clear = sub.add_parser("clear", help="delete memories for a user (or all)")
    p_clear.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_clear.add_argument("--user", metavar="USER", help="user_id to clear (omit to clear all)")
    p_clear.set_defaults(func=cmd_clear)

    # ── export ────────────────────────────────────────────────────────────────
    p_export = sub.add_parser("export", help="export memories to a JSON file")
    p_export.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_export.add_argument(
        "--output", required=True, metavar="FILE", help="destination JSON file"
    )
    p_export.add_argument("--user", metavar="USER", help="export only this user's memories")
    p_export.add_argument("--agent", metavar="AGENT", help="export only this agent's memories")
    p_export.set_defaults(func=cmd_export)

    # ── import ────────────────────────────────────────────────────────────────
    p_import = sub.add_parser("import", help="import memories from a JSON file")
    p_import.add_argument("--db", required=True, metavar="PATH", help="path to the SQLite database")
    p_import.add_argument(
        "--input", required=True, metavar="FILE", help="source JSON file (from 'export')"
    )
    p_import.add_argument(
        "--dry-run", action="store_true", help="show what would be imported without writing"
    )
    p_import.set_defaults(func=cmd_import)

    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)


if __name__ == "__main__":
    main()
