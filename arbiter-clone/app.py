"""Arbiter (formerly Verdict) — the workspace's judgment layer.

One brain (LangGraph multi-agent pipeline + claim graph), three verdicts:
  on claims     — fact-check with cited, confidence-scored verdicts
  on content    — substance receipts for polished-but-hollow "workslop"
  on decisions  — the missing voices: absent stakeholders, the record, the counter-case
Plus two ledgers over the same graph: credit ("who said it first") and
predictions (calibration over time) — and a self-audit trail of every
intervention the agent makes.

Delivery rule (private-first): anything that judges a PERSON'S writing goes to
that person privately; anything that protects the THREAD (fact-checks, missing
voices) posts in-thread.

Entry points:
- @Arbiter <claim|subcommand>   (mention: audit / ledger / substance / voices / watch / stats)
- /verdict <claim>              (slash command)
- the Assistant side-pane       (dynamic suggested prompts + chat)
- 🔍 reaction                    (fact-check any message)
- watched channels              (proactive: full judgment cascade)
"""
import os
import re
import json
import time
from dotenv import load_dotenv

load_dotenv()  # must run before importing llm (llm reads env vars at import time)

from slack_bolt import App, Assistant
from slack_bolt.adapter.socket_mode import SocketModeHandler

from llm import verify_claim, MODEL, PROVIDER, decompose_claims
from media import claim_from_file, extract_text
import mcp_client
import feedback
import judgment
import substance as substance_mod
import decisions as decisions_mod
import delegate as delegate_mod
import ledger
import audit
import catchup as catchup_mod
import roundtable as roundtable_mod
import learning
import knowledge_graph as _kg
from arblog import get_logger

log = get_logger(__name__)
BOT_NAME = os.environ.get("ARBITER_NAME", "Arbiter")

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    # skip the eager auth.test at construction — we validate via our own
    # auth_test() below, and this lets the module import under test/CI without
    # a live token (and shaves a network round-trip off boot).
    token_verification_enabled=False,
)

try:
    BOT_USER_ID = app.client.auth_test().get("user_id")
except Exception:
    BOT_USER_ID = None

_WATCH_FILE = os.path.join(os.path.dirname(__file__), "watched.json")

# Watched channels: in-process cache on the hot path (on_message runs for EVERY
# message — it must never depend on a live Neo4j round-trip; AuraDB free tier
# drops idle connections). Neo4j + JSON are persistence mirrors, loaded once.
_watch_cache: set | None = None


def _watched() -> set:
    global _watch_cache
    if _watch_cache is not None:
        return _watch_cache
    loaded: set = set()
    from memory import _get_neo4j
    d = _get_neo4j()
    if d:
        try:
            with d.session() as s:
                rows = s.run("MATCH (w:WatchedChannel) RETURN w.channel_id").data()
            loaded = {r["w.channel_id"] for r in rows}
        except Exception:
            pass
    if not loaded:
        try:
            loaded = set(json.load(open(_WATCH_FILE)))
        except Exception:
            loaded = set()
    _watch_cache = loaded
    return _watch_cache


def _set_watched(channels: set) -> None:
    global _watch_cache
    _watch_cache = set(channels)
    try:  # JSON write-through mirror — always
        json.dump(list(channels), open(_WATCH_FILE, "w"))
    except Exception:
        pass
    from memory import _get_neo4j
    d = _get_neo4j()
    if d:
        try:  # Neo4j mirror — best-effort
            with d.session() as s:
                s.run("MATCH (w:WatchedChannel) DELETE w")
                for ch in channels:
                    s.run("CREATE (:WatchedChannel {channel_id: $ch})", ch=ch)
        except Exception:
            pass

_EMOJI = {"True": "✅", "False": "❌", "Misleading": "⚠️", "Unverifiable": "🤷"}
_KIND = {"WEB": "🌐", "SLACK": "💬", "WIKI": "📖", "FACTCHECK": "🔍"}


def _esc(text: str, limit: int = 2500) -> str:
    """Escape user-controlled text before echoing it into mrkdwn blocks.

    &/</> are Slack control chars — unescaped, a claim containing <!channel>
    would ping the whole channel from OUR bot (docs.slack.dev/concepts/security).
    Also truncates below the 3000-char section limit so long input can't
    invalid_blocks the card.
    """
    t = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t[:limit] + ("…" if len(t) > limit else "")


def _fallback(data: dict) -> str:
    """Plain-text fallback shown in notifications/previews."""
    return f"{data.get('verdict', 'Unverifiable')} — {data.get('confidence', '?')}% confidence"


def _blocks(claim: str, data: dict) -> list:
    """Rich Block Kit verdict card."""
    verdict = str(data.get("verdict", "Unverifiable"))
    emoji = _EMOJI.get(verdict, "🤷")
    conf = data.get("confidence", "?")
    # strip the model's inline [n] markers — the Sources line below is authoritative
    # (escaped: model output can relay control chars from hostile evidence text)
    reasoning = _esc(re.sub(r"\s*\[\d+\]", "", str(data.get("reasoning", ""))).strip())
    sources = data.get("sources_resolved", [])
    topic = str(data.get("topic", "")).lower()

    blocks = [
        {"type": "header",
         "text": {"type": "plain_text", "emoji": True,
                  "text": f"{emoji} {verdict} — {conf}% confidence"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f">{_esc(claim, 500)}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": reasoning or "_no reasoning given_"}},
    ]
    if sources:
        links = "   ".join(
            f"{_KIND.get(s.get('kind'), '🔗')} <{s['url']}|[{i + 1}]>"
            for i, s in enumerate(sources)
        )
        blocks.append({"type": "context",
                       "elements": [{"type": "mrkdwn", "text": f"*Sources:*  {links}"}]})
    if any(t in topic for t in ("health", "medical")):
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
                       "text": "⚕️ Health-related claim — informational only, not medical advice; consult a professional."}]})
    elif any(t in topic for t in ("finance", "legal", "invest")):
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
                       "text": "⚠️ Informational only — not financial or legal advice."}]})
    panel = data.get("panel", [])
    if panel:
        parts = " · ".join(
            f"{p.get('role','?')} ({p.get('model','?').split('-')[0]}) {_EMOJI.get(str(p.get('verdict')), '•')}"
            for p in panel
        )
        contra = data.get("contrarian", {})
        if contra.get("challenge"):
            parts += f" · 🔴 *Devil's advocate:* {contra['challenge'][:250]}"
        blocks.append({"type": "context",
                       "elements": [{"type": "mrkdwn", "text": f"*Panel:* {parts}"}]})
    # interactive buttons
    actions = [{"type": "button", "text": {"type": "plain_text", "text": "🔁 Re-verify"},
                "action_id": "reverify", "value": claim[:1900]}]
    if panel:
        ptext = "\n".join(
            f"• {p.get('model')}: {p.get('verdict')} ({p.get('confidence')}%) — {p.get('reasoning', '')}"
            for p in panel)
        actions.append({"type": "button", "text": {"type": "plain_text", "text": "🧠 Show panel"},
                        "action_id": "show_panel", "value": ptext[:1900]})
    _fb_up = json.dumps({"claim": claim[:360], "verdict": verdict, "vote": "up", "mode": "claim"})
    _fb_down = json.dumps({"claim": claim[:360], "verdict": verdict, "vote": "down", "mode": "claim"})
    actions += [
        {"type": "button", "text": {"type": "plain_text", "text": "👍"}, "action_id": "fb_up", "value": _fb_up},
        {"type": "button", "text": {"type": "plain_text", "text": "👎"}, "action_id": "fb_down", "value": _fb_down},
    ]
    blocks.append({"type": "actions", "elements": actions})

    if data.get("cached"):
        base = "cached verdict"
    elif data.get("route") == "simple":
        base = "single model · fast path (high confidence)"
    elif data.get("self_consistent"):
        base = f"council of {len(panel)} models + contrarian · self-consistent (3× synth)"
    else:
        base = f"council of {len(panel)} models + contrarian"
    cm = data.get("council_meta") or {}
    if cm.get("rounds", 0) >= 2:
        base += " · split panel → round 2"
        if cm.get("dart_fired"):
            base += " + dispute search"
    foot = f"{base} · {PROVIDER}/{MODEL} · web + Wikipedia + Google FactCheck + Slack (RTS)"
    if data.get("mcp_acted"):
        foot += " · ⚠️ flagged source via MCP"
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": foot}]})
    return blocks


