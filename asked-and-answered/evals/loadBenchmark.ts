/**
 * Local, hermetic load benchmark for the drafting pipeline.
 *
 * Measures throughput and latency of the full parse → plan → draft → review
 * path without any external API calls. Uses in-memory fakes for RTS, LLM,
 * visibility, and library.
 */

import { AnswerLibrary } from '../src/core/library.js';
import { Ledger } from '../src/core/ledger.js';
import { QueryPlanner, RateBudget } from '../src/core/planner.js';
import { DraftingPipeline, type DraftingLlm } from '../src/core/pipeline.js';
import { parseText } from '../src/core/parse.js';
import type { Question } from '../src/core/types.js';
import type { RtsHit } from '../src/core/planner.js';

export interface LoadBenchmarkResult {
  questions: number;
  totalMs: number;
  throughputQps: number;
  avgMsPerQuestion: number;
  p50Ms: number;
  p95Ms: number;
  p99Ms: number;
  errors: number;
}

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  const idx = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[Math.max(0, idx)]!;
}

export interface LoadBenchmarkOptions {
  /** Number of questionnaires to run. */
  runs?: number;
  /** Questions per questionnaire. */
  questionsPerRun?: number;
}

const HITS: RtsHit[] = [
  { permalink: 'p/enc', channelId: 'C1', ts: '1', snippet: 'AES-256 encryption at rest' },
  { permalink: 'p/mfa', channelId: 'C1', ts: '2', snippet: 'MFA enforced via Okta' },
  { permalink: 'p/backup', channelId: 'C1', ts: '3', snippet: 'Quarterly backup restore drills' },
];

export async function runLoadBenchmark(options: LoadBenchmarkOptions = {}): Promise<LoadBenchmarkResult> {
  const runs = options.runs ?? 100;
  const questionsPerRun = options.questionsPerRun ?? 5;

  const rts = {
    async searchContext({ query }: { query: string }) {
      const hit = HITS.find((h) => h.snippet.toLowerCase().includes(query.toLowerCase().split(' ')[0] ?? ''));
      return { hits: hit ? [hit] : [] };
    },
  };

  const llm: DraftingLlm = {
    async draft(_q: Question, hits: RtsHit[]) {
      const h = hits[0] ?? HITS[0]!;
      return { kind: 'answer', answerText: `Yes — ${h.snippet}.`, citedPermalinks: [h.permalink] };
    },
  };

  const planner = new QueryPlanner(rts, {
    budget: new RateBudget({ maxPerWindow: 1_000_000, windowMs: 60_000 }),
    sleep: async () => {},
  });

  const latencies: number[] = [];
  let errors = 0;

  const start = performance.now();
  for (let r = 0; r < runs; r++) {
    const questions = Array.from({ length: questionsPerRun }, (_, i) => `Question ${i + 1}: Do we encrypt data at rest?`);
    const parsed = parseText(questions.join('\n'));
    const library = AnswerLibrary.inMemory();
    const pipeline = new DraftingPipeline(library, llm, { canSee: async () => true });

    const runStart = performance.now();
    try {
      const evidence = await planner.retrieve(parsed.questions, { strategy: 'per-question' });
      await pipeline.run(parsed.questions, evidence, 'U_BENCH');
      latencies.push(performance.now() - runStart);
    } catch {
      errors++;
    }
  }
  const totalMs = performance.now() - start;
  const totalQuestions = runs * questionsPerRun;
  const sorted = [...latencies].sort((a, b) => a - b);

  return {
    questions: totalQuestions,
    totalMs,
    throughputQps: totalQuestions / (totalMs / 1000),
    avgMsPerQuestion: latencies.length ? totalMs / totalQuestions : 0,
    p50Ms: percentile(sorted, 50),
    p95Ms: percentile(sorted, 95),
    p99Ms: percentile(sorted, 99),
    errors,
  };
}

export function formatLoadReport(r: LoadBenchmarkResult): string {
  return [
    '=== Local Load Benchmark ===',
    `Questions:       ${r.questions}`,
    `Total time:      ${r.totalMs.toFixed(1)} ms`,
    `Throughput:      ${r.throughputQps.toFixed(1)} questions/sec`,
    `Avg per question:${r.avgMsPerQuestion.toFixed(2)} ms`,
    `p50 latency:     ${r.p50Ms.toFixed(2)} ms`,
    `p95 latency:     ${r.p95Ms.toFixed(2)} ms`,
    `p99 latency:     ${r.p99Ms.toFixed(2)} ms`,
    `Errors:          ${r.errors}`,
  ].join('\n');
}
