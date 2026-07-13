"""Live boxing-data.com (RapidAPI) client: the second, corroborating data source.

stdlib-only and fail-quiet by design: ANY failure (no key, timeout, non-200, bad JSON,
quota 429) returns None and the caller degrades to an UNAVAILABLE corroboration, which
never blocks and never loosens a verdict. Successful responses are cached in Postgres
(the free tier is 100 requests/month); when CORNERCHECK_DEMO_FALLBACK is on, recorded
real responses bundled with the package serve as a last resort, labeled as cached data.
"""

import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from cornercheck.config import get_settings
from cornercheck.db.pool import get_pool

log = logging.getLogger("cornercheck.boxing_data")

_BASE = "https://boxing-data-api.p.rapidapi.com"
_HOST = "boxing-data-api.p.rapidapi.com"
# The origin's Cloudflare bans default Python user agents (error 1010); a product UA passes.
_UA = "cornercheck/1.0 (+https://cornercheck.onrender.com)"
_TIMEOUT_S = 6.0
# Career records change only when a fighter actually fights; 21 days keeps the demo
# period warm on one live call per boxer while staying honest for record data.
_CACHE_TTL_DAYS = 21
_FIXTURES = Path(__file__).parent / "fixtures" / "boxing_data"


def search_fighters(name: str) -> list[dict[str, Any]] | None:
    """GET /v2/fighters/?name=<name>. Returns the data list, or None on ANY failure."""
    key = get_settings().boxing_data_api_key
    if not key:
        return None
    url = f"{_BASE}/v2/fighters/?" + urllib.parse.urlencode({"name": name})
    req = urllib.request.Request(
        url,
        headers={
            "X-RapidAPI-Key": key,
            "X-RapidAPI-Host": _HOST,
            "User-Agent": _UA,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as r:
            body = json.loads(r.read())
    except Exception as e:
        # The failure class matters on a 100-requests/month budget: a 429 (quota gone)
        # reads very differently from a timeout or a Cloudflare block.
        log.warning(
            "boxing-data search failed for %r: %s: %s (degrading to UNAVAILABLE)",
            name,
            type(e).__name__,
            e,
        )
        return None
    data = body.get("data") if isinstance(body, dict) else None
    return data if isinstance(data, list) else None


def cached_search(name: str) -> tuple[list[dict[str, Any]] | None, str, str | None]:
    """Search with the Postgres cache in front and the recorded-real demo fixtures behind
    (fixtures only when CORNERCHECK_DEMO_FALLBACK is on AND the live call failed).

    Returns (hits, origin, fetched_at_iso); origin is live | cache | demo-fixture | none.
    """
    norm = name.strip().casefold()
    hit = _cache_get(norm)
    if hit is not None:
        return hit[0], "cache", hit[1]
    live = search_fighters(name)
    if live is not None:
        _cache_put(norm, live)
        return live, "live", datetime.now(UTC).isoformat()
    if get_settings().cornercheck_demo_fallback:
        fx = _fixture_get(norm)
        if fx is not None:
            return fx[0], "demo-fixture", fx[1]
    return None, "none", None


def _cache_get(norm: str) -> tuple[list[dict[str, Any]], str] | None:
    """A cache failure must never break corroboration: fall through to the live call."""
    try:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT payload, fetched_at FROM boxing_search_cache"
                " WHERE query_name = %s AND fetched_at > now() - make_interval(days => %s)",
                (norm, _CACHE_TTL_DAYS),
            ).fetchone()
    except Exception as e:
        log.warning(
            "boxing cache read failed (%s: %s); falling through to the live call",
            type(e).__name__,
            e,
        )
        return None
    if row is None or not isinstance(row[0], list):
        return None
    return row[0], row[1].isoformat()


def _cache_put(norm: str, payload: list[dict[str, Any]]) -> None:
    try:
        with get_pool().connection() as conn:
            conn.execute(
                "INSERT INTO boxing_search_cache (query_name, payload, fetched_at)"
                " VALUES (%s, %s, now())"
                " ON CONFLICT (query_name) DO UPDATE"
                " SET payload = EXCLUDED.payload, fetched_at = now()",
                (norm, Jsonb(payload)),
            )
    except Exception as e:
        log.warning("boxing cache write failed (%s: %s); result not cached", type(e).__name__, e)


def _slug(norm: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", norm).strip("_")


def _fixture_get(norm: str) -> tuple[list[dict[str, Any]], str] | None:
    path = _FIXTURES / f"{_slug(norm)}.json"
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text())
        return doc["data"], doc["fetched_at"]
    except Exception as e:
        log.warning("boxing fixture unreadable: %s (%s: %s)", path, type(e).__name__, e)
        return None
