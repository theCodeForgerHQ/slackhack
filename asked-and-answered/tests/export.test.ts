import { describe, test, expect } from 'vitest';
import ExcelJS from 'exceljs';
import { exportXlsx } from '../src/core/export.js';
import type { DraftResult } from '../src/core/pipeline.js';

const RESULTS: DraftResult[] = [
  {
    questionId: 'q1',
    questionText: 'Do you encrypt data at rest?',
    state: 'verified',
    answerText: 'Yes — AES-256 via cloud KMS.',
    citations: [{ permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' }],
    approvedBy: 'U_SME',
    approvedAt: '2026-07-11T10:00:00.000Z',
  },
  {
    questionId: 'q2',
    questionText: 'Are backups tested quarterly?',
    state: 'grounded',
    answerText: 'Yes, restore drills run quarterly.',
    citations: [
      { permalink: 'https://s.example/p2', channelId: 'C2', ts: '2.0' },
      { permalink: 'https://s.example/p3', channelId: 'C2', ts: '3.0' },
    ],
  },
  {
    questionId: 'q3',
    questionText: 'Do you carry cyber liability insurance?',
    state: 'needs_sme',
    reason: 'no_evidence',
  },
];

async function readBack(buf: Buffer): Promise<string[][]> {
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(buf as unknown as ArrayBuffer);
  const ws = wb.worksheets[0]!;
  const rows: string[][] = [];
  ws.eachRow((row) => {
    const values = row.values as (ExcelJS.CellValue | undefined)[];
    rows.push(values.slice(1).map((v) => (v === null || v === undefined ? '' : String(v))));
  });
  return rows;
}

describe('exportXlsx', () => {
  test('writes one row per question with state, answer, citations, and approval record', async () => {
    const buf = await exportXlsx(RESULTS);
    const rows = await readBack(buf);

    expect(rows[0]).toEqual([
      '#',
      'Question',
      'Status',
      'Answer',
      'Evidence (Slack permalinks)',
      'Approved by',
      'Approved at',
    ]);

    expect(rows[1]?.[1]).toBe('Do you encrypt data at rest?');
    expect(rows[1]?.[2]).toBe('Verified');
    expect(rows[1]?.[3]).toBe('Yes — AES-256 via cloud KMS.');
    expect(rows[1]?.[4]).toBe('https://s.example/p1');
    expect(rows[1]?.[5]).toBe('U_SME');

    expect(rows[2]?.[2]).toBe('Grounded');
    expect(rows[2]?.[4]).toBe('https://s.example/p2\nhttps://s.example/p3');

    expect(rows[3]?.[2]).toBe('Needs SME');
    expect(rows[3]?.[3]).toBe('');
    expect(rows[3]?.[4]).toBe('');
  });

  test('needs_sme rows never leak partial answers', async () => {
    const buf = await exportXlsx(RESULTS);
    const rows = await readBack(buf);
    const needsSmeRow = rows.find((r) => r[2] === 'Needs SME');
    expect(needsSmeRow?.[3]).toBe('');
    expect(needsSmeRow?.[5]).toBe('');
  });
});
