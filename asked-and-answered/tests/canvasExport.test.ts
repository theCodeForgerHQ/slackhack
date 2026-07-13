import { describe, test, expect } from 'vitest';
import { buildCanvasDocument, canvasToApiSections, canvasToMarkdown } from '../src/slack/canvasExport.js';
import type { DraftResult } from '../src/core/pipeline.js';

function result(overrides: Partial<DraftResult> & Pick<DraftResult, 'questionId' | 'state'>): DraftResult {
  return {
    questionText: `Question for ${overrides.questionId}`,
    ...overrides,
  } as DraftResult;
}

const MIXED: DraftResult[] = [
  result({
    questionId: 'q1',
    state: 'verified',
    answerText: 'Yes.',
    citations: [{ permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' }],
    approvedBy: 'U_SME',
    approvedAt: '2026-07-11T10:00:00.000Z',
  }),
  result({ questionId: 'q2', state: 'needs_sme', reason: 'no_evidence' }),
];

describe('buildCanvasDocument', () => {
  test('includes title, summary, every question, and invariant statement', () => {
    const doc = buildCanvasDocument(MIXED, { runId: 'run-abc', requesterId: 'U_REQ', title: 'Test Canvas' });

    expect(doc.title).toBe('Test Canvas');
    const headers = doc.sections.filter((s) => s.type === 'header').map((s) => s.text);
    expect(headers).toContain('Test Canvas');
    expect(headers).toContain('1. Question for q1');
    expect(headers).toContain('2. Question for q2');
    expect(headers).toContain('Invariant statement');

    const bullets = doc.sections.find((s) => s.type === 'bullets');
    expect(bullets?.items).toContain('Total questions: 2');
    expect(bullets?.items).toContain('Verified: 1');
    expect(bullets?.items).toContain('Needs SME: 1');
  });

  test('verified answer section carries citation and approval record', () => {
    const doc = buildCanvasDocument(MIXED, { runId: 'run-abc', requesterId: 'U_REQ' });
    const json = JSON.stringify(doc);

    expect(json).toContain('Verified');
    expect(json).toContain('Yes.');
    expect(json).toContain('https://s.example/p1');
    expect(json).toContain('U_SME');
  });

  test('needs_sme row explains the refusal without inventing an answer', () => {
    const doc = buildCanvasDocument(MIXED, { runId: 'run-abc', requesterId: 'U_REQ' });
    const q2Index = doc.sections.findIndex((s) => s.text === '2. Question for q2');
    const paragraph = doc.sections[q2Index + 2];
    expect(paragraph?.text).toMatch(/routed to a human|No sufficient workspace evidence/);
  });
});

describe('canvasToMarkdown', () => {
  test('produces a Markdown document with headers and bullets', () => {
    const doc = buildCanvasDocument(MIXED, { runId: 'run-abc', requesterId: 'U_REQ' });
    const md = canvasToMarkdown(doc);

    expect(md).toContain('# Questionnaire — Asked & Answered');
    expect(md).toContain('## 1. Question for q1');
    expect(md).toContain('- Total questions: 2');
    expect(md).toContain('https://s.example/p1');
  });
});

describe('canvasToApiSections', () => {
  test('converts sections to Slack Canvas API shaped objects', () => {
    const doc = buildCanvasDocument(MIXED, { runId: 'run-abc', requesterId: 'U_REQ' });
    const sections = canvasToApiSections(doc);

    expect(sections.length).toBe(doc.sections.length);
    expect(sections[0]).toMatchObject({ type: 'header' });
    expect(sections[1]).toMatchObject({ type: 'rich_text' });
  });
});
