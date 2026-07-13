import ExcelJS from 'exceljs';
import type { ParsedQuestionnaire, Question } from './types.js';

const LIST_MARKER = /^\s*(?:\d+\s*[.)\]:-]|[-*•▪‣]|[a-z]\s*[.)])\s+/i;
const MIN_QUESTION_LENGTH = 12;
const QUESTION_HEADER = /question|prompt|inquiry|requirement|item/i;
const SECTION_HEADER = /category|section|domain|area|topic/i;

/** Normalization key used only for de-duplication, never for display. */
function dedupeKey(text: string): string {
  return text
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[?.!\s]+$/g, '')
    .trim();
}

function looksLikeQuestion(text: string): boolean {
  return text.includes('?') || text.length >= MIN_QUESTION_LENGTH;
}

interface Candidate {
  text: string;
  sourceRef: string;
  section?: string;
}

function toQuestionnaire(
  candidates: Candidate[],
  format: ParsedQuestionnaire['format'],
): ParsedQuestionnaire {
  const seen = new Set<string>();
  const questions: Question[] = [];
  let duplicatesRemoved = 0;

  for (const c of candidates) {
    const key = dedupeKey(c.text);
    if (seen.has(key)) {
      duplicatesRemoved++;
      continue;
    }
    seen.add(key);
    const q: Question = {
      id: `q${questions.length + 1}`,
      text: c.text,
      sourceRef: c.sourceRef,
    };
    if (c.section !== undefined) q.section = c.section;
    questions.push(q);
  }

  return { questions, totalCandidates: candidates.length, duplicatesRemoved, format };
}

export function parseText(input: string): ParsedQuestionnaire {
  const candidates: Candidate[] = [];
  const lines = input.split(/\r?\n/);

  lines.forEach((raw, i) => {
    const stripped = raw.replace(LIST_MARKER, '').trim();
    if (!stripped || !looksLikeQuestion(stripped)) return;
    candidates.push({ text: stripped, sourceRef: `line ${i + 1}` });
  });

  return toQuestionnaire(candidates, 'text');
}

/** Minimal RFC-4180-ish CSV row splitter (handles quoted fields with commas). */
function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let cur = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"') {
        if (line[i + 1] === '"') {
          cur += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        cur += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      cells.push(cur);
      cur = '';
    } else {
      cur += ch;
    }
  }
  cells.push(cur);
  return cells.map((c) => c.trim());
}

/**
 * Shared table → questionnaire logic for CSV and XLSX.
 * Row refs are 1-based and include the header row, matching what a user
 * sees in their spreadsheet app.
 */
function fromTable(
  rows: string[][],
  format: ParsedQuestionnaire['format'],
): ParsedQuestionnaire {
  if (rows.length === 0) return toQuestionnaire([], format);

  const header = rows[0] ?? [];
  let questionCol = header.findIndex((h) => QUESTION_HEADER.test(h));
  const sectionCol = header.findIndex((h) => SECTION_HEADER.test(h));
  let dataStart = 1;

  if (questionCol === -1) {
    // No recognizable header: treat every row as data and pick the column
    // with the longest average text — questionnaires bury questions in prose.
    dataStart = 0;
    const width = Math.max(...rows.map((r) => r.length));
    let bestAvg = -1;
    for (let col = 0; col < width; col++) {
      const lengths = rows.map((r) => (r[col] ?? '').length);
      const avg = lengths.reduce((a, b) => a + b, 0) / rows.length;
      if (avg > bestAvg) {
        bestAvg = avg;
        questionCol = col;
      }
    }
  }

  const candidates: Candidate[] = [];
  for (let i = dataStart; i < rows.length; i++) {
    const row = rows[i] ?? [];
    const text = (row[questionCol] ?? '').trim();
    if (!text || !looksLikeQuestion(text)) continue;
    const candidate: Candidate = { text, sourceRef: `row ${i + 1}` };
    const section = sectionCol >= 0 ? (row[sectionCol] ?? '').trim() : '';
    if (section) candidate.section = section;
    candidates.push(candidate);
  }

  return toQuestionnaire(candidates, format);
}

export function parseCsv(input: string): ParsedQuestionnaire {
  const rows = input
    .split(/\r?\n/)
    .filter((line) => line.trim().length > 0)
    .map(splitCsvLine);
  return fromTable(rows, 'csv');
}

export async function parseXlsx(buffer: Buffer): Promise<ParsedQuestionnaire> {
  const wb = new ExcelJS.Workbook();
  await wb.xlsx.load(buffer as unknown as ArrayBuffer);
  const ws = wb.worksheets[0];
  if (!ws) return toQuestionnaire([], 'xlsx');

  const rows: string[][] = [];
  ws.eachRow({ includeEmpty: true }, (row) => {
    const cells: string[] = [];
    // row.values is 1-based; index 0 is unused.
    const values = row.values as (ExcelJS.CellValue | undefined)[];
    for (let c = 1; c < values.length; c++) {
      const v = values[c];
      cells.push(v === null || v === undefined ? '' : String(v).trim());
    }
    rows.push(cells);
  });

  // Drop fully-empty rows but keep original spreadsheet row numbers by
  // tagging refs before filtering.
  const tagged = rows
    .map((cells, i) => ({ cells, rowNum: i + 1 }))
    .filter(({ cells }) => cells.some((c) => c.length > 0));

  // fromTable computes refs from array position; rebuild with real row numbers.
  const result = fromTable(tagged.map((t) => t.cells), 'xlsx');
  const refMap = new Map<number, number>();
  tagged.forEach((t, i) => refMap.set(i + 1, t.rowNum));
  for (const q of result.questions) {
    const pos = Number(q.sourceRef.replace('row ', ''));
    const real = refMap.get(pos);
    if (real !== undefined) q.sourceRef = `row ${real}`;
  }
  return result;
}
