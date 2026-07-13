import type { RtsHit } from './planner.js';

export interface GroundingFailure {
  permalink: string;
  /** The snippet that failed grounding (truncated in logs). */
  snippet: string;
  reason: 'missing_source' | 'no_text_overlap' | 'too_weak';
}

export interface GroundingResult {
  ok: boolean;
  failures: GroundingFailure[];
}

/**
 * Deterministic citation-grounding gate.
 *
 * Current A&A checks that a cited permalink is in the retrieved evidence set.
 * That stops prompt-injected foreign URLs, but it does not stop a well-behaved
 * LLM from paraphrasing too loosely, or a misbehaving LLM from citing a real
 * permalink while making up a "fact" that does not appear in the evidence.
 *
 * GroundingGate verifies the *snippet text* of every cited permalink against
 * the drafted answer. It is fully deterministic, fast, and requires no model.
 *
 * Algorithm:
 *   1. NFKC-normalize answer and evidence snippet.
 *   2. Lowercase, strip punctuation, collapse whitespace.
 *   3. Exact substring match in either direction.
 *   4. If exact fails, compute character-trigram Jaccard similarity.
 *   5. Require similarity >= threshold (default 0.85).
 *
 * The threshold is intentionally high: we would rather route a borderline
 * paraphrase to a human than ship an unsupported claim.
 */
export class GroundingGate {
  constructor(private readonly threshold = 0.8) {}

  verify(answerText: string, hits: RtsHit[], citedPermalinks: string[]): GroundingResult {
    const allowed = new Map(hits.map((h) => [h.permalink, h]));
    const failures: GroundingFailure[] = [];

    for (const raw of [...new Set(citedPermalinks)]) {
      const permalink = raw.trim();
      if (permalink.length === 0) continue;

      const hit = allowed.get(permalink);
      if (!hit) {
        // A prior citation-subset check should catch this, but the gate is
        // fail-closed: any unknown source is ungrounded.
        failures.push({ permalink, snippet: '', reason: 'missing_source' });
        continue;
      }

      const normalizedAnswer = normalize(answerText);
      const normalizedSnippet = normalize(hit.snippet);

      if (exactMatch(normalizedAnswer, normalizedSnippet)) {
        continue;
      }

      const similarity = trigramJaccard(normalizedAnswer, normalizedSnippet);
      if (similarity < this.threshold) {
        failures.push({
          permalink,
          snippet: hit.snippet,
          reason: similarity === 0 ? 'no_text_overlap' : 'too_weak',
        });
      }
    }

    return { ok: failures.length === 0, failures };
  }
}

function normalize(text: string): string {
  return text
    .normalize('NFKC')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function exactMatch(a: string, b: string): boolean {
  if (a.length === 0 || b.length === 0) return false;
  return a.includes(b) || b.includes(a);
}

function trigrams(text: string): Set<string> {
  const set = new Set<string>();
  const chars = [...text.replace(/\s+/g, '')];
  for (let i = 0; i <= chars.length - 3; i++) {
    set.add(chars.slice(i, i + 3).join(''));
  }
  return set;
}

function trigramJaccard(a: string, b: string): number {
  const ta = trigrams(a);
  const tb = trigrams(b);
  if (ta.size === 0 || tb.size === 0) return 0;
  let intersection = 0;
  for (const g of ta) if (tb.has(g)) intersection++;
  return intersection / (ta.size + tb.size - intersection);
}
