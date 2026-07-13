import type Database from 'better-sqlite3';
import { Ledger, computeEntryHash, type LedgerEntry } from '../../src/core/ledger.js';

/**
 * Test-only attacker simulation. Reaches into the Ledger's private database
 * handle from OUTSIDE the production class, exactly like a real attacker
 * with file access would — the production Ledger API itself has no mutation
 * surface beyond append().
 */
export function tamperLedger(
  ledger: Ledger,
  seq: number,
  changes: Partial<Pick<LedgerEntry, 'actor' | 'answerHash' | 'action'>>,
  opts: { rehashSelf?: boolean } = {},
): void {
  const db = (ledger as unknown as { db: Database.Database }).db;
  const target = ledger.entries().find((e) => e.seq === seq);
  if (!target) throw new Error(`no ledger entry with seq ${seq}`);
  const updated = { ...target, ...changes };
  const { hash: _oldHash, ...rest } = updated;
  const hash = opts.rehashSelf ? computeEntryHash(rest) : updated.hash;
  db.prepare('UPDATE ledger SET actor = ?, answer_hash = ?, action = ?, hash = ? WHERE seq = ?').run(
    updated.actor,
    updated.answerHash,
    updated.action,
    hash,
    seq,
  );
}
