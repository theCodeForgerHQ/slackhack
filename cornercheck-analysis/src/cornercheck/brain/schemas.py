"""Pydantic contracts. The Slack card renders from these, never from LLM prose."""

from datetime import date

from pydantic import BaseModel, Field

from cornercheck.er.thresholds import ResolutionResult
from cornercheck.rules.engine import RuleVerdict


class CandidateOut(BaseModel):
    fighter_id: str
    full_name: str
    weight_class: str | None
    record: str
    sport: str
    jurisdiction: str | None
    score: float


class ActiveSuspensionOut(BaseModel):
    suspension_type: str
    start_date: date
    end_date: date | None
    indefinite: bool
    jurisdiction: str
    reason: str
    source_url: str


class CorroborationOut(BaseModel):
    """A second-source check of identity and record (boxing-data.com). It annotates
    always and TIGHTENS on disagreement; it can never loosen a verdict.
    status: CONFIRMED | DISAGREED | UNMATCHED | UNAVAILABLE | NOT_APPLICABLE."""

    source: str = "boxing-data.com"
    status: str
    note: str
    live_record: str | None = None
    checked_at: str | None = None
    data_origin: str = "none"  # live | cache | demo-fixture | none


class ClearanceVerdict(BaseModel):
    """The deterministic pipeline's answer. status NEEDS_DISAMBIGUATION/NOT_FOUND are
    fail-closed identity outcomes; CLEAR/DO_NOT_CLEAR come only from the rule engine."""

    status: str  # CLEAR | DO_NOT_CLEAR | NEEDS_DISAMBIGUATION | NOT_FOUND
    query: str
    on_date: date
    fighter_id: str | None = None
    fighter_name: str | None = None
    candidates: list[CandidateOut] = Field(default_factory=list)
    active_suspensions: list[ActiveSuspensionOut] = Field(default_factory=list)
    applied_rules: list[str] = Field(default_factory=list)
    consultation_note: str | None = None
    identity_note: str = ""
    ledger_seq: int | None = None
    corroboration: CorroborationOut | None = None


def from_resolution(query: str, on_date: date, r: ResolutionResult) -> ClearanceVerdict:
    status = "NEEDS_DISAMBIGUATION" if r.status == "AMBIGUOUS" else "NOT_FOUND"
    return ClearanceVerdict(
        status=status,
        query=query,
        on_date=on_date,
        candidates=[CandidateOut(**c.__dict__) for c in r.candidates],
        identity_note=r.note,
    )


def from_rule_verdict(
    query: str,
    fighter_id: str,
    fighter_name: str,
    v: RuleVerdict,
    ledger_seq: int | None,
) -> ClearanceVerdict:
    return ClearanceVerdict(
        status=v.decision,
        query=query,
        on_date=v.on_date,
        fighter_id=fighter_id,
        fighter_name=fighter_name,
        active_suspensions=[ActiveSuspensionOut(**s.__dict__) for s in v.active],
        applied_rules=v.applied_rules,
        consultation_note=v.consultation_note,
        ledger_seq=ledger_seq,
    )
