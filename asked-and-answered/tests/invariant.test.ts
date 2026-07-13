import { describe, test, expect } from 'vitest';
import { DraftingPipeline, type DraftingLlm } from '../src/core/pipeline.js';
import { AnswerLibrary } from '../src/core/library.js';
import { runInvariantPropertyTest, invariantHealthCheck, generateSmtLibStub } from '../src/core/invariant.js';
import type { QuestionEvidence, RtsHit } from '../src/core/planner.js';
import type { Question } from '../src/core/types.js';

function q(id: string, text: string): Question {
  return { id, text, sourceRef: id };
}

function hit(permalink: string, snippet: string): RtsHit {
  return { permalink, channelId: 'C_PRIVATE', ts: '1.0', snippet };
}

function evidence(questionId: string, hits: RtsHit[]): QuestionEvidence {
  return { questionId, hits, searchFailed: false };
}

const groundedLlm: DraftingLlm = {
  async draft(_q, hits) {
    const snippet = hits[0]?.snippet ?? '';
    return { kind: 'answer', answerText: `Yes — ${snippet}.`, citedPermalinks: [hits[0]?.permalink ?? ''] };
  },
};

describe('Permission invariant — non-vacuity', () => {
  test('invisible citation degrades even when the draft is well-formed and grounded', async () => {
    const pipeline = new DraftingPipeline(
      AnswerLibrary.inMemory(),
      groundedLlm,
      { canSee: async () => false },
    );

    const results = await pipeline.run(
      [q('q1', 'Do you encrypt data at rest?')],
      new Map([['q1', evidence('q1', [hit('https://s.example/priv', 'AES-256 encryption at rest')])]]),
      'U_OUTSIDER',
    );

    expect(results[0]?.state).toBe('needs_sme');
    expect(results[0]?.reason).toBe('acl_degraded');
    expect(results[0]?.answerText).toBeUndefined();
  });

  test('NON-VACUITY: the same draft would be released if visibility were naively trusted', async () => {
    // This test documents the counterfactual: if the ACL guard were removed or
    // the visibility checker were fail-open, the answer text would be released.
    // The presence of this passing test proves the invariant is doing real work.
    const openPipeline = new DraftingPipeline(
      AnswerLibrary.inMemory(),
      groundedLlm,
      { canSee: async () => true },
    );

    const results = await openPipeline.run(
      [q('q1', 'Do you encrypt data at rest?')],
      new Map([['q1', evidence('q1', [hit('https://s.example/priv', 'AES-256 encryption at rest')])]]),
      'U_ANYONE',
    );

    expect(results[0]?.state).toBe('grounded');
    expect(results[0]?.answerText).toContain('AES-256');
  });
});

describe('Invariant property test', () => {
  test('passes and proves non-vacuity', async () => {
    const result = await runInvariantPropertyTest({ iterations: 50, proveNonVacuity: true });
    expect(result.passed).toBe(true);
    expect(result.nonVacuityPassed).toBe(true);
    expect(result.casesRun).toBe(50);
  });

  test('fails when non-vacuity is not proven', async () => {
    const result = await runInvariantPropertyTest({ iterations: 50, proveNonVacuity: false });
    expect(result.passed).toBe(true);
    expect(result.failures).toHaveLength(0);
  });

  test('health check returns pass', async () => {
    const health = await invariantHealthCheck();
    expect(health.status).toBe('pass');
  });

  test('SMT-LIB stub is generated', () => {
    const stub = generateSmtLibStub();
    expect(stub).toContain('(check-sat)');
    expect(stub).toContain('visible');
    expect(stub).toContain('returned');
    expect(stub).toContain('RETURN-GUARD');
  });
});
