# Arbiter — the workspace's judgment layer

**66 unit tests passing** (`pytest tests/`) · fact-check 100% (+10pp) · workslop 20/20 (held-out 9/10) · routing 91% (macro-F1 0.84) · 12/12 adversarial

> Your team reads a thousand things a day. **Arbiter tells you which ones deserve trust** —
> the facts, the documents, and the decisions. One multi-agent brain (a debating panel of
> heterogeneous LLMs over your workspace's own record), three kinds of verdicts:
>
> - **On claims** — fact-checks with cited, confidence-scored verdicts
> - **On content** — substance receipts for polished-but-hollow *workslop*
> - **On decisions** — the missing voices: absent stakeholders, the record, the counter-case
> - **On people's positions** — a quote-first *delegate* that answers for absent teammates
>   from their own record, in their own style — and escalates instead of guessing
>
> …plus a credit ledger ("who said it first"), a prediction ledger (who's actually
> calibrated), and a **self-audit trail** of every intervention the agent makes.

Built for the **Slack Agent Builder Challenge** — using **two** of the required technologies in
Slack's "search → reason → act" pattern: the **Real-Time Search API** (retrieve workspace
evidence) and the **Slack MCP server** (act — flag messages, export audit Canvas).

---

## Why it's different

Most Slack AI tools *summarize*. Arbiter **judges**:

- **Workslop** (Stanford/BetterUp, HBR 2026): 40% of workers receive polished-but-hollow AI
  content, ~2 hours wasted per incident. Arbiter's substance receipts are **decomposed and
  arithmetic** (density + groundedness + novelty − fluff) — never a holistic LLM "rating,"
  which is verbosity-biased toward exactly the padding it should catch.
- **Decisions** form fast in Slack with nobody who'll be affected in the room. Arbiter finds the
  **missing voices** — strictly **quote-first** (real messages, permalinked; it never generates a
  position for anyone), checks **the record** (was this decided before? why does the current
  state exist?), and argues the **strongest counter-case** once.
- **Internal contradictions**: it's still the only agent that checks a claim against **your
  workspace's own messages** ("someone said 90-day refunds, but the policy says 30").
- **It judges itself**: every intervention is logged (mode, trigger, confidence, action) —
  `@Arbiter audit` renders the transparency report, `audit canvas` exports an
  EU-AI-Act-shaped audit trail.

## Private-first rule

Anything that judges a **person's writing** goes to that person **privately** (ephemeral
substance receipts). Anything that protects the **thread** (fact-flags, missing voices) posts
in-thread. Credit is phrased as a gift ("Maya raised this first on Jun 2"), never a call-out.

## How it works

```
message / mention / watched channel
   |
   v
[Heuristics]  free pre-filter - length, decision phrases, filler density   <- kills ~90% of traffic
   |
   v
[Classifier]  one fast-model call (temp 0) -> which judgment does this need?
   |
   |- claim -----> [Evidence] web + news + FactCheck + your Slack (RTS)
   |               [Debate]   Skeptic -> Advocate + Analyst (3 LLM families)
   |               [Contrarian -> Synthesizer] -> verdict card (+ credit line)
   |
   |- substance -> [Extract units] decisions/asks/commitments/facts (strict concreteness)
   |               [Arithmetic score] 60% density + 20% grounded + 20% novel - fluff penalty
   |               -> private receipt to the author
   |
   |- decision --> [Missing voices] RTS quotes from affected people not in the thread
                   [The record]     past decisions + knowledge graph (Chesterton's Fence)
                   [Counter-case]   grounded devil's advocate
                   -> missing-voices card in-thread
   |
   v
[Arbitration]  one intervention max per message - confidence-gated - everything audited
```

**Architecture:** an orchestrator-worker multi-agent system (LangGraph) with a judgment-routing
layer, a Neo4j claim graph (authors, contradictions, predictions, interventions), and
provider-agnostic model routing (7 inference providers behind one OpenAI-compatible interface).

## Benchmarks

**Fact-checking** (10 claims: well-known facts, myths, recent events): the debate pipeline
scores **100% vs. 90% for a plain single model with no evidence (+10pp)**. Run: `python eval.py`.

**Workslop detection** — to our knowledge the first benchmarked workslop detector (no public
benchmark exists; AI-authorship detectors measure the wrong thing — hollow content is hollow
regardless of who wrote it):

| Set | Cases | Accuracy | Notes |
|---|---|---|---|
| Development | 10 hollow vs 10 dense | **20/20 (100%)** | incl. 5 cliché-free "polite vagueness" hard cases |
| **Held-out** | 5 hollow vs 5 dense | **9/10 (90%)** | frozen formula, single run, written after tuning |

Hollow avg 18 vs dense avg 89 on the dev set (+50 separation gap). Run:
`python eval.py substance` / `python eval.py holdout`.

**Routing** — the metric a multi-verdict agent lives on: does the coordinator send
each message to the *right* judgment? On a 22-case labeled set across all four
outcomes (claim / decision / substance / stay-silent): **91% accuracy, macro-F1
0.84**, with a full confusion matrix. Claim, decision, and *stay-silent* score a
perfect 1.00 F1 (the bot never misroutes chit-chat into a judgment). Substance
recall is threshold-limited — the two misses are 46- and 55-word messages, shorter
than the paragraph-length "workslop" the mode targets; flagging every brief vague
message would be noise, so that's deliberate. No competitor reports routing metrics
because none of them route between judgment types. Run: `python eval.py router`.

