"""Spike D: the Data Table block ("table") renders in a normal message.

Schema (docs.slack.dev table-block, fetched live 2026-06-07): type "table",
rows max 100 x 20 cells, cell types raw_text/raw_number/rich_text,
column_settings align/is_wrapped. Renders via chat.postMessage blocks.

Run: uv run python scripts/spikes/spike_d_table.py
Then: eyeball #general on desktop (and phone if handy). Fallback if broken:
section-fields/markdown table (cosmetic only).
"""

from slack_sdk import WebClient

from cornercheck.config import get_settings

settings = get_settings()
client = WebClient(token=settings.slack_bot_token)

table = {
    "type": "table",
    "rows": [
        [
            {"type": "raw_text", "text": "Fighter"},
            {"type": "raw_text", "text": "Decision"},
            {"type": "raw_text", "text": "Rule applied"},
            {"type": "raw_text", "text": "When"},
        ],
        [
            {"type": "raw_text", "text": "Dragan Petrovic"},
            {"type": "raw_text", "text": "DO NOT CLEAR"},
            {"type": "raw_text", "text": "KO 60-day window (NV), expires 2026-06-25"},
            {"type": "raw_text", "text": "2026-06-07"},
        ],
        [
            {"type": "raw_text", "text": "Marco Silva"},
            {"type": "raw_text", "text": "CLEAR"},
            {"type": "raw_text", "text": "No active suspension on record"},
            {"type": "raw_text", "text": "2026-06-07"},
        ],
    ],
    "column_settings": [
        {"align": "left"},
        {"align": "center"},
        {"align": "left", "is_wrapped": True},
        {"align": "left"},
    ],
}

resp = client.chat_postMessage(
    channel="#general",
    text="Spike D: audit-ledger data table (fallback text for notifications)",
    blocks=[
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Spike D: audit ledger table"},
        },
        table,
    ],
)
print("posted ok:", resp["ok"], "ts:", resp["ts"])