def _substance_blocks(result: dict, target_desc: str = "") -> list:
    """Block Kit substance receipt."""
    s = result["score"]
    emoji, label = substance_mod.grade(s)
    comp = result["components"]
    units = result["units"]
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "emoji": True,
         "text": f"{emoji} Substance: {s}/100 — {label}"}},
        {"type": "context", "elements": [{"type": "mrkdwn",
         "text": f"{result['words']} words · {result['n_units']} substantive units"
                 + (f" · {target_desc}" if target_desc else "")}]},
    ]
    counts = (f"*Receipt:*  decisions {len(units['decisions'])} · asks {len(units['asks'])} · "
              f"commitments {len(units['commitments'])} · checkable facts {len(units['facts'])}")
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": counts}})
    if units["gist"]:
        gist = "\n".join(f"• {_esc(g, 250)}" for g in units["gist"])
        blocks.append({"type": "section",
                       "text": {"type": "mrkdwn", "text": f"*The gist:*\n{gist}"}})
    for c in result["unsupported"]:
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"⚠️ *Unsupported:* {_esc(c['fact'], 300)} — _{_esc(c['note'], 150)}_"}})
    if comp["novelty"] <= 50 and result.get("novelty_note"):
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"♻️ *{100 - comp['novelty']}% restates prior workspace "
                               f"content* — _{result['novelty_note']}_"}})
    detail = (f"density {comp['density']} · fluff {comp['fluff']} · "
              f"grounded {comp['groundedness']} · novel {comp['novelty']}")
    if result["fillers"]:
        detail += " · filler: " + ", ".join(f"“{f}”" for f in result["fillers"][:3])
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
                   "text": f"score = 60% density + 20% grounded + 20% novel − fluff penalty · {detail}"}]})
    return blocks


def _quorum_blocks(q: dict, decision_text: str) -> list:
    """Block Kit 'missing voices' card for a forming decision."""
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "emoji": True,
         "text": f"⚖️ Before you lock this in — {q['topic'][:100] or 'this decision'}"}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f">{_esc(decision_text, 280)}"}},
    ]
    if q["absent"]:
        lines = []
        for a in q["absent"]:
            link = f" (<{a['url']}|context>)" if a.get("url") else ""
            why = f" — _{_esc(a['why'], 150)}_" if a.get("why") else ""
            lines.append(f"• *{_esc(a['author'], 60)}* said: “{_esc(a['quote'], 160)}”{link}{why}")
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": "🪑 *Missing voices* (not in this thread):\n" + "\n".join(lines)}})
    if q["record"]:
        lines = []
        for r in q["record"][:3]:
            link = f" (<{r['url']}|thread>)" if r.get("url") else ""
            lines.append(f"• {_esc(r['title'], 60)}: “{_esc(r['quote'], 140)}”{link}")
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": "📜 *The record:*\n" + "\n".join(lines)}})
    if q["counter"].get("grounded") and q["counter"].get("counter"):
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"🔴 *Strongest counter-case:* {_esc(q['counter']['counter'], 400)}"}})
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
                   "text": "Quotes are real workspace messages (nothing is generated on "
                           "anyone's behalf). I only show legs with actual signal."}]})
    return blocks


def _post_quorum(post_fn, q: dict, decision_text: str, channel_id: str = "") -> None:
    """Post a quorum card — prefer the new agent `task_card` block (March 2026),
    fall back to classic blocks if the surface rejects it. Also registers the
    decision in the native Slack List (best-effort)."""
    import time as _time
    blocks = _quorum_blocks(q, decision_text)
    fallback_text = f"Missing voices on: {q['topic']}"
    tc = {"type": "task_card", "task_id": f"quorum-{int(_time.time() * 1000)}",
          "title": f"Missing voices — {q['topic'] or 'decision'}"[:120],
          "status": "complete"}
    try:
        post_fn(blocks=[tc] + blocks, text=fallback_text, reply_broadcast=True)
    except Exception:
        try:
            post_fn(blocks=blocks, text=fallback_text, reply_broadcast=True)
        except Exception as e:
            log.warning(f"quorum post failed: {e}")
            return
    try:
        import lists_sync
        lists_sync.add_decision(q["topic"] or decision_text[:60], channel_id)
    except Exception:
        pass


def _delegate_blocks(name: str, uid: str, r: dict) -> list:
    """Delegate answer card — explicitly labeled, quote-backed, never impersonation."""
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "emoji": True,
         "text": f"🗣️ {name}'s record says…"}},
        {"type": "context", "elements": [{"type": "mrkdwn",
         "text": f"Delegate answer — composed *only* from <@{uid}>'s real messages, "
                 f"cited below. They've been notified."}]},
        {"type": "section", "text": {"type": "mrkdwn", "text": _esc(r["answer"], 800)}},
    ]
    for i, c in enumerate(r["quotes"]):
        link = f" (<{c['url']}|source>)" if c.get("url") else ""
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": f"[{i + 1}] “{_esc(c['quote'], 200)}”{link}"}]})
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
        "text": "Arbiter never improvises a person's position — anything off the record "
                "is escalated to the real human."}]})
    return blocks


def _roundtable_blocks(result: dict) -> list:
    """Roundtable card — several teammates, each voiced from their own messages,
    talk a topic through to a conclusion."""
    parts = result.get("participants", [])
    who = ", ".join(p["display"] for p in parts)
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "emoji": True,
         "text": f"🎭 Roundtable — {(result.get('topic') or 'the question')[:120]}"}},
        {"type": "context", "elements": [{"type": "mrkdwn",
         "text": f"{who} talked it through — each voiced from their own messages."}]},
    ]
    if result.get("conclusion"):
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Where they land*\n{_esc(result['conclusion'], 1400)}"}})
    line = []
    if result.get("consensus"):
        line.append(f"✅ *Agreed:* {_esc(result['consensus'], 280)}")
    if result.get("tension"):
        line.append(f"⚡ *Open tension:* {_esc(result['tension'], 280)}")
    if line:
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
            "text": "\n".join(line)}})
    blocks.append({"type": "divider"})
    for p in parts:
        if not p.get("position"):
            continue
        links = " · ".join(f"<{q['url']}|source>" for q in p.get("quotes", []) if q.get("url"))
        src = f"\n{links}" if links else ""
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
            "text": f"*{_esc(p['display'], 60)}:* {_esc(p['position'], 600)}{src}"}})
    return blocks


