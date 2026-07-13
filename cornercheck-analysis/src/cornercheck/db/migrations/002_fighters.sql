-- Canonical fighter identities. Source column cites where each row came from.
CREATE TABLE IF NOT EXISTS fighters (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name text NOT NULL,
    dob date,
    weight_class text,
    wins integer NOT NULL DEFAULT 0,
    losses integer NOT NULL DEFAULT 0,
    draws integer NOT NULL DEFAULT 0,
    sport text NOT NULL DEFAULT 'mma',
    primary_jurisdiction text,
    source text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- High-recall retrieval: trigram index for fuzzy name candidates
CREATE INDEX IF NOT EXISTS fighters_name_trgm
    ON fighters USING gin (full_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS fighters_name_lower
    ON fighters (lower(full_name));
