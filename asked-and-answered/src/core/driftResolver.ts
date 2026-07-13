/**
 * Deterministic drift resolver.
 *
 * Uses DecisionGraph to detect when newer workspace evidence contradicts an
 * approved answer. If a reversal is found, the answer is flagged for re-review
 * rather than silently returned as verified.
 */

import { DecisionGraph } from './decisionGraph.js';
import type { ApprovedAnswer } from './library.js';

export interface DriftCheck {
  drift: boolean;
  reason?: string;
  rows: Array<{ topic: string; currentValue: string; previousValue: string; permalink: string }>;
}

export function detectDrift(answer: ApprovedAnswer, hits: Array<{ permalink: string; channelId: string; ts: string; snippet: string }>): DriftCheck {
  const graph = new DecisionGraph();
  for (const h of hits) {
    graph.addEvidence(h.permalink, h.channelId, h.ts, h.snippet);
  }

  const rows = graph.resolve(answer.questionText);
  const reversed = rows.filter((r) => r.reversed);

  if (reversed.length > 0) {
    return {
      drift: true,
      reason: `Newer evidence reverses prior value${reversed.length > 1 ? 's' : ''}: ${reversed.map((r) => `${r.topic} changed from "${r.previousValue}" to "${r.currentValue}"`).join('; ')}`,
      rows: reversed.map((r) => ({ topic: r.topic, currentValue: r.currentValue, previousValue: r.previousValue ?? '', permalink: r.permalink })),
    };
  }

  return { drift: false, rows: [] };
}
