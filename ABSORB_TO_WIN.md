# Absorb to Win — What Asked & Answered Should Steal From the Field

**Context:** Slack Agent Builder Challenge, New Slack Agent track. Time is short; this doc ignores submitable polish (video, CI badge, live URL, App Home UI) and focuses on **rubric scoring, engineering impressiveness, and ideas worth absorbing**.

---

## 1. The official rubric (from slackhack.devpost.com/rules §6)

Stage 2 scoring is **four criteria, equally weighted 25% each**:

| Criterion | What it really rewards |
|---|---|
| **Technological Implementation** | Deep, load-bearing use of all three required technologies (Slack AI, MCP, RTS); tests; error handling; architecture legibility; reproducibility. |
| **Design** | Slack-native UX, Block Kit interactivity, App Home, loading/empty states — a balanced frontend/backend product, not a headless script. |
| **Potential Impact** | Quantified, nameable-user story. Who benefits, how many, how much time/money/risk saved. Slack community first. |
| **Quality of the Idea** | Creative *or* a clear, measured improvement on an existing concept. The rubric explicitly allows a non-novel idea if it “IMPROVES” on incumbents. |

**Tie-break order:** Tech Implementation → Design → Impact → Idea. Engineering depth is the first tie-breaker.

So the win is **not** “who has the most reliable uptime.” It is who scores highest across all four, with Tech as the tie-break weapon.

---

## 2. Why Consensus and Arbiter score better on the rubric — not just “reliability”

### Consensus (New Slack Agent)

| Rubric pillar | Why it scores high |
|---|---|
| **Tech Implementation** | 58-case eval incl. 9 adversarial injection patterns (Unicode homoglyphs, HTML entities, zero-width/RTL delimiters); redaction gate; membership cache; dismissal memory; dual-model stack. |
| **Design** | Ambient capture → ephemeral contradiction alert → App Home dashboard → audit report. It feels like a complete product, not a script. |
| **Potential Impact** | “Decision memory” is a universal team pain; it quantifies consistency and policy drift. |
| **Quality of Idea** | The “contradiction firewall” framing is **novel** and instantly legible. It is not a chatbot wrapper; it is a new kind of organizational immune system. |

**Key insight:** Consensus wins on **Idea novelty** and **eval/safety breadth**, not just tests. A&A’s “security questionnaire filler” is a clearer workflow but a less surprising idea.

### Arbiter (New Slack Agent)

| Rubric pillar | Why it scores high |
|---|---|
| **Tech Implementation** | Multi-agent debate across heterogeneous LLM families; held-out workslop benchmark; router F1 metric; Neo4j claim graph; prediction ledger; 12/12 adversarial cases. |
| **Design** | Seven entry points (`@Arbiter`, `/verdict`, Assistant pane, message shortcut, watched channels, multimodal). Dense but coherent. |
| **Potential Impact** | Anchored to measurable wastes: 40% of workers receive polished-but-hollow AI content, ~2 hours wasted per incident. |
| **Quality of Idea** | “Judgment layer” / “workslop detector” / “missing voices” are fresh framings with direct citations (Stanford/BetterUp, HBR). |

**Key insight:** Arbiter wins on **algorithmic sophistication** and **eval breadth**. It looks like research engineering, not a product prototype.

### Where Asked & Answered still beats both

- **Property-tested invariant** (200-run fast-check): neither has this.
- **Deterministic fail-closed pipeline** with citation-subset guard: stronger than their heuristic/prompt-based safety.
- **Strict TypeScript + clean architecture**: easier to defend as “quality software development.”
- **Hash-chained tamper-evident ledger**: a concrete theater piece for the demo.

**Your gap is not reliability. It is perceived novelty, eval size, and architectural ambition.**

---

## 3. Other projects better than them you can learn from

These are cross-track winners, top engineering entries, and ancestor-event winners. They show what “undisputed winner” looks like.

### CornerCheck (Agent for Good track) — the engineering ceiling
- **Repo:** https://github.com/StephenSook/cornercheck
- **Signals:** 252 tests, **Z3 formal safety proof** that an active suspension can never return CLEAR, conformal prediction for identity matching (95.1% holdout), live dashboard, Data Table, Canvas, Workflow Builder step, Incoming Webhooks.
- **Lessons to absorb:**
  - **Formal verification of a safety invariant.** A&A’s invariant is property-tested; CornerCheck proves a core safety property with Z3 and runs it live in the product.
  - **Neurosymbolic separation:** model proposes, deterministic engine disposes. A&A’s pipeline is close — lean into that narrative.
  - **Live proof as theater:** every verdict card has a “See the safety proof” button. A&A could have a “Verify invariant” button.
  - **Multiple Slack surfaces:** Data Table, Canvas, Workflow step, web dashboard. A&A has only Block Kit sections.

