import { describe, test, expect } from 'vitest';
import { JuryDrafter } from '../src/core/jury.js';
import type { DraftingLlm, LlmDraft } from '../src/core/pipeline.js';
import type { RtsHit } from '../src/core/planner.js';
import type { Question } from '../src/core/types.js';

const Q: Question = { id: 'q1', text: 'Do you encrypt data at rest?', sourceRef: '1' };

function hit(permalink: string, snippet: string): RtsHit {
  return { permalink, channelId: 'C1', ts: '1.0', snippet };
}

function constantDrafter(draft: LlmDraft): DraftingLlm {
  return { async draft() { return draft; } };
}

describe('JuryDrafter', () => {
  test('single drafter returns its draft', async () => {
    const jury = new JuryDrafter({
      drafters: [constantDrafter({ kind: 'answer', answerText: 'Yes.', citedPermalinks: ['p/enc'] })],
    });
    const result = await jury.draft(Q, [hit('p/enc', 'AES-256')]);
    expect(result.kind).toBe('answer');
    expect(result).toEqual({ kind: 'answer', answerText: 'Yes.', citedPermalinks: ['p/enc'] });
  });

  test('consensus across panelists returns the agreed answer with union of citations', async () => {
    const jury = new JuryDrafter({
      drafters: [
        constantDrafter({ kind: 'answer', answerText: 'Yes, AES-256.', citedPermalinks: ['p/enc'] }),
        constantDrafter({ kind: 'answer', answerText: 'Yes, AES-256.', citedPermalinks: ['p/enc'] }),
        constantDrafter({ kind: 'answer', answerText: 'Yes, AES-256.', citedPermalinks: ['p/backup'] }),
      ],
      labels: ['a', 'b', 'c'],
    });
    const result = await jury.draft(Q, [hit('p/enc', 'AES-256'), hit('p/backup', 'quarterly')]);
    expect(result.kind).toBe('answer');
    if (result.kind !== 'answer') return;
    expect(result.answerText).toBe('Yes, AES-256.');
    expect(result.citedPermalinks).toContain('p/enc');
    expect(result.citedPermalinks).toContain('p/backup');
  });

  test('disagreement on material facts leads to refusal', async () => {
    const jury = new JuryDrafter({
      drafters: [
        constantDrafter({ kind: 'answer', answerText: 'Yes, AES-256.', citedPermalinks: ['p/enc'] }),
        constantDrafter({ kind: 'answer', answerText: 'No, we do not.', citedPermalinks: ['p/enc'] }),
      ],
      labels: ['a', 'b'],
    });
    const result = await jury.draft(Q, [hit('p/enc', 'AES-256')]);
    expect(result.kind).toBe('refuse');
  });

  test('majority answer wins when one panelist dissents', async () => {
    const jury = new JuryDrafter({
      drafters: [
        constantDrafter({ kind: 'answer', answerText: 'Yes, AES-256.', citedPermalinks: ['p/enc'] }),
        constantDrafter({ kind: 'answer', answerText: 'Yes, AES-256.', citedPermalinks: ['p/enc'] }),
        constantDrafter({ kind: 'answer', answerText: 'Yes, we use KMS.', citedPermalinks: ['p/enc'] }),
      ],
    });
    const result = await jury.draft(Q, [hit('p/enc', 'AES-256')]);
    expect(result.kind).toBe('answer');
    if (result.kind !== 'answer') return;
    expect(result.answerText).toBe('Yes, AES-256.');
  });

  test('all panelists refuse → final is refusal', async () => {
    const jury = new JuryDrafter({
      drafters: [
        constantDrafter({ kind: 'refuse', reason: 'no evidence' }),
        constantDrafter({ kind: 'refuse', reason: 'insufficient' }),
      ],
    });
    const result = await jury.draft(Q, []);
    expect(result.kind).toBe('refuse');
  });

  test('telemetry captures every panelist call', async () => {
    const jury = new JuryDrafter({
      drafters: [
        constantDrafter({ kind: 'answer', answerText: 'Yes.', citedPermalinks: ['p/enc'] }),
        constantDrafter({ kind: 'answer', answerText: 'Yes.', citedPermalinks: ['p/enc'] }),
      ],
      labels: ['anthropic', 'openai'],
    });
    await jury.draft(Q, [hit('p/enc', 'AES-256')]);
    expect(jury.lastCallLog).toHaveLength(2);
    expect(jury.lastCallLog.map((c) => c.provider)).toEqual(['anthropic', 'openai']);
    expect(jury.lastCallLog.every((c) => c.latencyMs >= 0)).toBe(true);
  });

  test('LLM synthesizer overrides deterministic vote', async () => {
    const synthesizer: DraftingLlm = {
      async draft() {
        return { kind: 'answer', answerText: 'Synthesized.', citedPermalinks: ['p/enc'] };
      },
    };
    const jury = new JuryDrafter({
      drafters: [
        constantDrafter({ kind: 'answer', answerText: 'Yes, AES-256.', citedPermalinks: ['p/enc'] }),
        constantDrafter({ kind: 'answer', answerText: 'No.', citedPermalinks: ['p/enc'] }),
      ],
      synthesizer,
    });
    const result = await jury.draft(Q, [hit('p/enc', 'AES-256')]);
    expect(result.kind).toBe('answer');
    if (result.kind !== 'answer') return;
    expect(result.answerText).toBe('Synthesized.');
  });

  test('self-consistency: multiple synthesizer runs vote to stabilize output', async () => {
    let call = 0;
    const synthesizer: DraftingLlm = {
      async draft() {
        call++;
        // First two calls disagree; third agrees with first.
        return call <= 2
          ? { kind: 'answer', answerText: 'Alpha.', citedPermalinks: ['p/enc'] }
          : { kind: 'answer', answerText: 'Beta.', citedPermalinks: ['p/enc'] };
      },
    };
    const jury = new JuryDrafter({
      drafters: [constantDrafter({ kind: 'answer', answerText: 'Yes.', citedPermalinks: ['p/enc'] })],
      synthesizer,
      synthesizerRuns: 3,
    });
    const result = await jury.draft(Q, [hit('p/enc', 'AES-256')]);
    expect(result.kind).toBe('answer');
    if (result.kind !== 'answer') return;
    expect(result.answerText).toBe('Alpha.');
  });

  test('throws when constructed with zero drafters', () => {
    expect(() => new JuryDrafter({ drafters: [] })).toThrow('JuryDrafter requires at least one drafter');
  });
});