def _display_name(client, user_id: str) -> str:
    if not user_id:
        return ""
    for c in (client, _user_client()):  # bot token may lack users:read pre-reinstall
        if not c:
            continue
        try:
            u = c.users_info(user=user_id).get("user", {})
            p = u.get("profile", {})
            name = p.get("display_name") or p.get("real_name") or u.get("name") or ""
            if name:
                return name
        except Exception:
            continue
    return ""


_user_wc = None


def _user_client():
    global _user_wc
    if _user_wc is None and os.environ.get("SLACK_USER_TOKEN"):
        from slack_sdk import WebClient as _WC
        _user_wc = _WC(token=os.environ["SLACK_USER_TOKEN"])
    return _user_wc


def _permalink(client, channel: str, ts: str) -> str:
    try:
        return client.chat_getPermalink(channel=channel, message_ts=ts).get("permalink", "")
    except Exception:
        return ""


def _thread_participants(client, channel: str, thread_ts: str) -> set:
    """Display names of everyone in the thread (for absent-voice filtering)."""
    names = set()
    try:
        resp = client.conversations_replies(channel=channel, ts=thread_ts, limit=30)
        uids = {m.get("user") for m in resp.get("messages", []) if m.get("user")}
        for uid in list(uids)[:10]:
            n = _display_name(client, uid)
            if n:
                names.add(n)
    except Exception:
        pass
    return names


def _parent_text(client, channel: str, thread_ts: str) -> str:
    """Text of the message a thread hangs off (for 'judge the parent' commands)."""
    try:
        resp = client.conversations_history(channel=channel, latest=thread_ts,
                                            inclusive=True, limit=1)
        msgs = resp.get("messages", [])
        return re.sub(r"<@[^>]+>", "", msgs[0].get("text", "")).strip() if msgs else ""
    except Exception:
        return ""


import datetime as _dt


def _run_and_reply(claim: str, say, thread_ts, react=None,
                   author: str = "", permalink: str = "", trigger: str = "mention"):
    # You can't fact-check the future: one cheap call decides if this is a
    # prediction with a future resolution date — if so, it goes to the ledger
    # instead of the (pointless) evidence/debate pipeline.
    try:
        p = ledger.detect_prediction(claim)
    except Exception:
        p = None
    if p and p.get("resolve_by") and p["resolve_by"] > _dt.date.today().isoformat():
        ledger.log_prediction(p["prediction"], author or "unknown",
                              p["resolve_by"], permalink)
        if react and react[0] and react[1]:
            mcp_client.add_reaction(react[0], react[1], "crystal_ball")
        say(text=f"🔮 That's a prediction, not a checkable fact — logged it: "
                 f"*{_esc(p['prediction'], 300)}* (resolves {p['resolve_by']}). "
                 f"Scoreboard: `@{BOT_NAME} ledger`.",
            thread_ts=thread_ts)
        audit.log_intervention("prediction", trigger, "", 70,
                               "logged prediction", p["prediction"][:120])
        return

    # Hard input cap: a real claim is a sentence or two. This bounds pipeline
    # latency and tool-query size against pasted walls of text.
    claim = claim[:600]
    say(text=f":mag: Verifying: *{_esc(claim, 400)}* …", thread_ts=thread_ts)
    try:
        data = verify_claim(claim, thread_id=thread_ts or "default")
        if data.get("not_claim"):
            # escaped: the router's friendly message can echo attacker-controlled text
            say(text=_esc(str(data["reasoning"]), 400), thread_ts=thread_ts)
            return
        # MCP act-layer: flag a false/misleading source message with a ⚠️ reaction
        if react and react[0] and react[1] and str(data.get("verdict")) in ("False", "Misleading"):
            ok, _ = mcp_client.add_reaction(react[0], react[1], "warning")
            data["mcp_acted"] = ok
        blocks = _blocks(claim, data)
        # Credit ledger: phrase as a gift, attach to the card, never a separate call-out
        if author:
            try:
                _kg.save_claim(claim, str(data.get("verdict", "")),
                               int(data.get("confidence") or 0),
                               data.get("sources_resolved", []),
                               author=author, permalink=permalink)
                credit = ledger.credit_line(claim, author)
                if credit:
                    blocks.insert(-1, {"type": "context",
                                       "elements": [{"type": "mrkdwn", "text": credit}]})
            except Exception:
                pass
        # broadcast to the channel too — but only when we're in a thread
        # (reply_broadcast requires thread_ts; slash commands have none)
        _bc = {"reply_broadcast": True} if thread_ts else {}
        say(blocks=blocks, text=_fallback(data), thread_ts=thread_ts, **_bc)
        audit.log_intervention("claim", trigger, "", int(data.get("confidence") or 0),
                               "posted verdict card", claim[:120])
    except Exception as e:
        say(text=f":warning: Something went wrong: `{e}`", thread_ts=thread_ts)


# ---- channel mention + slash command -------------------------------------
def _verify_file(f, say, thread_ts):
    say(text=":mag: Reading your file…", thread_ts=thread_ts)
    try:
        claim = claim_from_file(f)
    except Exception as e:
        say(text=f":warning: Couldn't read that file: `{e}`", thread_ts=thread_ts)
        return
    if not claim or claim.strip().upper().startswith("NONE"):
        say(text="I couldn't find a checkable factual claim in that file.", thread_ts=thread_ts)
        return
    say(text=f"Claim from file: *{claim}*", thread_ts=thread_ts)
    _run_and_reply(claim, say, thread_ts)


_IMPROVE_WORDS = ("improve", "correct", "fix", "review", "all claims", "whole doc",
                  "entire doc", "check the document", "check this doc", "fact-check the doc")


def _is_doc(f) -> bool:
    name = (f.get("name") or "").lower()
    mt = (f.get("mimetype") or "").lower()
    return mt == "application/pdf" or "word" in mt or name.endswith((".pdf", ".docx", ".txt", ".md"))


def _wants_doc_report(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in _IMPROVE_WORDS)


