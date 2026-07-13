"""Live Z3 verification demo (for the video / judges).

  uv run python scripts/z3_proof_demo.py

Shows: (1) the engine's clearance logic proven EQUIVALENT to an independent safety spec over
all dates/intervals; (2) the proof's teeth, including the real fail-open bug it surfaced (a
malformed end<start range that silently cleared a suspended fighter, now fixed). The
'equivalent -> mutate the engine -> Z3 hands you the broken input' arc is the demo beat:
the safety property is verified, not asserted."""

from cornercheck.verification.z3_safety import (
    counterexample_pre_fix_malformed_range,
    counterexample_when_start_boundary_loosened,
    prove_engine_equivalent_to_spec,
    prove_engine_refines_safety_spec,
    prove_identity_gate,
)


def main() -> None:
    print("=" * 74)
    print("CornerCheck clearance logic, formally verified with Z3")
    print("=" * 74)

    print("\n[1] Engine CLEAR decision refines an independent safety spec (<=3 suspensions):")
    r = prove_engine_refines_safety_spec(3)
    print(f"    {r.status}: {r.detail}")

    print("\n[2] Engine membership == independent spec, for ALL inputs:")
    r = prove_engine_equivalent_to_spec()
    print(f"    {r.status}: {r.detail}")

    print("\n[3] Identity contract (axiom consistency check, not a code-derived proof):")
    r = prove_identity_gate()
    print(f"    {r.status}: {r.detail}")

    print("\n[4] Teeth, the REAL bug this proof surfaced (malformed end<start range):")
    r = counterexample_pre_fix_malformed_range()
    print(f"    {r.status}: {r.detail}")

    print("\n[5] Teeth, a deliberate boundary mutation (>= became >):")
    r = counterexample_when_start_boundary_loosened()
    print(f"    {r.status}: {r.detail}")

    print("\n    => Not a tautology: the engine formula is checked against an independently")
    print("       written spec. Corrupt the engine and Z3 hands you the exact fighter the")
    print("       broken logic would wrongly clear. This proof caught a real fail-open bug.")


if __name__ == "__main__":
    main()
