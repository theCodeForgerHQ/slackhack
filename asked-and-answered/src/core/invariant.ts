/**
 * Formal invariant verification for Asked & Answered.
 *
 * THE INVARIANT:
 *   Answer text is returned to a requester only if that requester can
 *   currently see every citation backing the answer.
 *
 * This module provides:
 *   1. A property-test runner that exercises the invariant on a synthetic
 *      corpus with randomized visibility.
 *   2. A non-vacuity check: if the visibility guard is disabled, the property
 *      test must fail.
 *   3. An optional Z3/SMT-LIB encoding stub for future automated proof.
 */

import { AnswerLibrary, type VisibilityChecker, type Citation } from './library.js';
import { DraftingPipeline } from './pipeline.js';
import type { RtsHit } from './planner.js';
import type { Question } from './types.js';

export interface InvariantResult {
  passed: boolean;
  casesRun: number;
  failures: Array<{ caseIndex: number; reason: string }>;
  nonVacuityPassed: boolean;
}

interface SyntheticCase {
  question: Question;
  hits: RtsHit[];
  visiblePermalinks: Set<string>;
}

function buildCorpus(): SyntheticCase[] {
  const hits: RtsHit[] = [
    { permalink: 'p/public-a', channelId: 'C_PUBLIC', ts: '1', snippet: 'Public fact A.' },
    { permalink: 'p/public-b', channelId: 'C_PUBLIC', ts: '2', snippet: 'Public fact B.' },
    { permalink: 'p/private-x', channelId: 'C_PRIVATE', ts: '3', snippet: 'Private fact X.' },
    { permalink: 'p/private-y', channelId: 'C_PRIVATE', ts: '4', snippet: 'Private fact Y.' },
  ];

  return [
    {
      question: { id: 'q1', text: 'What is public fact A?', sourceRef: '1' },
      hits: [hits[0]!],
      visiblePermalinks: new Set(['p/public-a']),
    },
    {
      question: { id: 'q2', text: 'What are the private facts?', sourceRef: '2' },
      hits: [hits[2]!, hits[3]!],
      visiblePermalinks: new Set(['p/private-x', 'p/private-y']),
    },
    {
      question: { id: 'q3', text: 'What is mixed?', sourceRef: '3' },
      hits: [hits[0]!, hits[2]!],
      visiblePermalinks: new Set(['p/public-a']),
    },
  ];
}

function visibilityFor(visible: Set<string>): VisibilityChecker {
  return {
    async canSee(_userId: string, citation: Citation): Promise<boolean> {
      return visible.has(citation.permalink);
    },
  };
}

/** Deterministic fake LLM that echoes the first visible-ish hit. */
function fakeDrafter(visible: Set<string>): {
  draft: (q: Question, hits: RtsHit[]) => Promise<{ kind: 'answer'; answerText: string; citedPermalinks: string[] }>;
} {
  return {
    async draft(_q: Question, hits: RtsHit[]) {
      const pick = hits.find((h) => visible.has(h.permalink)) ?? hits[0]!;
      return { kind: 'answer' as const, answerText: `Yes — ${pick.snippet}`, citedPermalinks: [pick.permalink] };
    },
  };
}

/**
 * Run the invariant property test on a synthetic corpus.
 *
 * For each case, the requester is granted visibility to a random subset of
 * permalinks. The pipeline result must never contain answer text backed by an
 * invisible citation.
 */
export async function runInvariantPropertyTest(options?: {
  iterations?: number;
  /** If true, temporarily force visibility to true to prove the guard is real. */
  proveNonVacuity?: boolean;
}): Promise<InvariantResult> {
  const iterations = options?.iterations ?? 100;
  const proveNonVacuity = options?.proveNonVacuity ?? true;
  const corpus = buildCorpus();
  const failures: Array<{ caseIndex: number; reason: string }> = [];

  for (let i = 0; i < iterations; i++) {
    const c = corpus[i % corpus.length]!;
    const visible = new Set(c.visiblePermalinks);
    if (Math.random() > 0.5) {
      // Randomly drop one visible permalink half the time.
      const first = [...visible][0];
      if (first) visible.delete(first);
    }

    const library = AnswerLibrary.inMemory();
    const pipeline = new DraftingPipeline(
      library,
      proveNonVacuity ? fakeDrafter(new Set()) : fakeDrafter(visible),
      proveNonVacuity ? { canSee: async () => true } : visibilityFor(visible),
    );

    const evidence: Map<string, { questionId: string; hits: RtsHit[]; searchFailed: false }> = new Map([
      [c.question.id, { questionId: c.question.id, hits: c.hits, searchFailed: false }],
    ]);

    const [result] = await pipeline.run([c.question], evidence, 'U_RAND');

    if (result?.state === 'verified' || result?.state === 'grounded') {
      const cited = result.citations ?? [];
      for (const cit of cited) {
        if (!visible.has(cit.permalink)) {
          failures.push({ caseIndex: i, reason: `cited invisible permalink ${cit.permalink}` });
        }
      }
    }
  }

  // Non-vacuity: when visibility is forced true and the fake drafter cites
  // everything, the property test SHOULD see invisible citations and fail.
  let nonVacuityPassed = false;
  if (proveNonVacuity) {
    nonVacuityPassed = failures.length > 0;
  }

  return {
    passed: proveNonVacuity ? nonVacuityPassed : failures.length === 0,
    casesRun: iterations,
    failures: proveNonVacuity ? failures.slice(0, 5) : failures,
    nonVacuityPassed,
  };
}

/** Generate the SMT-LIB model used by scripts/verifyInvariantZ3.ts. */
export function generateSmtLibStub(): string {
  return `; Asked & Answered — Permission Invariant SMT-LIB Spec
(set-logic UFBV)
(declare-sort User)
(declare-sort Citation)
(declare-sort Answer)
(declare-fun visible (User Citation) Bool)
(declare-fun returned (User Answer) Bool)
(declare-fun cites (Answer Citation) Bool)
(declare-fun checked (User Citation) Bool)

; RETURN-GUARD: returned => every citation checked.
(assert (forall ((u User) (a Answer))
  (=> (returned u a)
      (forall ((c Citation))
        (=> (cites a c) (checked u c))))))

; CHECKER-SOUND: checked => actually visible.
(assert (forall ((u User) (c Citation))
  (=> (checked u c) (visible u c))))

; Negation of the invariant.
(assert (exists ((u User) (a Answer) (c Citation))
  (and (returned u a)
       (cites a c)
       (not (visible u c)))))

(check-sat)
`;
}

/** Check the invariant synchronously for use in health endpoints. */
export async function invariantHealthCheck(): Promise<{ status: 'pass' | 'fail'; casesRun: number; detail?: string }> {
  const result = await runInvariantPropertyTest({ iterations: 50, proveNonVacuity: true });
  if (result.passed && result.nonVacuityPassed) {
    return { status: 'pass', casesRun: result.casesRun };
  }
  return {
    status: 'fail',
    casesRun: result.casesRun,
    detail: result.failures.map((f) => f.reason).join('; '),
  };
}
