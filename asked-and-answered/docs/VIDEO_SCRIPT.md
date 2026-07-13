# Demo video script — Asked & Answered (~3 minutes)

> Record at 1920×1080, clear voice, no music under narration. Show the Slack
> workspace and the bot responses in real time.

---

## Scene 1 — The problem (0:00–0:25)

**Visual:** Screen shows a security questionnaire spreadsheet open next to Slack.

**Narration:**
"Every B2B deal ships a security questionnaire — fifty to three hundred rows — and most of it asks what the team already answered somewhere in Slack. It lands on the same one or two experts and stalls deals for days. Asked & Answered is a Slack agent that turns that history into completed questionnaires — cited, approved, and fail-closed."

---

## Scene 2 — Submit a questionnaire (0:25–0:55)

**Visual:** Open the Slack DM with AskedAnswered. Drag an `.xlsx` questionnaire into the message field and send it.

**Narration:**
"You upload a questionnaire directly in the bot's Messages tab. The agent parses it, removes duplicates, and immediately starts searching the workspace with Slack's Real-Time Search API. Results are scoped to what the requester can actually see — so we never surface evidence from a private channel the requester isn't in."

**Visual:** Bot replies with a streamed plan: "Parsed 12 questions → searching workspace evidence…"

---

## Scene 3 — Three-state results (0:55–1:40)

**Visual:** Bot posts the Block Kit review table.

**Narration:**
"Every question lands in one of three states. Verified — a matching answer the team already approved, and the requester can still see every citation. Grounded — a fresh draft cited to the actual Slack messages behind it. And Needs SME — not enough evidence, or an ACL block, or an ungrounded citation. In that case the agent refuses to draft and routes it to a human."

**Visual:** Click the Review button on a Grounded row. The answer card pops up showing the answer text and the Slack permalink citation.

---

## Scene 4 — Deterministic grounding (1:40–2:05)

**Visual:** Switch to a test channel where a planted poison document says something like 'We do NOT encrypt data at rest.' Then run a question that should only answer from the real evidence.

**Narration:**
"We don't trust the model to cite honestly. GroundingGate verifies every cited snippet against the retrieved evidence. A fabricated or out-of-context citation is automatically downgraded to Needs-SME. That is deterministic — not prompt-engineered."

**Visual:** Bot returns the grounded answer from the real evidence; the poison doc is ignored.

---

## Scene 5 — Human review and export (2:05–2:35)

**Visual:** Approve one grounded answer, edit another, reject a third. Then type `export` in the DM.

**Narration:**
"Experts approve, edit, or reject each answer inside Slack. Every approval is appended to a tamper-evident, event-sourced ledger. Type 'export' and the agent returns a finished xlsx with every answer, its citations, and the approval trail."

**Visual:** Download and open the exported xlsx. Show columns: question, answer, citations, status, approved by.

---

## Scene 6 — The invariant and closing (2:35–3:00)

**Visual:** Type `verify ledger` in the DM. Bot replies that the ledger chain verifies.

**Narration:**
"The core invariant is simple: no answer text ever flows to a requester who cannot see all of its evidence. We enforce it in library reuse, fresh drafts, and the MCP server — and we prove it with property tests. Asked & Answered: your Slack history, turned into completed questionnaires, without inventing a single compliance answer."

**Visual:** End card with app name, GitHub repo URL, and Render URL.

---

## Suggested recording flow

1. Pre-seed the sandbox:
   - `#security` with a message like "We use AES-256 KMS encryption at rest."
   - `#compliance-private` with a message like "SOC 2 Type II completed 2025-06."
   - A planted poison doc in a public channel with contradictory text.
2. Create a small xlsx with 4–6 questions covering:
   - encrypt data at rest → should be Grounded
   - SOC 2 status → should be Grounded for members of private channel, Needs SME for others
   - a nonsense question → Needs SME
   - a question matching an already-approved answer → Verified on second run
3. Record in one take; pause between scenes if needed.
