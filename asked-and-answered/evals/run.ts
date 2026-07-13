/**
 * `npx tsx evals/run.ts` — runs the eval and prints a report table plus a
 * machine-readable JSON block for the README. Set AA_EVAL_LLM=anthropic
 * (with ANTHROPIC_API_KEY) to score with the real drafting model.
 */
import { runEval } from './harness.js';
import type { DraftingLlm } from '../src/core/pipeline.js';

let llm: DraftingLlm | undefined;
const evalProvider = process.env.AA_EVAL_LLM ?? 'fake';
if (evalProvider === 'anthropic') {
  const { AnthropicDrafter } = await import('../src/llm/anthropic.js');
  llm = new AnthropicDrafter();
} else if (evalProvider === 'openai' || evalProvider === 'azure') {
  const { OpenAiDrafter } = await import('../src/llm/openai.js');
  llm = new OpenAiDrafter(evalProvider);
}

const report = await runEval(llm);

console.log('\n=== Asked & Answered — Eval Report ===');
console.log(
  `LLM: ${evalProvider === 'anthropic' ? 'anthropic (real)' : evalProvider === 'openai' || evalProvider === 'azure' ? `${evalProvider} (real)` : 'faithful fake (deterministic)'}`,
);
console.log(`Cases: ${report.total} (dev ${report.dev.total}, held-out ${report.heldOut.total})\n`);
const row = (label: string, m: { hit: number; of: number; pct: number }) =>
  console.log(`  ${label.padEnd(26)} ${String(m.hit).padStart(2)}/${m.of}  (${m.pct}%)`);

console.log('Development set');
row('Grounded recall', report.dev.groundedRecall);
row('Fail-closed correctness', report.dev.failClosed);
row('Injection resistance', report.dev.injectionResistance);
row('Citation faithfulness', report.dev.citationFaithfulness);
row('Stale-evidence detection', report.dev.staleEvidence);

console.log('\nHeld-out set');
row('Grounded recall', report.heldOut.groundedRecall);
row('Fail-closed correctness', report.heldOut.failClosed);
row('Injection resistance', report.heldOut.injectionResistance);
row('Citation faithfulness', report.heldOut.citationFaithfulness);
row('Stale-evidence detection', report.heldOut.staleEvidence);

console.log('\nModel dependence');
row('Guard-only metrics', report.guardOnly);
row('Model-dependent metrics', report.modelDependent);

const failures = report.cases.filter((c) => !c.pass);
if (failures.length > 0) {
  console.log('\nFailures:');
  for (const f of failures) {
    console.log(`  ${f.id}: expected ${f.expected.kind} got ${f.gotState} ${f.gotReason ?? ''}`);
  }
}

console.log('\n```json');
console.log(
  JSON.stringify(
    {
      cases: report.total,
      dev: report.dev,
      heldOut: report.heldOut,
      guardOnly: report.guardOnly,
      modelDependent: report.modelDependent,
    },
    null,
    2,
  ),
);
console.log('```');

process.exit(failures.length === 0 ? 0 : 1);
