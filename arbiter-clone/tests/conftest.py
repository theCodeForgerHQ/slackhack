"""Test config: set placeholder env so modules that read keys at import time
load cleanly. These tests exercise PURE LOGIC — no network, no real API calls."""
import os

for k in ("TAVILY_API_KEY", "NVIDIA_API_KEY", "CEREBRAS_API_KEY", "GROQ_API_KEY",
          "OPENROUTER_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY",
          "ANTHROPIC_API_KEY", "SLACK_BOT_TOKEN", "SLACK_USER_TOKEN",
          "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET", "GOOGLE_FACTCHECK_API_KEY",
          "DEEPGRAM_API_KEY"):
    os.environ.setdefault(k, "test-placeholder")