### Relay (Agent for Good track) — operational rigor
- **Repo:** https://github.com/indrapranesh/relay-crisis
- **Signals:** Event-sourced ledger, 86.1% extraction / 100% critical recall, load-replay benchmark, human-gated MCP write tool, PII-free projections, Fly.io deploy, counterfactual simulator.
- **Lessons to absorb:**
  - **Human-gated MCP writes.** A&A’s MCP server is read-only; that is safe but less impressive. Relay’s `pledge_support` write tool is opt-in and routed through the same human gate as human actions.
  - **Counterfactual / simulated impact.** “Structured coordination beats chat” is an adjective until it is a number. A&A could simulate “hours saved vs. manual SME chase.”
  - **PII-free by construction.** A&A’s redaction is good; Relay makes donor reports redacted and grep-clean.
  - **Load benchmark.** A&A has no throughput or latency numbers.

### Lore (drMurlly, Agent for Good) — research polish
- **Repo:** https://github.com/drMurlly/lore-slack-agent
- **Signals:** 191 tests, knowledge graph with contradiction/timeline resolution, Canvas reports, MCP glossary server, YouTube demo.
- **Lessons to absorb:**
  - **Multi-hop retrieval + knowledge graph.** A&A does one keyword search per question. Lore decomposes, searches, builds a graph, resolves contradictions.
  - **MCP glossary round-trip.** Lore’s MCP server resolves acronyms and feeds expanded terms back into retrieval. A&A could do the same for compliance acronyms (SOC 2, ISO 27001, MFA).
  - **Canvas as artifact.** A&A exports xlsx; Canvas is more native and visually impressive.

### Call Prep Agent — Agentforce Virtual Hackathon 2025 Grand Prize ($50k)
- **Why it won:** One narrow, universally relatable workflow (meeting prep). Chained **7 real external actions**: Calendar → Perplexity/LinkedIn → Salesforce → rich in-chat UI → Google Doc artifact.
- **Lessons to absorb:**
  - **Tangible artifact ends the demo.** A&A already has xlsx export; make it the closing shot.
  - **Multi-step orchestration across real systems.** A&A uses Slack-native evidence; consider adding one external system (e.g., pull SOC 2 doc from Google Drive / Notion via MCP).
  - **Nameable user + time saved.** A&A’s security engineer / AE story is correct; make it specific and quoted.

### Agent Halo — TDX 2026 $100k winner
- **Why it won:** Multi-agent network coordinating insurers/repair/responders/family after a car accident. Submitted a **20-page deck** mapping rubric criteria to architecture, roadmap, MVP, business case.
- **Lessons to absorb:**
  - **Rubric mirroring.** Write the submission so every criterion is pre-answered with a file path or demo timestamp.
  - **Multi-agent narrative.** A&A is single-agent; framing “planning agent + retrieval agent + approval agent” would raise the idea score.

### HarvestBridge — TDX 2026 Agent for Good Grand Prize
- **Why it won:** Four-agent network (DonorBot / MatchMaker / LogisticsCoordinator / ImpactAnalyst) rescuing surplus food **“in under 90 seconds,”** coordinating via the Slack MCP server.
- **Lessons to absorb:**
  - **Quantified human-story outcome.** “90 seconds” / “hours to minutes” is the kind of number judges repeat.
  - **Slack MCP server as coordination backbone.** A&A uses its own MCP server; using Slack’s hosted MCP server for Canvas/DM actions is the platform-native move.

### Upload Drive-In — Kiro 1st place ($30k)
- **Why it won:** A 15-year-old product category (file upload portal) with **zero AI**. Won because it ran publicly early, maxed sponsor-tech depth, had a **1:56 demo**, and completed every optional deliverable.
- **Lessons to absorb:**
  - **Boring hard parts done right** > exotic tech.
  - **Tight demo beats padded demo.**
  - **Do every optional deliverable** (architecture diagram, runbook, etc.).

### Get Together / AccessOwl — Digital HQ Slackathon 2021–22 winners
- **Why they won:** Narrow, native-feeling Slack workflow tools (scheduling, SaaS access requests), not chatbot wrappers.
- **Lessons to absorb:**
  - **Native Slack surfaces matter.** App Home, modals, message shortcuts — these were the winning shape then; Data Tables / Cards / Canvas are the winning shape now.

---

## 4. Absorbable tactics, organized by rubric

### Technological Implementation

| Tactic | Source | How to apply to A&A quickly |
|---|---|---|
| **Formal / probabilistic guarantee** | CornerCheck (Z3), CornerCheck (conformal prediction) | Add a Z3 or SMT proof that “no answer text flows without visibility.” Or add conformal calibration of the library match threshold. |
| **Larger adversarial eval** | Consensus (9 injection patterns), Arbiter (12/12 adversarial) | Expand `evals/dataset.ts` from 2 poison docs to 5+ patterns: homoglyphs, zero-width, RTL override, HTML entities, instruction override. |
| **Held-out eval set** | Arbiter (workslop held-out) | Split eval into dev + held-out; report numbers separately. |
| **Multi-agent / debate drafting** | Arbiter (3-model debate) | Replace single LLM drafter with a small panel: one model drafts, one critic checks citations, one synthesizes. |
| **Deterministic grounding gate** | Sales Copy Concierge (verbatim + trigram check) | After LLM draft, verify every cited snippet is actually a substring of a retrieved RTS hit. |
| **Knowledge graph of evidence** | Lore (drMurlly) | Build a tiny graph: question → evidence → channel → owner → prior approved answer. Use it for contradiction detection and SME routing. |
| **Durable human-in-the-loop workflow** | Quorum (Vercel Workflow 7-day approval), Relay (human-gated MCP writes) | Make approval a durable workflow step, not an in-memory button session. |
| **User-token private search** | Quorum, Compass | Add per-user OAuth path so RTS can search private channels the bot is not in. |
| **Rate-limit strategy with per-strategy numbers** | v2 design doc | Publish eval numbers for per-question vs OR-batch retrieval. |
| **Two-app strategy** | v2 judge panel | Keep App A internal for judging; App B only for Marketplace. |

