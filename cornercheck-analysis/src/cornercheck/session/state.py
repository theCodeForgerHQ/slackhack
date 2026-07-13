"""Thread-keyed state machine backing the fail-closed gates.

Stages: new -> awaiting_pick -> confirmed. A fighter can only be confirmed from the
candidate list the thread actually saw; the PreToolUse hook cross-checks writes against
this store. In-memory by design (single worker); the ledger is the durable record.
"""

import threading
from dataclasses import dataclass, field


@dataclass
class ThreadState:
    stage: str = "new"  # new | awaiting_pick | confirmed
    candidate_ids: dict[str, str] = field(default_factory=dict)  # fighter_id -> full_name
    confirmed_fighter_id: str | None = None
    confirmed_fighter_name: str | None = None
    last_verdict_decision: str | None = None
    last_written_seq: int | None = None


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: dict[str, ThreadState] = {}

    def get(self, thread_key: str) -> ThreadState:
        with self._lock:
            return self._threads.setdefault(thread_key, ThreadState())

    def snapshot(self, thread_key: str) -> ThreadState:
        """Consistent copy for cross-thread readers (the PreToolUse gate). Never hands
        out the live object, so multi-field reads cannot tear (review finding I1)."""
        with self._lock:
            st = self._threads.setdefault(thread_key, ThreadState())
            return ThreadState(
                stage=st.stage,
                candidate_ids=dict(st.candidate_ids),
                confirmed_fighter_id=st.confirmed_fighter_id,
                confirmed_fighter_name=st.confirmed_fighter_name,
                last_verdict_decision=st.last_verdict_decision,
                last_written_seq=st.last_written_seq,
            )

    def set_candidates(self, thread_key: str, candidates: dict[str, str]) -> None:
        with self._lock:
            st = self._threads.setdefault(thread_key, ThreadState())
            st.stage = "awaiting_pick"
            st.candidate_ids = dict(candidates)
            st.confirmed_fighter_id = None
            st.confirmed_fighter_name = None
            st.last_verdict_decision = None

    def confirm(self, thread_key: str, fighter_id: str) -> bool:
        """Confirm ONLY a fighter this thread was actually shown. Returns False otherwise."""
        with self._lock:
            st = self._threads.setdefault(thread_key, ThreadState())
            if fighter_id not in st.candidate_ids:
                return False
            st.stage = "confirmed"
            st.confirmed_fighter_id = fighter_id
            st.confirmed_fighter_name = st.candidate_ids[fighter_id]
            return True

    def record_verdict(self, thread_key: str, decision: str) -> None:
        with self._lock:
            self._threads.setdefault(thread_key, ThreadState()).last_verdict_decision = decision

    def record_written(self, thread_key: str, seq: int) -> None:
        with self._lock:
            self._threads.setdefault(thread_key, ThreadState()).last_written_seq = seq

    def reset(self, thread_key: str) -> None:
        with self._lock:
            self._threads[thread_key] = ThreadState()

    def discard(self, thread_key: str) -> None:
        """Drop a thread's state entirely. Single-shot surfaces (the Workflow Builder
        step uses a fresh uuid key per execution) must discard on the way out, or an
        unattended workflow leaks one entry per run for the process lifetime."""
        with self._lock:
            self._threads.pop(thread_key, None)


SESSION_STORE = SessionStore()
