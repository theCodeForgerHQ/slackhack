import ExcelJS from 'exceljs';
import type { DraftResult } from './pipeline.js';

const STATE_LABEL: Record<DraftResult['state'], string> = {
  verified: 'Verified',
  grounded: 'Grounded',
  needs_sme: 'Needs SME',
};

/**
 * Export the reviewed questionnaire as xlsx. Every answered row carries its
 * evidence permalinks and (for verified answers) the approval record;
 * needs_sme rows are deliberately blank — unanswered means unanswered.
 */
export async function exportXlsx(results: DraftResult[]): Promise<Buffer> {
  const wb = new ExcelJS.Workbook();
  wb.creator = 'Asked & Answered';
  const ws = wb.addWorksheet('Questionnaire');

  ws.addRow(['#', 'Question', 'Status', 'Answer', 'Evidence (Slack permalinks)', 'Approved by', 'Approved at']);
  ws.getRow(1).font = { bold: true };
  ws.columns = [
    { width: 6 },
    { width: 60 },
    { width: 12 },
    { width: 60 },
    { width: 50 },
    { width: 14 },
    { width: 24 },
  ];

  results.forEach((r, i) => {
    const answered = r.state !== 'needs_sme';
    ws.addRow([
      i + 1,
      r.questionText,
      STATE_LABEL[r.state],
      answered ? (r.answerText ?? '') : '',
      answered ? (r.citations ?? []).map((c) => c.permalink).join('\n') : '',
      answered ? (r.approvedBy ?? '') : '',
      answered ? (r.approvedAt ?? '') : '',
    ]);
  });

  return Buffer.from(await wb.xlsx.writeBuffer());
}
