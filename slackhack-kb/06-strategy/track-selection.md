# Track Selection — Decision & Rationale (2026-07-11)

## Decision: build one flagship app → **primary: Slack Agent for Organizations**, with a **zero-cost fallback to New Slack Agent** decided at T-24h.

The app itself (a new agent using all three qualifying technologies) satisfies both tracks' project requirements; only the Marketplace submission differs. Track is chosen on the Devpost form at submission time.

## Why Organizations track first
| Factor | Evidence |
|---|---|
| Thinnest field | ~8 GitHub-visible entries, **none above 3.5/5**, none visibly completing the Marketplace path (`02-intel`) |
| Invisible competition also thinnest | 4,160 registrants skew "vibe coder"/no-code — they won't do Marketplace bureaucracy; the last-72h surge dilutes the other two tracks far more |
| Same rubric, same $8k | Judging criteria identical across tracks; Orgs 1st adds exec conversation + Stack Overflow podcast |
| Barrier is bureaucratic, not technical | Landing/support/privacy pages, multi-workspace OAuth, listing assets, AI disclosures — all systematically producible (`05-tech/oss-leverage.md`); this rewards checklist discipline, which is our chosen weapon |
| Sponsor intent | Slack runs this track to seed the Marketplace; Devpost published a hand-holding deployment guide with 4 days left → they *want* completions |

## Why NOT the others as primary
- **Agent for Good:** most crowded (~25 visible) AND contains the four strongest entries in the entire field — CornerCheck (252 tests, Z3 proof, live verification dashboard), Relay (published eval numbers, CDK), Vigie (159 tests, live 24/7 sandbox), Crisis Navigator (7 ADRs). Beating them in 60h is a coin-flip at best.
- **New Slack Agent:** 10-entry pileup on decision-memory/org-knowledge; strong leaders (Quorum, Consensus, Ishu). Viable as fallback with our differentiated niche, not as first choice.

## The Marketplace gate (the one real risk) and its control
Gate: automated pre-submission check **blocks submission** unless the app is installed in **5 active workspaces** (used in past 28 days; sandboxes don't count) + distribution activated (real multi-workspace OAuth) + public landing/support/privacy pages + listing assets/disclosures.
- Devpost's own guidance sanctions "create a free Slack workspace to build and deploy" for entrants without one. We create 5 real free workspaces, install via our public OAuth flow, and use them (real messages, real runs) — mechanically satisfying "active." Free plans lack the agent container; that's fine — judging happens in the sandbox; the track requires *submission*, evidenced by App ID.
- Approval is NOT required by the deadline (10-day preliminary + 10-week functional clocks make it impossible for everyone) — only a valid submission.
- **Decision gate at T-24h (evening July 12 IST):** if the automated pre-submission checks aren't green, we select "New Slack Agent" on the Devpost form instead. Zero rework — the build is identical.

## Secondary prize alignment
The engineering-depth profile also targets **Best Technological Implementation ($2k)** — awarded to a non-podium entry, so it's a natural consolation slot; tie-breaks across all prizes resolve Tech-Implementation-first, favoring us by construction.
