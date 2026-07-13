import type { Question } from './types.js';

/**
 * Thin abstraction over `assistant.search.context`. The production adapter
 * lives in src/slack/rts.ts; tests inject fakes. Zero-copy: snippets flow
 * through to drafting but are never persisted.
 */
export interface RtsHit {
  permalink: string;
  channelId: string;
  ts: string;
  snippet: string;
}

export interface RtsSearchParams {
  query: string;
  /** Bounded page size; RTS caps at 20. */
  limit?: number;
}

export interface RtsClient {
  searchContext(params: RtsSearchParams): Promise<{ hits: RtsHit[] }>;
}

export interface QuestionEvidence {
  questionId: string;
  hits: RtsHit[];
  searchFailed: boolean;
}

const STOPWORDS = new Set(
  ('a an and are as at be by can could did do does for from had has have how i if in is it its of on or ' +
    'our shall should that the their there these this those to was we were what when where which who will ' +
    'with would you your please describe provide detail details any all').split(' '),
);
const MAX_KEYWORDS = 8;
const OR_BATCH_SIZE = 5;

/**
 * Sliding-window rate budget. RTS allows ~10 requests/min per user and
 * pagination counts, so every call goes through this gate.
 */
export class RateBudget {
  private readonly stamps: number[] = [];

  constructor(
    private readonly opts: {
      maxPerWindow: number;
      windowMs: number;
      now?: () => number;
    },
  ) {}

  private now(): number {
    return this.opts.now ? this.opts.now() : Date.now();
  }

  /** Milliseconds until the next call is allowed (0 = go now). */
  nextDelayMs(): number {
    const now = this.now();
    const cutoff = now - this.opts.windowMs;
    while (this.stamps.length > 0 && (this.stamps[0] as number) <= cutoff) this.stamps.shift();
    if (this.stamps.length < this.opts.maxPerWindow) return 0;
    return (this.stamps[0] as number) + this.opts.windowMs - now;
  }

  record(): void {
    this.stamps.push(this.now());
  }
}

/** Salient-keyword query: RTS keyword mode has no synonym help, so keep terms literal. */
export function buildSearchQuery(questionText: string): string {
  const words = questionText
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 1 && !STOPWORDS.has(w));
  const unique: string[] = [];
  for (const w of words) if (!unique.includes(w)) unique.push(w);
  return unique.slice(0, MAX_KEYWORDS).join(' ');
}

function tokenSet(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length > 1 && !STOPWORDS.has(w)),
  );
}

function overlapScore(a: Set<string>, b: Set<string>): number {
  let n = 0;
  for (const t of a) if (b.has(t)) n++;
  return n;
}

export interface PlannerOptions {
  budget: RateBudget;
  /** Injectable for tests; production uses real setTimeout. */
  sleep: (ms: number) => Promise<void>;
}

export interface RetrieveOptions {
  strategy: 'per-question' | 'or-batch';
  limit?: number;
}

/**
 * The Query Planner: turns N questions into rate-budgeted RTS calls and
 * attributes every hit back to exactly one question.
 *
 * - `per-question` (primary): one call per question — slow but attribution
 *   is exact. 41 questions ≈ 5 minutes at the 10/min budget.
 * - `or-batch` (degraded): OR-joined batches of 5 — fast but attribution is
 *   recovered by token overlap and can misfile evidence. Used only when the
 *   budget cannot afford per-question.
 */
export class QueryPlanner {
  constructor(
    private readonly rts: RtsClient,
    private readonly opts: PlannerOptions,
  ) {}

  async retrieve(
    questions: Question[],
    options: RetrieveOptions,
  ): Promise<Map<string, QuestionEvidence>> {
    return options.strategy === 'per-question'
      ? this.retrievePerQuestion(questions, options)
      : this.retrieveOrBatch(questions, options);
  }

  private async gate(): Promise<void> {
    const delay = this.opts.budget.nextDelayMs();
    if (delay > 0) await this.opts.sleep(delay);
    this.opts.budget.record();
  }

  private async retrievePerQuestion(
    questions: Question[],
    options: RetrieveOptions,
  ): Promise<Map<string, QuestionEvidence>> {
    const out = new Map<string, QuestionEvidence>();
    for (const question of questions) {
      const query = buildSearchQuery(question.text);
      if (query.length === 0) {
        // All-stopword question: a degenerate empty query would search the
        // whole workspace for nothing. Skip the call; downstream treats
        // zero hits as no_evidence (fail-closed).
        out.set(question.id, { questionId: question.id, hits: [], searchFailed: false });
        continue;
      }
      await this.gate();
      const params: RtsSearchParams = { query };
      if (options.limit !== undefined) params.limit = options.limit;
      try {
        const { hits } = await this.rts.searchContext(params);
        out.set(question.id, { questionId: question.id, hits, searchFailed: false });
      } catch {
        out.set(question.id, { questionId: question.id, hits: [], searchFailed: true });
      }
    }
    return out;
  }

  private async retrieveOrBatch(
    questions: Question[],
    options: RetrieveOptions,
  ): Promise<Map<string, QuestionEvidence>> {
    const out = new Map<string, QuestionEvidence>(
      questions.map((question) => [
        question.id,
        { questionId: question.id, hits: [], searchFailed: false },
      ]),
    );

    for (let i = 0; i < questions.length; i += OR_BATCH_SIZE) {
      const batch = questions.slice(i, i + OR_BATCH_SIZE);
      const subQueries = batch
        .map((question) => buildSearchQuery(question.text))
        .filter((s) => s.length > 0);
      if (subQueries.length === 0) continue;
      await this.gate();
      const query = subQueries.join(' OR ');
      const params: RtsSearchParams = { query };
      if (options.limit !== undefined) params.limit = options.limit;
      try {
        const { hits } = await this.rts.searchContext(params);
        const batchTokens = batch.map((question) => ({
          id: question.id,
          tokens: tokenSet(question.text),
        }));
        for (const hit of hits) {
          const hitTokens = tokenSet(hit.snippet);
          let bestId: string | undefined;
          let bestScore = 0;
          for (const candidate of batchTokens) {
            const score = overlapScore(candidate.tokens, hitTokens);
            if (score > bestScore) {
              bestScore = score;
              bestId = candidate.id;
            }
          }
          // Zero-overlap hits are dropped: misfiled evidence is worse than
          // no evidence for a fail-closed pipeline.
          if (bestId !== undefined) out.get(bestId)?.hits.push(hit);
        }
      } catch {
        for (const question of batch) {
          const entry = out.get(question.id);
          if (entry) entry.searchFailed = true;
        }
      }
    }
    return out;
  }
}
