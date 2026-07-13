/**
 * Offline smoke test — the full product loop with zero network:
 * parse → plan (fake RTS) → draft (fake LLM) → review actions → ledger → export.
 *
 * `npm run smoke` must end with SMOKE PASS. Run it before every deploy and
 * before recording any demo footage.
 */
import { strict as assert } from 'node:assert';
import { writeFileSync } from 'node:fs';
import { AnswerLibrary, type VisibilityChecker } from '../src/core/library.js';
import { Ledger } from '../src/core/ledger.js';
import { QueryPlanner, RateBudget, type RtsClient } from '../src/core/planner.js';
import { parseText } from '../src/core/parse.js';
import { exportXlsx } from '../src/core/export.js';
import type { DraftingLlm } from '../src/core/pipeline.js';
import { runQuestionnaire } from '../src/slack/flows.js';
import { planSummaryText } from '../src/slack/blocks.js';
import { tamperLedger } from '../tests/helpers/tamper.js';

const QUESTIONNAIRE = [
  '1. Do you encrypt customer data at rest?',
  '2. Is multi-factor authentication enforced for all employees?',
  '3. Do you carry cyber liability insurance?',
  '4. Do you encrypt customer data at rest?', // duplicate on purpose
].join('\n');

const EVIDENCE: Record<string, { permalink: string; snippet: string }> = {
  encrypt: { permalink: 'https://smoke.example/enc', snippet: 'we encrypt everything at rest with AES-256 via KMS' },
  authentication: { permalink: 'https://smoke.example/mfa', snippet: 'MFA/multi-factor authentication is enforced for employees through Okta' },
};

const rts: RtsClient = {
  async searchContext({ query }) {
    for (const [keyword, e] of Object.entries(EVIDENCE)) {
      if (query.includes(keyword)) {
        return { hits: [{ permalink: e.permalink, channelId: 'C_SMOKE', ts: '1.0', snippet: e.snippet }] };
      }
    }
    return { hits: [] };
  },
};

const llm: DraftingLlm = {
  async draft(question, hits) {
    const snippet = hits[0]?.snippet ?? '';
    return {
      kind: 'answer',
      answerText: `Yes — ${snippet} (${question.id}).`,
      citedPermalinks: [hits[0]?.permalink ?? ''],
    };
  },
};

const allVisible: VisibilityChecker = { canSee: async () => true };

const deps = {
  library: AnswerLibrary.inMemory(),
  ledger: Ledger.inMemory(),
  llm,
  visibility: allVisible,
  planner: new QueryPlanner(rts, {
    budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000 }),
    sleep: async () => {},
  }),
};

// ---- Run 1: fresh workspace ----
const parsed = parseText(QUESTIONNAIRE);
assert.equal(parsed.questions.length, 3, 'dedupe should collapse 4 → 3');

const run1 = await runQuestionnaire(parsed, 'U_REQ', deps, (m) => console.log(`  [progress] ${m}`));
console.log(planSummaryText(run1.counts));
assert.deepEqual(
  { grounded: run1.counts.grounded, needsSme: run1.counts.needsSme, verified: run1.counts.verified },
  { grounded: 2, needsSme: 1, verified: 0 },
  'run 1 states',
);

// Fail-closed check: the insurance question must be routed, not answered.
const insurance = run1.results.find((r) => r.questionText.includes('insurance'));
assert.equal(insurance?.state, 'needs_sme');
assert.equal(insurance?.answerText, undefined);

// ---- Review actions: two mandatory human gates ----
run1.confirm('q1', 'U_SME', run1.runId);
run1.approve('q1', 'U_REVIEWER', run1.runId);
run1.smeProvide(insurance?.questionId ?? '', 'U_SME', 'Yes, $5M coverage via Acme, renewed annually.', run1.runId);
run1.approve(insurance?.questionId ?? '', 'U_REVIEWER', run1.runId);
assert.equal(deps.ledger.entries().length, 4, 'four ledger entries after confirm+approve for both answers');

// ---- Run 2: compounding ----
const run2 = await runQuestionnaire(parseText(QUESTIONNAIRE), 'U_OTHER', deps, () => {});
assert.equal(run2.results.filter((r) => r.state === 'verified').length, 2, 'run 2 reuses both approvals');
console.log(`  Run 2: ${run2.counts.verified}/3 auto-verified (compounding works)`);

// ---- Ledger tamper theater ----
assert.equal(deps.ledger.verify().ok, true);
tamperLedger(deps.ledger, 0, { actor: 'U_ATTACKER' });
const verdict = deps.ledger.verify();
assert.equal(verdict.ok, false, 'tampering must be detected');
console.log(`  Tamper detected at ledger entry #${verdict.firstBadSeq} ✔`);

// ---- Export ----
const xlsx = await exportXlsx(run2.results);
const outPath = '/tmp/aa-smoke-export.xlsx';
writeFileSync(outPath, xlsx);
assert.ok(xlsx.length > 1000, 'xlsx export non-trivial');
console.log(`  Exported ${xlsx.length} bytes → ${outPath}`);

console.log('\nSMOKE PASS');
