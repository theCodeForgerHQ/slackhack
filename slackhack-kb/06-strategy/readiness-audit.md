# Pre-Build Readiness Audit (Sat Jul 11, ~10:00 IST) — GO/NO-GO

## Verdict: GO. Further planning now has negative expected value.
Every remaining decision-changing unknown is empirical — resolvable only by touching the platform (the four Phase-0 spikes), not by more research. Each planning hour now costs a build hour out of ~50.

## Closed in this audit
1. **Conveyor Slack app exists** (conveyor.com/integrations/slack — @Conveyor answers security questions in-channel; their agent accepts questionnaires via Slack). **Pitch correction (supersedes v1 "incumbents live outside Slack"):** incumbents *bridge* Slack to an external answer library you must separately maintain and pay for; A&A makes the workspace itself the library (RTS evidence, zero-copy), adds per-requester permission-aware answers (the ACL invariant — no incumbent has this), runs fail-closed, and is a native agent_view agent, not a bot-mention bridge. Name Conveyor in the text description only (trademark clause: not in video). This makes the Idea pitch more precise, not weaker — the rubric explicitly rewards "how much does it improve on what exists."
2. **Sandbox durability:** Developer Program sandboxes last 6 months (docs.slack.dev/tools/developer-sandboxes) — covers the Aug 6 judging end. Action: extend if prompted; don't archive.
3. **Hosting durability through Aug 6:** judges may test in week 3 of judging. Use a non-sleeping tier (Railway Hobby / Fly min-machines-1), add an uptime monitor + keep-alive, calendar a weekly health check until Aug 11.
4. **Citation binding simplified (design decision):** answer-level citations (each answer lists 1–3 evidence permalinks + snippets), not per-sentence. Per-sentence binding is the highest-variance ML task in the build for near-zero rubric gain. LIMITATIONS.md notes per-sentence as future work.
5. **Judge-README-first:** write the judges' 5-minute walkthrough BEFORE feature code (it becomes the acceptance spec for the never-cut journey).
6. **Second hedge submission: rejected.** Rules allow multiple substantially-different entries; 50 hours makes a second entry a quality tax on the first. Depth over spread.

## Only resolvable by building (Phase-0 spikes, first 6h)
S1 agent_view events · S2 action_token semantics · S3 Data Table rendering · S4 Marketplace counter. Fallbacks pre-designed for each (see project-design v2).

## USER-ONLY checklist (cannot be delegated — do before/at build start)
- [ ] Devpost: register for the hackathon, open "Enter a Submission," **screenshot every form field** (form recon — fields may exist we haven't prepped; also confirms how track selection works).
- [ ] Slack: join Developer Program, provision sandbox (needs your identity).
- [ ] Accounts/keys ready: Anthropic (or OpenAI) API key with billing, GitHub, Railway/Fly with a paid-capable card, YouTube channel for the video.
- [ ] The real human: message a security engineer / AE contact today for the 30-min interview (quote + hour-count + permission to reference).
- [ ] Recording setup sanity check: screen recorder + mic + a quiet hour on Monday.

## Confidence movement
This audit + the judge-panel hardening is the ceiling of what planning can buy (~30–35% Orgs-1st, ~45–55% any-prize). The next probability points are purchased only by: spikes passing (+), deploying by hour 20 (+), measured eval numbers (+), the ACL-invariant demo (+, Best-Tech play), submitting a day early (+). All of these require building.
