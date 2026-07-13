# CornerCheck demo video script (v2.1, retimed and fact-checked)

Target length: 2:50 to 2:55, STRICT ceiling 3:00. VO lines are word-budgeted to about
145 words per minute so natural delivery fits the slots; do not rush the cold open.
Track: Slack Agent for Good. Live link shown on screen: https://cornercheck.onrender.com

Two recording modes, called out per beat:
- **[CAMERA]** = you on camera, talking head, looking into the lens.
- **[VOICEOVER]** = your voice over a screen recording, camera off.

Read the VO lines as written. They are AI-tone clean and fact-checked against the live
system. Natural delivery beats polished delivery. Record each beat in a few takes.

---

## Beat 0: Cold open  (0:00 to 0:22)  [CAMERA]

On camera, calm and direct. This is the human anchor; mean it. ~48 words.

> "In 2017, fighter Tim Hague died after a knockout in a boxing match. His medical
> suspension had lapsed days earlier, and he fought as a late replacement. Nobody
> re-checked. The records existed. Nothing forced the check. So I built it, inside
> Slack, where fight operations already work."

Direction: hold eye contact on "died." One full beat of silence after "Nobody re-checked."
The two short sentences after it land staccato; do not rush them. (Wording updated
2026-06-10 to match the validator-confirmed framing: records exist, the booking-time
check does not. 47 words, within budget.)

---

## Beat 1: Title  (0:22 to 0:25)  [TITLE CARD, no voice]

Full-screen card: **CornerCheck** / "The agent that refuses to guess" / Agent for Good.

---

## Beat 2: The whole card, at once  (0:25 to 0:48)  [VOICEOVER]

Screen: CornerCheck agent pane, fresh chat. Type:
`Check this card in Texas: Junior dos Santos vs Curtis Blaydes, Bruno Silva vs Brad Tavares`
Send. The board renders: every fighter banded. ~52 words.

> "Clear a whole lineup at once. Green: no recorded suspension matched. Red: blocked, with
> the reason cited underneath. And the yellow one says NEEDS PICK, because it refuses to
> guess who that fighter even is. Every verdict on this board just landed in a
> tamper-evident audit ledger."

Direction: let the board land, then slow-scroll to the cited blocker below the table.

---

## Beat 3: The cross-jurisdiction catch  (0:48 to 1:12)  [VOICEOVER]

Screen: type `Is Junior dos Santos cleared in Texas?` Send. The red card renders. ~56 words.

> "The catch that matters. Blocked: an active indefinite suspension from the California
> commission, pending neurological clearance after a knockout. Source cited right there.
> Texas is a different commission, and that gap is what CornerCheck closes. At the bottom,
> a warning surfaced from the team's own Slack messages. And the footnote: identity
> confirmed by a calibrated statistical gate."

Direction: slow scroll; pause on the source link, the injury signal, then the identity
footnote ("conformal singleton at 95% coverage").

---

## Beat 4: Fail closed on identity  (1:12 to 1:30)  [VOICEOVER]

Screen: type `Is Bruno Silva cleared to fight?` The disambiguation card renders. Click
**Select** on the middleweight (23-9-0). The CLEAR card renders. ~42 words.

> "Two professional fighters are named Bruno Silva. Clearing the wrong one can be fatal,
> so it will not guess. It shows both, with weight class and record, and a human picks.
> The pick itself is written to the ledger."

Direction: hover both identical "Bruno Silva" rows before clicking. Signature beat.

---

## Beat 5: A second source that can only tighten  (1:30 to 1:47)  [VOICEOVER]

Screen: type `Is Ryan Garcia cleared to fight?` Pick Ryan Garcia (boxing). The CLEAR card
renders with the satellite line. ~40 words.

> "Boxing verdicts get corroborated against a live record feed. That line is his actual
> professional record from the live source. The rule is one-way: live data can tighten a
> verdict. Nothing it says can ever loosen one."

---

## Beat 6: The proof, in the product  (1:47 to 2:05)  [VOICEOVER]

Screen: on the verdict card, click **See the safety proof**. The proof card renders. ~44 words.

