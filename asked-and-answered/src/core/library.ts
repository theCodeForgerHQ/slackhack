import Database from 'better-sqlite3';
import type { ConformalMatcher } from './conformal.js';
import type { EvidenceGraph } from './evidenceGraph.js';

/**
 * A pointer to evidence living in Slack. Zero-copy: we never store the
 * message/file content itself — only enough to re-locate and re-check it.
 */
export interface Citation {
  permalink: string;
  channelId: string;
  ts: string;
}

/**
 * Provenance of an approved answer:
 * - 'evidence': grounded in Slack citations (must have ≥1 citation)
 * - 'sme_testimony': typed by an SME with no workspace evidence — the
 *   approver IS the provenance, and the label says so honestly.
 */
export type AnswerKind = 'evidence' | 'sme_testimony';

export interface ApprovedAnswer {
  id: number;
  questionText: string;
  answerText: string;
  citations: Citation[];
  approvedBy: string;
  approvedAt: string;
  kind: AnswerKind;
}

export interface SaveApprovedInput {
  questionText: string;
  answerText: string;
  citations: Citation[];
  approvedBy: string;
  kind?: AnswerKind;
}

/**
 * Answers whether `userId` can currently see the Slack content behind a
 * citation. Production implementation checks channel membership /
 * conversations.info; tests inject a fake.
 */
export interface VisibilityChecker {
  canSee(userId: string, citation: Citation): Promise<boolean>;
}

export type LibraryLookup =
  | { status: 'verified'; answer: ApprovedAnswer }
  | { status: 'degraded'; questionText: string; blockedCitations: string[]; reason?: 'acl' | 'stale_evidence' }
  | { status: 'miss' };

const TOKEN_OVERLAP_THRESHOLD = 0.8;

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokens(text: string): Set<string> {
  return new Set(normalize(text).split(' ').filter(Boolean));
}

function jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 && b.size === 0) return 1;
  let intersection = 0;
  for (const t of a) if (b.has(t)) intersection++;
  return intersection / (a.size + b.size - intersection);
}

/**
 * The approved-answer library.
 *
 * THE INVARIANT (enforced here, property-tested): answer text is returned
 * to a requester only when that requester can currently see EVERY citation
 * backing the answer. Anything less degrades to a redacted result that
 * carries no answer content.
 */
export class AnswerLibrary {
  private constructor(
    private readonly db: Database.Database,
    private readonly graph?: EvidenceGraph,
    private readonly matcher?: ConformalMatcher,
  ) {
    this.db
      .prepare(
        `CREATE TABLE IF NOT EXISTS answers (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           question_text TEXT NOT NULL,
           question_norm TEXT NOT NULL,
           answer_text TEXT NOT NULL,
           citations_json TEXT NOT NULL,
           approved_by TEXT NOT NULL,
           approved_at TEXT NOT NULL,
           kind TEXT NOT NULL DEFAULT 'evidence'
         )`,
      )
      .run();
  }

  static inMemory(graph?: EvidenceGraph, matcher?: ConformalMatcher): AnswerLibrary {
    return new AnswerLibrary(new Database(':memory:'), graph, matcher);
  }

  static atPath(path: string, graph?: EvidenceGraph, matcher?: ConformalMatcher): AnswerLibrary {
    return new AnswerLibrary(new Database(path), graph, matcher);
  }