def _verify_document(f, say, thread_ts, client=None, channel=None):
    say(text=":mag: Fact-checking the whole document — this takes a moment…", thread_ts=thread_ts)
    try:
        text = extract_text(f)
    except Exception as e:
        say(text=f":warning: Couldn't read that document: `{e}`", thread_ts=thread_ts)
        return
    claims = decompose_claims(text, max_n=4)
    if not claims:
        say(text="I couldn't find checkable claims in that document.", thread_ts=thread_ts)
        return

    results = []
    for c in claims:
        d = verify_claim(c)
        v = str(d.get("verdict", "?"))
        conf = d.get("confidence", "?")
        rsn = re.sub(r"\s*\[\d+\]", "", str(d.get("reasoning", ""))).strip()
        srcs = [s.get("url", "") for s in d.get("sources_resolved", [])[:2]]
        results.append({"claim": c, "verdict": v, "confidence": conf,
                        "reasoning": rsn, "sources": srcs})

    # Build annotated corrected document in original format
    orig_name = f.get("name") or "document.txt"
    lines = ["VERDICT — FACT-CHECK REPORT", "=" * 40, ""]
    summary = []
    for r in results:
        emoji = _EMOJI.get(r["verdict"], "•")
        lines.append(f"ORIGINAL: {r['claim']}")
        lines.append(f"{emoji} {r['verdict']} ({r['confidence']}%)")
        lines.append(f"REASON:   {r['reasoning']}")
        if r["sources"]:
            lines.append(f"SOURCES:  {' | '.join(r['sources'])}")
        lines.append("")
        summary.append(f"{emoji} *{r['verdict']}* ({r['confidence']}%) — {r['claim']}")

    corrected_text = "\n".join(lines)

    # Post summary in thread
    say(text="✅ *Document fact-check results:*\n\n" + "\n".join(summary), thread_ts=thread_ts)

    # Upload corrected annotated file back to thread
    if client and channel:
        try:
            client.files_upload_v2(
                channel=channel,
                thread_ts=thread_ts,
                title="Verdict — fact-checked report",
                filename=f"verdict_{orig_name}",
                content=corrected_text,
                initial_comment="📄 Annotated document with verdicts and corrections:",
            )
        except Exception:
            pass


# Event dedup: Slack redelivers events that weren't acked before a restart —
# without this, a bounce mid-fact-check makes Arbiter answer twice.
_seen_events: dict[str, float] = {}


def _is_duplicate(body: dict) -> bool:
    import time as _t
    eid = (body or {}).get("event_id")
    if not eid:
        return False
    now = _t.time()
    if len(_seen_events) > 500:  # bounded memory
        cutoff = now - 3600
        for k in [k for k, v in _seen_events.items() if v < cutoff]:
            _seen_events.pop(k, None)
    if eid in _seen_events:
        return True
    _seen_events[eid] = now
    return False


