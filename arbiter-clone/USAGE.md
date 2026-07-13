# Using Arbiter — the workspace's judgment layer

Arbiter works two ways: **just talk to it** with `@Arbiter …`, or **let it watch a channel** and it judges on its own. Below is everything you can do.

> **Fastest way to see it work:** in any channel, send `@Arbiter watch` and wait for *"Now judging this channel."* Then paste a shaky claim, a padded update, or a decision — Arbiter reacts on its own.

---

## 1. Fact-check a claim  ⚖️
A multi-model **council** (3 models + a contrarian) debates the claim; when they split, they run another round with a fresh evidence search. Cited from web, Wikipedia, Google Fact Check, **and your own workspace messages**.

```
@Arbiter The refund window is 90 days, so we're covered on the Henderson complaint.
```
→ Returns **True / False / Misleading** with sources. (It will catch a message that contradicts your own posted policy.)

Also: `/arbiter <claim>` or `/verdict <claim>`.

## 2. Weigh substance (anti-"workslop")  📊
Scores how much is *actually in* a message — real facts, decisions, commitments — not how confident it sounds. Immune to length/verbosity bias. Delivered **privately** to the author.

```
@Arbiter substance <paste a long, polished-but-empty update>
```
→ Score /100 + a receipt of what real content it found (or didn't).
Aliases: "slop check", "workslop". Slash: `/arbiter substance <text>`.

## 3. Missing voices on a decision  🪑
When a decision is forming, Arbiter surfaces the people it affects who **aren't in the thread** — quoting their real words, even from other channels — plus the record and a counter-case.

```
@Arbiter voices Decision: we're pulling the MuleSoft advisory and moving the Edge go-live up two weeks.
```
→ "Before you lock this in…" card with the absent stakeholders.
Aliases: "who's missing", "missing voices". Slash: `/arbiter voices <decision>`.

## 4. Delegate — ask an absent teammate  🗣️
Answers a question **on behalf of** someone who's away (or has left), using **only their real Slack messages**, every line cited with a permalink. If their record can't answer, it refuses rather than guess — with an opt-in "best guess" button that's clearly labeled speculation. The person is DM'd that it spoke for them.

```
@Arbiter ask @Tim Smith what's the plan for the SAP integration?
```
→ A grounded, quoted answer — or a refusal + "Best guess" pill if there's nothing on record.

## 5. Catch-up — what did I miss?  📥
A welcome-back digest of what matters after time away: decisions made, open questions, things that mention you. Ask for it, or Arbiter can DM it when you return from being away.

```
@Arbiter catchup
```
Aliases: "what did I miss".

## 6. Roundtable — several teammates talk it through  🎭
Voices two or more teammates from **their own real messages** and has them debate a topic across a round, then a facilitator states where the group lands — with source links under each person's take.

```
@Arbiter act as @Tim Smith @Rosario Bennet should we accelerate the Edge go-live by two weeks?
```
→ A 🎭 Roundtable card: each person's grounded position, points of agreement, and the conclusion.
Aliases: "roundtable @A @B …", "debate as @A @B …".

---

## Proactive mode (in a watched channel — no command needed)
After `@Arbiter watch`, Arbiter acts on its own:
- **False claims** get a ⚠️ flag + a fact-check card.
- **Hollow long posts** get a private substance receipt to the author.
- **Forming decisions** get a missing-voices card.
- **@mentioning someone who's away** triggers their delegate automatically.

Turn it off with `@Arbiter unwatch`.

## Transparency & memory
- `@Arbiter audit` — a transparency report of every judgment it has made.
- `@Arbiter ledger` — predictions logged and who said it first (track record).
- `@Arbiter stats` — feedback stats. Every card has 👍/👎; a 👎 makes that kind of alert more careful next time (it learns, and the memory persists in a graph DB).

---

*One brain, six verdicts — claims, content, decisions, people, roundtable, catch-up — all grounded in your team's own record.*
