"""Verdict's brain — LangGraph-orchestrated multi-agent debate pipeline.

Graph flow:
  route → [not a claim?] → END
        → evidence → [high-confidence simple?] → synthesize → save → END
                   → [complex / uncertain]     → debate → contrarian → synthesize → save → END

Improvements applied (research-backed):
  - Dynamic role assignment: Skeptic / Advocate / Analyst prompts (arxiv 2601.17152, +74.8%)
  - Sequential debate: Skeptic runs first; Advocate+Analyst see its verdict (arxiv 2507.19090)
  - Adaptive debate skipping: fast confidence gate after evidence (arxiv 2504.05047)
  - Corrective RAG: evidence sorted by relevance before debaters see it (humanloop 2025)
  - KG context injected into debaters, not just synthesizer (GKMAD, ScienceDirect 2025)
  - Anonymized panel identities in synthesizer prompt to prevent sycophancy (arxiv 2510.07517)
  - Self-consistency: synthesizer runs 3x when panel is split; majority vote (Wang et al.)
"""
import os
import re
import json
import operator
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict, Annotated

import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import ToolNode
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from tools import web_search, wikipedia_search, google_factcheck, slack_search, EVIDENCE_TOOLS
import memory as _memory
import knowledge_graph as _kg
from arblog import get_logger

_log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------
_PROVIDERS = {
    "nvidia":     ("https://integrate.api.nvidia.com/v1",                      "NVIDIA_API_KEY"),
    "cerebras":   ("https://api.cerebras.ai/v1",                               "CEREBRAS_API_KEY"),
    "groq":       ("https://api.groq.com/openai/v1",                           "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1",                             "OPENROUTER_API_KEY"),
    "gemini":     ("https://generativelanguage.googleapis.com/v1beta/openai",  "GEMINI_API_KEY"),
    "openai":     ("https://api.openai.com/v1",                                "OPENAI_API_KEY"),
    "anthropic":  ("https://api.anthropic.com/v1",                             "ANTHROPIC_API_KEY"),
}

_DEFAULT_DEBATERS = (
    "nvidia:meta/llama-4-maverick-17b-128e-instruct,"
    "nvidia:qwen/qwen3.5-122b-a10b,"
    "nvidia:google/gemma-3-27b-it"
)
_FAST = "nvidia:meta/llama-4-maverick-17b-128e-instruct"


def _pm(s: str) -> tuple[str, str]:
    provider, model = s.split(":", 1)
    return provider.strip(), model.strip()


DEBATERS = [_pm(x) for x in os.environ.get("VERDICT_DEBATERS", _DEFAULT_DEBATERS).split(",") if x.strip()]
SYNTH    = _pm(os.environ.get("VERDICT_SYNTH",   _FAST))
ROUTER   = _pm(os.environ.get("VERDICT_ROUTER",  _FAST))
PROVIDER, MODEL = SYNTH  # for card footer / app.py

# ---------------------------------------------------------------------------
# Client factories
# ---------------------------------------------------------------------------
_raw_clients: dict[str, OpenAI] = {}


def _extra_headers(provider: str, key: str) -> dict:
    """Anthropic's OpenAI-compat endpoint authenticates via x-api-key, not Bearer."""
    if provider == "anthropic":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    return {}


# Circuit-breaker: no call may hang the pipeline. Retries handle transient
# failures; this bounds the worst case a judge can experience.
_CALL_TIMEOUT = float(os.environ.get("ARBITER_LLM_TIMEOUT", "60"))


def _raw_client(provider: str) -> OpenAI:
    if provider not in _raw_clients:
        base, keyvar = _PROVIDERS[provider]
        key = os.environ[keyvar]
        _raw_clients[provider] = OpenAI(base_url=base, api_key=key,
                                        timeout=_CALL_TIMEOUT,
                                        default_headers=_extra_headers(provider, key))
    return _raw_clients[provider]


def _lc_client(provider: str, model: str) -> ChatOpenAI:
    base, keyvar = _PROVIDERS[provider]
    key = os.environ[keyvar]
    return ChatOpenAI(base_url=base, api_key=key, model=model, temperature=0,
                      timeout=_CALL_TIMEOUT,
                      default_headers=_extra_headers(provider, key) or None)


