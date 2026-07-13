"""First-boot provisioning for the deployed service: apply migrations, and seed the data
ONCE if the fighters table is empty. Idempotent (subsequent boots skip). Best-effort: a
failure here logs but never crashes the worker (a degraded DB yields fail-closed NOT_FOUND
clearances, never a false CLEAR)."""

import importlib.util
import logging
from pathlib import Path

import cornercheck

log = logging.getLogger("cornercheck.bootstrap")

# repo root holds seeds/ (committed); the package lives at <root>/src/cornercheck
_REPO_ROOT = Path(cornercheck.__file__).resolve().parents[2]
_SEED_DB = _REPO_ROOT / "seeds" / "seed_db.py"


def _load_seed_module() -> object | None:
    if not _SEED_DB.exists():
        log.warning("seed_db.py not found at %s; skipping data seed", _SEED_DB)
        return None
    spec = importlib.util.spec_from_file_location("seed_db", _SEED_DB)
    if spec is None or spec.loader is None:
        log.warning("seed_db.py at %s could not be loaded as a module; skipping seed", _SEED_DB)
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def bootstrap_db() -> None:
    try:
        from cornercheck.db.migrate import apply_migrations
        from cornercheck.db.pool import get_pool

        apply_migrations()
        with get_pool().connection() as conn:
            row = conn.execute("SELECT count(*) FROM fighters").fetchone()
        count = row[0] if row else 0
        if count > 0:
            log.info("bootstrap: DB already seeded (%d fighters)", count)
            # Converge on newly curated cited cases without wiping anything: additive,
            # idempotent, keyed by (fighter, start_date, jurisdiction).
            mod = _load_seed_module()
            if mod is not None and hasattr(mod, "top_up_cases"):
                added = mod.top_up_cases()
                if added:
                    log.info("bootstrap: topped up %d new cited suspension cases", added)
            return
        mod = _load_seed_module()
        if mod is None:
            return
        mod.seed(force=False)  # type: ignore[attr-defined]
        log.info("bootstrap: seeded a fresh DB")
    except Exception:
        log.exception("bootstrap DB step failed; app continues (clearances fail closed)")
