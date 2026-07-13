# Demo video production (assembly layer)

The SCRIPT is the source of truth: `docs/demo-script.md` (v2.1, beats 0-10, strict 3:00
ceiling). This file covers only what the script does not: capture settings, file naming,
assembly, and the b-roll inventory.

## Folder layout

```
video/
  src/beats.ts          beat timeline (mirrors the script; flip `footage` as clips land)
  public/title.png      animated by Remotion (never AI-generated; text stays exact)
  public/end.png        same
  public/footage/       screen + camera clips land here (gitignored, *.mp4)
  public/vo/            voiceover takes land here (gitignored)
```

## File naming (drop-in, then set `footage:` in beats.ts)

| Beat | File |
|---|---|
| 0 | `camera-beat0.mp4` |
| 2-9 | `beat2.mp4` ... `beat9.mp4` |
| 10 | `camera-beat10.mp4` |
| VO | `vo/beat2.mp3` ... `vo/beat9.mp3` |

## Screen Studio export settings

- Capture the browser window only (Slack tab zoomed per the script), not the desktop.
- Export: 1920x1080 MP4, H.264, highest quality, 30 or 60 fps (Remotion timeline is 30).
- Cursor: smooth movement ON, click sound OFF, modest zoom-on-click only where the script
  says to focus (proof button, Select click). No zoom on typing.
- Trial watermark is fine for TEST passes; license before final takes (board item 4).

## B-roll inventory (Higgsfield, generated 2026-06-10)

Two 6s atmospheric clips, 1344x768 (Grok Imagine), no people, no text. Local at
`public/footage/broll-corner-v1.mp4` / `-v2.mp4` (gitignored; regenerable). Job ids
`30a80e64-...` / `fa0222f2-...` in the Higgsfield account if re-download is needed.

- v2 (wide, big negative space): cold-open underlay candidate behind beat 0 camera, or
  the first 2s before the talking head cuts in. Grade it darker; it must read as texture.
- v1 (tight corner, stool + towel): single transition insert if one beat needs air.

Rules: b-roll is garnish. Real screen captures remain the primary evidence. Never let
AI footage carry a factual claim. Title/end cards are Remotion-animated PNGs, never AI.
Credits: 18 spent, 132 remain (basic plan; preflight with get_cost before any batch).

## Working with the timeline

```bash
cd video
npm install            # once
npx remotion studio    # live preview while dropping clips
npx remotion still Demo --frame=690 --scale=0.25 check.png   # quick frame check
npx remotion render Demo out/demo.mp4                        # full render
```

`showGuide: true` overlays the script line per beat for assembly reference; set false
for the final render (final captions come from the VO transcription pass).

## Assembly checklist (after recording day)

1. Drop clips + VO, flip `footage:` fields, watch the full timeline in Studio.
2. Trim each clip so the on-screen action lands inside its beat window (the script's
   word budgets leave headroom; never speed up VO).
3. Captions from VO (transcribe, then burn as styled captions; AI-tone rules apply).
4. Music bed ducked under voice, loudness -16 LUFS, denoise camera audio.
5. Final length check: 2:50-2:55. The 3:00 ceiling is a disqualification line, not a goal.
6. Upload unlisted for review; flip PUBLIC before the Devpost video-link save (form
   requires it; judges must be able to view without auth).
