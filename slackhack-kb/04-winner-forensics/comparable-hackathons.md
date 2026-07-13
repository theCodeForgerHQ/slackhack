# Winner Forensics — 5 Comparable Sponsor Hackathons (23 winning projects analyzed, 2026-07-11)

Events: Google Chrome Built-in AI 2025 ($70k, 1,320 subs), Code with Kiro ($100k, 552), AWS AI Agent Global ($45k, 613), OpenAI Open Model ($30k+, 488), AI Partner Catalyst ($75k, ~600 — **identical equal-weight 4-criterion rubric to SlackHack**).

## Ranked winner factors (evidence-backed)
1. **Deployed, judge-testable product** — 22/23 winners had live URL/store listing/installable build. Explicit elimination filter, not bonus.
2. **Deep, on-label sponsor-tech use, narrated BY NAME** — winners chain multiple sponsor primitives and say so explicitly. (AWS weights Technical Execution 50%; OpenAI asks "can other models do the same thing?")
3. **One sharp use case with a nameable user — 87% of winners (20/23)**. Platform-shaped entries never took a podium top spot (best: 3rd in track).
4. **Numbers judges can repeat** — AWS judges quoted team benchmarks verbatim in the official announcement ("100% accuracy on Form 1040"). Every podium finisher had ≥1 hard number; losers assert impact without measurement.
5. **Architecture legibility** — diagram + component-by-component build story; winner write-ups average ~7 embedded images; AWS 1st place shipped a versioned docs site.
6. **Scripted ≤3-min demo of real product** — n=22 measured: mean 2:50, median 2:53, 21/22 ≤3:34. Two 1st-places under 2:00 (tight beats padded). "Often the first (and sometimes only!) thing judges review."
7. **Reproducibility artifacts** — public repo, visible license, run instructions, inspectable evidence (live dashboard links, requirement→file-path tables, published datasets).
8. **Specific impact story anchored to a real person/place** (vet friend's nightly charting; Timor-Leste waste; own children) — specificity, not TAM slides.
9. **Visible engineering judgment incl. negative results** (AAC Board rejected the flashy API at 80% accuracy; cleanclik admitted model failure) — documented trade-offs read as "quality software development."
10. **Ruthless scoping, stated openly** — winners cut features, not completeness.
11. **Product polish beyond PoC** (Design criterion) — "a complete, coherent product experience."
12. **Write-ups mirroring the rubric** — headings that pre-answer criteria; one winner mapped every requirement to an exact file path.

## The systematic-not-innovative winner (case study)
**Upload Drive-In — 1st place, $30,000, Kiro** — a Laravel file-upload portal (15-year-old product category, ZERO AI in product) beat 551 submissions. Won on: ran publicly early and kept running; maxed the sponsor-tech criterion with a credible narrative; boring hard parts done right (OAuth, chunked uploads, queues, modular storage interface, deploy pipeline); **1:56 demo video**; did every optional deliverable.
Same profile: AegisAgent (stock insurance triage, 2nd AWS), Storytopia (executed sponsor prompt literally + public live dashboard, 2nd Datadog), Province ("TurboTax as chat," measured 40%→100% phased accuracy, 3rd AWS).
**Template: mundane workflow with obvious value → sponsor stack used deeply and nominally → deployed → measured → diagrammed → sub-3-min scripted demo → every checklist item incl. optional. Under equal-weight rubrics, 4/5 on all four beats a 5/5 idea with 2/5 implementation.**

## Common disqualifiers
1. Failing the completeness screen (Stage One) before humans judge creativity.
2. No judge-accessible working app / missing credentials / repos that don't build.
3. Video failures: over cap, slideware instead of on-device footage, no end-to-end workflow.
4. Missing/undetectable OSS license where required; private repo.
5. Sponsor tech used superficially (wrapper-detection questions kill these).
6. Platform pitches with no single demonstrable user journey.
7. Reusing prior work.
8. Unquantified claims ("revolutionizes X").
9. Last-minute uploads (video processing takes hours).
10. Missing meta-deliverables (architecture diagram, track-specific requirements).

## Calibration stats
- Demo videos: mean 2:50; 95% ≤3:34; two 1st-places <2:00.
- ~87% of winners = single sharp use case.
- **Solo developers won top prizes in all five events** — team size is not a factor; completeness is.
- Serial winner (Anh Lam, 2 wins same season) proves the playbook is repeatable: deployed product + phased-metrics write-up + ~3:00 scripted demo + hybrid architecture story.
