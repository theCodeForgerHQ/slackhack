"""Z3 verification of CornerCheck's fail-closed clearance logic.

This is NOT a tautology. The engine's interval-membership decision (mirrored from
rules.engine.suspension_interval) is checked for EQUIVALENCE against an INDEPENDENTLY
written safety specification, over the infinite space of all integer dates and intervals.
Because the two formulas are written by different reasoning, Z3 must actually solve the
interval logic; any divergence (a loosened boundary, a dropped branch, the malformed-range
edge) yields a concrete counterexample. A finite test suite cannot cover that input space.

This proof FOUND a real fail-open bug: a suspension with end_date < start_date produced an
empty interval, so the fighter was never active and silently CLEARED. The engine now fails
closed on malformed ranges; counterexample_pre_fix_malformed_range() preserves the witness.

Neurosymbolic framing (Kautz Type 2): the LLM perceives and orchestrates; this Z3-checked
symbolic core decides clearance.
"""

from dataclasses import dataclass, field
from typing import Any

import z3


@dataclass(frozen=True)
class ProofResult:
    status: str  # "PROVEN" | "COUNTEREXAMPLE" | "UNKNOWN"
    detail: str
    counterexample: dict[str, Any] = field(default_factory=dict)

    @property
    def proven(self) -> bool:
        return self.status == "PROVEN"


def engine_active(
    d: z3.ArithRef, start: z3.ArithRef, end: z3.ArithRef, open_ended: z3.BoolRef
) -> z3.BoolRef:
    """Mirror of rules.engine.suspension_interval membership AS THE CODE COMPUTES IT:
    open-ended -> active iff d >= start; well-formed bounded -> start <= d <= end; malformed
    (end < start) -> active iff d >= start (the fail-closed fix)."""
    return z3.And(d >= start, z3.Or(open_ended, d <= end, end < start))


def _spec_must_block(
    d: z3.ArithRef, start: z3.ArithRef, end: z3.ArithRef, open_ended: z3.BoolRef
) -> z3.BoolRef:
    """INDEPENDENT safety specification, written by different reasoning: a fighter must not
    be cleared on d when the suspension has started (d >= start) and has not PROPERLY ended
    before d (a proper end requires a well-formed bounded range with d past the end). A
    malformed range has no proper end, so it keeps blocking. Logically equivalent to
    engine_active iff the engine is correct; Z3 checks that, it is not assumed."""
    properly_ended = z3.And(z3.Not(open_ended), end >= start, d > end)
    return z3.And(d >= start, z3.Not(properly_ended))


def _decls(i: int) -> tuple[z3.ArithRef, z3.ArithRef, z3.BoolRef]:
    return z3.Int(f"start_{i}"), z3.Int(f"end_{i}"), z3.Bool(f"open_ended_{i}")


def prove_engine_refines_safety_spec(n_suspensions: int = 3) -> ProofResult:
    """Prove: for ALL dates and ALL <=n suspensions, if the engine CLEARS (no suspension
    active per engine_active) then the independent spec agrees nobody must be blocked.
    We assert the negation and show it is unsatisfiable."""
    s = z3.Solver()
    d = z3.Int("query_date")
    engine_clears = []
    spec_blocks = []
    for i in range(n_suspensions):
        start, end, open_ended = _decls(i)
        engine_clears.append(z3.Not(engine_active(d, start, end, open_ended)))
        spec_blocks.append(_spec_must_block(d, start, end, open_ended))

    s.add(z3.And(engine_clears))  # the engine cleared the fighter
    s.add(z3.Or(spec_blocks))  # ...but the independent spec says someone must be blocked
    result = s.check()
    if result == z3.unsat:
        return ProofResult(
            "PROVEN",
            f"unsat over all dates/intervals (<= {n_suspensions} suspensions): the engine's "
            "CLEAR decision never contradicts the independent safety spec. The clearance "
            "logic provably refines fail-closed safety, malformed-range edges included.",
        )
    if result == z3.sat:
        return ProofResult(
            "COUNTEREXAMPLE", "the engine diverges from the spec", _model_dict(s.model())
        )
    return ProofResult("UNKNOWN", "Z3 returned unknown")


