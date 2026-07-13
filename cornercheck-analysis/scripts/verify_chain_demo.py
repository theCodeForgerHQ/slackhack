"""Live tamper-evidence demo for the audit ledger.

Usage:
  uv run python scripts/verify_chain_demo.py status        # verify the whole chain
  uv run python scripts/verify_chain_demo.py seed          # append 5 demo entries
  uv run python scripts/verify_chain_demo.py tamper <seq>  # privileged bypass + edit one row
  uv run python scripts/verify_chain_demo.py reset         # wipe ledger (bypass) for re-demo
"""

import sys

from cornercheck.db.pool import get_pool
from cornercheck.ledger.store import append_entry
from cornercheck.ledger.verify import verify_chain


def status() -> None:
    r = verify_chain()
    flag = "INTACT" if r.ok else f"BROKEN at seq {r.first_bad_seq}"
    print(f"chain: {flag} | entries checked: {r.checked} | {r.detail}")


def seed() -> None:
    for i in range(1, 6):
        e = append_entry(
            "demo",
            "clearance_decision",
            {"fighter": f"Demo Fighter {i}", "decision": "CLEAR" if i % 2 else "DO NOT CLEAR"},
        )
        print(f"appended seq {e.seq} hash {e.hash[:16]}...")


def tamper(seq: int) -> None:
    with get_pool().connection() as conn:
        conn.execute("SET session_replication_role = replica")  # privileged trigger bypass
        conn.execute(
            "UPDATE ledger SET payload = jsonb_set(payload, '{decision}',"
            " to_jsonb('CLEAR (silently forged)'::text)) WHERE seq = %s",
            (seq,),
        )
        conn.execute("SET session_replication_role = DEFAULT")
    print(f"row seq {seq} silently edited (decision forged). Now run: status")


def reset() -> None:
    with get_pool().connection() as conn:
        conn.execute("SET session_replication_role = replica")
        conn.execute("TRUNCATE ledger RESTART IDENTITY")
        conn.execute("SET session_replication_role = DEFAULT")
    print("ledger wiped for re-demo")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "seed":
        seed()
    elif cmd == "tamper":
        tamper(int(sys.argv[2]))
    elif cmd == "reset":
        reset()
    else:
        print(__doc__)
        sys.exit(1)