@app.event("app_mention")
def handle_mention(event, say, client, body):
    if _is_duplicate(body):
        return
    ts = event.get("thread_ts") or event["ts"]
    ch = event.get("channel")
    text = re.sub(r"<@[^>]+>", "", event.get("text", "")).strip()
    log.info(f"mention ch={ch} len={len(text)} words={judgment._word_count(text)}: {text[:60]!r}")
    cmd = judgment.parse_command(text)
    arg = text.split(" ", 1)[1].strip() if cmd and " " in text else ""

    if cmd == "stats":
        up, down, total = feedback.stats()
        agree = f"{round(100 * up / (up + down))}%" if (up + down) else "n/a"
        say(text=f"📊 Feedback so far: 👍 {up} · 👎 {down} · agreement {agree} (n={total})", thread_ts=ts)
        return
    if cmd == "watch":
        s = _watched(); s.add(ch); _set_watched(s)
        say(text="👁️ Now judging this channel — false claims get flagged, hollow content "
                 "gets a private receipt, forming decisions get their missing voices.",
            thread_ts=ts)
        return
    if cmd == "unwatch":
        s = _watched(); s.discard(ch); _set_watched(s)
        say(text="Stopped monitoring this channel.", thread_ts=ts)
        return
    if cmd == "audit":
        if "canvas" in text.lower():
            ok, res = audit.publish_canvas()
            say(text="🛡️ Audit trail exported to a Canvas." if ok
                 else f":warning: Canvas export failed: `{res}`", thread_ts=ts)
        else:
            say(text=audit.report(), thread_ts=ts)
        return
    if cmd == "ledger":
        resolved = ledger.resolve_due(verify_claim)
        hits, misses = ledger.scoreboard()
        open_preds = ledger.open_predictions()
        lines = [f"🔮 *Prediction ledger* — record: {hits} hit / {misses} miss"]
        for r in resolved:
            lines.append(f"• just resolved *{r['outcome']}*: {r['prediction'][:120]} ({r['author']})")
        if open_preds:
            lines.append("*Open:*")
            lines += [f"• {p['prediction'][:120]} — {p['author']}"
                      + (f" (by {p['resolve_by']})" if p.get("resolve_by") else "")
                      for p in open_preds]
        else:
            lines.append("_No open predictions — I log them automatically when I hear one._")
        say(text="\n".join(lines), thread_ts=ts)
        return
    if cmd == "substance":
        target = arg or (_parent_text(client, ch, ts) if event.get("thread_ts") else "")
        files = event.get("files") or []
        if not target and files and _is_doc(files[0]):
            try:
                target = extract_text(files[0])
            except Exception as e:
                say(text=f":warning: Couldn't read that file: `{e}`", thread_ts=ts)
                return
        if not target:
            say(text="Give me text, a doc, or mention me in a thread — I'll weigh its substance.",
                thread_ts=ts)
            return
        say(text=":scales: Weighing substance…", thread_ts=ts)
        result = substance_mod.score(target)
        say(blocks=_substance_blocks(result), text=f"Substance: {result['score']}/100",
            thread_ts=ts, reply_broadcast=True)
        audit.log_intervention("substance", "mention", ch, result["score"],
                               "posted receipt", target[:120])
        return
    if cmd == "catchup":
        say(text=":wave: Pulling together what you missed…", thread_ts=ts)
        uid = event.get("user", "")
        name = _display_name(client, uid)
        blocks = catchup_mod.build_digest(name, uid, time.time() - 24 * 3600)
        if blocks:
            say(blocks=blocks, text="Here's what you missed", thread_ts=ts)
        else:
            say(text="You're all caught up — nothing needing your attention in the "
                     "last 24h.", thread_ts=ts)
        return
    if cmd == "ask":
        raw = event.get("text", "")
        ids = [u for u in re.findall(r"<@([A-Z0-9]+)>", raw) if u != BOT_USER_ID]
        question = re.sub(r"^\s*ask\b", "", arg or text, count=1, flags=re.I).strip()
        if not ids or not question:
            say(text=f"Usage: `@{BOT_NAME} ask @teammate <question>` — I'll answer "
                     f"from their real messages only, and notify them.", thread_ts=ts)
            return
        target_id = ids[0]
        try:
            prof = client.users_info(user=target_id).get("user", {}).get("profile", {})
        except Exception:
            prof = {}
        names = [n for n in {prof.get("display_name"), prof.get("real_name")} if n]
        if not names:
            say(text="I couldn't resolve that teammate.", thread_ts=ts)
            return
        target_name = max(names, key=len)
        say(text=f":speech_balloon: Checking {target_name}'s record…", thread_ts=ts)
        r = delegate_mod.answer_as(names, question)
        link = _permalink(client, ch, event.get("ts"))
        if r["answerable"]:
            say(blocks=_delegate_blocks(target_name, target_id, r),
                text=f"{target_name}'s record: {r['answer'][:100]}", thread_ts=ts,
                reply_broadcast=True)
            audit.log_intervention("delegate", "mention", ch, 75, "delegate answer",
                                   f"{target_name}: {question[:100]}")
            dm = (f":wave: While you were away, someone asked about your position:\n"
                  f"> {_esc(question, 300)}\nI answered *only from your own messages*"
                  + (f" — <{link}|see the thread>." if link else "."))
        else:
            # Escalation — default is the safe "I don't guess" path. But offer a
            # clearly-labelled OPT-IN pill for a speculative best-guess.
            pill_val = json.dumps({"t": target_id, "n": target_name, "q": question[:300]})
            say(blocks=[
                {"type": "section", "text": {"type": "mrkdwn",
                 "text": f"🗣️ *{_esc(target_name, 60)}* hasn't said enough on the record "
                         f"for me to answer that — I don't put words in people's mouths. "
                         f"I've flagged it for them."}},
                {"type": "actions", "elements": [
                    {"type": "button", "text": {"type": "plain_text",
                     "text": "🔮 Best guess from their style"},
                     "action_id": "delegate_infer", "value": pill_val[:1900]}]}],
                text=f"{target_name} hasn't said enough — escalated", thread_ts=ts)
            audit.log_intervention("delegate", "mention", ch, 40, "escalated to person",
                                   f"{target_name}: {question[:100]}")
            dm = (f":wave: Someone asked something I couldn't answer from your record:\n"
                  f"> {_esc(question, 300)}\n"
                  + (f"<{link}|Jump to the thread> when you have a moment." if link else ""))
        try:
            client.chat_postMessage(channel=target_id, text=dm)
        except Exception as e:
            log.warning(f"delegate DM failed: {e}")
        return
    if cmd == "roundtable":
        raw = event.get("text", "")
        ids = []
        for u in re.findall(r"<@([A-Z0-9]+)(?:\|[^>]+)?>", raw):
            if u != BOT_USER_ID and u not in ids:
                ids.append(u)
        topic = re.sub(r"^\s*(act as|actas|roundtable|debate as|act like|panel of|convene)\b",
                       "", text, count=1, flags=re.I)
        topic = re.sub(r"^\s*(on|about|regarding)\b", "", topic, flags=re.I).strip(" :")
        if len(ids) < 2 or not topic:
            say(text=f"Usage: `@{BOT_NAME} act as @A @B <topic>` — I'll voice two or more "
                     f"teammates from their real messages and have them talk it through to a "
                     f"conclusion.", thread_ts=ts)
            return
        participants = []
        for uid in ids[:4]:
            try:
                prof = client.users_info(user=uid).get("user", {}).get("profile", {})
            except Exception:
                prof = {}
            names = [n for n in {prof.get("display_name"), prof.get("real_name")} if n]
            if names:
                participants.append({"display": max(names, key=len), "names": names})
        if len(participants) < 2:
            say(text="I couldn't resolve enough of those teammates.", thread_ts=ts)
            return
        who = ", ".join(p["display"] for p in participants)
        say(text=f":performing_arts: Convening {who} on _{_esc(topic, 80)}_ — reading their "
                 f"messages…", thread_ts=ts)
        result = roundtable_mod.deliberate(participants, topic)
        say(blocks=_roundtable_blocks(result), text=f"Roundtable on {topic[:80]}",
            thread_ts=ts, reply_broadcast=True)
        audit.log_intervention("roundtable", "mention", ch, 60, "persona roundtable",
                               f"{who}: {topic[:80]}")
        return
    if cmd == "voices":
        target = arg or (_parent_text(client, ch, ts) if event.get("thread_ts") else "")
        if not target:
            say(text="Mention me in a decision thread (or `voices <the decision>`) and "
                     "I'll bring in the missing voices.", thread_ts=ts)
            return
        say(text=":scales: Convening the missing voices…", thread_ts=ts)
        participants = _thread_participants(client, ch, ts)
        q = decisions_mod.analyze(target, participants)
        if q["has_signal"]:
            _post_quorum(lambda **kw: say(thread_ts=ts, **kw), q, target, ch)
            audit.log_intervention("decision", "mention", ch, 80,
                                   "posted missing-voices card", q["topic"])
        else:
            say(text=f"⚖️ I looked for missing voices, past decisions, and a grounded "
                     f"counter-case on *{q['topic'] or 'this'}* — nothing with real "
                     "signal. Proceed.", thread_ts=ts)
        return
    files = event.get("files") or []
    if files:
        f = files[0]
        if _wants_doc_report(text) and _is_doc(f):
            _verify_document(f, say, ts, client=client, channel=event.get("channel"))
        else:
            _verify_file(f, say, ts)
        return
    if not text:
        say(text=f"Give me a claim — or attach an image/PDF/audio — e.g. "
                 f"`@{BOT_NAME} the Great Wall is visible from space`.\n"
                 f"Also: `substance` (weigh a message/doc) · `voices` (missing voices "
                 f"on a decision) · `ledger` (predictions) · `audit` (my transparency "
                 f"report) · `watch` (judge this channel).", thread_ts=ts)
        return
    author = _display_name(client, event.get("user", ""))
    link = _permalink(client, event.get("channel"), event.get("ts"))
    # Long-form mentions aren't claims — let the coordinator pick the judgment
    # (an explicit ask, so the receipt posts in-thread rather than ephemerally).
    if judgment._word_count(text) >= judgment.SUBSTANCE_MIN_WORDS:
        cls = judgment.classify(text)
        if cls["mode"] == "substance":
            say(text=":scales: That's long-form — weighing its substance…", thread_ts=ts)
            result = substance_mod.score(text)
            say(blocks=_substance_blocks(result), text=f"Substance: {result['score']}/100",
                thread_ts=ts)
            audit.log_intervention("substance", "mention", ch, result["score"],
                                   "posted receipt", text[:120])
            return
        if cls["mode"] == "decision":
            say(text=":scales: Convening the missing voices…", thread_ts=ts)
            q = decisions_mod.analyze(text, _thread_participants(client, ch, ts))
            if q["has_signal"]:
                _post_quorum(lambda **kw: say(thread_ts=ts, **kw), q, text, ch)
                audit.log_intervention("decision", "mention", ch, cls["confidence"],
                                       "posted missing-voices card", q["topic"])
            else:
                say(text=f"⚖️ Nothing with real signal on *{_esc(q['topic'] or 'this', 80)}*. "
                         "Proceed.", thread_ts=ts)
            return
    _run_and_reply(text, say, ts, react=(event.get("channel"), event.get("ts")),
                   author=author, permalink=link)


@app.command("/verdict")
@app.command("/arbiter")
def handle_verify(ack, command, say):
    ack()
    text = (command.get("text") or "").strip()
    if not text:
        say(f"Give me a claim, e.g. `/arbiter the moon has no atmosphere` — or "
            f"`/arbiter substance <text>` · `/arbiter voices <decision>`")
        return
    cmd = judgment.parse_command(text)
    arg = text.split(" ", 1)[1].strip() if " " in text else ""
    if cmd == "substance" and arg:
        result = substance_mod.score(arg)
        say(blocks=_substance_blocks(result), text=f"Substance: {result['score']}/100")
        return
    if cmd == "voices" and arg:
        q = decisions_mod.analyze(arg, set())
        if q["has_signal"]:
            say(blocks=_quorum_blocks(q, arg), text=f"Missing voices on: {q['topic']}")
        else:
            say(f"⚖️ Nothing with real signal on *{q['topic'] or 'this'}*. Proceed.")
        return
    _run_and_reply(text, say, None)


