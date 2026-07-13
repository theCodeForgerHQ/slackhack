-- Least-privilege roles. NOLOGIN group roles; per-environment login users are
-- granted membership outside migrations (never passwords in SQL files).
DO $do$ BEGIN
    CREATE ROLE cornercheck_app NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL;
END $do$;

DO $do$ BEGIN
    CREATE ROLE cornercheck_reader NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL;
END $do$;

GRANT USAGE ON SCHEMA public TO cornercheck_app, cornercheck_reader;

-- App can read everything and append; it can never UPDATE/DELETE anything.
GRANT SELECT, INSERT ON fighters, suspensions, ledger TO cornercheck_app;
GRANT SELECT ON fighters, suspensions, ledger TO cornercheck_reader;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cornercheck_app;
