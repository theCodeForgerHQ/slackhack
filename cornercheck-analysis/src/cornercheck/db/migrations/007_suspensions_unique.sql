-- One suspension record per (fighter, start_date, jurisdiction): retires the
-- SELECT-then-INSERT race in the boot-time case top-up (two instances booting
-- concurrently could both insert; duplicates over-block, the safe direction, but
-- poison the data). ON CONFLICT DO NOTHING in the seeder pairs with this.
CREATE UNIQUE INDEX IF NOT EXISTS suspensions_unique_case
    ON suspensions (fighter_id, start_date, jurisdiction);
