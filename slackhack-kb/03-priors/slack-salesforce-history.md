# Prior Runs & Slack/Salesforce Winner History (researched 2026-07-11)

## Was there a prior run?
**No.** This is the first "Slack Agent Builder Challenge." Evidence of absence: Devpost API (`devpost.com/api/hackathons?organization=Slack`) returns exactly one past Slack-organized hackathon (Digital HQ Slackathon 2021–22); `?search=slack`/`?search=agentforce` surface nothing else Slack-branded. But it has clear ancestors with published winners.

## Ancestor/sibling events, winner by winner

### 1. Digital HQ Slackathon (slack.devpost.com, Nov 2021–Feb 2022, $47k, 500 participants, **39 submissions**)
Criteria: Impact ("solve an actual problem for a real team"), Originality, Quality & Completeness — with explicit note: *"an app with less polish that demonstrates the end-to-end flow is better than a super-slick submission that only demonstrates part of the solution."* Judges: Slack executives.
- **1st ($15k) Get Together** — scheduling inside Slack (Home tab + modals; Django/Postgres/GCP). devpost.com/software/get-together-slack-hack-2-0
- **2nd ($10k) AccessOwl** — SaaS access-request management in Slack; later became a real commercial app. devpost.com/software/accessowl
- **3rd ($5.5k) Daily Scrum Supporter** — timeboxed standup facilitator.
- HMs: Pulse (auto status), SalesSync, Shi-Q-Know (support queue), Pyroscope Bot, SLA Monitor, FileOpen Sharebot. $1k feedback bonuses for platform-beta feedback.
- **Pattern: every podium winner = narrow, native-feeling workflow tool on Slack surfaces (Home tab, modals), not a chatbot wrapper.**

### 2. Slack App Virtual Hackathon (Mar 2020, 24 teams)
Winners: Intwixt, Workstreams, Morgan by Nextup, Clerk Chat. Slack's framing: winners "leveraged Slack's newest developer tools… while solving practical workflow problems." **Winning move = showcase the just-launched platform primitives.** 2026 analogue: Agent Builder + MCP + RTS.

### 3. Agentforce Virtual Hackathon (agentforcehackathon.devpost.com, Mar–Apr 2025, $140k, 7,206 participants, **225 submissions ≈ 3% submission rate**)
Criteria: Business Relevance, Creativity, Potential Impact (measurable value), Design, Technical Implementation.
- **Grand $50k — Call Prep Agent**: meeting-prep agent chaining Google Calendar → Perplexity/LinkedIn research → Salesforce logs → rich in-chat UI → Google Docs pre-call brief. Won on: universal relatable pain, 7 orchestrated real actions, tangible artifact output.
- Most Creative $20k — AgentPlus (platform-enhancement suite, zero external dependencies).
- Most Impactful $20k — AgentResQ (crisis response end-to-end pipeline, real-time Slack alerts).
- Best Demo Delivery $20k — OnePath AI (won on demo storytelling of high-stakes incident response).
- **Best Use of Slack $25k — EcoZen** (Slack as operational surface for carbon-efficiency insights).
- Salesforce's praise blog highlights: multi-step automation, multi-channel integration, voice/hands-free UX. admin.salesforce.com/blog/2025/agentforce-in-action-use-cases-from-the-agentforce-virtual-hackathon

### 4. TDX Agentforce Hackathon 2025 (in-person, $100k)
**Team Agent Halo** — multi-agent network coordinating insurers/repair/responders/family after a car accident, built in 16h.
Why they won (their own words): deliberately simple out-of-the-box tech (no LWC); **repeatedly re-read the judging criteria** and aligned to sponsor's strategic vision; submitted a **20-page deck (architecture, roadmap, MVP, business case)** on top of the demo; instantly understandable real-world story. salesforceben.com/how-team-agent-halo-won-100k-at-the-tdx-agentforce-hackathon/

### 5. TDX 2026 Hackathon (Mar 2026) — most recent Salesforce judging signal
admin.salesforce.com/blog/2026/award-winning-agentforce-solutions-to-inspire-your-next-build
- Grand Prize: **City Pulse Agent** (municipal infrastructure, Slack + Tableau + Data 360).
- Agentforce for Good Grand: **HarvestBridge** — four-agent network (DonorBot/MatchMaker/LogisticsCoordinator/ImpactAnalyst) rescuing surplus food "in under 90 seconds," coordinating volunteers **via Slack MCP Server**, voice + vision.
- Best Use of Slack: **EdAdmit** (admissions scoring that supports, not replaces, humans).
- **9 of 11 winners used Slack as coordination surface; both grand prizes had a quantified human-story outcome ("90 seconds," "hours to minutes").**

## Recurring winner patterns (Slack/Salesforce-specific)
1. **One narrow, universally relatable workflow, killed completely** (Call Prep, Get Together, AccessOwl, Agent Halo). Sponsor says it outright: "not Swiss Army knives."
2. **Multi-step orchestration across real external systems** beats clever single-turn bots — grand winners chained 4–7 concrete actions; multi-agent networks won both TDX grand prizes.
3. **Tangible artifact / measurable outcome ends the demo** (Google Doc, voucher, "90 seconds", "5 hours → minutes").
4. **Native platform surfaces are load-bearing** (2020 App Home/modals → 2026 Block Kit Data Tables/Cards/Alerts/Carousels — the "new toy" bonus).
5. **Demo + narrative are half the win** (Agent Halo's rubric-study + 20-page deck; OnePath's $20k purely for demo delivery).
6. **Human + agent, not human replacement** (EdAdmit, Purple 11's dedicated award).
7. **Social-impact tracks reward QUANTIFIED impact** — vague "helps nonprofits" loses; a number wins.
8. **Simplicity over exotic tech** (Agent Halo skipped LWC; AgentPlus used only core tools).

## Direct signals for THIS challenge (from updates + June 2026 newsletter)
- **Update 44783 (verbatim tell):** *"If your agent would work identically without the MCP server or RTS API, that's a tell — and it costs you on Technological Implementation."* → required tech must be LOAD-BEARING.
- Update 44560: do one thing well; Block Kit native ("not walls of text"); **lead video with the pain point**; judges watch ≤3 min; **don't let AI write your name/description ("you'll end up the fourth 'SlackSage' in the gallery")**; architecture diagram must show WHERE the AI/MCP/RTS piece sits; submit early.
- June 2026 newsletter pushes: **Block Kit Data Tables, Cards/Alerts/Carousels** ("agents shouldn't just talk, they should act"), `slack create agent` bring-your-own-LLM, Slack MCP Server + RTS (Dev Huddles Ep05, Sr PM Manuela Caicedo), nine-part Marketplace series.
- Orgs track is a distribution play (Slack wants Marketplace-ready apps); judges incl. Gillian Bruce (ex-Salesforce evangelist) — same judging culture as Agentforce events.

## Bottom line
Winning formula, stable across 5 sibling events: **narrow named workflow pain + MCP/RTS load-bearing + Block Kit-native interactive output (Data Tables/Cards = new-toy bonus) + ≤3-min demo opening with the problem and ending with a measurable outcome + human-voiced writeup + real architecture diagram.**
