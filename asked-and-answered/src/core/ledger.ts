import { createHash, createHmac } from 'node:crypto';
import Database from 'better-sqlite3';

export type LedgerAction = 'approve' | 'confirm' | 'reject' | 'edit' | 'export' | 'degrade';

export interface AppendInput {
  action: LedgerAction;
  /** Slack user id of the human (or system) performing the action. */
  actor: string;
  questionId: string;
  /**
   * The answer text at the moment of action. Only its hash is stored —
   * the ledger must never hold answer content verbatim (zero-copy).
   */
  answerHashInput: string;
  /** Slack permalinks / file ids supporting the answer. */
  evidenceRefs: string[];
}

export interface LedgerEntry {
  seq: number;
  ts: string;
  action: LedgerAction;
  actor: string;
  questionId: string;
  answerHash: string;
  evidenceHash: string;
  prevHash: string;
  hash: string;
}

export interface VerifyResult {
  ok: boolean;
  entriesChecked: number;
  /** Sequence number of the first entry that fails verification. */
  firstBadSeq?: number;
}

const GENESIS = 'GENESIS';

/**
 * Content hashes are keyed (HMAC) so short, guessable answers ("Yes") can't
 * be recovered from the ledger by dictionary attack. The chain hash itself
 * is integrity-only and uses plain SHA-256 over a JSON-encoded field array
 * (no delimiter-collision ambiguity).
 */
function contentHash(input: string): string {
  const key = process.env.AA_LEDGER_KEY ?? 'aa-integrity-only-v1';
  return createHmac('sha256', key).update(input).digest('hex');
}

/** Exported for the test-only tamper helper — not part of the public API surface. */
export function computeEntryHash(e: Omit<LedgerEntry, 'hash'>): string {
  return createHash('sha256')
    .update(
      JSON.stringify([e.seq, e.ts, e.action, e.actor, e.questionId, e.answerHash, e.evidenceHash, e.prevHash]),
    )
    .digest('hex');
}

/**
 * Append-only, hash-chained approval ledger.
 *
 * Every review action chains to the previous entry's hash; `verify()`
 * recomputes the whole chain so any post-hoc edit to any field of any row
 * is detectable. Answer text enters only as a SHA-256 hash.
 */
export class Ledger {
  private constructor(private readonly db: Database.Database) {
    this.db
      .prepare(
        `CREATE TABLE IF NOT EXISTS ledger (
           seq INTEGER PRIMARY KEY,
           ts TEXT NOT NULL,
           action TEXT NOT NULL,
           actor TEXT NOT NULL,
           question_id TEXT NOT NULL,
           answer_hash TEXT NOT NULL,
           evidence_hash TEXT NOT NULL,
           prev_hash TEXT NOT NULL,
           hash TEXT NOT NULL
         )`,
      )
      .run();
  }

  static inMemory(): Ledger {
    return new Ledger(new Database(':memory:'));
  }

  static atPath(path: string): Ledger {
    return new Ledger(new Database(path));
  }

  append(input: AppendInput): LedgerEntry {
    // Transactional read-modify-write: concurrent appends serialize instead
    // of racing on seq/prevHash.
    const insert = this.db.transaction((): LedgerEntry => {
      const prev = this.lastEntry();
      const partial: Omit<LedgerEntry, 'hash'> = {
        seq: (prev?.seq ?? -1) + 1,
        ts: new Date().toISOString(),
        action: input.action,
        actor: input.actor,
        questionId: input.questionId,
        answerHash: contentHash(input.answerHashInput),
        evidenceHash: contentHash(input.evidenceRefs.slice().sort().join('\n')),
        prevHash: prev?.hash ?? GENESIS,
      };
      const entry: LedgerEntry = { ...partial, hash: computeEntryHash(partial) };
      this.db
        .prepare(
          `INSERT INTO ledger (seq, ts, action, actor, question_id, answer_hash, evidence_hash, prev_hash, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .run(
          entry.seq,
          entry.ts,
          entry.action,
          entry.actor,
          entry.questionId,
          entry.answerHash,
          entry.evidenceHash,
          entry.prevHash,
          entry.hash,
        );
      return entry;
    });
    return insert();
  }

  entries(): LedgerEntry[] {
    const rows = this.db.prepare('SELECT * FROM ledger ORDER BY seq').all() as Array<{
      seq: number;
      ts: string;
      action: LedgerAction;
      actor: string;
      question_id: string;
      answer_hash: string;
      evidence_hash: string;
      prev_hash: string;
      hash: string;
    }>;
    return rows.map((r) => ({
      seq: r.seq,
      ts: r.ts,
      action: r.action,
      actor: r.actor,
      questionId: r.question_id,
      answerHash: r.answer_hash,
      evidenceHash: r.evidence_hash,
      prevHash: r.prev_hash,
      hash: r.hash,
    }));
  }

  verify(): VerifyResult {
    const all = this.entries();
    let prevHash = GENESIS;
    let checked = 0;
    for (const e of all) {
      const { hash, ...rest } = e;
      if (e.prevHash !== prevHash || computeEntryHash(rest) !== hash) {
        return { ok: false, entriesChecked: checked, firstBadSeq: e.seq };
      }
      checked++;
      prevHash = hash;
    }
    return { ok: true, entriesChecked: checked };
  }

  private lastEntry(): LedgerEntry | undefined {
    return this.entries().at(-1);
  }
}