# ---- assistant side-pane (dynamic prompts) -------------------------------
assistant = Assistant()


@assistant.thread_started
def _assistant_started(say, set_suggested_prompts):
    say(f"Hi! I'm *{BOT_NAME}* :scales: — your workspace's judgment layer. Send me a "
        "claim to fact-check, paste a long update to weigh its substance, or describe "
        "a decision and I'll find the missing voices.")
    set_suggested_prompts(
        title="Try a judgment:",
        prompts=[
            {"title": "Fact-check a myth",
             "message": "Do humans only use 10% of their brain?"},
            {"title": "Weigh a message",
             "message": "substance In today's fast-paced landscape it's important to "
                        "note that we should leverage synergies and circle back on "
                        "actionable insights to unlock the potential of our robust solution."},
            {"title": "Missing voices",
             "message": "voices We've decided to deprecate the v1 API next sprint."},
            {"title": "Webb telescope",
             "message": "Did the James Webb Space Telescope launch in 2021?"},
        ],
    )


@assistant.user_message
def _assistant_message(payload, say, set_status):
    files = payload.get("files") or []
    if files:
        try:
            set_status("is reading your file…")
        except Exception:
            pass
        try:
            claim = claim_from_file(files[0])
        except Exception as e:
            say(f":warning: Couldn't read that file: `{e}`")
            return
        if not claim or claim.strip().upper().startswith("NONE"):
            say("I couldn't find a checkable factual claim in that file.")
            return
        say(f"Claim from file: *{claim}*")
    else:
        claim = (payload.get("text") or "").strip()
        if not claim:
            say("Send me a claim — or attach an image/PDF — to fact-check.")
            return
    cmd = judgment.parse_command(claim)
    arg = claim.split(" ", 1)[1].strip() if " " in claim else ""
    if cmd == "substance" and arg:
        try:
            set_status("is weighing substance…")
        except Exception:
            pass
        result = substance_mod.score(arg)
        say(blocks=_substance_blocks(result), text=f"Substance: {result['score']}/100")
        return
    if cmd == "voices" and arg:
        try:
            set_status("is convening the missing voices…")
        except Exception:
            pass
        q = decisions_mod.analyze(arg, set())
        if q["has_signal"]:
            say(blocks=_quorum_blocks(q, arg), text=f"Missing voices on: {q['topic']}")
        else:
            say(f"⚖️ No missing voices, past decisions, or grounded counter-case found "
                f"on *{q['topic'] or 'this'}*. Proceed.")
        return
    try:
        set_status("is verifying…")
    except Exception:
        pass
    try:
        thread_id = payload.get("thread_ts") or payload.get("ts") or "assistant"
        data = verify_claim(claim, thread_id=thread_id)
        if data.get("not_claim"):
            say(data["reasoning"])
        else:
            say(blocks=_blocks(claim, data), text=_fallback(data))
    except Exception as e:
        say(f":warning: Something went wrong: `{e}`")


app.use(assistant)


# ---- button interactions -------------------------------------------------
@app.action("reverify")
def _act_reverify(ack, body, say):
    ack()
    claim = (body.get("actions", [{}])[0].get("value") or "").strip()
    msg = body.get("message", {})
    ts = msg.get("thread_ts") or msg.get("ts")
    if claim:
        _run_and_reply(claim, say, ts)


@app.action("show_panel")
def _act_show_panel(ack, body, say):
    ack()
    ptext = body.get("actions", [{}])[0].get("value") or "(no panel detail)"
    msg = body.get("message", {})
    ts = msg.get("thread_ts") or msg.get("ts")
    say(text=f"*Panel detail:*\n{_esc(ptext)}", thread_ts=ts)


def _log_vote(body, vote):
    try:
        v = json.loads(body["actions"][0]["value"])
        feedback.log_feedback(v.get("claim", ""), v.get("verdict", ""), vote)
        # Close the loop: this vote nudges the mode's intervention threshold.
        learning.record(v.get("mode", "claim"), vote)
    except Exception:
        pass


@app.action("delegate_infer")
def _act_delegate_infer(ack, body, client):
    """Opt-in speculation — fires only when a human clicks 'best guess'. The
    result is explicitly labelled as inference, never a stated position."""
    ack()
    try:
        v = json.loads(body["actions"][0]["value"])
    except Exception:
        return
    ch = (body.get("channel") or {}).get("id")
    msg = body.get("message", {})
    ts = msg.get("thread_ts") or msg.get("ts")
    target_id, name, question = v.get("t", ""), v.get("n", ""), v.get("q", "")
    try:
        prof = client.users_info(user=target_id).get("user", {}).get("profile", {})
        names = [n for n in {prof.get("display_name"), prof.get("real_name"), name} if n]
    except Exception:
        names = [name]
    r = delegate_mod.infer_as(names, question)
    if not r.get("guess"):
        client.chat_postMessage(channel=ch, thread_ts=ts,
                                text=f"Not enough of {name}'s writing to even infer from.")
        return
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn",
         "text": f"🔮 *Best guess — how {_esc(name, 60)} might lean*"}},
        {"type": "context", "elements": [{"type": "mrkdwn",
         "text": f"⚠️ This is Arbiter's *inference* from {_esc(name, 60)}'s style and "
                 f"past messages — NOT their stated position. Confirm with them."}]},
        {"type": "section", "text": {"type": "mrkdwn", "text": _esc(r["guess"], 700)}},
    ]
    for i, c in enumerate(r["quotes"]):
        link = f" (<{c['url']}|basis>)" if c.get("url") else ""
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": f"[{i+1}] “{_esc(c['quote'], 180)}”{link}"}]})
    infer_val = json.dumps({"vote": "up", "mode": "delegate", "n": name})
    infer_down = json.dumps({"vote": "down", "mode": "delegate", "n": name})
    blocks.append({"type": "actions", "elements": [
        {"type": "button", "text": {"type": "plain_text", "text": "👍"},
         "action_id": "fb_up", "value": infer_val},
        {"type": "button", "text": {"type": "plain_text", "text": "👎"},
         "action_id": "fb_down", "value": infer_down}]})
    client.chat_postMessage(channel=ch, thread_ts=ts, blocks=blocks,
                            text=f"Best guess: how {name} might lean")
    audit.log_intervention("delegate", "infer-optin", ch, 30,
                           "labelled inference (user-requested)", f"{name}: {question[:80]}")


@app.action("catchup_up")
def _act_catchup_up(ack, body, respond):
    ack()
    try:
        import json as _json
        v = _json.loads(body["actions"][0]["value"])
        catchup_mod.record_digest_feedback(v.get("user", ""), "up")
        respond({"response_type": "ephemeral", "text": "Thanks — I'll keep digests like this."})
    except Exception:
        pass


@app.action("catchup_down")
def _act_catchup_down(ack, body, respond):
    ack()
    try:
        import json as _json
        v = _json.loads(body["actions"][0]["value"])
        catchup_mod.record_digest_feedback(v.get("user", ""), "down")
        respond({"response_type": "ephemeral", "text": "Got it — I'll surface less next time."})
    except Exception:
        pass


