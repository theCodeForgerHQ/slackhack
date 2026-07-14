/**
 * Real-LLM eval on a representative subset of the full dataset.
 *
 * Use this when the full 136-case run is too slow due to provider rate limits.
 * The subset preserves all categories: grounded recall, fail-closed, ACL
 * degradation, injection (refuse + grounded), citation faithfulness (fabricator),
 * stale evidence, and near-miss/scope carve-outs.
 */
import { runEval } from './harness.js';
import type { DraftingLlm } from '../src/core/pipeline.js';

const SUBSET = [
  // Grounded recall
  'g1', 'g5', 'g10', 'g15', 'g20', 'g25', 'g30', 'g34',
  // No visible evidence
  'n1', 'n5', 'n10', 'n15', 'n20',
  // ACL degradation
  'a1', 'a5', 'a10', 'a15',
  // Injection — must refuse / ACL block
  'i1', 'i2', 'i11', 'i12', 'i22', 'i27',
  // Injection — real evidence dominates
  'i5', 'i6', 'i13', 'i14', 'i15', 'i16', 'i25',
  // Citation faithfulness (fabricator LLM override)
  'c1', 'c3', 'c5', 'c7', 'c9',
  // Stale evidence
  's1', 's3', 's5', 's7',
  // Near-miss / scope
  'nm1', 'nm2', 'nm3', 'nm4',
];

let llm: DraftingLlm | undefined;
const evalProvider = process.env.AA_EVAL_LLM ?? 'fake';
if (evalProvider === 'anthropic') {
  const { AnthropicDrafter } = await import('../src/llm/anthropic.js');
  llm = new AnthropicDrafter();
} else if (evalProvider === 'openai' || evalProvider === 'azure') {
  const { OpenAiDrafter } = await import('../src/llm/openai.js');
  llm = new OpenAiDrafter(evalProvider);
}

const report = await runEval(llm, SUBSET);

console.log('\n=== Asked & Answered — Subset Eval Report ===');
console.log(`LLM: ${evalProvider === 'anthropic' ? 'anthropic (real)' : evalProvider === 'openai' || evalProvider === 'azure' ? `${evalProvider} (real)` : 'faithful fake (deterministic)'}`);
console.log(`Subset: ${SUBSET.length} cases`);
console.log(`  Grounded recall            ${report.dev.groundedRecall.hit}/${report.dev.groundedRecall.of}  (${report.dev.groundedRecall.pct}%)`);
console.log(`  Fail-closed correctness    ${report.dev.failClosed.hit}/${report.dev.failClosed.of}  (${report.dev.failClosed.pct}%)`);
console.log(`  Injection resistance       ${report.dev.injectionResistance.hit}/${report.dev.injectionResistance.of}  (${report.dev.injectionResistance.pct}%)`);
console.log(`  Citation faithfulness      ${report.dev.citationFaithfulness.hit}/${report.dev.citationFaithfulness.of}  (${report.dev.citationFaithfulness.pct}%)`);
console.log(`  Stale-evidence detection   ${report.dev.staleEvidence.hit}/${report.dev.staleEvidence.of}  (${report.dev.staleEvidence.pct}%)`);
console.log(`  Guard-only metrics         ${report.guardOnly.hit}/${report.guardOnly.of}  (${report.guardOnly.pct}%)`);
console.log(`  Model-dependent metrics    ${report.modelDependent.hit}/${report.modelDependent.of}  (${report.modelDependent.pct}%)`);

const failures = report.cases.filter((c) => !c.pass);
if (failures.length > 0) {
  console.log('\nFailures:');
  for (const f of failures) {
    console.log(`  ${f.id}: expected ${f.expected.kind} got ${f.gotState} ${f.gotReason ?? ''}`);
  }
}

console.log('\n```json');
console.log(JSON.stringify(report, null, 2));
console.log('```');

process.exit(failures.length === 0 ? 0 : 1);
