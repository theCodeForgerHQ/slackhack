"""Proactive roster monitoring: the Tim Hague failure mode, watched daily.

A lapsed suspension window plus a late replacement and nobody re-checking is the
canonical way this sport kills people. This monitor ticks hourly, gated to roughly
one run per day, and pushes an ops digest when, and only when, there is something to say.

Every trigger is DETERMINISTIC (window arithmetic and ledger diffs); no LLM decides,
phrases, or filters an alert. Quiet days stay quiet. Every run is itself written to
the append-only ledger (auditable alerting), so "since the last run" is read from the
ledger, not from mutable state. The ops push is a Slack incoming webhook and is
fail-quiet: unset or unreachable, the findings are still ledgered and logged, and the
service never crashes over its own monitoring.

Runs in-process (a daemon thread with a ledger-stamped daily gate, so restarts never
double-fire) and doubles as a CLI for an external cron:  uv run python -m cornercheck.monitor
"""

import contextlib
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from cornercheck.config import get_settings
from cornercheck.db.pool import get_pool
from cornercheck.ledger.store import append_entry, hmac_key

log = logging.getLogger("cornercheck.monitor")

LAPSING_DAYS = 14
LAPSED_DAYS = 7
_TICK_S = 3600
_RUN_EVERY = timedelta(hours=23)

# Suppresses an identical re-push if the ledger write failed after a successful post
# (the gate would not have advanced, so the next tick regathers the same digest).
# In-process only: a restart can re-send one duplicate, the safe direction.
_last_digest: str | None = None


@dataclass(frozen=True)
class Watermark:
    """Where the previous run's ledger scan ended. seq is assigned under the hash
    chain's advisory lock, so seq order is commit order: diffing `seq > prior` is
    exact, with no race window around the gather/post/append sequence (a wall-clock
    watermark had a permanent blind spot there, caught in adversarial review)."""

    seq: int
    ts: datetime  # DB clock at gather time, used only for suspensions.created_at
    # Chain head hash at gather time. Riding in the ops digest, it becomes an EXTERNAL
    # anchor (Slack message history) against tail truncation, which in-table
    # verification alone cannot catch.
    head_hash: str = ""


@dataclass(frozen=True)
class Findings:
    lapsing: list[dict[str, Any]] = field(default_factory=list)
    lapsed: list[dict[str, Any]] = field(default_factory=list)
    new_suspensions: list[dict[str, Any]] = field(default_factory=list)
    blocked_decisions: list[dict[str, Any]] = field(default_factory=list)
    disagreements: list[dict[str, Any]] = field(default_factory=list)
    # Informational: indefinite ("until cleared") suspensions have no window to lapse,
    # so they never trigger an alert; the count rides along when a digest fires anyway.
    indefinite_on_file: int = 0

    def empty(self) -> bool:
        return not (
            self.lapsing
            or self.lapsed
            or self.new_suspensions
            or self.blocked_decisions
            or self.disagreements
        )

    def as_payload(self) -> dict[str, Any]:
        return {
            "lapsing": self.lapsing,
            "lapsed": self.lapsed,
            "new_suspensions": self.new_suspensions,
            "blocked_decisions": self.blocked_decisions,
            "disagreements": self.disagreements,
            "indefinite_on_file": self.indefinite_on_file,
        }


_WINDOW_SQL = """
SELECT f.full_name, s.suspension_type, s.jurisdiction, s.end_date
FROM suspensions s JOIN fighters f ON f.id = s.fighter_id
WHERE NOT s.indefinite AND s.end_date IS NOT NULL AND s.end_date >= %s AND s.end_date <= %s
ORDER BY s.end_date, f.full_name
"""

_NEW_SUSPENSIONS_SQL = """
SELECT f.full_name, s.suspension_type, s.jurisdiction, s.end_date, s.indefinite
FROM suspensions s JOIN fighters f ON f.id = s.fighter_id
WHERE s.created_at > %s
ORDER BY s.created_at
"""

_DECISIONS_SQL = """
SELECT payload FROM ledger
WHERE action = 'clearance_decision' AND seq > %s AND seq <= %s
ORDER BY seq
"""


