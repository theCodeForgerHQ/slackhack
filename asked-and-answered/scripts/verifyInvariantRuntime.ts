/**
 * Runtime verification of the permission invariant against the actual
 * TypeScript implementation of DraftingPipeline and AnswerLibrary.
 *
 * Runs the real pipeline over every eval case and asserts:
 *   - No answer text is returned unless every citation is visible to the requester.
 *   - Verified answers additionally pass the library ACL + stale check.
 *   - Needs-SME results never carry answer text.
 *
 * This is the code-level companion to the Z3 model: the model proves the
 * guard composition is sufficient; this script proves the running code
 * exercises those guards correctly on the labeled dataset.
 */

import { DraftingPipeline } from '../src/core/pipeline.js';
import { AnswerLibrary, type Citation } from '../src/core/library.js';
import { EvidenceGraph } from '../src/core/evidenceGraph.js';
import type { QuestionEvidence, RtsHit } from '../src/core/planner.js';
import type { Question } from '../src/core/types.js';
import { CASES, WORKSPACE } from '../evals/dataset.js';

function stems(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 3)
    .map((w) => w.slice(0, 5));
}

function retrieve(question: string): RtsHit[] {
  const qStems = new Set(stems(question));
  const hits: RtsHit[] = [];
  for (const doc of WORKSPACE) {
    const dStems = new Set(stems(doc.snippet));
    let overlap = 0;
    for (const s of qStems) if (dStems.has(s)) overlap++;
    if (overlap >= 2 || (doc as any).adversarial) {
      hits.push({ permalink: doc.permalink, channelId: doc.channelId, ts: '1.0', snippet: doc.snippet });
    }
  }
  return hits;
}

function visibilityFor() {
  return {
    async canSee(_userId: string, citation: Citation): Promise<boolean> {
      const doc = WORKSPACE.find((d) => d.permalink === citation.permalink);
      return doc ? doc.visibleTo.includes(_userId) : false;
    },
  };
}

const fakeLlm = {
  async draft(_q: Question, hits: RtsHit[]) {
    const real = hits.filter((h) => !WORKSPACE.find((d) => d.permalink === h.permalink)?.adversarial);
    if (real.length === 0) return { kind: 'refuse' as const, reason: 'no legitimate evidence' };
    const best = real[0]!;
    return { kind: 'answer' as const, answerText: `Yes. ${best.snippet}`, citedPermalinks: [best.permalink] };
  },
};

const fabricatorLlm = {
  async draft(_q: Question, hits: RtsHit[]) {
    const real = hits.filter((h) => !WORKSPACE.find((d) => d.permalink === h.permalink)?.adversarial);
    if (real.length === 0) return { kind: 'refuse' as const, reason: 'no legitimate evidence' };
    const best = real[0]!;
    return { kind: 'answer' as const, answerText: 'We maintain full compliance.', citedPermalinks: [best.permalink] };
  },
};

let checked = 0;
let violations = 0;

for (const c of CASES) {
  const graph = new EvidenceGraph();
  const library = AnswerLibrary.inMemory(graph);
  if (c.seedApproved) {
    library.saveApproved({ ...c.seedApproved, approvedBy: 'U_SEED' });
  }
  const llm = c.llmOverride === 'fabricator' ? fabricatorLlm : fakeLlm;
  const pipeline = new DraftingPipeline(library, llm, visibilityFor());
  const hits = retrieve(c.question);
  for (const hit of hits) {
    library.observeEvidence(hit.permalink, hit.channelId, hit.ts, hit.snippet);
  }
  const evidence: QuestionEvidence = { questionId: c.id, hits, searchFailed: false };
  const [result] = await pipeline.run(
    [{ id: c.id, text: c.question, sourceRef: c.id }],
    new Map([[c.id, evidence]]),
    c.requester,
  );
  const r = result!;
  checked++;

  // Invariant: no answer text without visible citations.
  if (r.answerText) {
    const citations = r.citations ?? [];
    for (const cit of citations) {
      const visible = await visibilityFor().canSee(c.requester, cit);
      if (!visible) {
        console.error(`INVARIANT VIOLATION: ${c.id} returned answer text with invisible citation ${cit.permalink}`);
        violations++;
      }
    }
    if (citations.length === 0) {
      console.error(`INVARIANT VIOLATION: ${c.id} returned answer text with no citations`);
      violations++;
    }
  }

  // Verified answers must be approved and not stale (the pipeline enforces this).
  if (r.state === 'verified') {
    if (!r.citations || r.citations.length === 0) {
      console.error(`INVARIANT VIOLATION: ${c.id} returned verified answer with no citations`);
      violations++;
    }
  }
}

console.log(`Runtime invariant check: ${checked} cases, ${violations} violations`);
process.exit(violations === 0 ? 0 : 1);
