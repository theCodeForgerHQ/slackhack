"""Create (and pin) the judge guide Canvas in a channel: the five-minute tour.

Run once after creating a #start-here channel and inviting the CornerCheck bot:

    uv run python scripts/judge_canvas.py C0XXXXXXX

Creates a standalone Canvas with the demo beats, grants the channel read access, posts the
permalink into the channel, and pins it. Idempotent enough: re-running creates a fresh
canvas and re-pins the new link (delete the old pin by hand if you re-run)."""

import sys

from slack_sdk import WebClient

from cornercheck.config import get_settings

GUIDE = """# CornerCheck: the five-minute tour

The agent that refuses to guess. Everything below is live; nothing is mocked.

## 1. Check a whole fight card
Open the **CornerCheck** app and paste:
`Check this card in Texas: Junior dos Santos vs Curtis Blaydes, Bruno Silva vs Brad Tavares`
Every bout lands on one board: CLEAR, DO NOT CLEAR, or NEEDS PICK, blockers cited below.

## 2. The cross-jurisdiction catch
`Is Junior dos Santos cleared in Texas?`
Blocked: an active California suspension, the source cited, the consult-first note, and an
injury warning surfaced from this workspace's own messages.

## 3. Watch it refuse to guess
`Is Bruno Silva cleared to fight?`
Two real professional fighters share that name. The identity threshold is conformally
calibrated (95% coverage over 4,203 query variants from the real roster); when two are plausible,
the math forces a human pick.

## 4. Click the proof
On any verdict card, press **See the safety proof**. The Z3 theorem prover re-proves the
fail-closed invariant right then (about 4 milliseconds), plus a deliberately broken control
that must fail, proving the prover is no rubber stamp.

## 5. The audit trail
Press **View audit trail**: every decision in a tamper-evident, HMAC-chained ledger. Press
**Export to Canvas** for a chain-verified document you could hand to a commission.

## Bonus
- A famous case: `Is Jon Jones cleared to fight in California?`
- A live second source: `Is Ryan Garcia cleared to fight?` (pick the boxer; his live
  professional record is fetched and shown; live data can tighten a verdict, never loosen it)
- #cornercheck-ops carries the daily roster-monitor digest: deterministic triggers, quiet
  days send nothing.
- The public dashboard runs the same proof for anyone: https://cornercheck.onrender.com

Decision support; a human always makes the final call.
"""


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].startswith("C"):
        sys.exit("usage: uv run python scripts/judge_canvas.py <channel_id like C0XXXXXXX>")
    channel = sys.argv[1]
    client = WebClient(token=get_settings().slack_bot_token)
    created = client.canvases_create(
        title="CornerCheck: the five-minute tour",
        document_content={"type": "markdown", "markdown": GUIDE},
    )
    canvas_id = str(created["canvas_id"])
    client.canvases_access_set(canvas_id=canvas_id, access_level="read", channel_ids=[channel])
    info = client.files_info(file=canvas_id)
    permalink = str(info["file"].get("permalink") or "")
    msg = client.chat_postMessage(
        channel=channel,
        text=f":compass: Judge guide: <{permalink}|CornerCheck, the five-minute tour>",
    )
    try:
        client.pins_add(channel=channel, timestamp=msg["ts"])
        pinned = "and pinned"
    except Exception:
        pinned = "(pin it by hand: the bot lacks pins:write until the next manifest reinstall)"
    print(f"canvas {canvas_id} created, shared, posted {pinned} in {channel}")
    print(permalink)


if __name__ == "__main__":
    main()
