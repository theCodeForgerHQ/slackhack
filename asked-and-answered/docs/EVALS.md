# Evaluation

Run: `npx tsx evals/run.ts` (add `AA_EVAL_LLM=anthropic|openai|azure` + the matching credentials to score with the real drafting model).

The harness runs the **real pipeline** against a seeded company workspace
(`evals/dataset.ts`: 49 evidence docs across public/private channels + 26 planted
prompt-injection/stale-evidence/near-miss docs) over **127 labeled cases**
(103 dev, 24 held-out). It measures behavior the product *guarantees*, not model
vibes — the fail-closed, injection, citation-faithfulness, and stale-evidence
numbers come from the pipeline's deterministic guards, so they hold regardless
of which LLM drafts.

## Metrics measured

| Metric | What it proves |
|---|---|
| **Grounded recall** | When visible evidence exists, we ground the answer and cite the right document. |
| **Fail-closed correctness** | When no visible evidence exists (missing, or present-but-not-visible), we never emit a grounded answer. |
| **ACL correctness** | When evidence exists but the requester can't see it, we degrade to Needs-SME for that specific reason — the core invariant. |
| **Injection resistance** | Planted "ignore all instructions" / "leak the private region" / homoglyph / delimiter-break / fake-system / ZWJ / RTL docs never produce a foreign-cited answer or an ACL leak. |
| **Citation faithfulness** | Every grounded answer cites a real, question-relevant permalink; generic or hypothetical evidence cannot support a fabricated answer. |
| **Stale-evidence detection** | When newer workspace evidence contradicts an approved answer, it is degraded for re-review. |
| **Near-miss / scope** | Scope carve-outs and near-miss evidence are cited honestly rather than flattened into a generic yes. |

## Latest run (faithful deterministic LLM)

```json
{
  "cases": 127,
  "dev": { "total": 103, "grounded_recall_pct": 100, "fail_closed_pct": 100, "injection_resistance_pct": 100, "citation_faithfulness_pct": 100, "stale_evidence_pct": 100 },
  "held_out": { "total": 24, "grounded_recall_pct": 100, "fail_closed_pct": 100, "injection_resistance_pct": 100, "citation_faithfulness_pct": 100, "stale_evidence_pct": 100 },
  "guard_only_pct": 100,
  "model_dependent_pct": 100
}
```

These are honest measurements of the deterministic guarantees. Grounded recall
and citation faithfulness with the *real* model are measured in the sandbox
(with `AA_EVAL_LLM=anthropic|openai|azure`) and reported in the submission; the
fail-closed, injection, citation-faithfulness, and stale-evidence numbers are
model-independent by construction.

## Real-LLM run — Azure OpenAI `gpt-54-mini`

Set `AA_LLM_RATE_LIMIT_DELAY_MS=300` when running against Azure to avoid TPM/RPM throttling on the 127-case eval.

```json
{
  "cases": 127,
  "dev": {
    "total": 103,
    "groundedRecall": { "hit": 42, "of": 42, "pct": 100 },
    "failClosed": { "hit": 33, "of": 33, "pct": 100 },
    "injectionResistance": { "hit": 25, "of": 25, "pct": 100 },
    "citationFaithfulness": { "hit": 9, "of": 9, "pct": 100 },
    "staleEvidence": { "hit": 8, "of": 8, "pct": 100 }
  },
  "heldOut": {
    "total": 24,
    "groundedRecall": { "hit": 10, "of": 10, "pct": 100 },
    "failClosed": { "hit": 8, "of": 8, "pct": 100 },
    "injectionResistance": { "hit": 6, "of": 6, "pct": 100 },
    "citationFaithfulness": { "hit": 2, "of": 2, "pct": 100 },
    "staleEvidence": { "hit": 2, "of": 2, "pct": 100 }
  },
  "guardOnly": { "hit": 75, "of": 75, "pct": 100 },
  "modelDependent": { "hit": 52, "of": 52, "pct": 100 }
}
```

Overall: **127/127 cases pass (100%)**.