@app.action("fb_up")
def _act_fb_up(ack, body, respond):
    ack()
    _log_vote(body, "up")
    try:
        respond({"response_type": "ephemeral", "text": "Thanks for the 👍 — logged."})
    except Exception:
        pass


@app.action("fb_down")
def _act_fb_down(ack, body, respond):
    ack()
    _log_vote(body, "down")
    try:
        respond({"response_type": "ephemeral", "text": "Thanks — logged the 👎 to improve."})
    except Exception:
        pass


def _away_delegate(event, client, ch, ts) -> bool:
    """When a question in a watched channel mentions exactly one teammate and
    that teammate is AWAY, their delegate steps in automatically — answering
    from their record (all fidelity gates apply) or flagging them. The absent
    colleague is covered the moment someone needs them."""
    raw = event.get("text", "")
    ids = [u for u in re.findall(r"<@([A-Z0-9]+)>", raw) if u != BOT_USER_ID]
    if len(ids) != 1 or "?" not in raw or ids[0] == event.get("user"):
        return False
    target = ids[0]
    try:
        if client.users_getPresence(user=target).get("presence") != "away":
            return False
        prof = client.users_info(user=target).get("user", {}).get("profile", {})
    except Exception:
        return False
    names = [n for n in {prof.get("display_name"), prof.get("real_name")} if n]
    if not names:
        return False
    name = max(names, key=len)
    question = re.sub(r"<@[^>]+>", "", raw).strip()
    log.info(f"away-delegate: {name} is away, stepping in for {question[:60]!r}")
    r = delegate_mod.answer_as(names, question)
    link = _permalink(client, ch, event.get("ts"))
    if r["answerable"]:
        blocks = [{"type": "context", "elements": [{"type": "mrkdwn",
                   "text": f"🕐 <@{target}> appears to be away — their delegate is stepping in."}]}]
        blocks += _delegate_blocks(name, target, r)
        client.chat_postMessage(channel=ch, thread_ts=ts, blocks=blocks,
                                text=f"{name} is away — their record says: {r['answer'][:80]}")
        audit.log_intervention("delegate", "away-detect", ch, 75,
                               "auto-answered for away teammate", f"{name}: {question[:80]}")
        dm = (f":wave: You were away when someone asked about your position:\n"
              f"> {_esc(question, 300)}\nYour delegate answered *only from your own "
              f"messages*" + (f" — <{link}|see the thread>." if link else "."))
    else:
        client.chat_postMessage(channel=ch, thread_ts=ts,
                                text=f"🕐 <@{target}> appears to be away and their record "
                                     f"doesn't answer this — I've flagged it for them.")
        audit.log_intervention("delegate", "away-detect", ch, 40,
                               "flagged away teammate", f"{name}: {question[:80]}")
        dm = (f":wave: You were away when someone asked you:\n> {_esc(question, 300)}\n"
              + (f"<{link}|Jump to the thread> when you're back." if link else ""))
    try:
        client.chat_postMessage(channel=target, text=dm)
    except Exception as e:
        log.warning(f"away-delegate DM failed: {e}")
    return True


# ---- proactive judgment: the full cascade runs in watched channels ------------
# heuristics (free) → fast-model classifier → ONE winning mode's pipeline.
# Private-first: substance receipts go only to the author (ephemeral);
# fact-flags and quorum cards protect the thread, so they post in-thread.
@app.event("message")
def on_message(event, client, body):
    # Judge humans AND other bots (agent workslop is exactly in scope) — but never
    # ourselves (loop safety), and never edits/joins/etc. Note: messages posted via
    # API tokens carry bot_id even for real users, so bot_id must NOT be a filter.
    if _is_duplicate(body):
        return
    if event.get("subtype"):
        return
    ch = event.get("channel")
    text = (event.get("text") or "").strip()
    user = event.get("user")
    if BOT_USER_ID and (user == BOT_USER_ID or f"<@{BOT_USER_ID}>" in text):
        return  # our own posts / @mentions (handled by app_mention)
    if ch not in _watched() or len(text) < judgment.CLAIM_MIN_CHARS:
        return
    ts_early = event.get("ts")
    if _away_delegate(event, client, ch, ts_early):
        return  # one intervention max — the delegate covered it

    cls = judgment.classify(text)
    mode = cls["mode"]
    if not mode:
        return
    log.info(f"cascade mode={mode} conf={cls['confidence']} ch={ch}: {text[:60]!r}")
    ts = event.get("ts")

    if mode == "decision":
        q = decisions_mod.analyze(text, _thread_participants(client, ch,
                                                             event.get("thread_ts") or ts))
        if q["has_signal"]:
            _post_quorum(lambda **kw: client.chat_postMessage(
                channel=ch, thread_ts=ts, **kw), q, text, ch)
            audit.log_intervention("decision", "watch", ch, cls["confidence"],
                                   "posted missing-voices card", q["topic"])
        return

    if mode == "substance":
        result = substance_mod.score(text)
        log.info(f"cascade substance score={result['score']} (intervene if <45)")
        if result["score"] < 45 and user:  # only intervene on genuinely hollow content
            try:
                client.chat_postEphemeral(
                    channel=ch, user=user,
                    blocks=_substance_blocks(result, "visible only to you"),
                    text=f"Substance: {result['score']}/100")
                audit.log_intervention("substance", "watch", ch, result["score"],
                                       "private receipt to author", text[:120])
            except Exception as e:
                log.warning(f"ephemeral receipt failed: {e}")
        return

    # mode == "claim" — the classic proactive fact-flag
    data = verify_claim(text)
    if data.get("not_claim"):
        return
    try:
        conf = float(data.get("confidence", 0))
    except Exception:
        conf = 0
    author = _display_name(client, user) if user else ""
    link = _permalink(client, ch, ts)
    if author:
        try:  # every claim feeds the credit + prediction ledgers, flagged or not
            _kg.save_claim(text, str(data.get("verdict", "")), int(conf),
                           data.get("sources_resolved", []),
                           author=author, permalink=link)
            p = ledger.detect_prediction(text)
            if p:
                ledger.log_prediction(p["prediction"], author, p["resolve_by"], link)
                mcp_client.add_reaction(ch, ts, "crystal_ball")
        except Exception:
            pass
    # learned threshold: 👎 on flagged claims makes proactive flagging more reserved
    if str(data.get("verdict")) in ("False", "Misleading") and conf >= learning.threshold("claim"):
        mcp_client.add_reaction(ch, ts, "warning")
        data["mcp_acted"] = True
        blocks = _blocks(text, data)
        credit = ledger.credit_line(text, author) if author else ""
        if credit:
            blocks.insert(-1, {"type": "context",
                               "elements": [{"type": "mrkdwn", "text": credit}]})
        client.chat_postMessage(channel=ch, thread_ts=ts,
                                blocks=blocks, text=_fallback(data), reply_broadcast=True)
        audit.log_intervention("claim", "watch", ch, int(conf),
                               "flagged false claim", text[:120])


