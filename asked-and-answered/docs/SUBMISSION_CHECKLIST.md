# Slack Agent Builder Challenge — submission checklist

> Deadline: July 13, 2026 at 5:00 PM PT
> Track: New Slack Agent
> App: AskedAnswered · App ID A0BHW9UC23A

---

## ✅ Done

- [x] Slack app created and installed in sandbox (`Asked Answered Demo`, team `T0BGLJF0J23`).
- [x] Socket Mode OFF; Event Subscriptions request URL verified at `https://asked-and-answered-app.onrender.com/slack/events`.
- [x] Code deployed to Render free web service: `https://asked-and-answered-app.onrender.com`.
- [x] LLM routed through Azure OpenAI (`gpt-54-mini`, credits-only, no credit card).
- [x] Core v3 features implemented, tested, and deployed:
  - GroundingGate (deterministic snippet verification)
  - Multi-agent Jury with provider registry
  - EvidenceGraph + ConformalMatcher
  - LedgerV2 + decide() event-sourced lifecycle
  - 60-case eval harness, 146/146 unit tests passing
- [x] Submission text draft: `docs/SUBMISSION.md`.
- [x] Architecture diagram: `docs/architecture.svg`.
- [x] Architecture doc: `docs/ARCHITECTURE.md`.

---

## ⬜ Still required for Devpost

### 1. Sandbox access

In your Slack sandbox `Asked Answered Demo`, invite these users as **Members**:

- `slackhack@salesforce.com`
- `testing@devpost.com`

**How:**
1. Open Slack in browser → `https://e0bgzv586kg-2g1mp275.slack.com/admin`.
2. People → Invite People → enter both emails → Member role → Send.

### 2. Demo video (~3 minutes)

Record a public YouTube or Vimeo video following `docs/VIDEO_SCRIPT.md`.

Key beats:
1. Upload/paste questionnaire in DM.
2. Show Verified / Grounded / Needs-SME results.
3. Show Review card with citations.
4. Show poison-doc ignored due to GroundingGate.
5. Approve/edit/reject and export xlsx.
6. `verify ledger` command.

Upload link: `_____________`

### 3. Devpost submission form

Open [the Devpost submission page](https://slack-agent-builder-2026.devpost.com) and fill:

| Field | What to paste |
|---|---|
| App name | Asked & Answered |
| Elevator pitch | `docs/SUBMISSION.md` → Elevator pitch |
| Inspiration | `docs/SUBMISSION.md` → Inspiration |
| What it does | `docs/SUBMISSION.md` → What it does |
| How we built it | `docs/SUBMISSION.md` → How we built it |
| Challenges / accomplishments | Mix from `docs/SUBMISSION.md` → Engineering proud of + Evals |
| What we learned | Keep short — mention RTS rate budgets and permission invariant |
| What's next | `docs/SUBMISSION.md` → What's next |
| Demo video URL | Your YouTube/Vimeo link |
| GitHub repo | `https://github.com/theCodeForgerHQ/asked-and-answered` |
| Architecture diagram | Upload `docs/architecture.svg` |
| Slack sandbox URL | `https://e0bgzv586kg-2g1mp275.slack.com` |

### 4. Submission metadata

- [ ] Sandbox member access granted to required emails.
- [ ] Demo video uploaded and link copied.
- [ ] Devpost form submitted before deadline.

---

## Notes

- **Track:** New Slack Agent — no Marketplace submission or App ID proof required.
- **No credit card services used:** Azure OpenAI runs on subscription credits; Render runs on the free tier.
- **Keep the service warm:** Render free tier sleeps after inactivity. Before recording or judging, wake it with `curl https://asked-and-answered-app.onrender.com/health` or open the URL in a browser.
