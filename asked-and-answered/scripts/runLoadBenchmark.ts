import { runLoadBenchmark, formatLoadReport } from '../evals/loadBenchmark.js';

const report = await runLoadBenchmark({ runs: 100, questionsPerRun: 5 });
console.log(formatLoadReport(report));
