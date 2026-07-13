"""Self-audit — an agent that judges everything must also judge itself.

Every intervention Arbiter makes (any mode) is logged with mode, trigger,
confidence, and action taken. `@Arbiter audit` renders the transparency report;
the Canvas export gives compliance-style attribution (who triggered what, what
the agent did, how sure it was) — an EU-AI-Act-shaped audit trail.

Storage: Neo4j primary, local JSON fallback (same pattern as feedback.py).
"""
import os
import json
import time
import datetime as _dt

from memory import _get_neo4j
import feedback
import mcp_client

_F = os.path.join(os.path.dirname(__file__), "audit_log.json")


def log_intervention(mode: str, trigger: str, channel: str,
                     confidence: int, action: str, summary: str) -> None:
    """Record one intervention. Never raises."""
    rec = {"mode": mode[:30], "trigger": trigger[:30], "channel": (channel or "")[:30],
           "confidence": int(confidence or 0), "action": action[:60],
           "summary": (summary or "")[:300], "ts": time.time()}
    d = _get_neo4j()
    if d:
        try:
            with d.session() as s:
                s.run("CREATE (:Intervention {mode:$mode, trigger:$trigger, "
                      "channel:$channel, confidence:$confidence, action:$action, "
                      "summary:$summary, ts:$ts})", **rec)
            return
        except Exception:
            pass
    try:
        data = json.load(open(_F)) if os.path.exists(_F) else []
    except Exception:
        data = []
    data.append(rec)
    try:
        json.dump(data, open(_F, "w"))
    except Exception:
        pass


def _recent(limit: int = 50) -> list[dict]:
    d = _get_neo4j()
    if d:
        try:
            with d.session() as s:
                rows = s.run(
                    "MATCH (i:Intervention) RETURN i.mode, i.trigger, i.channel, "
                    "i.confidence, i.action, i.summary, i.ts "
                    "ORDER BY i.ts DESC LIMIT $n", n=limit).data()
            return [{k.split(".")[1]: r[k] for k in r} for r in rows]
        except Exception:
            pass
    try:
        data = json.load(open(_F)) if os.path.exists(_F) else []
    except Exception:
        data = []
    return sorted(data, key=lambda r: r.get("ts", 0), reverse=True)[:limit]


def report() -> str:
    """Short Slack-formatted transparency report."""
    recs = _recent(50)
    if not recs:
        return ("🛡️ *Arbiter transparency report*\nNo interventions logged yet — "
                "I only speak when a judgment clears its confidence threshold.")
    by_mode: dict[str, int] = {}
    for r in recs:
        by_mode[r.get("mode", "?")] = by_mode.get(r.get("mode", "?"), 0) + 1
    avg_conf = round(sum(r.get("confidence", 0) for r in recs) / len(recs))
    up, down, _total = feedback.stats()
    agree = f"{round(100 * up / (up + down))}%" if (up + down) else "n/a"
    try:
        import learning
        learn_line = learning.summary()
    except Exception:
        learn_line = ""

    mode_line = " · ".join(f"{m}: {n}" for m, n in sorted(by_mode.items()))
    last = recs[0]
    when = _dt.datetime.fromtimestamp(last["ts"]).strftime("%b %d %H:%M")
    return (
        "🛡️ *Arbiter transparency report* (last 50 interventions)\n"
        f"• By mode: {mode_line}\n"
        f"• Avg confidence at intervention: {avg_conf}%\n"
        f"• Human agreement with my verdicts: {agree} (👍 {up} / 👎 {down})\n"
        f"• Self-tuning: {learn_line}\n"
        f"• Most recent: [{last.get('mode')}] {last.get('summary', '')[:120]} ({when})\n"
        "_Every intervention I make is logged with trigger, confidence, and action. "
        "👎 makes me more reserved with that kind of intervention; 👍 relaxes it. "
        "Ask `@Arbiter audit canvas` for the full exportable trail._"
    )


def publish_canvas() -> tuple[bool, object]:
    """Export the full audit trail to a Slack Canvas via MCP."""
    recs = _recent(100)
    lines = ["# Arbiter — Intervention Audit Trail", "",
             f"Generated {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')} · "
             f"{len(recs)} interventions on record", "",
             "| When | Mode | Trigger | Channel | Confidence | Action | Summary |",
             "|---|---|---|---|---|---|---|"]
    for r in recs:
        when = _dt.datetime.fromtimestamp(r.get("ts", 0)).strftime("%m-%d %H:%M")
        lines.append(
            f"| {when} | {r.get('mode','')} | {r.get('trigger','')} | "
            f"{r.get('channel','')} | {r.get('confidence','')}% | "
            f"{r.get('action','')} | {str(r.get('summary','')).replace('|', '/')[:80]} |")
    return mcp_client.create_canvas("Arbiter — Audit Trail", "\n".join(lines))
