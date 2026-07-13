"""Public dashboard data layer: fail-soft stats, the live proof endpoint, and the page."""

from pathlib import Path

import pytest

from cornercheck.app import dashboard, web
from cornercheck.app.dashboard import proof_payload, stats_payload


def _reset_stats_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dashboard, "_stats_cache", None)
    monkeypatch.setattr(dashboard, "_stats_cached_at", 0.0)


def test_stats_is_fail_soft_when_db_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> dict:
        raise OSError("db down")

    _reset_stats_cache(monkeypatch)
    monkeypatch.setattr(dashboard, "_db_counts", boom)
    monkeypatch.setattr(dashboard, "_chain_status", lambda: {"ok": None, "detail": "x"})
    s = stats_payload()
    assert s["db"] == "unavailable"
    assert "generated_at" in s and "chain" in s  # the page still has something to render


def test_stats_merges_counts_and_conformal(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_stats_cache(monkeypatch)
    monkeypatch.setattr(
        dashboard,
        "_db_counts",
        lambda: {"fighters": 4123, "cases": 54, "jurisdictions": 14, "decisions": 9},
    )
    monkeypatch.setattr(
        dashboard, "_chain_status", lambda: {"ok": True, "checked": 9, "detail": "ok"}
    )
    s = stats_payload()
    assert s["fighters"] == 4123 and s["cases"] == 54
    assert s["chain"]["ok"] is True
    assert s["conformal"]["coverage_pct"] == 95  # the committed artifact loads


def test_proof_endpoint_runs_the_real_prover() -> None:
    p = proof_payload()
    assert p["healthy"] is True
    assert p["proof"] == "PROVEN" and p["control"] == "COUNTEREXAMPLE"
    assert p["ms"] >= 1


def test_proof_endpoint_failure_is_an_alarm_not_a_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cornercheck.verification.z3_safety as z

    def boom() -> None:
        raise RuntimeError("solver exploded")

    monkeypatch.setattr(z, "prove_engine_equivalent_to_spec", boom)
    p = proof_payload()
    assert p["healthy"] is False
    assert p["proof"] == "ERROR"
    assert "unproven" in p["proof_detail"]


def test_dashboard_page_exists_and_is_wired() -> None:
    html = (Path(web.__file__).parent / "static" / "dashboard.html").read_text()
    assert "provebtn" in html and "/api/proof" in html  # the live-proof stamp
    assert "/api/stats" in html  # live numbers, not hardcoded
    assert "refuses" in html
    assert "human makes the" in html or "final call" in html
    assert "—" not in html  # no em-dashes in judge-facing copy
    assert "Tim Hague" in html  # the why, stated plainly


def test_dashboard_fallback_does_not_poison_the_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    # A transient read failure serves the fallback ONCE; the next request with the file
    # readable again must recover (review caught the permanently-poisoned lru_cache version).
    monkeypatch.setattr(web, "_page_cache", None)
    monkeypatch.setattr(web, "_DASHBOARD", Path("/nonexistent/dashboard.html"))
    body = web._dashboard_bytes()
    assert b"CornerCheck" in body and b"provebtn" not in body  # degraded, never dead
    monkeypatch.setattr(web, "_DASHBOARD", Path(web.__file__).parent / "static" / "dashboard.html")
    body2 = web._dashboard_bytes()
    assert b"provebtn" in body2  # recovered, not poisoned
    monkeypatch.setattr(web, "_page_cache", None)


def test_stats_payload_is_cached_against_floods(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    def counting() -> dict:
        calls["n"] += 1
        return {"fighters": 1, "cases": 1, "jurisdictions": 1, "decisions": 0}

    _reset_stats_cache(monkeypatch)
    monkeypatch.setattr(dashboard, "_db_counts", counting)
    monkeypatch.setattr(dashboard, "_chain_status", lambda: {"ok": True, "detail": "x"})
    first = stats_payload()
    second = stats_payload()
    assert calls["n"] == 1  # the flood hits the cache, not the shared DB pool
    assert first is second
    monkeypatch.setattr(dashboard, "_stats_cache", None)


def test_chain_failure_detail_never_reaches_the_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Exception text can carry the DB host and port; the public detail must be fixed.
    def boom() -> None:
        raise OSError('connection to server at "db-secret-host", port 5432 failed')

    import cornercheck.ledger.verify as lv

    monkeypatch.setattr(lv, "verify_chain", boom)
    status = dashboard._chain_status()
    assert "db-secret-host" not in str(status)
    assert status["detail"] == "chain status unavailable"