def _chat(provider: str, model: str, system: str, user: str,
          temperature: float | None = None, retries: int = 2) -> str:
    """One chat call with retry — free-tier providers throw transient 5xx."""
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = _raw_client(provider).chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system},
                          {"role": "user",   "content": user}],
                **kwargs,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            last_err = e
            if attempt < retries:
                import time as _t
                _t.sleep(1.5 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def _parse(raw: str) -> dict:
    try:
        s, e = raw.find("{"), raw.rfind("}")
        return json.loads(raw[s:e + 1])
    except Exception:
        return {}


def _short(model: str) -> str:
    return model.split("/")[-1]


_tool_node = ToolNode(EVIDENCE_TOOLS)
_TOOL_MAP  = {t.name: t for t in EVIDENCE_TOOLS}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
ROUTER_SYSTEM = (
    "You are the router for a fact-checking bot. Classify the INPUT. Respond ONLY with JSON: "
    '"is_claim" (boolean: true ONLY for checkable factual statements; false for greetings, '
    "questions, opinions, chit-chat), "
    '"complexity" ("simple" for well-known facts; "complex" for contested, nuanced, recent claims), '
    '"message" (if is_claim is false: one friendly sentence asking for a factual claim).'
)

# Dynamic role prompts (arxiv 2601.17152) — replaces single DEBATER_SYSTEM
SKEPTIC_SYSTEM = (
    "You are the SKEPTIC on a fact-checking panel. Judge the CLAIM using the EVIDENCE. "
    "Lean toward False or Misleading — but only if evidence supports it. "
    "FACTCHECK sources (Snopes, PolitiFact, Reuters) outweigh web sources. "
    "You MUST pick True/False/Misleading — only use Unverifiable if zero relevant evidence exists. "
    "Respond with ONLY this JSON and nothing else: "
    '{"verdict":"False","confidence":75,"reasoning":"your reasoning here"}'
)

ADVOCATE_SYSTEM = (
    "You are the ADVOCATE on a fact-checking panel. Judge the CLAIM using the EVIDENCE. "
    "Lean toward True — but only if evidence supports it. "
    "A prior panelist verdict is shown below — challenge it if evidence points elsewhere. "
    "FACTCHECK sources (Snopes, PolitiFact, Reuters) outweigh web sources. "
    "You MUST pick True/False/Misleading — only use Unverifiable if zero relevant evidence exists. "
    "Respond with ONLY this JSON and nothing else: "
    '{"verdict":"True","confidence":75,"reasoning":"your reasoning here"}'
)

ANALYST_SYSTEM = (
    "You are the NEUTRAL ANALYST on a fact-checking panel. Judge the CLAIM using the EVIDENCE. "
    "Weigh all sources objectively — do not just agree with prior panelists. "
    "FACTCHECK sources (Snopes, PolitiFact, Reuters) outweigh web sources. "
    "You MUST pick True/False/Misleading — only use Unverifiable if zero relevant evidence exists. "
    "Respond with ONLY this JSON and nothing else: "
    '{"verdict":"False","confidence":75,"reasoning":"your reasoning here"}'
)

_ROLE_PROMPTS = {"skeptic": SKEPTIC_SYSTEM, "advocate": ADVOCATE_SYSTEM, "analyst": ANALYST_SYSTEM}
_ROLES        = ["skeptic", "advocate", "analyst"]

CONTRARIAN_SYSTEM = (
    "You are the devil's advocate on a fact-checking panel. Your ONLY job is to challenge "
    "the current consensus and prevent false confidence. Read the panelist opinions and evidence. "
    "Identify the STRONGEST argument against the majority verdict — weak evidence, recency gaps, "
    "missing context, or overlooked counter-sources. Do NOT simply agree with the panel. "
    "Respond with ONLY JSON: "
    '"verdict" (the verdict you are challenging FOR), "confidence" (0-100 int), '
    '"challenge" (1-2 sentences: the strongest counterargument or what the panel overlooked).'
)

SYNTH_SYSTEM = (
    "You are Verdict's lead fact-checker. Given a CLAIM, numbered EVIDENCE (WEB/WIKI/FACTCHECK/SLACK), "
    "PANELIST OPINIONS (anonymized A/B/C), and a CONTRARIAN CHALLENGE, produce the final verdict. "
    "FACTCHECK sources (human fact-checkers) should be weighted highest. "
    "Where panelists disagree or the contrarian raises a valid point, LOWER your confidence. "
    "If a SLACK (internal workspace) message contradicts the claim, call that out explicitly. "
    "Write reasoning in the same language as the claim. "
    "Respond with ONLY JSON (no prose, no code fences): "
    '"verdict" (True/False/Misleading/Unverifiable), "confidence" (0-100 int), '
    '"reasoning" (1-3 sentences), '
    '"sources" (array of evidence numbers that support the verdict), '
    '"topic" (one word: general/health/science/news/finance/legal/politics).'
)

_FAST_CHECK_SYSTEM = (
    "Quick fact-check. Given CLAIM and EVIDENCE, respond ONLY with JSON: "
    '"verdict" (True/False/Misleading/Unverifiable), "confidence" (0-100 int).'
)

_BASELINE_SYSTEM = (
    "You are a fact-checker. Judge using ONLY your own knowledge (no external evidence). "
    "Respond with ONLY JSON: "
    '"verdict" (True/False/Misleading/Unverifiable), "confidence" (0-100), "reasoning" (1 sentence).'
)

# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------
def route(claim: str) -> dict:
    try:
        d = _parse(_chat(ROUTER[0], ROUTER[1], ROUTER_SYSTEM, f"INPUT: {claim}"))
        comp = d.get("complexity")
        return {"is_claim": bool(d.get("is_claim", True)),
                "complexity": comp if comp in ("simple", "complex") else "complex",
                "message": str(d.get("message", ""))}
    except Exception:
        return {"is_claim": True, "complexity": "complex", "message": ""}


def _score_relevance(claim: str, content: str) -> float:
    """Keyword overlap score for Corrective RAG evidence sorting."""
    claim_words = set(w.lower() for w in re.findall(r"[a-zA-Z]+", claim) if len(w) > 3)
    if not claim_words:
        return 1.0
    content_lower = content.lower()
    return sum(1 for w in claim_words if w in content_lower) / len(claim_words)


def _build_evidence(claim: str) -> tuple[list[dict], str]:
    """Fetch all 4 evidence sources IN PARALLEL, then sort by relevance (Corrective RAG)."""
    evidence: list[dict] = []
    seen: set[str] = set()

    def _collect(items: list[dict], kind: str) -> None:
        for e in items:
            url = e.get("url", "")
            if url and url not in seen:
                seen.add(url)
                evidence.append({**e, "kind": kind})

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {
            ex.submit(web_search,       claim, 4): "WEB",
            ex.submit(wikipedia_search, claim, 2): "WIKI",
            ex.submit(google_factcheck, claim, 3): "FACTCHECK",
            ex.submit(slack_search,     claim, 3): "SLACK",
        }
        for fut in as_completed(futs):
            kind = futs[fut]
            try:
                _collect(fut.result(), kind)
            except Exception:
                pass

    # Corrective RAG: sort by relevance; always keep FACTCHECK at top
    evidence.sort(
        key=lambda e: (2.0 if e.get("kind") == "FACTCHECK"
                       else _score_relevance(claim, e.get("content", ""))),
        reverse=True,
    )

    ev_text = (
        "\n\n".join(
            f"[{i+1}] ({e['kind']}) {e['title']} — {e['url']}\n{e['content'][:500]}"
            for i, e in enumerate(evidence)
        )
        if evidence else "(no search results found)"
    )
    return evidence, ev_text


def _run_debater(pm: tuple[str, str], base_msg: str, role: str = "analyst") -> dict:
    """Single debater with dynamic role prompt. Falls back to plain completion if needed."""
    provider, model = pm
    system = _ROLE_PROMPTS.get(role, ANALYST_SYSTEM)

    try:
        llm = _lc_client(provider, model).bind_tools(EVIDENCE_TOOLS)
        messages = [SystemMessage(system), HumanMessage(base_msg)]

        for _ in range(2):
            response = llm.invoke(messages)
            messages.append(response)
            if not response.tool_calls:
                break
            with ThreadPoolExecutor(max_workers=len(response.tool_calls)) as ex:
                tc_futs = [
                    (tc["id"], ex.submit(_TOOL_MAP[tc["name"]].invoke, tc["args"]))
                    for tc in response.tool_calls if tc["name"] in _TOOL_MAP
                ]
            for tool_call_id, fut in tc_futs:
                try:
                    result = str(fut.result(timeout=15))
                except Exception as e:
                    result = f"Tool error: {e}"
                messages.append(ToolMessage(content=result, tool_call_id=tool_call_id))

        if getattr(response, "tool_calls", None):
            response = _lc_client(provider, model).invoke(messages)

        d = _parse(response.content if hasattr(response, "content") else str(response))
    except Exception:
        d = {}

    # Fallback to plain completion if bind_tools gave empty/bad result
    if not d or (str(d.get("verdict", "")) == "Unverifiable" and int(d.get("confidence", 0)) == 0):
        try:
            raw = _chat(provider, model, system, base_msg)
            d = _parse(raw)
        except Exception as ex:
            return {"model": _short(model), "role": role, "verdict": "Error",
                    "confidence": 0, "reasoning": str(ex)[:120]}

    return {
        "model":      _short(model),
        "role":       role,
        "verdict":    str(d.get("verdict", "Unverifiable")),
        "confidence": int(d.get("confidence", 0)),
        "reasoning":  str(d.get("reasoning", "")),
    }


def _debate(base_msg: str) -> list[dict]:
    """Sequential-then-parallel debate with dynamic roles (arxiv 2507.19090 + 2601.17152).

    Skeptic runs first. Advocate and Analyst then run in parallel, each seeing the
    Skeptic's verdict — forcing real disagreement rather than parallel groupthink.
    """
    if not DEBATERS:
        return []

    # Step 1: Skeptic runs first
    skeptic_role = _ROLES[0]
    skeptic = _run_debater(DEBATERS[0], base_msg, role=skeptic_role)
    results = [skeptic]

    if len(DEBATERS) == 1:
        return results

    # Step 2: remaining debaters see Skeptic's verdict (sequential context)
    prior_text = (
        f"Panelist A (Skeptic): {skeptic['verdict']} ({skeptic['confidence']}%) "
        f"— {skeptic['reasoning']}"
    )
    followup_msg = (
        base_msg
        + f"\n\nPRIOR PANELIST VERDICT (challenge or build on this if evidence supports it):\n{prior_text}"
    )

    remaining = list(zip(DEBATERS[1:], _ROLES[1:]))
    with ThreadPoolExecutor(max_workers=len(remaining)) as ex:
        futs = {ex.submit(_run_debater, pm, followup_msg, role): role
                for pm, role in remaining}
    for fut in as_completed(futs):
        try:
            results.append(fut.result())
        except Exception as e:
            results.append({"model": "?", "role": futs[fut],
                            "verdict": "Error", "confidence": 0, "reasoning": str(e)[:80]})

    return results


def _run_contrarian(base_msg: str, panel: list[dict]) -> dict:
    # Anonymized panel for contrarian too
    panel_text = "\n".join(
        f"- Panelist {chr(65+i)}: {p['verdict']} ({p['confidence']}%) — {p['reasoning']}"
        for i, p in enumerate(panel)
    )
    user = f"{base_msg}\n\nPANEL CONSENSUS:\n{panel_text}\n\nChallenge the majority verdict."
    try:
        d = _parse(_chat(SYNTH[0], SYNTH[1], CONTRARIAN_SYSTEM, user))
        return {
            "verdict":    str(d.get("verdict", "")),
            "confidence": d.get("confidence", 0),
            "challenge":  str(d.get("challenge", "")),
        }
    except Exception:
        return {}


def _resolve_sources(data: dict, evidence: list[dict]) -> list[dict]:
    resolved = []
    for n in (data.get("sources") or []):
        try:
            i = int(n) - 1
            if 0 <= i < len(evidence):
                resolved.append({"title": evidence[i]["title"],
                                 "url":   evidence[i]["url"],
                                 "kind":  evidence[i]["kind"]})
        except Exception:
            pass
    if not resolved and evidence:
        resolved = [{"title": e["title"], "url": e["url"], "kind": e["kind"]}
                    for e in evidence[:3]]
    return resolved


def decompose_claims(text: str, max_n: int = 4) -> list[str]:
    sys = (f"Extract up to {max_n} distinct, checkable factual claims from the text, each as "
           "one self-contained sentence. Respond ONLY with a JSON array of strings. If none, [].")
    raw = _chat(SYNTH[0], SYNTH[1], sys, text[:6000])
    try:
        s, e = raw.find("["), raw.rfind("]")
        return [str(x) for x in json.loads(raw[s:e + 1])][:max_n]
    except Exception:
        return []


def verify_baseline(claim: str) -> dict:
    d = _parse(_chat(SYNTH[0], SYNTH[1], _BASELINE_SYSTEM, f"Claim: {claim}"))
    return d or {"verdict": "Unverifiable", "confidence": 0}


# ---------------------------------------------------------------------------
# LangGraph state + nodes
# ---------------------------------------------------------------------------
class VerdictState(TypedDict):
    claim:          str
    is_claim:       bool
    complexity:     str
    not_claim_msg:  str
    evidence:       list[dict]
    ev_text:        str
    fast_check:     dict        # adaptive debate gate result
    panel:          list[dict]
    council_meta:   dict        # rounds / convergence / DART info from council.py
    contrarian:     dict
    verdict_data:   dict
    thread_history: Annotated[list[dict], operator.add]


def _route_node(state: VerdictState) -> VerdictState:
    r = route(state["claim"])
    return {"is_claim":      r["is_claim"],
            "complexity":    r.get("complexity", "complex"),
            "not_claim_msg": r.get("message", "")}


def _evidence_node(state: VerdictState) -> VerdictState:
    """Parallel fetch + Corrective RAG sort + adaptive debate confidence gate."""
    evidence, ev_text = _build_evidence(state["claim"])

    # Fast check for adaptive debate skipping (arxiv 2504.05047)
    fast_check = {}
    try:
        raw = _chat(ROUTER[0], ROUTER[1], _FAST_CHECK_SYSTEM,
                    f"CLAIM: {state['claim']}\n\nEVIDENCE:\n{ev_text[:1500]}")
        fast_check = _parse(raw)
    except Exception:
        pass

    return {"evidence": evidence, "ev_text": ev_text, "fast_check": fast_check}


def _debate_node(state: VerdictState) -> VerdictState:
    """Council debate (Lymerorium doctrine: convergence early-stop, Free-MAD
    round 2, DART dispute search). ARBITER_COUNCIL=0 falls back to the classic
    single-round sequential panel."""
    kg_ctx = _kg.find_related(state["claim"])
    base_msg = (
        f"CLAIM: {state['claim']}\n\n"
        f"EVIDENCE (pre-gathered):\n{state['ev_text']}\n\n"
        + (f"RELATED VERIFIED CLAIMS (knowledge graph):\n{kg_ctx}\n\n" if kg_ctx else "")
        + "Judge the claim from the evidence. Use search tools only to verify a specific detail."
    )
    import council as _council
    if _council.COUNCIL_ENABLED and len(DEBATERS) >= 2:
        out = _council.run_council(base_msg)
        return {"panel": out["panel"], "council_meta": out["meta"]}
    return {"panel": _debate(base_msg)}


def _contrarian_node(state: VerdictState) -> VerdictState:
    base_msg = f"CLAIM: {state['claim']}\n\nEVIDENCE:\n{state['ev_text']}"
    return {"contrarian": _run_contrarian(base_msg, state.get("panel", []))}


def _synthesize_node(state: VerdictState) -> VerdictState:
    claim    = state["claim"]
    ev_text  = state["ev_text"]
    panel    = state.get("panel", [])
    contra   = state.get("contrarian", {})
    evidence = state.get("evidence", [])

    # Thread history + KG + recent memory context
    history = state.get("thread_history", [])
    parts = []
    if history:
        lines = "\n".join(f"- {h['verdict']} ({h['confidence']}%): {h['claim'][:80]}"
                          for h in history[-3:])
        parts.append(f"[Prior claims in this thread]\n{lines}")
    kg_ctx = _kg.find_related(claim)
    if kg_ctx:
        parts.append(kg_ctx)
    mem_ctx = _memory.recent_context(3)
    if mem_ctx:
        parts.append(mem_ctx)
    ctx_block = ("\n\n" + "\n\n".join(parts)) if parts else ""

    # Anonymized panel identities (arxiv 2510.07517) — prevents sycophancy
    panel_text = "\n".join(
        f"- Panelist {chr(65+i)} [{p.get('role','analyst')}]: "
        f"{p.get('verdict')} ({p.get('confidence')}%) — {p.get('reasoning', '')}"
        for i, p in enumerate(panel)
    ) if panel else "(simple path — no panel)"

    contra_text = ""
    if contra.get("challenge"):
        contra_text = (
            f"\n\nCONTRARIAN CHALLENGE ({contra.get('verdict', '?')}, "
            f"{contra.get('confidence', 0)}%):\n{contra['challenge']}"
        )

    synth_user = (
        f"CLAIM: {claim}\n\nEVIDENCE:\n{ev_text}{ctx_block}\n\n"
        f"PANELIST OPINIONS:\n{panel_text}{contra_text}\n\nGive the final verdict."
    )

    # Self-consistency: run 3x when panel is split (Wang et al.)
    verdict_set = {p.get("verdict") for p in panel
                   if p.get("verdict") not in ("Error", "Unverifiable", None)}
    runs = 3 if len(verdict_set) > 1 else 1

    all_data = []
    for _ in range(runs):
        d = _parse(_chat(SYNTH[0], SYNTH[1], SYNTH_SYSTEM, synth_user))
        if d:
            all_data.append(d)

    if len(all_data) > 1:
        votes = Counter(d.get("verdict") for d in all_data)
        winning = votes.most_common(1)[0][0]
        winning_data = [d for d in all_data if d.get("verdict") == winning]
        data = max(winning_data, key=lambda d: len(str(d.get("reasoning", ""))))
        data["confidence"] = int(sum(d.get("confidence", 0) for d in winning_data) / len(winning_data))
        data["self_consistent"] = True
    else:
        data = all_data[0] if all_data else {
            "verdict": "Unverifiable", "confidence": 0,
            "reasoning": "Could not reach a parseable conclusion.",
            "sources": [], "topic": "general",
        }

    data["sources_resolved"] = _resolve_sources(data, evidence)
    data["panel"]        = panel
    data["route"]        = state.get("complexity", "complex")
    data["contrarian"]   = contra
    data["council_meta"] = state.get("council_meta") or {}

    return {
        "verdict_data": data,
        "thread_history": [{
            "claim":      claim,
            "verdict":    data.get("verdict"),
            "confidence": data.get("confidence", 0),
        }],
    }


def _save_node(state: VerdictState) -> VerdictState:
    claim = state["claim"]
    data  = state.get("verdict_data", {})
    _memory.save(claim, data)
    _kg.save_claim(
        claim,
        str(data.get("verdict", "Unverifiable")),
        int(data.get("confidence") or 0),
        data.get("sources_resolved", []),
    )
    return {}


# Conditional routing
def _after_route(state: VerdictState) -> str:
    return "end" if not state.get("is_claim") else "evidence"


def _after_evidence(state: VerdictState) -> str:
    if state.get("complexity") == "simple":
        return "synthesize"
    # Adaptive debate skipping: bypass debate when fast check is very confident (arxiv 2504.05047)
    fast = state.get("fast_check", {})
    if fast.get("confidence", 0) >= 92 and fast.get("verdict") in ("True", "False"):
        return "synthesize"
    return "debate"


# ---------------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------------
_builder = StateGraph(VerdictState)
_builder.add_node("route",      _route_node)
_builder.add_node("evidence",   _evidence_node)
_builder.add_node("debate",     _debate_node)
_builder.add_node("contrarian", _contrarian_node)
_builder.add_node("synthesize", _synthesize_node)
_builder.add_node("save",       _save_node)

_builder.set_entry_point("route")
_builder.add_conditional_edges("route",    _after_route,    {"end": END, "evidence": "evidence"})
_builder.add_conditional_edges("evidence", _after_evidence, {"debate": "debate", "synthesize": "synthesize"})
_builder.add_edge("debate",     "contrarian")
_builder.add_edge("contrarian", "synthesize")
_builder.add_edge("synthesize", "save")
_builder.add_edge("save",       END)


def _make_checkpointer():
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            cp = PostgresSaver.from_conn_string(db_url)
            cp.setup()
            _log.info("Using PostgreSQL checkpointer (cloud)")
            return cp
        except Exception as e:
            _log.warning(f"PostgreSQL unavailable ({e}) — falling back to SQLite")
    conn = sqlite3.connect("verdict_graph.db", check_same_thread=False)
    return SqliteSaver(conn)


_checkpointer = _make_checkpointer()
_graph = _builder.compile(checkpointer=_checkpointer)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def verify_claim(claim: str, thread_id: str = "default") -> dict:
    cached = _memory.lookup(claim)
    if cached:
        return cached

    config = {"configurable": {"thread_id": thread_id}}
    result = _graph.invoke({"claim": claim, "thread_history": []}, config=config)

    if not result.get("is_claim"):
        return {"not_claim": True,
                "reasoning": result.get("not_claim_msg") or
                "That doesn't look like a factual claim — send me a statement to fact-check."}

    return result.get("verdict_data", {"verdict": "Unverifiable", "confidence": 0,
                                       "reasoning": "Pipeline returned no data.",
                                       "sources_resolved": [], "panel": []})