  saveApproved(input: SaveApprovedInput): ApprovedAnswer {
    const kind: AnswerKind = input.kind ?? 'evidence';
    if (kind === 'evidence' && input.citations.length === 0) {
      throw new Error(
        'evidence-kind answers require at least one citation — use kind "sme_testimony" for expert-typed answers',
      );
    }
    const approvedAt = new Date().toISOString();
    const info = this.db
      .prepare(
        `INSERT INTO answers (question_text, question_norm, answer_text, citations_json, approved_by, approved_at, kind)
         VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .run(
        input.questionText,
        normalize(input.questionText),
        input.answerText,
        JSON.stringify(input.citations),
        input.approvedBy,
        approvedAt,
        kind,
      );
    const answer: ApprovedAnswer = {
      id: Number(info.lastInsertRowid),
      questionText: input.questionText,
      answerText: input.answerText,
      citations: input.citations,
      approvedBy: input.approvedBy,
      approvedAt,
      kind,
    };

    this.indexInGraph(answer);
    return answer;
  }

  private indexInGraph(answer: ApprovedAnswer): void {
    if (!this.graph) return;

    const answerNodeId = `answer:${answer.id}`;
    this.graph.addAnswer({
      id: answerNodeId,
      kind: 'answer',
      answerId: answer.id,
      questionText: answer.questionText,
      answerText: answer.answerText,
    });

    for (const citation of answer.citations) {
      const evidenceId = `evidence:${citation.permalink}`;
      this.graph.addEvidence({
        id: evidenceId,
        kind: 'evidence',
        permalink: citation.permalink,
        channelId: citation.channelId,
        ts: citation.ts,
        snippet: '', // Snippet is not stored in the library; caller should backfill via observeEvidence.
        observedAt: answer.approvedAt,
      });
      this.graph.supports(evidenceId, answerNodeId);
    }

    // Extract simple sentence-level claims from the answer text.
    const sentences = answer.answerText
      .split(/[.!?]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 10);
    for (let i = 0; i < sentences.length; i++) {
      const claimId = `claim:answer-${answer.id}:${i}`;
      this.graph.addClaim({ id: claimId, kind: 'claim', text: sentences[i]!, sourceId: answerNodeId });
      this.graph.supports(answerNodeId, claimId);
    }
  }

  /**
   * Let the graph observe the actual snippet behind a citation. This enables
   * auto-contradiction detection when new evidence arrives.
   */
  observeEvidence(permalink: string, channelId: string, ts: string, snippet: string, observedAt = new Date().toISOString()): void {
    if (!this.graph) return;
    const id = `evidence:${permalink}`;
    const existing = this.graph.getNode(id);
    if (existing?.kind === 'evidence') {
      // Re-observing the same permalink updates the snippet in-place for
      // contradiction detection without mutating the node identity.
      (existing as { snippet: string }).snippet = snippet;
      (existing as { observedAt: string }).observedAt = observedAt;
    } else {
      this.graph.addEvidence({ id, kind: 'evidence', permalink, channelId, ts, snippet, observedAt });
    }
  }

  /**
   * Look up an approved answer for `questionText` on behalf of `requesterId`.
   * Every citation is re-checked against the requester at lookup time —
   * approval in the past never grants visibility in the present.
   */
  async findVerified(
    questionText: string,
    requesterId: string,
    checker: VisibilityChecker,
  ): Promise<LibraryLookup> {
    const match = this.bestMatch(questionText);
    if (!match) return { status: 'miss' };

    const blocked: string[] = [];
    for (const citation of match.citations) {
      const visible = await checker.canSee(requesterId, citation);
      if (!visible) blocked.push(citation.permalink);
    }

    if (blocked.length > 0) {
      // Deliberately reconstructed without any answer fields: the compiler
      // and the property suite both guard against answer text riding along.
      return { status: 'degraded', questionText: match.questionText, blockedCitations: blocked, reason: 'acl' };
    }

    if (this.graph?.isStale(match.id)) {
      const conflicting = this.graph
        .contradictionsForAnswer(match.id)
        .map((c) => c.conflictingEvidence.permalink);
      return {
        status: 'degraded',
        questionText: match.questionText,
        blockedCitations: conflicting,
        reason: 'stale_evidence',
      };
    }

    return { status: 'verified', answer: match };
  }

  /**
   * Keyword search over approved answers (for the MCP tools). Unlike
   * findVerified, callers of this API receive answers without per-user ACL
   * checks — it is exposed only through the workspace-admin-installed MCP
   * server, whose access is already workspace-scoped.
   */
  searchAnswers(query: string, limit = 5): ApprovedAnswer[] {
    const queryTokens = tokens(query);
    if (queryTokens.size === 0) return [];
    const scored: Array<{ answer: ApprovedAnswer; score: number }> = [];
    for (const answer of this.allAnswers()) {
      // Query coverage, not symmetric similarity: a one-word query should
      // match any stored question containing that word.
      const docTokens = tokens(answer.questionText + ' ' + answer.answerText);
      let covered = 0;
      for (const t of queryTokens) if (docTokens.has(t)) covered++;
      const score = covered / queryTokens.size;
      if (score >= 0.5) scored.push({ answer, score });
    }
    return scored
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
      .map((s) => s.answer);
  }

  getById(id: number): ApprovedAnswer | undefined {
    return this.allAnswers().find((a) => a.id === id);
  }

  /** Re-index every approved answer already in the database into the evidence graph. */
  rebuildGraph(): void {
    for (const answer of this.allAnswers()) {
      this.indexInGraph(answer);
    }
  }

  allAnswers(): ApprovedAnswer[] {
    const rows = this.db.prepare('SELECT * FROM answers').all() as Array<{
      id: number;
      question_text: string;
      question_norm: string;
      answer_text: string;
      citations_json: string;
      approved_by: string;
      approved_at: string;
      kind: string;
    }>;
    return rows.map((row) => ({
      id: row.id,
      questionText: row.question_text,
      answerText: row.answer_text,
      citations: JSON.parse(row.citations_json) as Citation[],
      approvedBy: row.approved_by,
      approvedAt: row.approved_at,
      kind: (row.kind === 'sme_testimony' ? 'sme_testimony' : 'evidence') as AnswerKind,
    }));
  }

  private bestMatch(questionText: string): ApprovedAnswer | undefined {
    const answers = this.allAnswers();
    if (answers.length === 0) return undefined;

    // Exact match bypasses all statistical reasoning.
    const exact = answers.find((a) => normalize(a.questionText) === normalize(questionText));
    if (exact) return exact;

    // Calibrated conformal matcher, if available.
    if (this.matcher?.isCalibrated) {
      return this.matcher.match(questionText, answers);
    }

    // Fallback to hand-tuned token overlap.
    const queryTokens = tokens(questionText);
    let best: { answer: ApprovedAnswer; score: number } | undefined;
    for (const answer of answers) {
      const score = jaccard(queryTokens, tokens(answer.questionText));
      if (score >= TOKEN_OVERLAP_THRESHOLD && (best === undefined || score > best.score)) {
        best = { answer, score };
      }
    }
    return best?.answer;
  }
}
