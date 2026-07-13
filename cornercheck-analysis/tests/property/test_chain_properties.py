"""Hypothesis properties: any chain verifies intact; any single tamper is caught
at exactly the tampered seq. These are the fail-closed guarantees in property form."""

from hypothesis import given
from hypothesis import strategies as st

from cornercheck.ledger.chain import GENESIS, link_hash, verify_rows

KEY = b"property-test-key"

json_safe = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(min_value=-(2**31), max_value=2**31)
    | st.text(max_size=20),
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(min_size=1, max_size=10), children, max_size=4)
    ),
    max_leaves=10,
)
payloads_strategy = st.lists(
    st.dictionaries(st.text(min_size=1, max_size=10), json_safe, max_size=4),
    min_size=1,
    max_size=8,
)


def _build_rows(payloads: list[dict]) -> list[tuple[int, dict, str, str]]:
    rows = []
    prev = GENESIS
    for i, payload in enumerate(payloads, start=1):
        h = link_hash(KEY, prev, payload)
        rows.append((i, payload, prev, h))
        prev = h
    return rows


@given(payloads_strategy)
def test_any_chain_verifies_intact(payloads: list[dict]) -> None:
    result = verify_rows(KEY, _build_rows(payloads))
    assert result.ok and result.checked == len(payloads)


@given(payloads_strategy, st.data())
def test_any_payload_tamper_is_caught_at_exact_seq(
    payloads: list[dict], data: st.DataObject
) -> None:
    rows = _build_rows(payloads)
    idx = data.draw(st.integers(min_value=0, max_value=len(rows) - 1))
    seq, payload, prev, h = rows[idx]
    rows[idx] = (seq, {**payload, "__tampered__": 1}, prev, h)
    result = verify_rows(KEY, rows)
    assert not result.ok
    assert result.first_bad_seq == seq


@given(payloads_strategy, st.data())
def test_any_hash_tamper_is_caught_no_later_than_next_link(
    payloads: list[dict], data: st.DataObject
) -> None:
    rows = _build_rows(payloads)
    idx = data.draw(st.integers(min_value=0, max_value=len(rows) - 1))
    seq, payload, prev, _h = rows[idx]
    rows[idx] = (seq, payload, prev, "e" * 64)
    result = verify_rows(KEY, rows)
    assert not result.ok
    # The forged hash itself fails at seq; if it somehow matched, the next link's
    # prev_hash would break. Either way detection happens at seq or seq+1.
    assert result.first_bad_seq in (seq, seq + 1)
