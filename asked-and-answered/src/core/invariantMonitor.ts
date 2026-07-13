/**
 * Runtime invariant monitor.
 *
 * This module checks the permission invariant directly on live DraftResult
 * objects produced by the actual TypeScript pipeline. It can be used in tests,
 * health checks, and (optionally) in production to guarantee that no answer
 * text is ever returned to a requester who cannot see all of its citations.
 */

import type { DraftResult } from './pipeline.js';
import type { VisibilityChecker, Citation } from './library.js';

export interface InvariantCheck {
  ok: boolean;
  violations: string[];
}

/**
 * Check the permission invariant for a single result.
 *
 * Invariant: if answer text is returned, every citation backing the answer
 * must be visible to the requester.
 */
export async function checkPermissionInvariant(
  result: DraftResult,
  requesterId: string,
  visibility: VisibilityChecker,
): Promise<InvariantCheck> {
  // No answer text => invariant holds vacuously.
  if (!result.answerText || result.answerText.trim().length === 0) {
    return { ok: true, violations: [] };
  }

  const citations = result.citations ?? [];
  if (citations.length === 0) {
    return { ok: false, violations: ['answer text returned with zero citations'] };
  }

  const violations: string[] = [];
  for (const citation of citations) {
    const visible = await visibility.canSee(requesterId, citation);
    if (!visible) {
      violations.push(`invisible citation ${citation.permalink}`);
    }
  }

  return { ok: violations.length === 0, violations };
}

/**
 * Check the invariant over a batch of results.
 */
export async function checkPermissionInvariantBatch(
  results: DraftResult[],
  requesterId: string,
  visibility: VisibilityChecker,
): Promise<{ ok: boolean; violations: Array<{ questionId: string; violations: string[] }> }> {
  const allViolations: Array<{ questionId: string; violations: string[] }> = [];
  for (const result of results) {
    const check = await checkPermissionInvariant(result, requesterId, visibility);
    if (!check.ok) {
      allViolations.push({ questionId: result.questionId, violations: check.violations });
    }
  }
  return { ok: allViolations.length === 0, violations: allViolations };
}
