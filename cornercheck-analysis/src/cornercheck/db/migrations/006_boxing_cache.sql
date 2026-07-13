-- Cache for boxing-data.com fighter searches. The free tier is 100 requests/month,
-- so every successful live response is cached and reused for up to 7 days (TTL is
-- enforced in code so the window can change without a migration).
-- Deliberately OUTSIDE the 005 append-only role model: this is a disposable cache
-- (upsert requires UPDATE), written by the owner connection, never audit data.
CREATE TABLE IF NOT EXISTS boxing_search_cache (
    query_name text PRIMARY KEY,
    payload    jsonb NOT NULL,
    fetched_at timestamptz NOT NULL DEFAULT now()
);
