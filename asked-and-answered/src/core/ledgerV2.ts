import Database from 'better-sqlite3';
import { createHash } from 'node:crypto';
import type { DomainEvent } from './events.js';

const GENESIS = 'GENESIS';

export interface LedgerV2Entry {
  seq: number;
  ts: string;
  action: string;
  actor: string;
  questionId: string;
  payload: DomainEvent;
  prevHash: string;
  hash: string;
}

export interface LedgerV2VerifyResult {
  ok: boolean;
  entriesChecked: number;
  firstBadSeq?: number;
  metadataMismatch?: string;
}

/** Exported for test-only tamper simulations. */
export function computeHash(e: Omit<LedgerV2Entry, 'hash'>): string {
  return createHash('sha256')
    .update(JSON.stringify([e.seq, e.ts, e.action, e.actor, e.questionId, JSON.stringify(e.payload), e.prevHash]))
    .digest('hex');
}

function eventMeta(event: DomainEvent): { action: string; actor: string; questionId: string } {
  switch (event.type) {
    case 'QuestionnaireIntaken':
      return { action: event.type, actor: 'system', questionId: event.runId };
    case 'EvidenceRetrieved':
      return { action: event.type, actor: 'system', questionId: event.questionId };
    case 'DraftProduced':
      return { action: event.type, actor: 'system', questionId: event.questionId };
    case 'CitationValidated':
      return { action: event.type, actor: 'system', questionId: event.questionId };
    case 'VisibilityChecked':
      return { action: event.type, actor: 'system', questionId: event.questionId };
    case 'AnswerApproved':
      return { action: event.type, actor: event.actor, questionId: event.questionText };
    case 'AnswerEdited':
      return { action: event.type, actor: event.actor, questionId: String(event.answerId) };
    case 'AnswerRejected':
      return { action: event.type, actor: event.actor, questionId: event.questionId };
    case 'AnswerConfirmed':
      return { action: event.type, actor: event.actor, questionId: event.questionId };
    case 'AnswerProposed':
      return { action: event.type, actor: event.actor, questionId: event.questionText };
    case 'Exported':
      return { action: event.type, actor: event.actor, questionId: event.runId };
  }
}

/**
 * Event-sourced, tamper-evident ledger v2.
 *
 * Stores full DomainEvent payloads in a hash chain so that any mutation to
 * either the stored columns or the payload JSON breaks verification. The
 * payload itself embeds metadata (type, actor, ts), so the columns and the
 * payload are cross-checked.
 */
export class LedgerV2 {
  private constructor(private readonly db: Database.Database) {
    this.db
      .prepare(
        `CREATE TABLE IF NOT EXISTS ledger_v2 (
           seq INTEGER PRIMARY KEY,
           ts TEXT NOT NULL,
           action TEXT NOT NULL,
           actor TEXT NOT NULL,
           question_id TEXT NOT NULL,
           payload TEXT NOT NULL,
           prev_hash TEXT NOT NULL,
           hash TEXT NOT NULL
         )`,
      )
      .run();
  }

  static inMemory(): LedgerV2 {
    return new LedgerV2(new Database(':memory:'));
  }

  static atPath(path: string): LedgerV2 {
    return new LedgerV2(new Database(path));
  }

  append(event: DomainEvent): void {
    const meta = eventMeta(event);
    const insert = this.db.transaction((): void => {
      const prev = this.lastRow();
      const partial: Omit<LedgerV2Entry, 'hash'> = {
        seq: (prev?.seq ?? -1) + 1,
        ts: new Date().toISOString(),
        action: meta.action,
        actor: meta.actor,
        questionId: meta.questionId,
        payload: event,
        prevHash: prev?.hash ?? GENESIS,
      };
      const entry: LedgerV2Entry = { ...partial, hash: computeHash(partial) };
      this.db
        .prepare(
          `INSERT INTO ledger_v2 (seq, ts, action, actor, question_id, payload, prev_hash, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
        )
        .run(
          entry.seq,
          entry.ts,
          entry.action,
          entry.actor,
          entry.questionId,
          JSON.stringify(entry.payload),
          entry.prevHash,
          entry.hash,
        );
    });
    insert();
  }

  entries(): DomainEvent[] {
    return this.rows().map((r) => r.payload);
  }

  rows(): LedgerV2Entry[] {
    const rows = this.db.prepare('SELECT * FROM ledger_v2 ORDER BY seq').all() as Array<{
      seq: number;
      ts: string;
      action: string;
      actor: string;
      question_id: string;
      payload: string;
      prev_hash: string;
      hash: string;
    }>;
    return rows.map((r) => ({
      seq: r.seq,
      ts: r.ts,
      action: r.action,
      actor: r.actor,
      questionId: r.question_id,
      payload: JSON.parse(r.payload) as DomainEvent,
      prevHash: r.prev_hash,
      hash: r.hash,
    }));
  }

  verify(): LedgerV2VerifyResult {
    const all = this.rows();
    let prevHash = GENESIS;
    let checked = 0;
    for (const e of all) {
      const { hash, ...rest } = e;
      if (e.prevHash !== prevHash || computeHash(rest) !== hash) {
        return { ok: false, entriesChecked: checked, firstBadSeq: e.seq };
      }
      const meta = eventMeta(e.payload);
      if (e.action !== meta.action || e.actor !== meta.actor || e.questionId !== meta.questionId) {
        return {
          ok: false,
          entriesChecked: checked,
          firstBadSeq: e.seq,
          metadataMismatch: `entry ${e.seq}: stored metadata does not match payload`,
        };
      }
      checked++;
      prevHash = hash;
    }
    return { ok: true, entriesChecked: checked };
  }

  private lastRow(): LedgerV2Entry | undefined {
    return this.rows().at(-1);
  }
}
