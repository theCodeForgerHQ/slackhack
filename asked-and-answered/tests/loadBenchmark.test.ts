import { describe, test, expect } from 'vitest';
import { runLoadBenchmark, formatLoadReport } from '../evals/loadBenchmark.js';

describe('Load benchmark', () => {
  test('runs without errors and reports throughput', async () => {
    const result = await runLoadBenchmark({ runs: 20, questionsPerRun: 3 });
    expect(result.questions).toBe(60);
    expect(result.errors).toBe(0);
    expect(result.throughputQps).toBeGreaterThan(0);
    expect(result.p95Ms).toBeGreaterThanOrEqual(result.p50Ms);
    expect(formatLoadReport(result)).toContain('Throughput');
  });
});