The adversarial cases caught two real design flaws during development — LLM extraction
counting vague intentions ("we'll keep pushing") as content, and a scoring hole where
cliché-free vagueness earned points for style — both fixed (strict concreteness rule: a unit
must name a person, number, date, or artifact; and *substance earns, style only subtracts*).
The one held-out miss is a documented failure mode: decorative numbers ("12 meetings,
3 workstreams") can still fool extraction — future work: verify numbers attach to
commitments, not sentiment.

## Features

- **Three judgment modes** — claims, substance, decisions — one brain, one intervention max
- **Multi-model debate** — heterogeneous panel (different families make uncorrelated errors)
- **Anti-workslop receipts** — decomposed arithmetic scoring, immune to LLM verbosity bias
- **Missing-voices cards** — quote-first absent stakeholders, the record, counter-case
- **Credit ledger** — "who said it first," from the claim graph, phrased as a gift
- **Prediction ledger** — auto-detects predictions, resolves them when due, keeps score
- **Self-audit** — every intervention logged; transparency report + Canvas export via MCP
- **Grounded + cited** — web, recent dated news, and **your Slack** via the Real-Time Search API
- **Acts via MCP** — flags false claims (warning reaction), marks logged predictions
  (crystal-ball reaction), exports the audit-trail Canvas
- **Native Slack Lists** — Prediction Ledger and Decision Register, auto-maintained
- **App Home dashboard** — week's interventions, agreement rate, open predictions
- **Seven ways to use it** — `@Arbiter`, `/arbiter` (or `/verdict`), the **Assistant side-pane**,
  the **"Judge this message" right-click shortcut**, magnifier-react to any message,
  **watched channels** (full proactive cascade), file uploads
- **Multimodal** — fact-check **images** (vision), **PDFs/Word**, and **voice clips** (Deepgram)
- **Self-improving** — thumbs-up/down feedback logged (`@Arbiter stats` shows agreement)
- **Multilingual** · **health-aware disclaimers** · **provider-agnostic** (one env var to swap
  to frontier models)

## Commands

| Say | Get |
|---|---|
| `@Arbiter <claim>` | fact-check verdict card |
| `@Arbiter substance <text>` (or in a thread) | substance receipt for the text / parent message |
| `@Arbiter voices <decision>` (or in a thread) | missing voices · record · counter-case |
| `@Arbiter ask @teammate <question>` | delegate answer from their record (cited, persona-styled); escalates + notifies them |
| *(automatic)* question mentioning an **away** teammate in a watched channel | their delegate steps in unprompted — same fidelity gates, same DM notification |
| `@Arbiter ledger` | prediction scoreboard + open predictions |
| `@Arbiter audit` / `audit canvas` | transparency report / exportable audit trail |
| `@Arbiter watch` / `unwatch` | proactive judgment cascade on this channel |
| `@Arbiter stats` | human agreement with verdicts |

## Required Slack tech used (two of three)

- **Real-Time Search API** (`assistant.search.context`) — *retrieve*: grounds claims, finds
  missing voices, checks novelty against the workspace record
- **Slack MCP server** (`mcp.slack.com`) — *act*: reactions, audit-trail Canvas
- **Agents & AI Apps** assistant experience with dynamic suggested prompts (Slack AI capability)

## Setup

```bash
python -m venv .venv && .venv/Scripts/activate        # Windows
pip install -r requirements.txt
cp .env.example .env                                   # then fill in tokens/keys
python app.py                                          # runs in Socket Mode
```

`.env` needs: `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_USER_TOKEN`,
`TAVILY_API_KEY`, and at least one model provider key (`OPENROUTER_API_KEY`, `NVIDIA_API_KEY`, …).

To run against a second workspace (e.g. a judging sandbox), put its four Slack tokens in
`.env.sandbox` and use `python run_sandbox.py`. Never run two instances against one workspace.

## Configuration

| Env var | What it sets | Default |
|---|---|---|
| `VERDICT_ROUTER` | triage/classifier model | fast free-tier model |
| `VERDICT_DEBATERS` | panel (comma-sep `provider:model`) | free 3-family panel |
| `VERDICT_SYNTH` | synthesizer | fast free-tier model |
| `VERDICT_VISION` | image-claim model | `gemini:gemini-2.5-flash` |
| `ARBITER_SUBSTANCE_MIN_WORDS` | substance-mode trigger threshold | `120` |
| `ARBITER_NAME` | display name in messages | `Arbiter` |

Frontier demo config (direct keys — three labs argue every claim):
```
VERDICT_DEBATERS="openai:gpt-4.1,anthropic:claude-sonnet-5,gemini:gemini-2.5-flash"
VERDICT_SYNTH="anthropic:claude-sonnet-5"
```

## Project layout

- `app.py` — Slack Bolt app: entry points, Block Kit cards, private-first delivery
- `judgment.py` — the coordinator: heuristics → classifier → mode arbitration
- `llm.py` — fact-check pipeline: router + debate + contrarian + synthesis (LangGraph)
- `substance.py` — anti-workslop receipts (decomposed arithmetic scoring)
- `decisions.py` — missing-voices cards: absent stakeholders (quote-first) + record + counter-case
- `delegate.py` — quote-first delegate: answers for absent teammates from their record, persona-styled
- `ledger.py` — credit ("who said it first") + prediction scoreboard
- `audit.py` — self-audit trail + transparency report + Canvas export
- `lists_sync.py` — native Slack Lists mirror (per-workspace state)
- `knowledge_graph.py` — Neo4j claim graph (authors, contradictions, sources)
- `tools.py` — web search (Tavily) + Wikipedia + Google FactCheck + Slack RTS
- `arblog.py` / `memory.py` / `feedback.py` / `media.py` / `mcp_client.py` — logging, cache,
  votes, multimodal, MCP
- `eval.py` — fact-check, substance, and held-out benchmarks

## License

MIT
