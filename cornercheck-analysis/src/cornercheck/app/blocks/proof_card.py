"""The in-product safety proof. A judge clicks the button and Z3 runs the ACTUAL proof
right then, plus a negative control (a deliberately loosened boundary that must yield a
counterexample) proving the prover is not a rubber stamp. Rendered from ProofResult
fields only, never from model prose. If either check misbehaves, the card says so in
the loudest possible way: a safety proof that fails must never render as reassurance."""

import logging
from typing import Any

from cornercheck.verification.z3_safety import ProofResult

log = logging.getLogger("cornercheck.proof_card")


def _cx(d: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v}" for k, v in sorted(d.items()))[:200]


def _coverage_phrase() -> str:
    """The live calibrated level, never a stranded hardcode: a recalibration at a
    different alpha must not leave this card claiming the old number."""
    try:
        from cornercheck.er.conformal import load_gate

        gate = load_gate()
        if gate:
            return f"{gate.coverage_pct}% coverage"
    except Exception as exc:
        # The fallback phrase is an honest degrade, but a persistently broken gate
        # load must not be invisible.
        log.warning("conformal gate unavailable for the proof card: %s", exc)
    return "calibrated coverage"


def build_proof_card(positive: ProofResult, control: ProofResult) -> list[dict[str, Any]]:
    """positive: the live equivalence proof (must be PROVEN). control: the loosened
    boundary (must yield COUNTEREXAMPLE, or the prover proved nothing)."""
    healthy = positive.proven and control.status == "COUNTEREXAMPLE"
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "The proof behind this verdict"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "The engine's suspension-window logic is checked for *equivalence* with "
                    "an independently written safety specification over *all* dates and "
                    "intervals: if a suspension is active on the date, the engine can never "
                    "return CLEAR. The Z3 theorem prover ran this check *just now*, live:"
                ),
            },
        },
    ]
    if healthy:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":white_check_mark: *PROVEN* (live run)\n{positive.detail}"[:3000],
                },
            }
        )
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":test_tube: *Non-vacuity control:* a deliberately loosened start "
                        "boundary was also checked and Z3 produced a concrete counterexample "
                        f"({_cx(control.counterexample)}). The prover earns its keep; it is "
                        "not a tautology."
                    )[:3000],
                },
            }
        )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        ":rotating_light: *PROOF FAILED.* The live check did not behave as a "
                        "healthy system must "
                        f"(proof: {positive.status}; control: {control.status}). "
                        f"{_cx(positive.counterexample)}\n"
                        "*Treat every CLEAR verdict as unsafe until this is investigated.*"
                    )[:3000],
                },
            }
        )
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "Scope: the suspension-window decision logic. Identity matching is "
                        f"separately certified by conformal calibration ({_coverage_phrase()}). "
                        "Decision support; a human makes the call."
                    ),
                }
            ],
        }
    )
    return blocks


def fallback_text(positive: ProofResult) -> str:
    return f"CornerCheck safety proof: {positive.status}"
