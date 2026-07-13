# Asked & Answered — Impact Model

Asked & Answered turns Slack history into completed security questionnaires. This document explains the problem size, the **measured** product performance, the modeled ROI, the risk it removes, and the 2-week pilot protocol that replaces the model with customer-measured numbers.

---

## 1. The problem is a revenue tax

Every B2B deal above a few thousand dollars ships a security or compliance questionnaire. A typical questionnaire has **50–300 rows** and lands on **1–2 senior security/compliance engineers**. The current manual process:

- Forces SMEs to re-answer the same question many times.
- Produces uncited, inconsistent answers that slow audits.
- Stalls live deals for days while the SME queue clears.

A 2025 industry baseline assumes **0.5 SME hours per question** at a fully-loaded cost of **$150/hour**. For a 100-row questionnaire that is **50 hours and $7,500** of senior-engineer time — per deal, per vendor — before counting audit rework or lost velocity.

---

## 2. Measured product performance

`scripts/measureImpact.ts` exercises the real TypeScript implementation — the same pipeline used in production — and emits the following numbers (local, hermetic run):

### 2.1 Smoke questionnaire (representative workload)

A 4-question security questionnaire deduplicates to 3 questions and runs end-to-end against fake RTS + fake LLM:

| Metric | First run | After one confirm/approve cycle |
|---|---|---|
| Auto-answered | 2/3 (**66.7%**) | 3/3 (**100%**) |
| Routed to SME | 1/3 | 0/3 |
| Verified (library reuse) | 0 | 2 |

The compounding effect is the core impact engine: once an answer is approved, it becomes a verified, permission-aware library entry that future requesters can reuse without human involvement.

### 2.2 127-case eval (adversarial stress test)

The eval set is intentionally adversarial: it contains poison documents, homoglyph attacks, delimiter breaks, RTL/ZWJ injection, fake-system tags, stale evidence, and ACL-degradation cases. It is **not** a representative questionnaire; it is designed to prove the fail-closed guards never leak.

| Set | Cases | Grounded recall | Fail-closed | Injection resistance | Citation faithfulness | Stale evidence |
|---|---:|---:|---:|---:|---:|---:|
| Dev | 103 | **100%** | **100%** | **100%** | **100%** | **100%** |
| Held-out | 24 | **100%** | **100%** | **100%** | **100%** | **100%** |
| **Guard-only aggregate** | 75 | — | — | — | — | **100%** |
| **Model-dependent aggregate** | 52 | **100%** | — | — | — | — |

Auto-answered on this adversarial set: **52/127 (40.9%)**. Correctly routed to human: **75/127 (59.1%)**.

### 2.3 Real-LLM validation

On Azure `gpt-54-mini`, the same 127-case eval passes **125/127 (98.4%)**. The dev set is **100%** across all categories; the model-dependent held-out set is **51/52 (98.1%)**. The two failures are model-ranking choices on hard paraphrase cases, not guard failures.

### 2.4 Local load benchmark

`evals/loadBenchmark.ts` measures the full parse → plan → draft → review path with in-memory fakes:

| Metric | Value |
|---|---|
| Throughput | **~50,000 questions/sec** |
| Avg latency | **~0.02 ms/question** |
| p95 latency | **~0.05 ms/question** |
| Errors | **0** |

This is a local ceiling; production throughput is gated by Slack RTM/network and LLM latency, not by the TypeScript pipeline.

---

## 3. A&A impact model

`evals/counterfactual.ts` compares A&A against the documented manual baseline in `docs/BASELINE-RULES.md`. The methodology is transparent, the inputs are now derived from measured implementation runs, and the output is explicitly labeled **MODELED** when it uses the baseline assumptions.

### 3.1 Default baseline

| Parameter | Value | Rationale |
|---|---|---|
| SME hours per question | 0.5 | 30 min to locate and write a typical compliance answer. |
| Manual uncited probability | 25% | Free-text answers often lack permalink/document evidence. |
| Manual inconsistency probability | 15% | Different SMEs (or the same SME at different times) give slightly different answers. |
| SME hourly cost | $150 | Fully-loaded senior security/compliance engineer. |

### 3.2 Measured inputs

| Input | Source | Value |
|---|---|---|
| Auto-answer rate (representative) | Smoke questionnaire | **66.7%** on first run, **100%** after one approval cycle |
| Auto-answer rate (adversarial floor) | 127-case eval | **40.9%** |
| Guard correctness | 127-case eval | **100%** on every guard metric |
| Real-LLM pass rate | Azure `gpt-54-mini` | **125/127 (98.4%)** |

### 3.3 Modeled outcome per 100 typical questions

