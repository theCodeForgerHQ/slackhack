"""Run Arbiter against the judging sandbox (.env.sandbox) instead of .env.

Usage: python run_sandbox.py
Same app, different workspace — never run both against the same workspace.
"""
from dotenv import load_dotenv

load_dotenv(".env.sandbox", override=True)

import runpy

runpy.run_path("app.py", run_name="__main__")
