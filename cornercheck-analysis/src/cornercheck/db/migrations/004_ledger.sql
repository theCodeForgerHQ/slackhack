-- Append-only audit ledger with an HMAC-SHA256 hash chain (computed in app code).
-- Defense in depth: triggers block UPDATE/DELETE/TRUNCATE at the database layer;
-- the hash chain catches anyone privileged enough to bypass the triggers.
CREATE TABLE IF NOT EXISTS ledger (
    seq bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts timestamptz NOT NULL DEFAULT now(),
    actor text NOT NULL,
    action text NOT NULL,
    payload jsonb NOT NULL,
    prev_hash char(64) NOT NULL,
    hash char(64) NOT NULL UNIQUE
);

CREATE OR REPLACE FUNCTION ledger_block_mutation() RETURNS trigger AS $fn$
BEGIN
    RAISE EXCEPTION 'ledger is append-only: % blocked', TG_OP;
END
$fn$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ledger_no_mutate ON ledger;
CREATE TRIGGER ledger_no_mutate
    BEFORE UPDATE OR DELETE ON ledger
    FOR EACH ROW EXECUTE FUNCTION ledger_block_mutation();

DROP TRIGGER IF EXISTS ledger_no_truncate ON ledger;
CREATE TRIGGER ledger_no_truncate
    BEFORE TRUNCATE ON ledger
    FOR EACH STATEMENT EXECUTE FUNCTION ledger_block_mutation();
