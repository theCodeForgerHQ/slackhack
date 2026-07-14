# Competitor Swarm Findings (Updated) — Slack Agent Builder Challenge 2026

**Date:** 2026-07-14  
**Baseline:** [Asked & Answered](https://github.com/theCodeForgerHQ/asked-and-answered)  
**Sources:** `COMPETITOR_SWARM_FINDINGS.md` baseline + latest 7-agent swarm output  
**Scope:** Every distinct public repo found across both sources, merged and deduplicated. URLs that could not be verified live are marked **unverified**.

---

## Executive Summary

The merged swarm found **55 distinct public competitor repositories** (plus `slk` as relevant tooling). About two dozen are substantive enough to threaten Asked & Answered (A&A) on specific rubric dimensions.

**A&A still leads on engineering rigor:** 284 tests, 136-case eval (26 held-out), code-level Z3 contract proof, runtime invariant verification, deterministic snippet-level `GroundingGate`, hash-chained ledger, App Home, Workflow Builder custom step, Canvas/Lists export, MCP read-only server, RTS, and a live Render deploy.

**The narrowest margins are:**
- **Design / Idea:** Council for Slack, Arbiter, Lore, Quorum.
- **Adversarial hardening / eval:** Consensus, Kept.
- **Formal assurance:** CornerCheck.
- **Measured real-world impact:** Gavel, Vigie.
- **Governance / durable approvals:** Aegis, Kept, Quorum, Settled, blast-radius-gate.

Most high-value patterns can be absorbed without changing the existing fail-closed questionnaire pipeline.

---

## 1. Distinct Public Repositories

### New Slack Agent track

#### [Council for Slack](https://github.com/alex-jb/council-for-slack-2026)
- **Track:** New Slack Agent
- **Thesis:** Five domain-typed LLM personas deliberate on a decision, return a scored verdict, and are later Brier-scored against reality.
- **Stack:** Next.js 16, Vercel, Bolt JS, Supabase SECURITY DEFINER RPCs, Anthropic Sonnet, `council-diff`, MCP wrapper.
- **Evidence:** Live multi-workspace OAuth install, four case studies, Canvas log, Workflow Builder step spec; **zero automated tests** found.
- **Surfaces:** `/council`, message shortcut, Workflow Builder custom step, channel Canvas log, MCP, App Home calibration.
- **Better than A&A:** Best demo/idea novelty, multi-persona deliberation, Brier calibration loop, polished landing page.
- **Absorbable:** Brier scoring for SME approvals; Canvas decision log for approvals; multi-persona review for contested answers.

#### [Consensus](https://github.com/BitTriad/consensus-slack-agent)
- **Track:** New Slack Agent
- **Thesis:** Ambient contradiction firewall that silently captures decisions from normal chat and warns authors before they contradict an active decision.
- **Stack:** TypeScript, Bolt, MongoDB/SQLite ledger, Cerebras GLM-4.7 + Gemini fallback, Slack MCP, RTS.
- **Evidence:** 58-case eval, 9 adversarial injection patterns, published P/R 1.000/0.964, NFKC normalization, fail-closed membership gate.
- **Surfaces:** Ambient capture, ephemeral alerts, App Home, `@Consensus` Q&A, edit/delete sync, consistency audit, Canvas/Lists.
- **Better than A&A:** Ambient UX, proactive contradiction detection, published adversarial eval, injection hardening, permission redaction.
- **Absorbable:** Adversarial cases into `evals/`; NFKC + delimiter wrapping; per-user dismissal memory; contradiction scanner over the answer library.

#### [Kept](https://github.com/kaviyakumar23/kept)
- **Track:** New Slack Agent
- **Thesis:** Human-verified, event-sourced obligation ledger for shared customer channels with two mandatory human gates before every transition.
- **Stack:** TypeScript, Bolt, PostgreSQL event store, Redis/BullMQ, MCP deterministic client, Zod, Vitest.
- **Evidence:** 140 hermetic tests + live integration tests, `npm run demo`, 7-round adversarial hardening, 100% correct-transition eval.
- **Surfaces:** `/kept`, App Home ledger, Block Kit confirm/verify/closure cards, edit modals, Linear/Jira/webhook adapters.
- **Better than A&A:** Explicit guarded FSM, deterministic MCP client, idempotency/optimistic concurrency, audience-safe redaction.
- **Absorbable:** Guarded FSM for answer lifecycle; deterministic MCP tool selection; idempotency keys; adversarial regression discipline.

#### [Quorum](https://github.com/OrionArchitekton/quorum-slack-agent)
- **Track:** New Slack Agent
- **Thesis:** Detects thread-level decisions, drafts a structured Decision Record, and routes approval through a durable Vercel Workflow.
- **Stack:** pnpm monorepo, Next.js 15, Vercel Workflow `DurableAgent`, Bolt, Vercel AI SDK, Slack MCP, RTS.
- **Evidence:** 19 unit + 2 integration tests, live Vercel deploy with `/api/health`, fake-LLM offline mode.
- **Surfaces:** Message shortcut, durable Approve/Edit/Discard card, proactive nudge, `@Quorum` Q&A, Canvas + `#decision-log`.
- **Better than A&A:** Durable multi-day approval hook, clean curated-record + broad-workspace search split.
- **Absorbable:** Durable SME approval hooks; Decision Record schema; proactive nudge for stale rows; Canvas decision log.

#### [Arbiter](https://github.com/nirbhay221/arbiter)
- **Track:** New Slack Agent
- **Thesis:** Multi-verdict judgment layer that fact-checks claims, scores "workslop," finds missing decision voices, and delegates answers for absent teammates.
- **Stack:** Python, Bolt, Neo4j claim graph, LangGraph, 7-provider model router, Tavily/web search, Slack MCP.
- **Evidence:** 66 pytest tests; fact-check 10/10, workslop 20/20 dev + 9/10 held-out, routing 91%, 12/12 adversarial.
- **Surfaces:** Mentions, slash, shortcuts, reactions, assistant pane, watched channels, Slack Lists, Canvas export, file uploads.
- **Better than A&A:** Multi-model debate, claim/contradiction graph, anti-verbosity substance scoring, broadest UX surface, multimodal intake.
- **Absorbable:** Small council for low-confidence drafts; claim/contradiction graph; substance scoring; Canvas audit export; PDF/voice evidence intake.

#### [Déjà](https://github.com/bogacsmz/deja) — **unverified**
- **Track:** New Slack Agent
- **Thesis:** Decision-governance layer that ambiently watches Slack and brakes only when a new proposal conflicts with a standing, sourced decision.
- **Stack:** Python, Bolt, Claude Max, RTS, MCP (`recall_memory`, `check_decision`).
- **Evidence:** Baseline cited an 83-query adversarial benchmark; **latest swarm could not verify a live public repo or README**.
- **Surfaces:** Ambient watcher, MCP brake.
- **Better than A&A:** Benchmark transparency, ambient governance without opt-in, MCP as agent-to-agent brake.
- **Absorbable:** Adversarial benchmark structure; MCP governance tool for answer-library checks; honest limits documentation.

#### [Loop Closer](https://github.com/varunbhandarii/Loop-Closer)
- **Track:** New Slack Agent
- **Thesis:** Finds dropped balls (unanswered questions, unkept commitments) in Slack and closes them.
- **Stack:** TypeScript, Bolt, Postgres, Claude, MCP, RTS.
- **Evidence:** 340+ tests, streamed plan with sources, verify-before-nudge.
- **Surfaces:** Channel watcher, App Home, ephemeral nudges.
- **Better than A&A:** Largest test count in New Agent track per baseline, strong privacy model (no message content stored), loop-detection UX.
- **Absorbable:** Loop-detection for stale questions; streamed plan display; redaction/paraphrase storage policy.

#### [Lore (drMurlly)](https://github.com/drMurlly/lore-slack-agent)
- **Track:** Agent for Good (cross-track threat)
- **Thesis:** Multi-hop cited research over workspace history with an ephemeral knowledge graph and Canvas reports.
- **Stack:** Python, Bolt, local LLM via Ollama, FastMCP glossary server, RTS with interchangeable backends.
- **Evidence:** 191 offline tests, `scripts/run_demo.py`, YouTube demo.
- **Surfaces:** `/lore`, `@Lore`, Assistant split-view, App Home, Canvas report, MCP glossary.
- **Better than A&A:** Multi-hop retrieval and knowledge graph, deterministic timeline-drift resolution, deep source citations.
- **Absorbable:** Multi-hop retrieval for complex questionnaires; knowledge graph of controls/decisions/contradictions; MCP glossary server; Canvas research reports.

#### [Aegis](https://github.com/yama3133/aegis-slack-app)
- **Track:** New Slack Agent
- **Thesis:** MCP-based human-approval control plane — any agent pauses before risky actions and waits for Slack approval.
- **Stack:** TypeScript, Bolt, MCP, Amazon Bedrock, RTS.
- **Evidence:** Demo video, `post-demo.ts`, `agent-demo.ts`, policy engine.
- **Surfaces:** MCP tools `request_approval`/`check_approval`/`wait_for_approval`, Block Kit Approve/Deny/Edit & Approve/Request Info, audit log.
- **Better than A&A:** Generalizable approval infrastructure with policy engine, N-of-M approvals, edit & approve flow, TTL expiry.
- **Absorbable:** Policy engine for low-risk auto-approve; N-of-M for high-sensitivity questionnaires; Edit & Approve flow.

#### [Threadwork](https://github.com/ShreyanshVaibhaw/threadwork)
- **Track:** New Slack Agent
- **Thesis:** Turns any Slack thread into a Canvas work post, task list, cited related history, and a supervised Agent Run Card.
- **Stack:** JavaScript/Bolt, MCP, RTS, Canvas, Slack Lists, OpenRouter.
- **Evidence:** `npm run spike` capability probe, `scripts/seed.js`, graceful-degradation flags.
- **Surfaces:** `@Threadwork` in thread, Canvas, Lists, Agent Run Card with Approve.
- **Better than A&A:** Structured work artifacts with human-signed agent runs, graceful-degradation matrix for restricted scopes.
- **Absorbable:** Agent Run Card pattern for approval steps; human signature/attestation per row; capability probes at startup.

#### [flightrec-slack](https://github.com/kitfunso/flightrec-slack)
- **Track:** New Slack Agent
- **Thesis:** Privileged-action Slack agent whose every run is recorded in an append-only, hash-chained audit store.
- **Stack:** TypeScript, Bolt, SQLite (append-only hash chain), MCP.
- **Evidence:** 26 tests.
- **Surfaces:** `/grant` form, `/audit` report, `/audit tamper` demo mode.
- **Better than A&A:** Tamper-evident audit chain with integrity attestation, parameter-level deterministic gate.
- **Absorbable:** Hash-chained audit ledger for approvals; MCP audit server; structured modal approvals.

#### [Meridian](https://github.com/Tasfia-17/meridian-slack-agent)
- **Track:** New Slack Agent
- **Thesis:** Decision and commitment intelligence — auto-detects decisions/commitments from conversation, logs them as Canvas docs, exposes via MCP.
- **Stack:** Python, Bolt, FastMCP, Claude Haiku, SQLite/MemoryStore, Canvas API, RTS.
- **Evidence:** 45 offline tests.
- **Surfaces:** Channel watcher, Canvas docs, MCP.
- **Better than A&A:** Strong Canvas-native artifact design, commitment nudges, deterministic confidence scoring.
- **Absorbable:** Canvas-first audit artifacts; commitment tracking for deadlines; deterministic confidence scoring display.

#### [Slack Compass](https://github.com/nag-gude/slack-compass)
- **Track:** New Slack Agent
- **Thesis:** Detects missing stakeholders, forgotten decisions, and contradictions before they become launch failures.
- **Stack:** TypeScript/Bolt, Claude, evidence graph, RTS.
- **Evidence:** README/demo evidence.
- **Surfaces:** `/compass ghost`, `/compass resurrect`, `/compass contradict`, proactive `#ship-it` monitoring, App Home.
- **Better than A&A:** Proactive detection of missing stakeholders and contradictions, watch engine with alert/resolve lifecycle.
- **Absorbable:** Ghost-stakeholder detector for SME routing; watch engine for stale/contradicting approved answers.

#### [Priors](https://github.com/sneg55/priors)
- **Track:** New Slack Agent
- **Thesis:** Proactively flags when a forming decision contradicts the team's own prior decisions.
- **Stack:** TypeScript, `@slack/bolt`, Anthropic SDK, Zod, Result types.
- **Evidence:** 50 tests.
- **Surfaces:** Message events, ephemeral alerts.
- **Better than A&A:** Focused minimal UX, precision-over-recall design.
- **Absorbable:** Staged pipeline language for contradiction detection; precision-bias UX.

#### [Paper Trail](https://github.com/jacklachan/paper-trial)
- **Track:** New Slack Agent
- **Thesis:** "Your team's decisions, with receipts" — log decisions from any thread, browse a ledger in App Home, ask sourced questions.
- **Stack:** Python 3.11+, Bolt, SQLite, FastMCP, Gemini/Groq/heuristic fallback.
- **Evidence:** README/demo evidence.
- **Surfaces:** Message shortcut, App Home, MCP.
- **Better than A&A:** Simpler decision-capture UX, bidirectional MCP (read + propose with approval), AI-free fallback.
- **Absorbable:** Message shortcut for logging approved answers; MCP `propose_answer` UX patterns.

#### [Tribal Knowledge Agent](https://github.com/divergent99/tribal-knowledge-agent)
- **Track:** New Slack Agent
- **Thesis:** Synthesized workspace-history answers with citations, conflict detection, staleness flags, honest "no answer found."
- **Stack:** Node.js/Bolt, Claude, RTS, Block Kit.
- **Evidence:** Runnable `npm run dev`, manifest, `check-search-info` debug.
- **Surfaces:** `@tribal-bot` mention, Block Kit replies, RTS.
- **Better than A&A:** Query expansion fallback for keyword-only RTS, explicit conflict/stale flags and humility.
- **Absorbable:** Query expansion for low-coverage RTS; conflict/staleness badges on answers.

#### [Devil's Advocate](https://github.com/run58669-maker/devils-advocate)
- **Track:** New Slack Agent
- **Thesis:** Red-team bot that detects premature consensus in a thread and posts structured, evidence-backed dissent.
- **Stack:** Python/Bolt, Gemini 2.5 Flash, MCP DuckDuckGo web search.
- **Evidence:** `test_core.py`, runnable `app.py`, manifest.
- **Surfaces:** Watched channels, `/devil on/off`, in-thread Block Kit dissent.
- **Better than A&A:** Active red-teaming of decisions with external evidence, confidence-gated interventions.
- **Absorbable:** Red-team review for newly approved answers; external web evidence for security-control claims.

#### [Perseus for Slack](https://github.com/Perseus-Computing-LLC/slack-perseus-agent)
- **Track:** New Slack Agent
- **Thesis:** Brings live project context into Slack via a 31-tool Perseus MCP server so dev teams query services, decisions, and code.
- **Stack:** Python, Bolt, Perseus MCP server, optional local LLM.
- **Evidence:** Runnable `src/app.py`, demo docs, architecture; **no automated tests found**.
- **Surfaces:** `@perseus` mentions, Block Kit cards, MCP.
- **Better than A&A:** Domain-specific dev-context tools, local-LLM fallback, auto-generated tool registry.
- **Absorbable:** Per-question MCP tool calls to enrich technical evidence; deterministic fallback footer.

#### [TriageMate](https://github.com/abhishek2f24/triagemate)
- **Track:** Slack Agent for Organizations
- **Thesis:** Watches a support channel, answers from org knowledge via RTS, escalates to on-call with AI-written context, and tracks MTTR/SLA compliance.
- **Stack:** Node.js, Bolt, Claude tool-use, RTS, MCP-compatible tooling, in-memory SLA tracker.
- **Evidence:** Offline `npm run demo`, unit tests, manifest, mock/replay layer.
- **Surfaces:** Assistant split-view, channel watcher, `/triage-report`, Block Kit escalation cards.
- **Better than A&A:** Operational SLA tracking and on-call paging; Assistant split-view UX.
- **Absorbable:** Due-date/SLA tracking per questionnaire; offline demo replay script; Assistant split-view polish.

#### [Backchannel](https://github.com/ashana46/backchannel)
- **Track:** New Slack Agent
- **Thesis:** AI coordinator for event planners: voice note → drafted vendor email → IMAP reply tracking → shuttle diplomacy.
- **Stack:** Python, Bolt, Claude Agent SDK, Slack MCP, OpenAI Whisper, Gmail SMTP/IMAP.
- **Evidence:** `tests/`, `DEMO.md`, `DIAGRAMS.md`, runnable `app.py`, manifest.
- **Surfaces:** DM, `@mention`, voice notes, `/backchannel-refresh`, Block Kit approval cards, App Home.
- **Better than A&A:** Two-way external coordination (email) with human-in-the-loop approval before sending.
- **Absorbable:** Email-based SME outreach for unreachable reviewers; approval gates before external actions.

#### [GreenLog](https://github.com/cipoklean/Greenlog)
- **Track:** Agent for Good
- **Thesis:** Logs climate decisions in plain English and returns honest magnitude/direction triage, explicitly saying "we don't know" when there's no environmental signal.
- **Stack:** Node.js, Bolt, Gemini 3.1 Flash-Lite, Block Kit, JSON storage, Render.
- **Evidence:** Runnable `app.js`, sample outputs, manifest.
- **Surfaces:** `/greenlog log`, `/greenlog digest`, `@GreenLog`, App Home.
- **Better than A&A:** Honest uncertainty signaling instead of over-confident answers; simple App Home config.
- **Absorbable:** Confidence/evidence-strength badge on every Verified/Grounded answer.

#### [Pangea AI](https://github.com/MOHAMMADAima/pangea-ai)
- **Track:** Agent for Good
- **Thesis:** Connects vaccine researchers with complementary expertise and geographic field access, then drafts culturally adapted introductions.
- **Stack:** Python, Bolt, Block Kit, Claude Haiku, NetworkX, Matplotlib.
- **Evidence:** 5 demo profiles, runnable `app.py`, manifest.
- **Surfaces:** `/pangea`, App Home dashboard.
- **Better than A&A:** Relationship/expertise graph + proactive matching.
- **Absorbable:** Identify which SME answered similar past questions and route new "Needs SME" rows to them.

#### [Tracey](https://github.com/aybbr/slack-agent-builder-challenge)
- **Track:** New Slack Agent
- **Thesis:** Detects dbt model mentions in data-team channels, runs impact analysis, finds stale discussions, ranks domain experts, and annotates GitHub PRs.
- **Stack:** Python, FastMCP, DuckDB, dbt MCP server, DeepSeek, Slack RTS, GitHub API.
- **Evidence:** `Makefile` (`make test`, `make seed-data`, `make run-dev`), demo workspace seeder, Railway deployment config.
- **Surfaces:** Ambient channel monitoring, Slackbot MCP client, App Home/Block Kit cards, PR modal.
- **Better than A&A:** Deep vertical integration (dbt lineage + GitHub) instead of generic search.
- **Absorbable:** Domain-specific MCP servers (GitHub, Jira) to ground technical compliance answers.

#### [Comp Copilot](https://github.com/sainathek1999/comp-planning-copilot)
- **Track:** New Slack Agent / Orgs
- **Thesis:** HR comp agent that enforces merit budget guardrails and EU Pay Transparency equity checks on every proposed raise inside Slack.
- **Stack:** Python, Bolt async, FastMCP 3.x, SQLAlchemy/SQLite, FastAPI dashboard, Chart.js.
- **Evidence:** 22 pytest tests, seed data (58 employees + 17 proposals), dashboard.
- **Surfaces:** `/comp`, App Home, web dashboard, Block Kit, MCP.
- **Better than A&A:** Numeric guardrails and policy enforcement with clean dashboard.
- **Absorbable:** Numeric guardrails for answer confidence thresholds and reviewer workload; web dashboard for compliance metrics.

#### [Sales Copy Approval Concierge](https://github.com/takumimorimoto-yakumo/slack-agent-builder-challenge)
- **Track:** New Slack Agent
- **Thesis:** Grounds AI-drafted sales copy in a company's own website text, verifies citations deterministically, and holds every draft for explicit Approve/Reject in Slack.
- **Stack:** Python, Bolt, FastMCP stdio server, SQLite ledger, Claude CLI/Vertex/mock backends, Cloud Run.
- **Evidence:** 54 pytest tests including MCP stdio e2e, offline `scripts/demo_cli.py`, Cloud Run deploy script.
- **Surfaces:** Assistant thread, `@Copy Concierge`, Block Kit Approve/Reject, MCP.
- **Better than A&A:** Deterministic verbatim-citation verification before human review.
- **Absorbable:** Harden `GroundingGate` with character-trigram/verbatim checks; store per-answer provenance hashes.

#### [DecisionOps](https://github.com/rdxsai/decisionops)
- **Track:** New Slack Agent
- **Thesis:** Turns a Slack thread into a captured, approved, and remembered decision using incremental Slack-native memory.
- **Stack:** TypeScript, Bolt, Anthropic Messages API, Canvas, Slack-native ledger.
- **Evidence:** 65 Vitest tests, `npm run doctor` preflight, `npm run seed`, cold-vs-warm RTS eval.
- **Surfaces:** Message shortcut, Canvas brief, Block Kit approval buttons, RTS.
- **Better than A&A:** Warm-start retrieval so repeated questions cost fewer RTS calls.
- **Absorbable:** Cache per-topic evidence profiles and search delta for follow-up questionnaires.

#### [Forenly AI Skill Agent](https://github.com/ForenlyAI/slack-agent-builder)
- **Track:** New Slack Agent
- **Thesis:** Human-in-the-loop RLHF control center for humanoid robot training: operators rate MuJoCo trial videos in Slack and intervene when training bottlenecks.
- **Stack:** Python/Node conceptual, Slack AI, MCP, RTS, MuJoCo simulation.
- **Evidence:** Concept README with architecture, Discord community; **pre-build stage, no tests/runnable code**.
- **Surfaces:** Block Kit Skill Audit Cards, Slack AI, MCP, RTS.
- **Better than A&A:** Novel robotics/RLHF domain with rich human feedback loop.
- **Absorbable:** Human feedback ratings on approved answers to train an answer-quality model over time.

#### [culprit](https://github.com/Uthmannabeel/culprit)
- **Track:** New Slack Agent
- **Thesis:** Incident triage that recalls how similar incidents were fixed, gathers GitHub evidence over MCP, and drafts a fileable GitHub issue.
- **Stack:** TypeScript ESM strict, Bolt v4, Anthropic/Google SDKs, MCP SDK, Gemini embeddings, Socket Mode, Vitest.
- **Evidence:** GitHub Actions CI, `npm test`, `verify:evidence/memory/learning` scripts, Block Kit Builder link, dual LLM providers, seed corpus.
- **Surfaces:** `@Culprit` mention/DM, alert-channel watcher, App Home track record, Canvas incident doc, MCP server.
- **Better than A&A:** Bidirectional MCP, compounding memory, categorical confidence, multi-signal evidence cross-check.
- **Absorbable:** App Home track-record dashboard for approved-answer outcomes; categorical confidence labels; promote resolved thread to answer library; bidirectional MCP write path.

#### [greenops-agent](https://github.com/BenDuske/greenops-agent)
- **Track:** New Slack Agent
- **Thesis:** Sustainability intelligence agent for facilities teams using simulated BMS data.
- **Stack:** JavaScript, Bolt, Claude Agent SDK.
- **Evidence:** 95 files, 13 test files, docs, `PRIVACY.md`.
- **Surfaces:** App Home, DMs, `@GreenOps`, Agent panel, Slack MCP Server.
- **Better than A&A:** Rich Agent-panel integration with suggested prompts; domain simulation tools.
- **Absorbable:** Agent panel suggested prompts for questionnaire ingestion; richer demo/simulation mode.

#### [Slack-agent-_01-bot](https://github.com/Bonu000/Slack-agent-_01-bot)
- **Track:** New Slack Agent
- **Thesis:** RTS-grounded Q&A and workflow automation with a rule-based fallback mode.
- **Stack:** Node.js, Bolt, RTS, Supabase, OpenAI/Anthropic.
- **Evidence:** 11 files, runnable `npm start`, manifest in README.
- **Surfaces:** `@mention`, DM, `/ask`, `/search`, `/agent-stats`, scheduled workflows.
- **Better than A&A:** Simple scheduled workflow automation; rule-based fallback when no LLM key is configured.
- **Absorbable:** Scheduled status workflows (weekly digest); rule-based fallback for air-gapped demos.

#### [Pedro](https://github.com/EstevanSL/slackHackathon)
- **Track:** Agent for Good
- **Thesis:** Dog-rescue health passport from a short video clip, using MCP CV and RTS for reunification.
- **Stack:** Python, Bolt, Qwen, MCP, Canvas, RTS.
- **Evidence:** Built-in mock CV server for local runs, manifest, architecture diagram.
- **Surfaces:** Assistant pane, `#found`, Canvas passports, App Home.
- **Better than A&A:** Stateful Assistant-pane wizard, per-record Canvas passport, mock mode for safe demos.
- **Absorbable:** Stateful Assistant-pane onboarding for questionnaires; per-questionnaire Canvas dossier; mock MCP/LLM mode.

#### [Veritype](https://github.com/tdries/dev-slackathon-agent)
- **Track:** New Slack Agent
- **Thesis:** Proactive fact-checker that listens to channels, offers verification, and posts chart-rich verdict cards.
- **Stack:** TypeScript, Bolt, Anthropic Haiku/Opus, Puppeteer, Datatype variable font, MCP.
- **Evidence:** Web dashboard, sample fixtures, card renderer, MCP server, screenshots, operator manual.
- **Surfaces:** Channel listener, ephemeral offer, thread verdict card, App Home dashboard, library, playground, MCP.
- **Better than A&A:** Proactive claim screening; rich data-visualization cards; standalone web dashboard.
- **Absorbable:** Proactive screening of uploaded claims against approved answers; richer review UI with inline charts; web analytics dashboard.

#### [Amnesia Agent](https://github.com/shubhambhattacharya-dev/SlackHackerthon)
- **Track:** New Slack Agent
- **Thesis:** Catches forgotten commitments in Slack, tracks live countdowns, and drafts completion emails.
- **Stack:** Node.js, TypeScript, Bolt, Groq, PostgreSQL (Neon), SMTP, MCP.
- **Evidence:** 39 files, architecture diagram, Render deploy instructions.
- **Surfaces:** `/commitments`, interactive cards, MCP tools.
- **Better than A&A:** Commitment tracking and proactive nudges; external email follow-through.
- **Absorbable:** Track SME commitments to answer questions and send reminders/follow-up emails.

#### [omniops-slack-agent](https://github.com/sajithanand/omniops-slack-agent)
- **Track:** New Slack Agent
- **Thesis:** Autonomous ITOps agent that searches workspace history, queries infrastructure over MCP (K8s/GitHub), and synthesizes root-cause analyses in Block Kit.
- **Stack:** TypeScript, Bolt, Slack AI, MCP, RTS.
- **Evidence:** `npm run test:agent` no-credential simulation, architecture diagram, submission checklist.
- **Surfaces:** `@omniops` mention, `/omniops` slash command, Block Kit UI, Canvas export.
- **Better than A&A:** Incident-specific multi-signal synthesis (workspace context + infra metrics).
- **Absorbable:** Multi-signal evidence synthesis card; Canvas export of root-cause report; ops MCP tools as optional evidence sources.

#### [slack-legacy-modernization-commander](https://github.com/Nafsgerman/slack-legacy-modernization-commander)
- **Track:** New Slack Agent
- **Thesis:** Legacy-modernization command center: turns a COBOL module into a business-readable assessment with grounded citations, SME validation workflow, and traceability graph.
- **Stack:** TypeScript, Bolt, MCP server over stdio, Claude grounding, App Home dashboard.
- **Evidence:** `npm test`, `npm run typecheck`, type-enforced validation boundary, adversarial tests proving model cannot emit `sme_validated`.
- **Surfaces:** `/legacy assess` slash command, assessment cards, App Home dashboard, traceability graph PNG, MCP.
- **Better than A&A:** Type-enforced model/app boundary; citation verification against real source lines; derived SME checklist.
- **Absorbable:** Type-enforced status machine so only humans can mark approved; evidence-catalog IDs for citations; App Home SME review dashboard.

#### [blast-radius-gate](https://github.com/Hokutoman00/blast-radius-gate)
- **Track:** New Slack Agent
- **Thesis:** Policy Enforcement Point at the MCP tool-call boundary: computes blast radius, evaluates OPA/Rego policy, and posts a human-approval card before any destructive action.
- **Stack:** TypeScript, OPA/Rego compiled to WASM, kind (Kubernetes) + filesystem domains, Bolt.
- **Evidence:** `npm run fs-demo` prompt-injection proof, ledger invariant verifier, kind-cluster demo scripts.
- **Surfaces:** `/demo`, `/incident`, `/incident-naive`, App Home audit dashboard, Block Kit challenge cards.
- **Better than A&A:** Proves safety for write-capable agents with deterministic policy below the LLM; LLM-independent guarantee.
- **Absorbable:** Blast-radius + policy gate before any A&A write action (Canvas export, Workflow Builder trigger); human-approval Block Kit pattern.

#### [Settled](https://github.com/GHGuide/settled)
- **Track:** New Slack Agent
- **Thesis:** Maintains a decision ledger with an epistemic lifecycle and exposes a `decisions://` MCP server so agents can query `is_binding()` before acting.
- **Stack:** Python, Bolt, SQLite (hash-chained audit), MCP, OpenRouter (DeepSeek).
- **Evidence:** 29 pytest tests, hash-chain tamper detection, `bench/benchmark.py` (naive agents ~60% stale-action vs 0% Settled), Railway/Fly deploy configs.
- **Surfaces:** `/settled` slash command, assistant DM/`@mention`, App Home dashboard, MCP server.
- **Better than A&A:** Explicit epistemic status (`proposed→contested→settled→superseded`), agent-queryable binding status, tamper-evident audit.
- **Absorbable:** Add `is_binding`/`superseded` status to approved answers; MCP tool to let external agents check answer validity; stale-action benchmark harness.

#### [Lore (atcuality2021)](https://github.com/atcuality2021/lore-slack-agent)
- **Track:** New Slack Agent
- **Thesis:** Org-memory agent that passively captures decisions, commitments, and facts from Slack, then answers with provenance across Slack, GitHub, Jira, and Notion via bidirectional MCP.
- **Stack:** Python 3.12, Node 18, Redis, PostgreSQL, Qdrant, aiohttp, React/Vite admin console, Bolt.
- **Evidence:** Redis-stream exactly-once intake, PII/credential regex armor, 4 intent dispatch paths, human approval gate with `asyncio.Future` bridge, admin console.
- **Surfaces:** Assistant thread events, `@mention`, Block Kit Confirm/Correct/Forget buttons, MCP server + client, RTS.
- **Better than A&A:** External integrations as MCP client, passive memory capture, hybrid vector+keyword retrieval with reinforcement/decay, multi-agent council mode.
- **Absorbable:** PII/credential screen before LLM calls; hybrid vector+keyword retrieval; multi-agent council for high-stakes answers; memory reinforcement.

---

### Agent for Good track

#### [CornerCheck](https://github.com/StephenSook/cornercheck)
- **Track:** Agent for Good
- **Thesis:** Fail-closed fighter-clearance agent across jurisdictions, with formally verified safety proof.
- **Stack:** Python, `slack-bolt`, FastMCP, Z3-solver, Pydantic, Postgres, `jellyfish`, `portion`.
- **Evidence:** 252 passing tests + Z3 safety proof that active suspension ⇒ never CLEAR, conformal prediction on 4,203 real fighter pairs, live dashboard at `cornercheck.onrender.com`, CI with real Postgres.
- **Surfaces:** Assistant pane, Block Kit verdict/disambiguation cards, Data Table audit view, Canvas export, Workflow Builder custom step, MCP, RTS, live dashboard.
- **Better than A&A:** Full Z3 formal verification of concrete safety invariant, conformal prediction for identity matching, public live dashboard, three fail-closed locks.
- **Absorbable:** Z3 to prove date/interval invariants for evidence freshness; conformal calibration for answer-matching thresholds; public dashboard showing audit-chain verification; live verify-ledger button.

#### [Gavel](https://github.com/tmoody1973/gavel-slack-agent)
- **Track:** Agent for Good
- **Thesis:** Proactive Slack agent for Milwaukee civic transparency — watches city agendas, warns neighborhoods before votes, bilingual English/Spanish.
- **Stack:** JS/TS, Bolt, Claude Agent SDK, Convex vector DB, custom Milwaukee Civic MCP server, RTS, Deepgram, Fly.io.
- **Evidence:** **927 tests**, live deployed, real civic data, custom MCP server, demo video.
- **Surfaces:** Proactive unprompted posts, assistant thread with prompts/status/streaming, `app_mention`, reply-in-thread, DM, App Home, Block Kit bilingual cards.
- **Better than A&A:** Largest test count across all tracks; real-world deployment with live civic data; three-memory retrieval architecture; bilingual generation.
- **Absorbable:** Proactive alert scheduling for stale deadlines; bilingual Canvas/export support; custom MCP server for external compliance data.

#### [Vigie](https://github.com/Vitalcheffe/vigie)
- **Track:** Agent for Good
- **Thesis:** Elder watch during heatwaves — crosses Météo-France alerts with beneficiary registry.
- **Stack:** Python, `slack_bolt`, MCP, OpenAI, Redis, Pydantic.
- **Evidence:** 159 tests, live Railway sandbox, App Home KPI dashboard, scenario simulation.
- **Surfaces:** `/vigie` slash commands, DMs, App Home, Canvas, Block Kit check-in buttons, MCP.
- **Better than A&A:** Strong social-impact story; live KPI dashboard; operational scenario simulation.
- **Absorbable:** KPI dashboard in App Home (auto-answer rate, pending reviews, stale answers); scenario-based demo scripts.

#### [Clarion](https://github.com/knarayanareddy/clarion)
- **Track:** Agent for Good
- **Thesis:** Accessibility agent for deaf/HoH, low-vision, dyslexic, ESL, neurodivergent workers.
- **Stack:** TypeScript, Bolt JS v4, GPT-4o, better-sqlite3, MCP stdio server.
- **Evidence:** README/manifest evidence.
- **Surfaces:** File-event handlers, `@Access` mentions, in-thread replies, Assistant.
- **Better than A&A:** Accessibility profiles; dignity-by-default UX.
- **Absorbable:** Accessibility profiles for requesters; private image-description flow.

#### [Setu](https://github.com/Ritesh-Root/setu-agent)
- **Track:** Agent for Good
- **Thesis:** Two-way language bridge: non-English field workers post in their language; managers reply in English; Setu threads translations privately.
- **Stack:** Node.js, Bolt, Socket Mode, Gemini 2.5 Flash, stdio MCP server.
- **Evidence:** Working demo flow, manifest, MCP server tested with an MCP client; no tests found.
- **Surfaces:** Channel message events (two-way threaded translation), Slack AI assistant panel, MCP.
- **Better than A&A:** Real-time multilingual two-way thread bridging; assistant panel Q&A in user's language.
- **Absorbable:** Multilingual wrapper for questionnaire input/output; assistant-panel digest in requester's language; translation tools via MCP.

#### [Bridge (SaudSatopay)](https://github.com/SaudSatopay/bridge-slack-agent)
- **Track:** Agent for Good
- **Thesis:** Accessibility agent that translates, simplifies, describes images, transcribes voice notes, and keeps a living plain-language Canvas digest per channel.
- **Stack:** Node.js, Bolt, Claude Agent SDK, Slack MCP server, Groq Whisper, Canvas API.
- **Evidence:** 58 unit tests, live integration script, manifest, proactive dedupe/cooldown logic.
- **Surfaces:** Message reactions, message shortcuts, `/bridge`, App Home, Canvas digest, Assistant, DM, `@mention`.
- **Better than A&A:** Inclusive UX for non-native/neurodivergent/blind users; agentic tool-use loop.
- **Absorbable:** Plain-language simplification of drafted answers; alt-text for images in evidence; MCP-exposed accessibility tools.

#### [Bridge (GuptaAnvesha)](https://github.com/GuptaAnvesha/Slack_Agent_Builder_Challenge)
- **Track:** Agent for Good
- **Thesis:** Accessibility agent that auto-generates alt-text, rewrites messages in plain language, translates, and gives plain-language catch-ups.
- **Stack:** Node.js, Bolt, Slack AI assistant threads, Google Gemini, MCP server for simplify/translate/describe.
- **Evidence:** Runs offline with `npm start`, paste-ready manifest, MCP server usable outside Slack.
- **Surfaces:** Assistant pane, message shortcuts, `/bridge language`, ephemeral private outputs.
- **Better than A&A:** Agentic tool-use loop and first-class accessibility surface, privacy-by-default ephemeral outputs.
- **Absorbable:** Ephemeral plain-language/translate fallback for dense answers; MCP-exposed accessibility tools reusable by other clients.

#### [Grant-Copilot](https://github.com/Mounir1200/Grant-Copilot)
- **Track:** Agent for Good
- **Thesis:** Helps small nonprofits find, track, and apply to U.S. federal grants inside Slack via live Grants.gov data and a first-pass Project Summary generator.
- **Stack:** Python 3.14, uv, Bolt, FastMCP, Mistral Small, SQLite, APScheduler.
- **Evidence:** `uv run pytest`, integration spikes for Grants.gov API, MCP round-trip, Mistral tools.
- **Surfaces:** Assistant pane discovery, App Home pipeline (To apply / In progress / Submitted), modals, DM deadline reminders.
- **Better than A&A:** Tight human-in-the-loop workflow with deterministic filter injection so the model cannot silently alter eligibility criteria.
- **Absorbable:** Deterministic pre-filter injection before LLM step; deadline reminder scheduler; App Home pipeline/status board.

#### [LabOps Agent](https://github.com/Marianooss/Labops-Agent)
- **Track:** Agent for Good
- **Thesis:** Predicts clinical-lab reagent stockouts by test-type demand patterns and lets staff order/assign tasks directly from Slack.
- **Stack:** Python, FastAPI, Bolt, Prophet forecasting, Supabase/Postgres, Anthropic MCP, Canvas.
- **Evidence:** `tests/`, `docker-compose.yml`, Render deploy, YouTube demo, notebooks with CV metrics.
- **Surfaces:** `#labops-alerts`, App Home, Canvas inventory, Block Kit buttons/modals, MCP.
- **Better than A&A:** Time-series prediction + action loop; one-click Docker stack; live public Render deploy.
- **Absorbable:** Forecast questionnaire workload/seasonality; Docker-compose quick-start for judges; richer Canvas update flows.

#### [Dispatch](https://github.com/davidstrouk/dispatch-slack-agent)
- **Track:** Agent for Good
- **Thesis:** Mutual-aid coordination agent that reads free-text pleas in `#mutual-aid` and assigns the best-fit volunteer, justifying the match with past resolved requests recalled via RTS.
- **Stack:** TypeScript, Bolt, Slack AI classification, custom MCP roster server, RTS, Block Kit.
- **Evidence:** 39 tests, offline spike/smoke with no API keys, live end-to-end, demo, architecture diagram.
- **Surfaces:** Channel auto-dispatch, Slack Assistant/agent pane, assignment card, acceptance button, ledger loop posts resolved record.
- **Better than A&A:** Privacy-first, real-time resource coordination with precedent-based matching; dual surface (channel + assistant pane).
- **Absorbable:** Offline spike/smoke scripts that run without Slack tokens; dual-surface design; precedent recall to bias reuse of approved answers; acceptance → ledger loop.

#### [ResQ AI](https://github.com/Dolphin-Syndrom/Slack-Agent-For-Good)
- **Track:** Agent for Good
- **Thesis:** Multi-agent crisis-response coordinator inside Slack that activates crises, gathers live intel/resources, drafts comms, and routes approvals.
- **Stack:** TypeScript, Bolt, Groq LLM, MCP (9 tools), Google A2A protocol, SQLite.
- **Evidence:** Detailed README with architecture/sequence diagrams, runnable `npm run dev`, MCP/A2A curl examples; **no automated tests found**.
- **Surfaces:** `/crisis`, `/resq` slash commands, App Home dashboard, Block Kit approve/discard buttons, auto-created crisis channels.
- **Better than A&A:** Multi-agent A2A orchestration for complex workflows; auto-channel creation; human approval gate.
- **Absorbable:** A2A-style sub-agent orchestration for multi-step questionnaires; auto-create dedicated channels per case; approve/discard action pattern.

#### [Matchly](https://github.com/Kingnanaweb3/matchly)
- **Track:** Agent for Good — economic opportunity
- **Thesis:** Caseworker assistant that bridges clients to benefits, jobs, and launch opportunities, with a shared client snapshot and live-rules freshness engine.
- **Stack:** Python, Bolt, manifest, seeded corpus, RTS hook.
- **Evidence:** `demo.py` runs offline with no Slack/key; manifest; listeners. **No tests found**.
- **Surfaces:** `@Navi` mention, action-plan approval-gate buttons, assistant side-panel suggested prompts.
- **Better than A&A:** Reuses a single client snapshot across multiple skills; live-rules freshness check before drafting plans.
- **Absorbable:** Shared "case snapshot" for a requester reused across skills; live-rules refresh hook via RTS before reusing cached answers.

#### [gurtYos](https://github.com/amoghsingh130/gurtyos)
- **Track:** Agent for Good
- **Thesis:** Accessibility co-pilot that describes images, rewrites jargon into plain language, and produces accessible Canvas digests, with a custom MCP readability scorer.
- **Stack:** Python, Bolt, Claude, FastMCP, SQLite (prefs only), Slack Web API.
- **Evidence:** 59 offline pytest tests + gated live LLM/MCP tests, demo video, `scripts/selftest`.
- **Surfaces:** Slack Assistant ("catch me up", "accessibility report"), reaction triggers (👁️ / 🧩), proactive offers, App Home, Canvas digest.
- **Better than A&A:** Canvas as accessible digest surface; custom MCP scorer for readability/jargon/contrast; proactive reaction-based offers; prompt-injection fencing.
- **Absorbable:** Canvas digest export for review/approval summaries; custom MCP scoring tools for answer quality/readability; proactive offer UI; sanitize step for user-supplied questionnaire text.

#### [firstresponder-slack](https://github.com/4KInc/firstresponder-slack)
- **Track:** Agent for Good
- **Thesis:** Crisis/incident coordination agent that turns a Slack workspace into an emergency ops center, learning from every incident and using CSV-uploaded org data for context-aware response.
- **Stack:** Python, Bolt, Claude Agent SDK, Slack MCP Server, SQLite, Docker.
- **Evidence:** 28 pytest tests, 35 registered agent tools, CSV ingest engine auto-detecting 17 file types, 10 crisis playbooks, threat-zone-aware evacuation routing, time-based escalation, Dockerfile.
- **Surfaces:** `/crisis` slash command + subcommands, `@mention`/DM, emoji-reaction check-ins, App Home, Assistant view, Slack AI streaming, feedback buttons.
- **Better than A&A:** Deep domain-specific physical-safety workflow, zero-code CSV knowledge base, learning engine surfacing historical patterns, multi-modal emoji input.
- **Absorbable:** CSV-upload auto-detection for org/questionnaire data ingest; emoji-reaction handlers for user attestations; historical-comparison pattern for reused answers.

#### [access](https://github.com/Uthmannabeel/access)
- **Track:** Agent for Good
- **Thesis:** Auto alt-text for images, voice-clip transcription, and plain-language thread summaries in Slack.
- **Stack:** TypeScript, Bolt v4, Gemini vision/audio/text.
- **Evidence:** CI badge, `npm test`, manifest, docs folder.
- **Surfaces:** File-event handlers, `@Access` mentions, in-thread replies.
- **Better than A&A:** Accessibility-first, multimodal media handling.
- **Absorbable:** Auto alt-text/transcripts for questionnaire attachments; plain-language summaries of dense compliance threads.

---

### Slack Agent for Organizations track

#### [slack-inbox-triage](https://github.com/MukundaKatta/slack-inbox-triage)
- **Track:** Slack Agent for Organizations
- **Thesis:** Governed inbox-triage agent that classifies channel backlogs and drafts replies while refusing Slack API calls or outbound HTTP hosts outside declared allowlists.
- **Stack:** Python, `slack-sdk`, `pytest`, `FakeSlackProvider`.
- **Evidence:** 35 pytest tests, 90-sec offline demo, scope/egress allowlists, tool-arg validation, output-schema repair, append-only JSONL audit.
- **Surfaces:** `/triage` slash command, `@mention` handler, minimal manifest.
- **Better than A&A:** Governance as first-class feature; admins can read `governance.py` + manifest and know exactly what the agent can do.
- **Absorbable:** Scope/egress allowlist wrapper around Slack calls; `FakeSlackProvider` for hermetic tests; robust LLM JSON schema repair.

---

### Relevant non-submission tooling

#### [slk](https://github.com/howar31/slk)
- **Track:** N/A — agent-facing Slack CLI
- **Thesis:** Low-token Slack CLI for agents, supporting Canvas and Lists read/write with curated output.
- **Stack:** Go, Slack Web API, Cobra, OAuth, generated agent skills.
- **Evidence:** Go test suite across ~20 command/auth files, GitHub Actions CI/release, Homebrew/npm distribution, prebuilt binaries.
- **Surfaces:** CLI only (can be wrapped as MCP/skill); supports Canvas + Lists + messages + search.
- **Better than A&A:** Cheaper Canvas/List operations than official Slack MCP connector; composable with shell pipelines; encrypted token storage.
- **Absorbable:** Use `slk` as low-token utility for Canvas/List import/export scripts; generated skill pattern for internal tooling docs.

---

## 2. Head-to-Head Engineering Matrix

| Dimension | A&A | Council | Consensus | Kept | Quorum | Arbiter | CornerCheck | Gavel | Lore | culprit | Settled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Tests** | 284 | 0 | ~50+ repo; 58-case eval | 140+ | 21 | 66 | 252 | 927 | 191 | present; count N/S | 29 |
| **Eval / adversarial** | 136 cases, 26 held-out, 136/136 Azure | None | 58 cases, 9 injection patterns | 52+ lifecycle, 7 adv rounds | None | Fact/workslop/routing + 12/12 adv | Z3 + conformal | Unknown | Offline harness | `verify:*` scripts | Stale-action benchmark |
| **Formal assurance** | Z3 contract + runtime invariant | None | None | FSM invariant tests | None | None | Z3 safety proof | None | None | None | Hash-chain audit |
| **Citation grounding** | Snippet-level `GroundingGate` | None | Permalink-in-set | None | Permalink | Prompt-based / claim graph | Rule engine | Structured + news + RTS | Multi-hop KG | GitHub evidence hub | None |
| **App Home** | ✅ ACL-filtered dashboard | ✅ calibration | ✅ dashboard | ✅ ledger | ❌ declared only | ✅ | ❌ | ✅ | ✅ | ✅ track record | ✅ |
| **Workflow Builder** | ✅ custom step | ✅ step spec | ✅ step | ❌ | ❌ (Vercel Workflow) | ❌ | ✅ step | ❌ | ❌ | ❌ | ❌ |
| **Canvas/Lists** | ✅ Canvas + Lists | ✅ Canvas | ✅ Canvas + Lists | ❌ | ✅ Canvas | ✅ Lists + Canvas | ✅ Canvas export | ❌ | ✅ Canvas | ✅ Canvas | ❌ |
| **MCP** | ✅ read-only server | ✅ wrapper | ✅ Slack MCP | ✅ deterministic client | ✅ Slack MCP | ✅ Slack MCP | ✅ FastMCP | ✅ 3 servers | ✅ FastMCP glossary | ✅ bidirectional | ✅ `decisions://` |
| **RTS** | ✅ per-user | ❌ | ✅ | ✅ retriever | ✅ per-user | ✅ | ✅ injury scan | ✅ | ✅ interchangeable | ✅ | ❌ |
| **Live deploy** | ✅ Render | ✅ Vercel workspace | ❌ | ❌ | ✅ Vercel + health | ❌ | ✅ Render dashboard | ✅ Fly.io | ❌ | ❌ | configs only |
| **Idea novelty** | Fail-closed compliance memory | Brier council | Contradiction firewall | Obligation lifecycle | Durable provenance | Judgment layer | Fighter safety | Civic transparency | Research KG | Incident memory | Epistemic lifecycle |

*N/S = not stated in README*

---

## 3. Prioritized Absorption Plan

**Already done in Asked & Answered:** 284 tests, 136-case eval, Z3 contract proof, runtime invariant verification, deterministic snippet-level `GroundingGate`, hash-chained ledger, ACL-filtered App Home with KPI dashboard, public `/verify-ledger` endpoint, Workflow Builder custom step, Canvas + Lists export, Canvas-first decision log, N-of-M approval policy engine, read-only MCP server, per-user RTS, live Render deploy.

### Tier 1 — Do before judging (highest rubric ROI)

1. **Adversarial eval expansion vs Consensus** — Add 25+ adversarial cases (homoglyph, ZWJ, RTL, HTML entities, JSON smuggling, fake system tags, delimiter breaks, prompt chaining, role-play). Adopt NFKC normalization + delimiter wrapping in `src/core/sanitize.ts`. Publish guard-only vs model-dependent metrics. ✅ **Done** — 127 → 136 cases, `sanitize.ts` hardened.
2. **Public ledger verifier / "See the safety proof" button vs CornerCheck** — Expose a public `/verify-ledger` endpoint or Slack button that re-runs the Z3 proof + hash-chain verification. ✅ **Done** — `/verify-ledger` live + App Home button.
3. **Canvas-first approval decision log vs Council/Meridian/Quorum** — Mirror every approved answer to a channel Canvas decision log with citations and approver names. ✅ **Done** — `buildCanvasDocument` decision-log section + signatures.
4. **KPI App Home dashboard vs Vigie/Gavel** — Add stats: questionnaires run, verified answer rate, pending SME reviews, stale answers, ledger integrity. ✅ **Done** — App Home KPI dashboard live.
5. **N-of-M approvals + policy engine vs Aegis/Kept** — Auto-approve low-risk questionnaires, require N-of-M for high-sensitivity ones, add TTL escalation. Keep the existing two-gate model as default. ✅ **Done** — `src/core/policy.ts` + `decide.ts` N-of-M.

### Tier 2 — Strong differentiators if time allows

6. **Durable approval hooks vs Quorum** — Replace synchronous button timeouts with persistent deadline tracking for SME review; send proactive nudges for stale rows. *(not done)*
7. **Proactive contradiction watcher vs Consensus/Déjà** — Listen to channel messages and flag contradictions against approved answers; opt-in per channel. *(not done)*
8. **Multi-hop retrieval + lightweight KG vs Lore/Arbiter** — Decompose complex multi-control questions, follow citation chains across messages; build a knowledge graph of controls, decisions, contradictions. *(not done)*
9. **Deterministic state machine + audience redaction vs Kept** — Add explicit guarded FSM for answer lifecycle, audience-safe redaction before customer export, idempotency keys, optimistic concurrency. *(partial — ledger exists; FSM/redaction not done)*
10. **Bidirectional MCP governance tools vs Culprit/Paper Trail/Settled** — Expose `check_answer` / `propose_answer` / `is_binding` MCP tools; all writes still route through human approval. *(partial — read-only MCP exists; write/governance tools do not)*
11. **Type-enforced model/app boundary vs slack-legacy-modernization-commander** — Ensure the LLM output type cannot express `approved`; approval is application-owned. *(not done)*
12. **Blast-radius / policy gate before writes vs blast-radius-gate** — Post a human-approval Block Kit card before any Canvas export, Workflow Builder trigger, or external action. *(not done)*

### Tier 3 — Nice-to-have polish

13. Human signature/attestation per approved row vs Threadwork *(not done)*
14. Query expansion for keyword-only RTS vs Tribal Knowledge Agent ✅ **Done** — `src/core/planner.ts` literal-then-expanded fallback.
15. Conflict/staleness badges on answers vs Tribal Knowledge Agent *(not done)*
16. Red-team pre-approval check vs Devil's Advocate *(not done)*
17. Bilingual export support vs Gavel *(not done)*
18. Custom MCP server for external compliance data vs Gavel *(not done)*
19. Accessibility profiles vs Clarion/gurtYos *(not done)*
20. Audio/image accessibility export vs access/Bridge/gurtYos *(not done)*
21. Offline demo/spike scripts vs Dispatch/Culprit/OmniOps *(not done)*
22. Capability probes + graceful degradation vs Threadwork *(not done)*
23. Public dashboard for audit-chain status vs CornerCheck *(not done)*

---

## 4. Strategic Bottom Line

Asked & Answered remains the engineering-rigor leader of the New Slack Agent track. The Tier 1 gaps are now closed. The remaining highest-ROI moves before final judging are:

1. Keep the test/eval/proof lead (284 tests, 136 eval cases, Z3 proofs, live `/verify-ledger`).
2. Add Brier/calibration scoring for SMEs to match Council's long-term trust mechanism.
3. Add durable approval hooks / proactive stale nudges to match Quorum's multi-day review UX.
4. Surface conflict/staleness badges on answers to match Tribal Knowledge Agent's honest-signaling UX.
5. Add bidirectional MCP governance tools (`check_answer` / `propose_answer`) to match Culprit/Paper Trail.

All are additive and preserve the existing permission invariant.

---

## 5. What Changed vs the Baseline Document

- **More than doubled the repo set:** from ~25 substantive submissions to **55 distinct verified public repos** (plus `slk`), including many new entries the baseline missed (e.g., `culprit`, `Settled`, `blast-radius-gate`, `slack-legacy-modernization-commander`, `Veritype`, `Pedro`, `greenops-agent`, `Perseus`, `TriageMate`, `Grant-Copilot`, `gurtYos`, `firstresponder-slack`, `access`, `slack-inbox-triage`, `Dispatch`, `ResQ AI`, `Matchly`).
- **Déjà marked unverified:** the baseline listed a repo URL; the latest swarm could not verify a live public repository or README.
- **New cross-track threats surfaced:** `CornerCheck`, `Gavel`, and `Vigie` are now tied to concrete engineering evidence (Z3 proof, 927 tests, live dashboards) rather than named risks.
- **Fresh absorption patterns added:** durable Vercel-style approval hooks, type-enforced model/app boundary, blast-radius policy gate, bidirectional MCP governance tools, offline spike/demo scripts, capability probes, and governance allowlists.
- **Updated matrix:** expanded from 9 to 10 competitors and added `culprit`/`Settled`; clarified A&A strengths and partial gaps.
- **Absorption plan refined:** Tier 1/Tier 2/Tier 3 reordered by rubric ROI and explicitly marks what is already done vs not done in A&A. Tier 1 and keyword-variant query expansion are now implemented.