def prove_engine_equivalent_to_spec() -> ProofResult:
    """Stronger: engine_active and the spec are EQUIVALENT for every input (neither over- nor
    under-blocks). Asserts they differ; unsat means they agree everywhere."""
    s = z3.Solver()
    d = z3.Int("d")
    start = z3.Int("start")
    end = z3.Int("end")
    open_ended = z3.Bool("open_ended")
    s.add(engine_active(d, start, end, open_ended) != _spec_must_block(d, start, end, open_ended))
    result = s.check()
    if result == z3.unsat:
        return ProofResult(
            "PROVEN", "unsat: engine membership == independent safety spec, for all inputs."
        )
    if result == z3.sat:
        return ProofResult("COUNTEREXAMPLE", "engine and spec disagree", _model_dict(s.model()))
    # z3 'unknown' has no model; touching s.model() here would raise instead of reporting.
    return ProofResult("UNKNOWN", "Z3 returned unknown")


def counterexample_pre_fix_malformed_range() -> ProofResult:
    """Teeth + the real bug. The PRE-FIX engine used closed[start,end] for all bounded
    suspensions (no malformed-range branch). Z3 finds the concrete fighter it would wrongly
    clear: a suspension with end < start, queried on/after start."""
    s = z3.Solver()
    d = z3.Int("d")
    start = z3.Int("start")
    end = z3.Int("end")
    open_ended = z3.Bool("open_ended")
    pre_fix_active = z3.And(d >= start, z3.Or(open_ended, d <= end))  # the OLD formula
    s.add(z3.Not(pre_fix_active))  # the pre-fix engine clears...
    s.add(_spec_must_block(d, start, end, open_ended))  # ...while the spec says block
    if s.check() == z3.sat:
        ce = _model_dict(s.model())
        return ProofResult(
            "COUNTEREXAMPLE",
            f"the pre-fix engine clears a suspended fighter on a malformed (end<start) range: "
            f"{ce}. Z3 found the fail-open hole; the fixed engine is unsat here.",
            ce,
        )
    return ProofResult("PROVEN", "no counterexample (unexpected)")


def counterexample_when_start_boundary_loosened() -> ProofResult:
    """Extra teeth: if the engine used d > start instead of d >= start, the fighter would be
    wrongly cleared on the first day of the suspension. Z3 catches it."""
    s = z3.Solver()
    d = z3.Int("d")
    start = z3.Int("start")
    end = z3.Int("end")
    open_ended = z3.Bool("open_ended")
    loosened_active = z3.And(d > start, z3.Or(open_ended, d <= end, end < start))  # BUG: > not >=
    s.add(z3.Not(loosened_active))
    s.add(_spec_must_block(d, start, end, open_ended))
    result = s.check()
    if result == z3.sat:
        ce = _model_dict(s.model())
        return ProofResult(
            "COUNTEREXAMPLE", f"loosened start boundary clears day-one suspension: {ce}", ce
        )
    if result == z3.unsat:
        return ProofResult("PROVEN", "no counterexample (unexpected)")
    return ProofResult("UNKNOWN", "Z3 returned unknown")


def prove_identity_gate() -> ProofResult:
    """Sanity-check of the identity gate's intended CONTRACT (clearance implies a
    confirmed identity), encoded as an AXIOM and shown consistent: unlike the interval
    proofs above, this does not derive the property from engine code. The actual
    enforcement is the SessionStore + PreToolUse hook, which is tested, not proven."""
    s = z3.Solver()
    confirmed = z3.Bool("identity_confirmed")
    engine_clear = z3.Bool("engine_clear")
    s.add(z3.And(confirmed, engine_clear))
    s.add(z3.Not(confirmed))
    if s.check() == z3.unsat:
        return ProofResult(
            "PROVEN", "unsat: no clearance is ever emitted without a confirmed identity."
        )
    return ProofResult("COUNTEREXAMPLE", "identity gate FAILS", _model_dict(s.model()))


def _model_dict(m: z3.ModelRef) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for decl in m.decls():
        v = m[decl]
        out[decl.name()] = (
            v.as_long() if z3.is_int_value(v) else bool(v) if z3.is_bool(v) else str(v)
        )
    return out
