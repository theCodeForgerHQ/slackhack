# Real-LLM Evaluation Report

**Model:** Azure OpenAI deployment `gpt-54-mini`  
**Dataset:** 127 cases (103 dev, 24 held-out) from `evals/dataset.ts`  
**Date:** 2026-07-14

Run with:

```bash
AA_EVAL_LLM=azure \
  AA_LLM_RATE_LIMIT_DELAY_MS=300 \
  AZURE_OPENAI_ENDPOINT=https://asked-and-answered-openai-02202.openai.azure.com \
  AZURE_OPENAI_API_KEY=... \
  AZURE_OPENAI_DEPLOYMENT=gpt-54-mini \
  AZURE_OPENAI_API_VERSION=2024-08-01-preview \
  npx tsx evals/run.ts
```

The `AA_LLM_RATE_LIMIT_DELAY_MS=300` avoids Azure TPM/RPM throttling when running the full 127-case eval back-to-back.

## Results

| Metric | Dev | Held-out |
|---|---:|---:|
| Grounded recall | 42/42 (100%) | 10/10 (100%) |
| Fail-closed correctness | 33/33 (100%) | 8/8 (100%) |
| Injection resistance | 25/25 (100%) | 6/6 (100%) |
| Citation faithfulness | 9/9 (100%) | 2/2 (100%) |
| Stale-evidence detection | 8/8 (100%) | 2/2 (100%) |

- **Guard-only metrics:** 75/75 (100%)
- **Model-dependent metrics:** 52/52 (100%)
- **Overall:** 127/127 (100%)

## Failures

None.

## Interpretation

The deterministic guards (citation-subset, ACL, GroundingGate, stale-evidence detection) are model-independent and pass at 100%. The drafting model, prompted to ground answers in verbatim evidence clauses while refusing only when no relevant evidence exists or the question is vague/overbroad, correctly answers every grounded case and refuses every injection, ACL-degraded, no-evidence, stale, and ungrounded case. The system errs by routing to humans, never by fabricating or leaking.
