# Counterfactual Baseline Rules

This document defines the manual-process baseline used by `evals/counterfactual.ts`. The numbers are **rules for simulation**, not measured customer data. They are published so the methodology is transparent and auditable.

## Baseline manual process

When Asked & Answered is **not** available, we assume each security-questionnaire question follows this manual path:

1. A requester opens a ticket or DM to a subject-matter expert (SME).
2. The SME spends time locating the answer from memory, documents, or Slack history.
3. The SME replies with a free-text answer.

## Default parameter values

| Parameter | Value | Rationale |
|---|---|---|
| `smeHoursPerQuestion` | 0.5 | 30 minutes to find and type an answer for a typical compliance question. |
| `manualUncitedProbability` | 0.25 | Manual answers often lack a permalink or document reference. |
| `manualInconsistentProbability` | 0.15 | Different SMEs (or the same SME at different times) may give slightly different answers. |
| `smeHourlyCost` | $150 | Fully-loaded hourly cost for a senior security/compliance engineer. |

## What A&A changes

- Questions A&A answers automatically (`autoAnsweredCount`) consume **zero** SME time in the simulation.
- Questions A&A correctly routes to humans (`routedToHumanCount`) still consume SME time but are assumed to be cited and consistent once approved into the library.
- The simulation compares baseline waste against the A&A outcome.

## Honesty rule

Every report produced by this simulator carries:

```
NOTE: SIMULATED: based on the baseline rules above, not measured customer data.
```

Do not remove this label.
