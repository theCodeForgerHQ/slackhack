-- Suspension records. Every row carries its source citation (no uncited data).
CREATE TABLE IF NOT EXISTS suspensions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    fighter_id uuid NOT NULL REFERENCES fighters(id) ON DELETE CASCADE,
    suspension_type text NOT NULL, -- KO | TKO | medical | administrative
    start_date date NOT NULL,
    end_date date,                 -- NULL with indefinite=true means "until cleared"
    indefinite boolean NOT NULL DEFAULT false,
    jurisdiction text NOT NULL,
    reason text,
    source_url text NOT NULL,
    source_quote text,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT end_after_start CHECK (end_date IS NULL OR end_date >= start_date),
    CONSTRAINT bounded_or_indefinite CHECK (end_date IS NOT NULL OR indefinite)
);

CREATE INDEX IF NOT EXISTS suspensions_fighter ON suspensions (fighter_id);
CREATE INDEX IF NOT EXISTS suspensions_jurisdiction ON suspensions (jurisdiction);
