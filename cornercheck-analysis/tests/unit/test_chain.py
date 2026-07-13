"""Pure chain logic: canonicalization, hashing, verification, payload safety."""

import pytest

from cornercheck.ledger.chain import (
    GENESIS,
    UnsafePayloadError,
    canonical,
    link_hash,
    verify_rows,
)

KEY = b"unit-test-key"


def _build_rows(payloads: list[dict]) -> list[tuple[int, dict, str, str]]:
    rows = []
    prev = GENESIS
    for i, payload in enumerate(payloads, start=1):
        h = link_hash(KEY, prev, payload)
        rows.append((i, payload, prev, h))
        prev = h
    return rows


def test_canonical_is_key_order_independent() -> None:
    assert canonical({"a": 1, "b": "x"}) == canonical({"b": "x", "a": 1})


def test_canonical_rejects_floats_at_any_depth() -> None:
    with pytest.raises(UnsafePayloadError):
        canonical({"x": 1.5})
    with pytest.raises(UnsafePayloadError):
        canonical({"x": {"y": [1, 2, {"z": 3.0}]}})


def test_link_hash_depends_on_key_prev_and_payload() -> None:
    base = link_hash(KEY, GENESIS, {"a": 1})
    assert link_hash(b"other-key", GENESIS, {"a": 1}) != base
    assert link_hash(KEY, "1" * 64, {"a": 1}) != base
    assert link_hash(KEY, GENESIS, {"a": 2}) != base


def test_verify_intact_chain() -> None:
    rows = _build_rows([{"n": i} for i in range(5)])
    result = verify_rows(KEY, rows)
    assert result.ok and result.checked == 5 and result.first_bad_seq is None


def test_verify_reports_exact_seq_on_payload_tamper() -> None:
    rows = _build_rows([{"n": i} for i in range(5)])
    seq, payload, prev, h = rows[2]
    rows[2] = (seq, {**payload, "tampered": True}, prev, h)
    result = verify_rows(KEY, rows)
    assert not result.ok and result.first_bad_seq == 3


def test_verify_reports_exact_seq_on_prev_hash_tamper() -> None:
    rows = _build_rows([{"n": i} for i in range(4)])
    seq, payload, _prev, h = rows[1]
    rows[1] = (seq, payload, "f" * 64, h)
    result = verify_rows(KEY, rows)
    assert not result.ok and result.first_bad_seq == 2


def test_empty_chain_is_intact() -> None:
    result = verify_rows(KEY, [])
    assert result.ok and result.checked == 0
