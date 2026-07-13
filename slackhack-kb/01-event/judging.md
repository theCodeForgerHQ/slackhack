# Judging — Structure & Criteria (verified from Official Rules, 2026-07-11)

Source: https://slackhack.devpost.com/rules §6

## Two-stage process
- **Stage 1 — Pass/Fail viability:** does the project reasonably fit Submission Requirements? (Working install, required tech, track fit, all submission artifacts present.) **Losing here is unforced error — the checklist must be perfect.**
- **Stage 2 — Scored.** Four **equally weighted (25% each)** criteria:

| # | Criterion | Exact rubric language | How to max it |
|---|---|---|---|
| 1 | **Technological Implementation** | "Quality software development? Leverages at least one of: Slack AI capabilities, MCP server integration, or real-time search API?" | Use ALL THREE technologies deeply, not one. Tests, CI, error handling, architecture doc, real deployment. |
| 2 | **Design** | "UX well thought out? Balanced blend of frontend and backend?" | Native Block Kit UI (sponsor said this explicitly), polished App Home, loading states, empty states. "Balanced blend" = don't be a headless backend. |
| 3 | **Potential Impact** | "Impact on the Slack community? Beyond the target community?" | Quantify: who, how many, time saved. Slack community first, world second. |
| 4 | **Quality of the Idea** | "Creative and unique? Does the concept exist already? If so, how much does the project IMPROVE on it?" | ← Note the escape hatch: a non-novel idea scores well if it demonstrably improves on existing versions. Systematic > novel is viable per the rubric's own text. |

## Tie-breaking order
Tech Implementation → Design → Impact → Idea. **Engineering depth wins ties.**

## Notes
- Judging "may utilize expert panels, peer review, automated AI-driven analysis, or any combination" — write the submission text so an LLM analyzer can also parse it (clear headings, explicit tech claims, keyword-complete: "MCP server integration", "Real-Time Search API", "Slack AI").
- Judges may not watch beyond 3:00 of the video.
- At least one judge is not a Sponsor employee.

## Sponsor's own winning guidance (Updates page, verbatim signal)
- "**Do one thing really well. The best Slack agents aren't Swiss Army knives.**"
- Use **Block Kit** for "structured, interactive UI inside Slack" — native feel, not raw text dumps.
- If short on time: **cut scope, don't ship broken breadth.**
- Dev Huddle Ep. 05 covers MCP + RTS API — the sponsor is actively teaching these two; entries using them well align with what judges were primed to look for.
