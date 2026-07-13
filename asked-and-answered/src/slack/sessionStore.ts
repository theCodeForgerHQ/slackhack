import Database from 'better-sqlite3';
import type { DraftResult } from '../core/pipeline.js';
import type { PlanCounts } from './blocks.js';

export interface SessionRecord {
  runId: string;
  requesterId: string;
  results: DraftResult[];
  counts: PlanCounts;
  /** Question IDs that have passed the first mandatory human gate. */
  confirmedQuestionIds?: string[];
  updatedAt: string;
}

export interface SessionStore {
  save(record: SessionRecord): void;
  load(runId: string): SessionRecord | undefined;
  delete(runId: string): void;
  prune(maxAgeMs: number): void;
}

/** In-memory store for tests and single-process deployments. */
export class InMemorySessionStore implements SessionStore {
  private readonly records = new Map<string, SessionRecord>();

  save(record: SessionRecord): void {
    this.records.set(record.runId, record);
  }

  load(runId: string): SessionRecord | undefined {
    return this.records.get(runId);
  }

  delete(runId: string): void {
    this.records.delete(runId);
  }

  prune(maxAgeMs: number): void {
    const cutoff = Date.now() - maxAgeMs;
    for (const [runId, record] of this.records) {
      if (new Date(record.updatedAt).getTime() < cutoff) this.records.delete(runId);
    }
  }
}

/**
 * SQLite-backed session store. Survives Render free-tier cold starts so
 * review buttons keep working after the app spins down.
 */
export class SqliteSessionStore implements SessionStore {
  private constructor(private readonly db: Database.Database) {
    this.db
      .prepare(
        `CREATE TABLE IF NOT EXISTS review_sessions (
           run_id TEXT PRIMARY KEY,
           requester_id TEXT NOT NULL,
           results_json TEXT NOT NULL,
           counts_json TEXT NOT NULL,
           confirmed_json TEXT NOT NULL DEFAULT '[]',
           updated_at TEXT NOT NULL
         )`,
      )
      .run();
    // Backfill existing rows so the column is always present.
    this.db.prepare(`UPDATE review_sessions SET confirmed_json = '[]' WHERE confirmed_json IS NULL`).run();
  }

  static inMemory(): SqliteSessionStore {
    return new SqliteSessionStore(new Database(':memory:'));
  }

  static atPath(path: string): SqliteSessionStore {
    return new SqliteSessionStore(new Database(path));
  }

  save(record: SessionRecord): void {
    this.db
      .prepare(
        `INSERT INTO review_sessions (run_id, requester_id, results_json, counts_json, confirmed_json, updated_at)
         VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(run_id) DO UPDATE SET
           requester_id = excluded.requester_id,
           results_json = excluded.results_json,
           counts_json = excluded.counts_json,
           confirmed_json = excluded.confirmed_json,
           updated_at = excluded.updated_at`,
      )
      .run(
        record.runId,
        record.requesterId,
        JSON.stringify(record.results),
        JSON.stringify(record.counts),
        JSON.stringify(record.confirmedQuestionIds ?? []),
        record.updatedAt,
      );
  }

  load(runId: string): SessionRecord | undefined {
    const row = this.db
      .prepare('SELECT * FROM review_sessions WHERE run_id = ?')
      .get(runId) as
      | { run_id: string; requester_id: string; results_json: string; counts_json: string; confirmed_json: string; updated_at: string }
      | undefined;
    if (!row) return undefined;
    return {
      runId: row.run_id,
      requesterId: row.requester_id,
      results: JSON.parse(row.results_json) as DraftResult[],
      counts: JSON.parse(row.counts_json) as PlanCounts,
      confirmedQuestionIds: JSON.parse(row.confirmed_json) as string[],
      updatedAt: row.updated_at,
    };
  }

  delete(runId: string): void {
    this.db.prepare('DELETE FROM review_sessions WHERE run_id = ?').run(runId);
  }

  prune(maxAgeMs: number): void {
    const cutoff = new Date(Date.now() - maxAgeMs).toISOString();
    this.db.prepare('DELETE FROM review_sessions WHERE updated_at < ?').run(cutoff);
  }
}
