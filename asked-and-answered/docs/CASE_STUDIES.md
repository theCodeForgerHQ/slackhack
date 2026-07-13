# Asked & Answered — Documented Pilot Scenarios

These scenarios are composite, documented pilots based on the measured behavior of the running Asked & Answered implementation (`scripts/measureImpact.ts`) and the manual baseline documented in `docs/BASELINE-RULES.md`. They are designed to show how the product performs on realistic security-questionnaire workflows before a full customer deployment produces measured field data.

---

## 1. Series B SaaS — SOC 2 Type II renewal questionnaire

**Context:** A 250-person SaaS company receives a 120-row SOC 2 Type II questionnaire from a major enterprise prospect. The questionnaire is 80% identical to the one they answered six months ago.

**Manual baseline (documented in BASELINE-RULES.md)**

| Metric | Value |
|---|---|
| Rows | 120 |
| SME hours per question | 0.5 |
| Senior security engineer cost | $150/hr fully loaded |
| Likely uncited answers | 25% of rows |
| Likely inconsistent answers vs. prior response | 15% of rows |

**Baseline cost:** 60 SME hours × $150 = **$9,000** per questionnaire, plus audit-rework risk.

**With Asked & Answered (measured smoke-run basis: 66.7% auto-answer first run, 100% after one approval cycle)**

| Outcome | Value |
|---|---|
| Auto-answered on first run | 80 rows (66.7%) |
| Routed to SME | 40 rows |
| SME hours consumed | 20 hours |
| SME hours saved | **40 hours** |
| Cost saved | **$6,000** |
| Citations attached automatically | 80 rows |
| Inconsistency risk | reduced because approved answers are reused verbatim |

**What the product did:**
- 42 rows matched previously approved answers in the library and were returned as **Verified** after re-checking the requester could still see the evidence.
- 38 rows were drafted fresh from workspace evidence and passed `GroundingGate` as **Grounded**.
- 40 rows had no visible evidence, stale evidence, or ACL blocks and were routed to humans as **Needs SME**.
- Every approved answer was logged to the tamper-evident ledger.

**Stakeholder quote (illustrative):** *“The renewal questionnaire used to eat a full week of my senior engineer’s time. This time 80 rows were answered with citations before lunch, and we had an audit trail for every approval.”*

---

## 2. Fintech vendor security review

**Context:** A fintech startup is being onboarded as a vendor by a bank. The bank sends a 60-row security assessment with strict requirements: every answer must carry a permalink or document citation, and the bank may spot-check evidence visibility.

**Risk focus:** A wrong or uncited answer can trigger a 2–4 week security review delay or kill the deal.

**With Asked & Answered**

| Outcome | Value |
|---|---|
| Rows auto-answered with citations | 40 rows (66.7%) |
| Rows routed to SME | 20 rows |
| Potential wrong answers prevented | Any row without evidence was refused rather than fabricated |
| Permission invariant enforced | Every returned answer re-checked against the bank reviewer’s channel visibility |

**What the product did:**
- The bank reviewer’s user token limited RTS to channels they were a member of, so private engineering Slack evidence was never surfaced.
- A row about cyber-liability insurance had no matching workspace evidence; A&A returned **Needs SME** instead of inventing a policy number.
- The final export included the XLSX with citations and a Canvas audit artifact showing every approval.

**Stakeholder quote (illustrative):** *“The worst-case scenario is telling a bank something we can’t prove. A&A refused to answer where we had no evidence, which is exactly what I wanted it to do.”*

---

## 3. Enterprise RFP — repeat customer with evolving answers

**Context:** An enterprise software company answers the same 200-row procurement questionnaire every quarter from the same customer. The customer occasionally updates requirements, so some previous answers become stale.

**Baseline pattern:** SMEs copy the previous response, manually search Slack for updated evidence, and often miss contradictions.

**With Asked & Answered**

| Outcome | Value |
|---|---|
| Verified from library on first run | 140 rows (70%) |
| Flagged stale/contradicted by watcher | 12 rows |
| Grounded from fresh evidence | 36 rows |
| Routed to SME | 24 rows |
| Quarterly SME hours saved | ~80 hours vs. 100-hour baseline |

**What the product did:**
- Previously approved answers were returned as **Verified** when evidence was still visible and not contradicted.
- The proactive stale/contradiction watcher detected 12 approved answers where new Slack evidence reversed the claim (e.g., encryption-at-rest policy changed from AES-128 to AES-256). Those rows were downgraded for human review.
- The remaining rows were answered from current evidence or routed to SMEs.

**Stakeholder quote (illustrative):** *“We stopped shipping last quarter’s answer when this quarter’s Slack thread had already changed it. The watcher caught contradictions we would have missed.”*

---

## 4. Internal audit — compliance team spot-check

**Context:** A compliance team needs to verify that 50 previously approved questionnaire answers are still accurate after a security policy update.

**Manual baseline:** An auditor manually re-checks each answer against Confluence, Jira, and Slack. 0.5 hours per answer = 25 hours.

**With Asked & Answered**

| Outcome | Value |
|---|---|
| Answers still verified | 38 |
| Answers flagged stale/contradicted | 8 |
| Answers missing current evidence | 4 |
| Auditor hours saved | **~18 hours** |

**What the product did:**
- The watcher rescanned the approved library against current workspace evidence.
- Each answer’s citations were re-validated against the requester’s current permissions.
- A signed Agent Run Card was generated for every answer, showing the approval chain and a signature hash.

---

## Honesty note

These scenarios are composite pilots derived from the measured implementation performance and the documented manual baseline. They are not live customer deployments. The 2-week pilot protocol in `docs/IMPACT.md` is designed to replace these illustrative numbers with measured customer data.
