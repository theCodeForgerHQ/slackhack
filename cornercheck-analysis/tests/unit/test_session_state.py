"""Session store transitions: the gate's memory must be impossible to sidestep."""

from cornercheck.session.state import SessionStore


def test_confirm_only_from_shown_candidates() -> None:
    store = SessionStore()
    store.set_candidates("t1", {"id-a": "Bruno Silva", "id-b": "Bruno Silva"})
    assert store.confirm("t1", "id-zzz") is False  # forged pick: rejected
    assert store.get("t1").confirmed_fighter_id is None
    assert store.confirm("t1", "id-b") is True
    st = store.get("t1")
    assert st.stage == "confirmed"
    assert st.confirmed_fighter_id == "id-b"


def test_new_thread_cannot_confirm_anything() -> None:
    store = SessionStore()
    assert store.confirm("fresh", "any-id") is False


def test_setting_candidates_resets_confirmation_and_verdict() -> None:
    store = SessionStore()
    store.set_candidates("t1", {"id-a": "A"})
    store.confirm("t1", "id-a")
    store.record_verdict("t1", "DO_NOT_CLEAR")
    store.set_candidates("t1", {"id-c": "C"})  # new lookup starts fresh
    st = store.get("t1")
    assert st.confirmed_fighter_id is None
    assert st.last_verdict_decision is None
    assert st.stage == "awaiting_pick"


def test_threads_are_isolated() -> None:
    store = SessionStore()
    store.set_candidates("t1", {"id-a": "A"})
    store.confirm("t1", "id-a")
    assert store.get("t2").confirmed_fighter_id is None
