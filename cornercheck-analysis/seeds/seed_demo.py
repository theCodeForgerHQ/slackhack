"""Post realistic fight-ops conversations to the sandbox so RTS finds REAL fresh messages.

Per spike B: bot-authored messages ARE searchable, with 1-3 minute index lag. Run this
a few minutes before any demo or recording. Messages reference the locked demo fighters
and use injury-lexicon terms so the RTS injury scan surfaces them with permalinks.

Run: uv run python seeds/seed_demo.py [--channel general]
"""

import sys
import time

from slack_sdk import WebClient

from cornercheck.config import get_settings

# Real fighters present in the seeded DB; messages mirror how an ops team actually talks.
MESSAGES = [
    "Matchmaking sync: building Saturday's card. Need clearance on a few names before we book.",
    "Geoff Neal looked rocked in sparring Tuesday, we sat him down for the week. Hold off on him.",
    "Heads up on Junior dos Santos, he's still not cleared after that KO, pending neuro.",
    "Anyone have eyes on the Bruno Silva situation? There are two of them, don't mix them up.",
    "Reminder: confirm cross-state holds before offers. Last thing we need is a §6306 problem.",
    "Merab looked sharp in the gym, no issues, good to go once ops confirms.",
]


def seed_demo(channel: str) -> None:
    client = WebClient(token=get_settings().slack_bot_token)
    ch = channel if channel.startswith("#") else f"#{channel}"
    for text in MESSAGES:
        resp = client.chat_postMessage(channel=ch, text=text)
        print(f"posted ts={resp['ts']}: {text[:60]}...")
        time.sleep(1.1)  # chat.postMessage tier is ~1 msg/sec/channel; stay under it
    print("\nSeeded. RTS indexing lag is ~1-3 min; wait before running the injury-scan demo beat.")


if __name__ == "__main__":
    chan = "general"
    if "--channel" in sys.argv:
        chan = sys.argv[sys.argv.index("--channel") + 1]
    seed_demo(chan)