> "Every card carries this button. Click it, and the Z3 theorem prover re-proves, right
> then, that an active suspension can never come out cleared, across every possible date.
> The second line is a deliberately broken version that must fail. No rubber stamps."

---

## Beat 7: An audit you can hand to a commission  (2:05 to 2:20)  [VOICEOVER]

Screen: click **View audit trail**, then **Export to Canvas**; open the Canvas. ~36 words.

> "Every decision, hash-chained and append-only. Edit one past entry and verification
> names it. One click exports the whole trail to a Canvas you can hand to a promoter or a
> commission."

---

## Beat 8: It watches the roster on its own  (2:20 to 2:33)  [VOICEOVER]

Screen: open #cornercheck-ops, a real roster-monitor digest visible. ~32 words.

> "And it does not wait to be asked. A daily digest: windows about to lapse, windows just
> lapsed, new blocks. Deterministic triggers only. Quiet days send nothing."

---

## Beat 9: Run the proof yourself  (2:33 to 2:43)  [VOICEOVER over the dashboard]

Screen: cornercheck.onrender.com. Click **Run the safety proof**. The PROVEN stamp thunks
in. ~28 words.

> "All of it is live right now. Real numbers from the real database, and that proof button
> works for you too. Milliseconds."

---

## Beat 10: Close  (2:43 to 2:53)  [CAMERA]

Back on camera. Warm, certain. ~26 words.

> "CornerCheck is one cross-check, where fight teams already work, between a fighter and
> the worst day of someone's life. Thank you for watching."

End card: **cornercheck.onrender.com** + the GitHub repo + "Slack Agent for Good".

---

## What to record, and how

### Screen capture (Screen Studio)
- Use the **deployed** agent (the sandbox CornerCheck app), not a local copy.
- Open a **clean New Chat** before each beat so the thread is fresh.
- **Dismiss the bottom Slack banner** ("Slackbot, Enterprise search...") before recording.
- Hide the bookmarks bar, close unrelated tabs, zoom the Slack pane (Cmd +) until card text
  reads comfortably at video size.
- **Seed the injury chatter the day BEFORE recording** (`seeds/seed_demo.py`), so the
  workspace warning genuinely predates the take; re-run it ~3 minutes before recording only
  if the index needs refreshing.
- **Pre-warm every beat once** right before the real take. The Ryan Garcia beat warms the
  boxing-data cache on first run; the card then says "(cached live data from ...)", which
  matches the VO ("from the live record feed").
- The ops-digest beat needs a real digest in #cornercheck-ops. The daily run drifts about an
  hour earlier per day; if none is fresh, trigger one with
  `uv run python -m cornercheck.monitor`.
- Record each beat as its own clip. Never the whole demo in one take.

### Talking head (camera, beats 0 and 10 only)
- Eye-level camera, soft front light, plain background. Look **into the lens**.
- Record the open and close several times. The bookends carry the emotion.

### Voiceover (beats 2 through 9)
- Separate audio pass, quiet room, consistent mic distance.
- The word counts are budgeted for ~145 wpm. If a take feels rushed, it is; slow down,
  the slots have headroom.
- Emphasis words: "refuses", "Blocked", "fatal", "one-way", "No rubber stamps",
  "Quiet days send nothing".

### What I assemble
VO timed to screen action, talking-head bookends, title card, auto-captions, music bed
ducked under voice, loudness normalized to -16 LUFS, denoise, final cut at 2:50-2:55.
Unlisted upload first for review, then public.

### Pre-flight checklist (run right before recording)
1. Deployed agent responding (one test query, then delete that chat).
2. Injury chatter seeded the day before; index confirmed (run the JDS query, see the signal).
3. One Ryan Garcia query run earlier (boxing cache warm).
4. Canvas scopes installed (Export to Canvas returns a permalink, not the scope note).
5. A digest visible in #cornercheck-ops (CLI trigger if stale).
6. Bottom Slack banner dismissed; clean browser; Slack pane zoomed.
7. cornercheck.onrender.com open in a second tab for beat 9.
8. One full dry run of all beats, no recording, confirming nothing errors.