def gather_findings(today: date, since: Watermark) -> tuple[Findings, Watermark]:
    """Pure window arithmetic and ledger diffs. Nothing here guesses. Returns the
    findings plus THIS gather's watermark; the next run diffs from exactly there."""
    with get_pool().connection() as conn:
        wm_row = conn.execute("SELECT coalesce(max(seq), 0), now() FROM ledger").fetchone()
        assert wm_row is not None  # aggregate always returns one row
        head = conn.execute("SELECT hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        watermark = Watermark(
            seq=int(wm_row[0]), ts=wm_row[1], head_hash=str(head[0]) if head else ""
        )
        lapsing_rows = conn.execute(
            _WINDOW_SQL, (today, today + timedelta(days=LAPSING_DAYS))
        ).fetchall()
        lapsed_rows = conn.execute(
            _WINDOW_SQL, (today - timedelta(days=LAPSED_DAYS), today - timedelta(days=1))
        ).fetchall()
        new_rows = conn.execute(_NEW_SUSPENSIONS_SQL, (since.ts,)).fetchall()
        decision_rows = conn.execute(_DECISIONS_SQL, (since.seq, watermark.seq)).fetchall()
        indef_row = conn.execute("SELECT count(*) FROM suspensions WHERE indefinite").fetchone()

    def window(r: Any) -> dict[str, Any]:
        return {
            "fighter": r[0],
            "type": r[1],
            "jurisdiction": r[2],
            "end_date": r[3].isoformat(),
        }

    blocked: list[dict[str, Any]] = []
    disagreed: list[dict[str, Any]] = []
    skipped = 0
    for (p,) in decision_rows:
        if not isinstance(p, dict):
            # One malformed row must never wedge ALL monitoring behind it.
            skipped += 1
            continue
        if p.get("decision") == "DO_NOT_CLEAR":
            blocked.append({"fighter": p.get("fighter_name"), "rules": p.get("applied_rules")})
        corr = p.get("corroboration") or {}
        if corr.get("status") == "DISAGREED":
            disagreed.append({"fighter": p.get("fighter_name"), "note": corr.get("note")})
    if skipped:
        log.warning("monitor skipped %d malformed clearance_decision ledger rows", skipped)

    findings = Findings(
        lapsing=[window(r) for r in lapsing_rows],
        lapsed=[window(r) for r in lapsed_rows],
        new_suspensions=[
            {
                "fighter": r[0],
                "type": r[1],
                "jurisdiction": r[2],
                "end_date": r[3].isoformat() if r[3] else None,
                "indefinite": r[4],
            }
            for r in new_rows
        ],
        blocked_decisions=blocked,
        disagreements=disagreed,
        indefinite_on_file=int(indef_row[0]) if indef_row else 0,
    )
    return findings, watermark


def format_alert(f: Findings, today: date, anchor: str = "") -> str | None:
    """Deterministic digest text. None when there is nothing to report: quiet days
    stay quiet, no synthetic cheer. anchor (the chain head at gather time) makes every
    posted digest an external tamper anchor in Slack message history."""
    if f.empty():
        return None
    lines = [f":rotating_light: *CornerCheck roster monitor* ({today.isoformat()})"]
    for w in f.lapsing:
        days = (date.fromisoformat(w["end_date"]) - today).days
        lines.append(
            f"- Window lapsing in {days}d: *{w['fighter']}*, {w['type']}, "
            f"{w['jurisdiction']}, ends {w['end_date']}. Verify clearance before booking."
        )
    for w in f.lapsed:
        days = (today - date.fromisoformat(w["end_date"])).days
        lines.append(
            f"- Window lapsed {days}d ago: *{w['fighter']}*, {w['type']}, "
            f"{w['jurisdiction']}. Do not assume cleared; confirm with the commission."
        )
    for s in f.new_suspensions:
        ends = "INDEFINITE" if s["indefinite"] or not s["end_date"] else f"ends {s['end_date']}"
        lines.append(
            f"- New suspension on file: *{s['fighter']}*, {s['type']}, {s['jurisdiction']}, {ends}."
        )
    if f.blocked_decisions:
        names = ", ".join(str(b["fighter"]) for b in f.blocked_decisions[:10])
        lines.append(
            f"- {len(f.blocked_decisions)} DO NOT CLEAR verdict(s) since last run: {names}"
        )
    for d in f.disagreements:
        lines.append(f"- Live-record disagreement: *{d['fighter']}*. {d['note']}")
    if f.indefinite_on_file:
        lines.append(
            f"- {f.indefinite_on_file} indefinite (until cleared) suspension(s) on file; "
            "no window to lapse, the engine blocks these at decision time."
        )
    if anchor:
        lines.append(f"_Ledger anchor: {anchor}_")
    lines.append("_Deterministic triggers. Decision support; a human makes the call._")
    text = "\n".join(lines)
    if len(text) > 39000:  # Slack text limit, defensive
        text = text[:38900] + "\n_(truncated; full findings are in the ledger entry)_"
    return text


