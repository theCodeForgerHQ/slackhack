/**
 * Split-conformal prediction for question-to-approved-answer matching.
 *
 * The old AnswerLibrary used a hand-tuned token-overlap threshold (0.8).
 * ConformalMatcher replaces it with a statistically calibrated threshold that
 * guarantees coverage at level 1 - α on the calibration distribution.
 *
 * Nonconformity score: 1 - token-Jaccard(query, candidate.questionText).
 * Prediction set: all candidates whose score <= q_hat.
 * Verified reuse: only when the prediction set is a singleton.
 */

import type { ApprovedAnswer } from './library.js';
import calibrationArtifact from './calibration.json' with { type: 'json' };

export interface CalibrationPair {
  query: string;
  candidate: string;
  /** True if query and candidate refer to the same question. */
  same: boolean;
}

export interface CalibrationArtifact {
  qHat: number;
  alpha: number;
  nCalibration: number;
  nHoldout: number;
  holdoutCoverage: number;
  falsePositiveRate: number;
  calibratedAt: string;
  note?: string;
}

export class ConformalMatcher {
  private calibratedQuantile: number | null = null;

  constructor(private readonly alpha = 0.1) {}

  /**
   * Load a committed calibration artifact (e.g. from scripts/calibrateConformal.ts).
   * Validates q_hat ∈ [0, 1] and α matches; disables the conformal gate on bad data.
   */
  loadArtifact(artifact: CalibrationArtifact): boolean {
    if (artifact.alpha !== this.alpha) return false;
    if (artifact.qHat < 0 || artifact.qHat > 1) return false;
    this.calibratedQuantile = artifact.qHat;
    return true;
  }

  /**
   * Calibrate on labeled question pairs. Follows split-conformal prediction:
   *   q_hat = ceil((n + 1) * (1 - α)) / n-th quantile of nonconformity scores
   *          among the positive (same) pairs.
   */
  calibrate(pairs: CalibrationPair[]): void {
    const samePairs = pairs.filter((p) => p.same);
    if (samePairs.length === 0) {
      this.calibratedQuantile = null;
      return;
    }

    const scores = samePairs.map((p) => nonconformity(p.query, p.candidate));
    scores.sort((a, b) => a - b);

    const n = scores.length;
    const k = Math.ceil((n + 1) * (1 - this.alpha));
    const idx = Math.min(k, n) - 1;
    this.calibratedQuantile = scores[Math.max(0, idx)] ?? 0;
  }

  /** Returns the singleton match, or undefined if the prediction set is empty or ambiguous. */
  match(query: string, candidates: ApprovedAnswer[]): ApprovedAnswer | undefined {
    if (this.calibratedQuantile === null) return undefined;
    const threshold = this.calibratedQuantile;

    const predictionSet: Array<{ answer: ApprovedAnswer; score: number }> = [];
    for (const answer of candidates) {
      const score = nonconformity(query, answer.questionText);
      if (score <= threshold) {
        predictionSet.push({ answer, score });
      }
    }

    if (predictionSet.length !== 1) return undefined;
    return predictionSet[0]!.answer;
  }

  /** True if the matcher has been calibrated. */
  get isCalibrated(): boolean {
    return this.calibratedQuantile !== null;
  }

  /** Exposed for tests and calibration reporting. */
  score(query: string, candidateQuestion: string): number {
    return nonconformity(query, candidateQuestion);
  }

  /** The calibrated quantile (undefined before calibration). */
  get qHat(): number | undefined {
    return this.calibratedQuantile ?? undefined;
  }
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokens(text: string): Set<string> {
  return new Set(normalize(text).split(' ').filter((t) => t.length > 2));
}

function jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 && b.size === 0) return 1;
  let intersection = 0;
  for (const t of a) if (b.has(t)) intersection++;
  return intersection / (a.size + b.size - intersection);
}

function nonconformity(query: string, candidate: string): number {
  return 1 - jaccard(tokens(query), tokens(candidate));
}
