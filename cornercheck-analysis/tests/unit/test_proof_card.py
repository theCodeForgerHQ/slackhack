"""The in-product safety proof card, exercised against REAL Z3 runs (no mocks: the
prover is fast enough to run in unit tests, which is the whole point of the button)."""

from cornercheck.app.blocks.proof_card import build_proof_card, fallback_text
from cornercheck.verification.z3_safety import (
    ProofResult,
    counterexample_when_start_boundary_loosened,
    prove_engine_equivalent_to_spec,
)


def test_real_live_proof_renders_proven_with_nonvacuity_control() -> None:
    positive = prove_engine_equivalent_to_spec()
    control = counterexample_when_start_boundary_loosened()
    assert positive.proven and control.status == "COUNTEREXAMPLE"  # the healthy system
    blocks = build_proof_card(positive, control)
    text = str(blocks)
    assert "PROVEN" in text
    assert "Non-vacuity control" in text and "counterexample" in text
    assert "conformal calibration" in text  # honest scope line
    assert "human makes the call" in text
    assert "—" not in text  # no em-dashes in product copy
    assert fallback_text(positive) == "CornerCheck safety proof: PROVEN"


def test_failed_proof_renders_alarm_not_reassurance() -> None:
    broken = ProofResult("COUNTEREXAMPLE", "engine and spec disagree", {"d": 5, "start": 5})
    control = counterexample_when_start_boundary_loosened()
    text = str(build_proof_card(broken, control))
    assert "PROOF FAILED" in text
    assert "unsafe until this is investigated" in text
    assert "PROVEN" not in text.replace("PROOF FAILED", "")


def test_vacuous_prover_also_renders_alarm() -> None:
    # If the control comes back PROVEN, the prover demonstrated NOTHING: that must
    # alarm too, never reassure.
    positive = prove_engine_equivalent_to_spec()
    vacuous_control = ProofResult("PROVEN", "loosened boundary not caught")
    text = str(build_proof_card(positive, vacuous_control))
    assert "PROOF FAILED" in text


def test_verdict_card_carries_the_proof_button() -> None:
    from datetime import date

    from cornercheck.app.blocks.verdict_card import build_verdict_card
    from cornercheck.brain.schemas import ClearanceVerdict

    v = ClearanceVerdict(status="CLEAR", query="x", on_date=date(2026, 6, 9))
    blocks = build_verdict_card(v)
    actions = next(b for b in blocks if b["type"] == "actions")
    ids = [e["action_id"] for e in actions["elements"]]
    assert ids == ["view_audit_trail", "view_safety_proof"]