def post_ops_alert(text: str) -> bool:
    """Push to the ops incoming webhook. Fail-quiet: a monitoring push must never take
    the service down, and a failed push still leaves the ledgered findings. The webhook
    URL is a secret: no failure path may echo it into logs."""
    url = get_settings().ops_webhook_url
    if not url:
        log.warning("OPS_WEBHOOK_URL not set; monitor findings ledgered but not pushed")
        return False
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"text": text}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return bool(200 <= r.status < 300)
    except ValueError:
        # Raised on a malformed URL with the FULL URL in the message: never echo it.
        log.warning("OPS_WEBHOOK_URL is malformed (needs a full https:// URL); push skipped")
        return False
    except urllib.error.HTTPError as e:
        detail = ""
        with contextlib.suppress(Exception):
            detail = e.read()[:200].decode(errors="replace")
        log.warning("ops webhook push failed (HTTP %s): %s", e.code, detail)
        return False
    except Exception as e:
        # HTTPError/URLError strings carry no URL; verified safe to log.
        log.warning("ops webhook push failed (%s: %s)", type(e).__name__, e)
        return False


def _last_run_ts() -> datetime | None:
    try:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT ts FROM ledger WHERE action = 'monitor_run' ORDER BY seq DESC LIMIT 1"
            ).fetchone()
        return row[0] if row else None
    except Exception as e:
        log.warning("could not read last monitor run (%s: %s)", type(e).__name__, e)
        return None


def _prior_watermark() -> Watermark | None:
    """The previous run's gather watermark, from its ledgered payload."""
    try:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT payload FROM ledger WHERE action = 'monitor_run' ORDER BY seq DESC LIMIT 1"
            ).fetchone()
        if row is None or not isinstance(row[0], dict):
            return None
        wm = row[0].get("watermark") or {}
        return Watermark(seq=int(wm["seq"]), ts=datetime.fromisoformat(wm["ts"]))
    except Exception as e:
        log.warning("could not read prior monitor watermark (%s: %s)", type(e).__name__, e)
        return None


def _first_run_watermark() -> Watermark:
    """First run ever: baseline the diff at roughly 24 hours ago (documented; anything
    older is point-in-time window data anyway, never diff data)."""
    with get_pool().connection() as conn:
        row = conn.execute(
            "SELECT coalesce(max(seq), 0), now() - interval '24 hours' FROM ledger"
            " WHERE ts <= now() - interval '24 hours'"
        ).fetchone()
    assert row is not None
    return Watermark(seq=int(row[0]), ts=row[1])


def run_monitor_once(now: datetime | None = None) -> dict[str, Any]:
    """One full pass: gather, format, push, and ALWAYS ledger the run."""
    global _last_digest
    at = now or datetime.now(UTC)
    try:
        hmac_key()
    except Exception:
        # Alerting that cannot be ledgered must not fire: an unledgered push breaks the
        # auditable-alerting contract AND would re-fire every tick (the gate never
        # advances), spamming ops with identical digests.
        log.error("ledger HMAC key unavailable; monitor run skipped (alerts must be auditable)")
        return {"skipped": "ledger-unavailable"}
    since = _prior_watermark() or _first_run_watermark()
    f, watermark = gather_findings(at.date(), since)
    anchor = f"seq {watermark.seq}, head {watermark.head_hash[:16]}" if watermark.head_hash else ""
    # Dedup compares the ANCHORLESS text: the head hash advances with every ledgered
    # run, so comparing anchored digests would never match and the duplicate
    # suppression would silently die (caught by the suite when the anchor landed).
    core = format_alert(f, at.date())
    text = format_alert(f, at.date(), anchor=anchor)
    posted = False
    if text is not None:
        if core == _last_digest:
            log.info("digest identical to the last posted one; duplicate push suppressed")
        else:
            posted = post_ops_alert(text)
            if posted:
                _last_digest = core
    entry = append_entry(
        "cornercheck-monitor",
        "monitor_run",
        {
            "at": at.isoformat(),
            "since": {"seq": since.seq, "ts": since.ts.isoformat()},
            "watermark": {
                "seq": watermark.seq,
                "ts": watermark.ts.isoformat(),
                "head_hash": watermark.head_hash,
            },
            "findings": f.as_payload(),
            "alerted": text is not None,
            "posted": posted,
        },
    )
    log.info(
        "monitor run seq=%s: %d lapsing, %d lapsed, %d new, %d blocked, %d disagreed, posted=%s",
        entry.seq,
        len(f.lapsing),
        len(f.lapsed),
        len(f.new_suspensions),
        len(f.blocked_decisions),
        len(f.disagreements),
        posted,
    )
    return {"seq": entry.seq, "alerted": text is not None, "posted": posted}


def start_monitor_thread() -> threading.Thread:
    """Daily in-process scheduler. The gate is the LEDGER's last monitor_run timestamp,
    so service restarts never double-fire and never skip a due run."""

    def _loop() -> None:
        while True:
            try:
                last = _last_run_ts()
                if last is None or (datetime.now(UTC) - last) >= _RUN_EVERY:
                    run_monitor_once()
            except Exception:
                log.exception("monitor tick failed; retrying next tick")
            time.sleep(_TICK_S)

    t = threading.Thread(target=_loop, name="cornercheck-monitor", daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run_monitor_once())
