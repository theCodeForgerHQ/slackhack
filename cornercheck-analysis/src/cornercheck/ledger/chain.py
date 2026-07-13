"""Pure hash-chain logic (no database).

Payloads are floats-free JSON (str/int/bool/None/list/dict) so the canonical form
survives a Postgres jsonb round-trip byte-for-byte. Floats are rejected at append
time; verification recomputes the canonical form from what the database returns.
"""

import hashlib
import hmac
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

GENESIS = "0" * 64


class UnsafePayloadError(ValueError):
    """Payload contains a value that does not survive a jsonb round-trip (e.g. float)."""


def _check_json_safe(value: object, path: str = "payload") -> None:
    if isinstance(value, float):
        raise UnsafePayloadError(f"{path}: floats are not allowed in ledger payloads")
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise UnsafePayloadError(f"{path}: non-string key {k!r}")
            _check_json_safe(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _check_json_safe(v, f"{path}[{i}]")
    elif value is not None and not isinstance(value, str | int | bool):
        raise UnsafePayloadError(f"{path}: unsupported type {type(value).__name__}")


def canonical(payload: dict) -> bytes:
    """Deterministic byte form of a payload: sorted keys, tight separators, UTF-8."""
    _check_json_safe(payload)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def link_hash(key: bytes, prev_hash: str, payload: dict) -> str:
    """HMAC-SHA256 over prev_hash || canonical(payload)."""
    return hmac.new(key, prev_hash.encode("ascii") + canonical(payload), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checked: int
    first_bad_seq: int | None
    detail: str


# App clock vs DB clock skew allowance for the ts cross-check. Same-host they differ
# by milliseconds; a backdated/postdated column edit moves it by hours or days.
_TS_TOLERANCE_S = 120.0


def verify_rows(key: bytes, rows: Iterable[tuple]) -> VerifyResult:
    """Walk (seq, payload, prev_hash, hash[, actor, action[, ts]]) rows in seq order;
    report the FIRST break. When the extra columns are supplied AND the payload carries
    the hash-covered _meta stamp, a column edit that diverges from the stamp (actor,
    action, or a backdated/postdated ts) is itself a break. Rows older than the _meta
    scheme skip the cross-checks; the detail string reports how many were meta-checked
    so a caller passing too few columns cannot silently lose the coverage."""
    expected_prev = GENESIS
    checked = 0
    meta_checked = 0
    for row in rows:
        seq, payload, prev_hash, hash_ = row[0], row[1], row[2], row[3]
        if prev_hash != expected_prev:
            return VerifyResult(False, checked, seq, f"prev_hash mismatch at seq {seq}")
        try:
            recomputed = link_hash(key, prev_hash, payload)
        except UnsafePayloadError as exc:
            return VerifyResult(False, checked, seq, f"unverifiable payload at seq {seq}: {exc}")
        if recomputed != hash_:
            return VerifyResult(False, checked, seq, f"hash mismatch at seq {seq}")
        if len(row) >= 6 and isinstance(payload, dict) and "_meta" in payload:
            meta = payload["_meta"] if isinstance(payload["_meta"], dict) else {}
            if meta.get("actor") != row[4] or meta.get("action") != row[5]:
                return VerifyResult(
                    False, checked, seq, f"actor/action column mismatch at seq {seq}"
                )
            if len(row) >= 7 and meta.get("at"):
                try:
                    stamped_at = datetime.fromisoformat(str(meta["at"]))
                    drift = abs((row[6] - stamped_at).total_seconds())
                except Exception:
                    return VerifyResult(
                        False, checked, seq, f"unparseable _meta timestamp at seq {seq}"
                    )
                if drift > _TS_TOLERANCE_S:
                    return VerifyResult(
                        False, checked, seq, f"ts column drift ({drift:.0f}s) at seq {seq}"
                    )
            meta_checked += 1
        expected_prev = hash_
        checked += 1
    detail = f"chain intact ({checked} entries"
    detail += f", {meta_checked} meta-checked)" if meta_checked else ")"
    return VerifyResult(True, checked, None, detail)
