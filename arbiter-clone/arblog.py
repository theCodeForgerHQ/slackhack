"""Shared logging for Arbiter — console + rotating file (arbiter.log).

Usage:  from arblog import get_logger
        log = get_logger(__name__)

Design intent: the bot's failure mode stays silence in Slack, but never
silence in the logs — swallowed exceptions get log.warning so judging-week
issues are diagnosable after the fact.
"""
import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_FILE = os.path.join(os.path.dirname(__file__), "arbiter.log")
_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    _configured = True
    root = logging.getLogger("arbiter")
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                            datefmt="%m-%d %H:%M:%S")
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
    try:
        fileh = RotatingFileHandler(_LOG_FILE, maxBytes=1_000_000, backupCount=3,
                                    encoding="utf-8")
        fileh.setFormatter(fmt)
        root.addHandler(fileh)
    except Exception:
        pass  # read-only fs (some hosts): console-only is fine
    # quiet the noisy Neo4j property-key notices
    logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(f"arbiter.{name.split('.')[-1]}")
