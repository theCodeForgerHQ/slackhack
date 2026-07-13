# What Asked & Answered deliberately does NOT do

Honesty about scope is part of the design. These are conscious cuts, not oversights.

## Cut for scope (hackathon build window)
- **PDF/OCR intake.** Only xlsx, csv, and pasted text are parsed. PDF questionnaires must be converted first. (Parser is pluggable; PDF is a clean future addition.)
- **Per-sentence citations.** Answers are cited at the answer level (1-3 evidence permalinks), not per sentence. Answer-level binding is the higher-signal, lower-variance choice under time pressure.
- **Owner-suggestion heuristics.** SME routing uses an explicit human picker (`users_select`), not automatic expert inference. Explicit is safer and demonstrably correct.
- **Slack Connect / cross-workspace evidence.** Retrieval is scoped to the single workspace the agent is installed in.
- **Multi-language.** English questionnaires only.

## Cut on principle (would not add even with more time)
- **Auto-approval.** No answer is ever marked Verified without a human click. A compliance tool that self-approves is a liability, not a feature.
- **Answering without evidence.** The agent refuses rather than guesses. "Needs SME" is a correct outcome, not a failure.

## Platform constraints (not ours to fix)
- **Semantic RTS search is plan-gated** (Business+/Enterprise+). The agent is built for keyword mode as primary; semantic engages automatically where available. Do not judge it on semantic-only behavior.
- **Guests and free-plan workspaces** cannot use Slack AI apps at all. The agent degrades gracefully but cannot serve them.
- **`conversations.replies` is Tier-1 rate-limited** for new distributed apps, so context comes primarily from RTS `include_context_messages`, with replies as a cached last resort.

## Known sharp edges
- xlsx parsing assumes a question column detectable by header ("Question"/"Prompt"/...) or, failing that, the longest-text column. Merged cells across the question column may split oddly; paste-as-text is the reliable fallback.
- The answer library matches questions by token overlap, not semantics: heavily reworded duplicate questions may not be recognized as the same question and will re-draft.