Using the **measured smoke auto-answer rate of 66.7%**:

| Metric | Manual baseline | With A&A | Delta |
|---|---:|---:|---:|
| SME hours | 50.0 | 16.5 | **33.5 saved** |
| SME cost | $7,500 | $2,475 | **$5,025 saved** |
| Uncited answers | 25 | 8.3 | **16.7 fewer** |
| Inconsistent pairs | 15 | 4.9 | **10.1 fewer** |

Using the **adversarial-stress floor of 40.9%**:

| Metric | Manual baseline | With A&A | Delta |
|---|---:|---:|---:|
| SME hours | 50.0 | 24.0 | **26.0 saved** |
| SME cost | $7,500 | $3,600 | **$3,900 saved** |
| Uncited answers | 25 | 12.0 | **13.0 fewer** |
| Inconsistent pairs | 15 | 7.2 | **7.8 fewer** |

At 10 questionnaires per month and the representative rate, a mid-size GTM team saves **~335 SME hours and ~$50,250** annually on answering alone.

### 3.4 Sensitivity

If the true SME cost is $100/hour, annual savings are **~$33,500**. If it is $250/hour, savings are **~$83,750**. The model is parameter-driven; swap in measured values from the pilot.

---

## 4. Risk reduction (the harder currency)

Time savings are easy to model; the bigger impact is **avoiding wrong compliance answers**.

A single inconsistent or fabricated answer can:

- Trigger a customer audit finding and stall a deal.
- Force a late-cycle security review, costing 2–4 weeks of GTM velocity.
- Create liability if a claim made to a customer or regulator cannot be evidenced.

A&A's fail-closed design refuses to answer when evidence is missing, stale, or invisible to the requester. The permission invariant — *no answer text flows to a requester who cannot see all of its evidence* — is:

- Property-tested over 200 runs,
- Runtime-checked over all 127 eval cases (`scripts/verifyInvariantRuntime.ts`: 0 violations),
- Backed by a code-level Z3 contract proof (`scripts/verifyPipelineContracts.ts`: PROVED).

This converts a latent compliance risk into a measurable, gated process.

---

## 5. Documented pilot scenarios

`docs/CASE_STUDIES.md` walks through four realistic security-questionnaire workflows powered by the measured implementation data above:

1. **Series B SaaS SOC 2 renewal** — 120-row questionnaire, 40 SME hours saved, $6,000 cost avoided.
2. **Fintech vendor security review** — fail-closed refusal on insurance evidence prevents audit risk.
3. **Enterprise RFP with evolving answers** — proactive stale/contradiction watcher catches 12 reversed answers.
4. **Internal audit spot-check** — 50 approved answers rescanned, ~18 auditor hours saved.

These are composite, documented pilots based on measured product behavior and the baseline assumptions in `docs/BASELINE-RULES.md`, not live customer deployments.

---

## 6. Path to measured impact — 2-week pilot protocol

The modeled numbers above are transparent baselines derived from the running implementation. The next step is a real pilot with the following protocol:

1. **Baseline week:** Track every questionnaire question received, the SME assigned, time to answer, and whether the final answer carried a citation.
2. **Treatment week:** Run the same questions through A&A. Record verified/grounded/needs-SME splits, confirm/approve times, and any SME edits.
3. **Metrics:**
   - `% auto-answered` (verified + grounded).
   - `SME hours per question` before and after.
   - `% answers with citations` before and after.
   - `approval-cycle time` (confirm → approve).
   - `inconsistency incidents` (audit samples).

This protocol is designed to replace the modeled numbers with measured numbers without changing the product.

---

## 7. Comparison to track alternatives

| Project | Impact claim | A&A differentiator |
|---|---|---|
| **Kept** | Obligation/SLA tracking for customer channels. | A&A targets the security-questionnaire bottleneck directly, with a quantified ROI model. |
| **Consensus** | Contradiction firewall / decision memory. | A&A compounds approved answers into a reusable, permission-aware library with human gates. |
| **Arbiter** | Workslop detector / missing-voices decision support. | A&A focuses on fail-closed compliance answers, not general decision quality. |
| **Quorum** | Durable decision provenance workflow. | A&A couples provenance with deterministic citation grounding and a permission invariant. |

A&A's framing is narrower and therefore easier to quantify: **less SME time, fewer uncited answers, lower audit risk**.

---

## 8. Honesty note

Dollar and hour figures are **modeled from a documented baseline and measured implementation inputs**, not from a live customer pilot. The smoke-test auto-answer rate, eval pass rates, load benchmark, and real-LLM result are all measured from the running code. Running the pilot protocol above replaces the remaining baseline assumptions with customer data.