### Design

| Tactic | Source | How to apply to A&A quickly |
|---|---|---|
| **Data Table review surface** | Sponsor guidance, CornerCheck, Consensus | Replace sections+buttons with a Slack Data Table block; fallback to sections. |
| **App Home dashboard** | Consensus, Quorum, Arbiter | Show stats: questionnaires run, verified answers, pending SME, ledger integrity. |
| **Canvas artifact** | Lore, Relay, Council | Export the completed questionnaire to a Slack Canvas with citations and approval record. |
| **Task cards / streaming plan** | v2 design doc | Use `chat.startStream`/plan blocks for the planning phase. |
| **Feedback buttons on cards** | Consensus | `Approve / Edit / Reject / Show reasoning` with ephemeral follow-ups. |

### Potential Impact

| Tactic | Source | How to apply to A&A quickly |
|---|---|---|
| **Real human quote + hours number** | v2 judge panel, winner forensics | Interview a security engineer/AE; put their quote and hour-count in the first 5s of the video and in the write-up. |
| **Compounding before/after number** | v2 design doc | Measure “questionnaire #1: X minutes; questionnaire #2: Y% auto-verified.” Only if actually measured. |
| **Nameable user, not TAM** | Comparable hackathons | “Sarah, security engineer at a 200-person SaaS” beats “B2B companies.” |
| **Risk/framing** | A&A’s own fail-closed angle | A wrong compliance answer can kill a $500k deal or fail an audit. That is higher-stakes than “saves time.” |

### Quality of the Idea

| Tactic | Source | How to apply to A&A quickly |
|---|---|---|
| **Frame as improvement, not novelty** | Official rubric escape hatch | “Conveyor/Loopio make you maintain a separate knowledge base; A&A makes Slack itself the library — zero-copy, citation-first, permission-aware.” |
| **Reframe the product** | Winner forensics | “Objection — asked and answered” is good; “the workspace’s compliance memory” or “the only questionnaire agent that refuses to guess” is stronger. |
| **Multi-agent narrative** | Agent Halo, HarvestBridge | “Planner agent → Evidence agent → Drafting agent → Approval agent” raises the idea score without changing much code. |
| **The moat** | A&A’s own invariant | Lead with the property-tested permission invariant. It is genuinely unique in this field. |

---

## 5. Concrete A&A improvements — timeboxed

### If you have 6 hours left
1. **Expand the eval harness to ~30 cases and 5 adversarial patterns.** This directly closes the gap with Consensus.
2. **Add a deterministic grounding gate** after the LLM draft (verify cited snippets are substrings of retrieved evidence).
3. **Fix / verify the Verified ACL revalidation** is actually exercised in the eval (it is in code; make it a labeled case).
4. **Get a real human quote and hour-count** for the submission/video.
5. **Rewrite submission text** to explicitly map each rubric criterion to a feature/eval/file path.
6. **Record a ≤2:40 video** with the fail-closed refusal as the emotional peak.

### If you had another week (post-deadline reference)
1. Add App Home dashboard.
2. Add Data Table review surface with Card detail.
3. Add Canvas export artifact.
4. Add multi-agent drafting (drafter + critic + synthesizer).
5. Add Z3 or SMT proof of the ACL invariant.
6. Add per-user OAuth for private-channel RTS search.
7. Add a durable approval workflow (not in-memory sessions).
8. Add knowledge-graph evidence linking.

---

## 6. Honest verdict on “undisputed winner”

Asked & Answered is **not** currently the undisputed winner. It is a strong contender with one genuinely unique asset: a property-tested, deterministic fail-closed permission invariant.

To become undisputed, it needs to:
- **Match Consensus on eval rigor** (larger adversarial eval, multi-model reporting).
- **Match Arbiter on architectural ambition** (multi-agent, knowledge graph, or formal proof).
- **Surpass everyone on Design** (Data Table, App Home, Canvas artifact).
- **Anchor Impact with a real human story and measured numbers.**

The good news: the rubric rewards **systematic execution over raw novelty**, and your core idea already has a credible improvement story. The bad news: the top two New Slack Agent entries have already executed more of that playbook than you have.

Use this doc as a post-hackathon roadmap if the deadline closes before you can absorb everything.
