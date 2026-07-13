/** A single question extracted from an uploaded questionnaire. */
export interface Question {
  /** Stable id within one questionnaire run (q1, q2, …). */
  id: string;
  /** The question text, trimmed. */
  text: string;
  /** Where it came from: row number (xlsx/csv) or line number (text). */
  sourceRef: string;
  /** Optional section/category header the question appeared under. */
  section?: string;
}

export interface ParsedQuestionnaire {
  questions: Question[];
  /** Raw rows/lines seen, for reporting ("Parsed 47 → deduped to 41"). */
  totalCandidates: number;
  /** Number of near-duplicate questions removed. */
  duplicatesRemoved: number;
  format: 'xlsx' | 'csv' | 'text';
}
