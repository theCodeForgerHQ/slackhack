import type { AnswerLibrary, ApprovedAnswer } from './library.js';
import type { Edge, EvidenceGraph, EvidenceNode } from './evidenceGraph.js';

export interface StaleAlertContradiction {
  /** The claim text extracted from the approved answer. */
  claimText: string;
  /** Newer workspace evidence that contradicts the claim. */
  evidence: EvidenceNode;
}

export interface StaleAlertSupersession {
  /** The original citation the approved answer relied on. */
  oldEvidence: EvidenceNode;
  /** Newer evidence that supersedes the original citation. */
  newEvidence: EvidenceNode;
}

export interface StaleAlert {
  answerId: number;
  questionText: string;
  answerText: string;
  approvedBy: string;
  approvedAt: string;
  detectedAt: string;
  contradictions: StaleAlertContradiction[];
  supersessions: StaleAlertSupersession[];
}

export interface WatcherOptions {
  /** Scan interval in milliseconds. Defaults to 1 hour. */
  intervalMs?: number;
  /** Called synchronously or asynchronously when a stale answer is found. */
  onStale?: (alert: StaleAlert) => void | Promise<void>;
  /** Injectable clock; defaults to `Date.now`. */
  now?: () => number;
}

/**
 * Proactive stale/contradiction watcher.
 *
 * Periodically scans the approved library and emits a `StaleAlert` whenever an
 * approved answer is contradicted by newer evidence or one of its citations is
 * superseded. Alerts are de-duplicated by answer id so repeated scans do not
 * spam the callback or the pending-alert buffer.
 */
export class Watcher {
  private timer: ReturnType<typeof setInterval> | undefined = undefined;
  private readonly pending = new Map<number, StaleAlert>();

  constructor(
    private readonly library: AnswerLibrary,
    private readonly graph: EvidenceGraph,
    private readonly opts: WatcherOptions = {},
  ) {}

  /** Start periodic scans. The first scan runs immediately. */
  start(): void {
    this.scan();
    const intervalMs = this.opts.intervalMs ?? 3_600_000;
    this.timer = setInterval(() => this.scan(), intervalMs);
  }

  /** Stop periodic scans. */
  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = undefined;
    }
  }

  /** All currently pending alerts, latest per answer id. */
  getPendingAlerts(): StaleAlert[] {
    return [...this.pending.values()];
  }

  /** Clear the pending-alert buffer. */
  clearPendingAlerts(): void {
    this.pending.clear();
  }

  /** Run a single scan immediately. */
  scan(): void {
    const detectedAt = new Date(this.opts.now ? this.opts.now() : Date.now()).toISOString();
    for (const answer of this.library.allAnswers()) {
      const contradictions = this.gatherContradictions(answer);
      const supersessions = this.gatherSupersessions(answer);
      if (contradictions.length === 0 && supersessions.length === 0) continue;

      const alert: StaleAlert = {
        answerId: answer.id,
        questionText: answer.questionText,
        answerText: answer.answerText,
        approvedBy: answer.approvedBy,
        approvedAt: answer.approvedAt,
        detectedAt,
        contradictions,
        supersessions,
      };
      const isNew = !this.pending.has(answer.id);
      this.pending.set(answer.id, alert);

      const cb = this.opts.onStale;
      if (cb && isNew) {
        try {
          const result = cb(alert);
          if (result && typeof result.then === 'function') {
            result.catch(() => {
              /* best-effort callback; do not crash the watcher */
            });
          }
        } catch {
          /* best-effort callback */
        }
      }
    }
  }

  private gatherContradictions(answer: ApprovedAnswer): StaleAlertContradiction[] {
    return this.graph
      .contradictionsForAnswer(answer.id)
      .map((c) => ({ claimText: c.claim.text, evidence: c.conflictingEvidence }));
  }

  private gatherSupersessions(answer: ApprovedAnswer): StaleAlertSupersession[] {
    const out: StaleAlertSupersession[] = [];
    for (const citation of answer.citations) {
      const oldId = `evidence:${citation.permalink}`;
      const oldNode = this.graph.getNode(oldId);
      if (oldNode?.kind !== 'evidence') continue;

      for (const edge of this.graph.edgesTo(oldId)) {
        if (edge.kind !== 'SUPERSEDES') continue;
        const newNode = this.graph.getNode(edge.from);
        if (newNode?.kind === 'evidence') {
          out.push({ oldEvidence: oldNode, newEvidence: newNode });
        }
      }
    }
    return out;
  }
}