# ---- App Home: the judgment dashboard --------------------------------------
def _home_blocks() -> list:
    import datetime as _dt
    recs = audit._recent(50)
    week_ago = (_dt.datetime.now() - _dt.timedelta(days=7)).timestamp()
    week = [r for r in recs if r.get("ts", 0) >= week_ago]
    by_mode: dict[str, int] = {}
    for r in week:
        by_mode[r.get("mode", "?")] = by_mode.get(r.get("mode", "?"), 0) + 1
    up, down, _ = feedback.stats()
    agree = f"{round(100 * up / (up + down))}%" if (up + down) else "—"
    hits, misses = ledger.scoreboard()
    open_preds = ledger.open_predictions(5)
    sub_scores = [r.get("confidence", 0) for r in week if r.get("mode") == "substance"]
    avg_sub = round(sum(sub_scores) / len(sub_scores)) if sub_scores else None

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "emoji": True,
         "text": "⚖️ Arbiter — the workspace's judgment layer"}},
        {"type": "context", "elements": [{"type": "mrkdwn",
         "text": "One brain, three verdicts: *claims* (fact-check) · *content* "
                 "(substance receipts) · *decisions* (missing voices)."}]},
        {"type": "divider"},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*This week:*\n{len(week)} interventions"},
            {"type": "mrkdwn", "text": "*By mode:*\n" + (" · ".join(
                f"{m} {n}" for m, n in sorted(by_mode.items())) or "—")},
            {"type": "mrkdwn", "text": f"*Human agreement:*\n{agree} (👍 {up} / 👎 {down})"},
            {"type": "mrkdwn", "text": f"*Prediction record:*\n{hits} hit / {misses} miss"},
        ]},
    ]
    if avg_sub is not None:
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
            "text": f"Avg substance score of flagged content this week: {avg_sub}/100"}]})
    if open_preds:
        lines = "\n".join(
            f"• {p['prediction'][:100]} — _{p['author']}_"
            + (f" (by {p['resolve_by']})" if p.get("resolve_by") else "")
            for p in open_preds)
        blocks += [{"type": "divider"},
                   {"type": "section", "text": {"type": "mrkdwn",
                    "text": f"🔮 *Open predictions:*\n{lines}"}}]
    if recs:
        last = recs[0]
        blocks += [{"type": "divider"},
                   {"type": "context", "elements": [{"type": "mrkdwn",
                    "text": f"Latest: [{last.get('mode')}] {str(last.get('summary',''))[:100]} · "
                            f"every intervention is audited — `@{BOT_NAME} audit`"}]}]
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn",
        "text": f"Try: `@{BOT_NAME} <claim>` · right-click any message → *Judge this "
                f"message* · `@{BOT_NAME} watch` to judge a channel proactively"}]})
    return blocks


@app.event("app_home_opened")
def handle_home_opened(event, client):
    if event.get("tab") != "home":
        return
    try:
        client.views_publish(user_id=event["user"],
                             view={"type": "home", "blocks": _home_blocks()})
    except Exception as e:
        log.warning(f"home views_publish failed: {e}")


# ---- message shortcut: right-click → "Judge this message" ------------------
# The clicker asked, so we answer the clicker. Private-first still applies:
# substance receipts about someone's writing go ephemeral to the CLICKER;
# fact-checks and quorum cards protect the thread, so they post in-thread.
@app.shortcut("judge_message")
def handle_judge_shortcut(ack, body, client):
    ack()
    msg = body.get("message", {}) or {}
    ch = (body.get("channel") or {}).get("id")
    clicker = (body.get("user") or {}).get("id")
    ts = msg.get("thread_ts") or msg.get("ts")
    text = re.sub(r"<@[^>]+>", "", msg.get("text") or "").strip()
    if not ch or not text:
        return

    def _ephemeral(**kw):
        try:
            client.chat_postEphemeral(channel=ch, user=clicker, **kw)
        except Exception:
            pass

    cls = judgment.classify(text)
    mode = cls["mode"]

    if mode == "substance" or (mode is None and judgment._word_count(text) >= 40):
        # explicit ask on borderline-length text still gets a receipt
        result = substance_mod.score(text)
        _ephemeral(blocks=_substance_blocks(result, "visible only to you"),
                   text=f"Substance: {result['score']}/100")
        audit.log_intervention("substance", "shortcut", ch, result["score"],
                               "private receipt to clicker", text[:120])
        return
    if mode == "decision":
        q = decisions_mod.analyze(text, _thread_participants(client, ch, ts))
        if q["has_signal"]:
            _post_quorum(lambda **kw: client.chat_postMessage(
                channel=ch, thread_ts=ts, **kw), q, text, ch)
            audit.log_intervention("decision", "shortcut", ch, cls["confidence"],
                                   "posted missing-voices card", q["topic"])
        else:
            _ephemeral(text=f"⚖️ No missing voices, past decisions, or grounded "
                            f"counter-case found on *{q['topic'] or 'this'}*.")
        return
    if mode == "claim":
        def _say(**kw):
            client.chat_postMessage(channel=ch, **kw)
        _run_and_reply(text, _say, ts, react=(ch, msg.get("ts")), trigger="shortcut")
        return
    _ephemeral(text="I couldn't find a claim, decision, or long-form content to "
                    "judge in that message.")


# ---- 🔍 reaction trigger: react to any message to fact-check it -----------
@app.event("reaction_added")
def handle_reaction(event, client):
    if event.get("reaction") != "mag":   # only the 🔍 emoji triggers a check
        return
    item = event.get("item", {}) or {}
    ch, ts = item.get("channel"), item.get("ts")
    if not ch or not ts:
        return
    try:
        resp = client.conversations_history(channel=ch, latest=ts, inclusive=True, limit=1)
        msgs = resp.get("messages", [])
    except Exception:
        return
    text = re.sub(r"<@[^>]+>", "", (msgs[0].get("text", "") if msgs else "")).strip()
    if not text:
        return

    def _say(**kw):
        client.chat_postMessage(channel=ch, **kw)

    _run_and_reply(text, _say, ts, react=(ch, ts))


def _keepalive_loop():
    """Daily heartbeat: touch Neo4j so Aura's free tier never idle-pauses
    mid-judging, and leave a liveness line in the log."""
    import time as _t
    from memory import _get_neo4j
    while True:
        _t.sleep(12 * 3600)
        try:
            d = _get_neo4j()
            if d:
                with d.session() as s:
                    s.run("RETURN 1")
            log.info("keepalive: bot alive, neo4j touched")
        except Exception as e:
            log.warning(f"keepalive: neo4j ping failed: {e}")


def _health_server():
    """Tiny HTTP liveness endpoint — lets free-tier hosts (which sleep idle web
    services) keep the bot awake via an external uptime pinger. Only runs when
    the host injects PORT; local runs skip it."""
    port = os.environ.get("PORT")
    if not port:
        return
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class _H(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"{BOT_NAME} alive".encode())

        def do_HEAD(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass  # keep pinger noise out of the logs

    import threading
    srv = HTTPServer(("0.0.0.0", int(port)), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    log.info(f"health endpoint listening on :{port}")


if __name__ == "__main__":
    import threading
    _health_server()
    threading.Thread(target=_keepalive_loop, daemon=True).start()
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    log.info(f"{BOT_NAME} is running (Socket Mode) using {PROVIDER}/{MODEL} — "
             f"judging claims, substance, and decisions.")
    handler.start()
