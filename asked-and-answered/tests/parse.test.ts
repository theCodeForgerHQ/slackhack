import { describe, test, expect } from 'vitest';
import ExcelJS from 'exceljs';
import { parseText, parseCsv, parseXlsx } from '../src/core/parse.js';

describe('parseText', () => {
  test('extracts numbered questions from pasted text', () => {
    const input = [
      '1. Do you encrypt data at rest?',
      '2. Do you have a SOC 2 Type II report?',
      '',
      '3) Where is customer data hosted?',
    ].join('\n');

    const result = parseText(input);

    expect(result.questions.map((q) => q.text)).toEqual([
      'Do you encrypt data at rest?',
      'Do you have a SOC 2 Type II report?',
      'Where is customer data hosted?',
    ]);
    expect(result.format).toBe('text');
    expect(result.questions[0]?.id).toBe('q1');
    expect(result.questions[0]?.sourceRef).toBe('line 1');
  });

  test('extracts bulleted and plain-line questions, skipping blanks and short noise', () => {
    const input = [
      '- Do you perform annual penetration tests?',
      '* Is MFA enforced for all employees?',
      'ok',
      '',
      'Describe your incident response process.',
    ].join('\n');

    const result = parseText(input);

    expect(result.questions.map((q) => q.text)).toEqual([
      'Do you perform annual penetration tests?',
      'Is MFA enforced for all employees?',
      'Describe your incident response process.',
    ]);
  });

  test('dedupes questions that differ only in case, whitespace, and trailing punctuation', () => {
    const input = [
      'Do you encrypt data at rest?',
      'do you  encrypt data at rest',
      'DO YOU ENCRYPT DATA AT REST?',
      'Do you encrypt data in transit?',
    ].join('\n');

    const result = parseText(input);

    expect(result.questions.map((q) => q.text)).toEqual([
      'Do you encrypt data at rest?',
      'Do you encrypt data in transit?',
    ]);
    expect(result.duplicatesRemoved).toBe(2);
    expect(result.totalCandidates).toBe(4);
  });
});

describe('parseCsv', () => {
  test('uses the column whose header contains "question"', () => {
    const csv = [
      'ID,Category,Question,Response',
      '1,Security,"Do you encrypt data at rest?",',
      '2,Security,"Is MFA enforced?",',
    ].join('\n');

    const result = parseCsv(csv);

    expect(result.questions.map((q) => q.text)).toEqual([
      'Do you encrypt data at rest?',
      'Is MFA enforced?',
    ]);
    expect(result.questions[0]?.sourceRef).toBe('row 2');
    expect(result.questions[0]?.section).toBe('Security');
  });

  test('falls back to the longest-text column when no header matches', () => {
    const csv = [
      'A,B',
      '1,"Do you have a documented data retention policy?"',
      '2,"Are backups tested at least quarterly?"',
    ].join('\n');

    const result = parseCsv(csv);

    expect(result.questions.map((q) => q.text)).toEqual([
      'Do you have a documented data retention policy?',
      'Are backups tested at least quarterly?',
    ]);
  });

  test('handles quoted fields containing commas and skips empty question cells', () => {
    const csv = [
      'Question,Answer',
      '"Do you support SSO, SAML, or OIDC?",',
      '"",',
      '"Where are your data centers located?",',
    ].join('\n');

    const result = parseCsv(csv);

    expect(result.questions.map((q) => q.text)).toEqual([
      'Do you support SSO, SAML, or OIDC?',
      'Where are your data centers located?',
    ]);
  });
});

describe('parseXlsx', () => {
  async function buildXlsx(rows: (string | null)[][]): Promise<Buffer> {
    const wb = new ExcelJS.Workbook();
    const ws = wb.addWorksheet('Sheet1');
    for (const row of rows) ws.addRow(row);
    return Buffer.from(await wb.xlsx.writeBuffer());
  }

  test('parses questions from an xlsx with a question header column', async () => {
    const buf = await buildXlsx([
      ['#', 'Question', 'Vendor Response'],
      ['1', 'Do you encrypt data at rest?', null],
      ['2', 'Do you run a bug bounty program?', null],
    ]);

    const result = await parseXlsx(buf);

    expect(result.questions.map((q) => q.text)).toEqual([
      'Do you encrypt data at rest?',
      'Do you run a bug bounty program?',
    ]);
    expect(result.format).toBe('xlsx');
    expect(result.questions[1]?.sourceRef).toBe('row 3');
  });

  test('skips empty rows and dedupes across rows', async () => {
    const buf = await buildXlsx([
      ['Question'],
      ['Do you encrypt data at rest?'],
      [null],
      ['Do you encrypt data at rest?  '],
      ['Is access reviewed quarterly?'],
    ]);

    const result = await parseXlsx(buf);

    expect(result.questions.map((q) => q.text)).toEqual([
      'Do you encrypt data at rest?',
      'Is access reviewed quarterly?',
    ]);
    expect(result.duplicatesRemoved).toBe(1);
  });
});
