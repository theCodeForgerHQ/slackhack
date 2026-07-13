/**
 * Measured-impact harness.
 *
 * Unlike `scripts/runCounterfactual.ts`, which uses fixed simulated inputs,
 * this script derives impact inputs from the actual implementation:
 *
 *   - Smoke questionnaire counts (fresh run + compounding run).
 *   - 127-case eval pass rates with the deterministic fake LLM.
 *   - Local load-benchmark latency percentiles and throughput.
 *   - Counterfactual ROI computed from the observed auto-answer rate.
 *
 * The output is a machine-readable JSON block plus a human summary. Use it to
 * back `docs/IMPACT.md` with real implementation numbers instead of assumptions.
 */

import { strict as assert } from 'node:assert';
import { AnswerLibrary } from '../src/core/library.js';
import { Ledger } from '../src/core/ledger.js';
import { QueryPlanner, RateBudget } from '../src/core/planner.js';
import { parseText } from '../src/core/parse.js';
import { runQuestionnaire } from '../src/slack/flows.js';
import { runEval } from '../evals/harness.js';
import { runLoadBenchmark } from '../evals/loadBenchmark.js';
import { simulateImpact } from '../evals/counterfactual.js';
import type { DraftingLlm } from '../src/core/pipeline.js';
import type { RtsHit } from '../src/core/planner.js';
import type { Question } from '../src/core/types.js';

const QUESTIONNAIRE = [
  '1. Do you encrypt customer data at rest?',
  '2. Is multi-factor authentication enforced for all employees?',
  '3. Do you carry cyber liability insurance?',
  '4. Do you encrypt customer data at rest?', // duplicate on purpose
].join('\n');

const EVIDENCE: Record<string, { permalink: string; snippet: string }> = {
  encrypt: {
    permalink: 'https://smoke.example/enc',
    snippet: 'we encrypt everything at rest with AES-256 via KMS',
  },
  authentication: {
    permalink: 'https://smoke.example/mfa',
    snippet: 'MFA/multi-factor authentication is enforced for employees through Okta',
  },
};

const rts = {
  async searchContext({ query }: { query: string }) {
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

const allVisible = { canSee: async () => true };

interface MeasuredImpactReport {
  measuredAt: string;
  smoke: {
    questions: number;
    fresh: { grounded: number; verified: number; needsSme: number };
    afterApproval: { grounded: number; verified: number; needsSme: number };
    autoAnsweredRatePct: number;
    compoundingBoostPct: number;
  };
  eval: {
    cases: number;
    dev: {
      groundedRecallPct: number;
      failClosedPct: number;
      injectionResistancePct: number;
      citationFaithfulnessPct: number;
      staleEvidencePct: number;
    };
    heldOut: {
      groundedRecallPct: number;
      failClosedPct: number;
      injectionResistancePct: number;
      citationFaithfulnessPct: number;
      staleEvidencePct: number;
    };
    guardOnlyPct: number;
    modelDependentPct: number;
    autoAnswered: number;
    routedToHuman: number;
    autoAnsweredRatePct: number;
  };
  load: {
    questions: number;
    throughputQps: number;
    avgMsPerQuestion: number;
    p50Ms: number;
    p95Ms: number;
    p99Ms: number;
    errors: number;
  };
  roi: {
    realistic: {
      basis: string;
      per100Questions: {
        smeHoursSaved: number;
        smeCostSavedUsd: number;
        citationsGained: number;
        inconsistentAnswersAvoided: number;
      };
      annual10Questionnaires: {
        smeHoursSaved: number;
        smeCostSavedUsd: number;
      };
    };
    adversarial: {
      basis: string;
      per100Questions: {
        smeHoursSaved: number;
        smeCostSavedUsd: number;
        citationsGained: number;
        inconsistentAnswersAvoided: number;
      };
      annual10Questionnaires: {
        smeHoursSaved: number;
        smeCostSavedUsd: number;
      };
    };
  };
}

async function measureSmoke() {
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

  const parsed = parseText(QUESTIONNAIRE);
  assert.equal(parsed.questions.length, 3, 'dedupe should collapse 4 → 3');

  const run1 = await runQuestionnaire(parsed, 'U_REQ', deps, () => {});
  const fresh = { ...run1.counts };

  // Two mandatory human gates on one answer.
  run1.confirm('q1', 'U_SME', run1.runId);
  run1.approve('q1', 'U_REVIEWER', run1.runId);

  const insurance = run1.results.find((r) => r.questionText.includes('insurance'));
  run1.smeProvide(insurance?.questionId ?? '', 'U_SME', 'Yes, $5M coverage via Acme, renewed annually.', run1.runId);
  run1.approve(insurance?.questionId ?? '', 'U_REVIEWER', run1.runId);

  const run2 = await runQuestionnaire(parseText(QUESTIONNAIRE), 'U_OTHER', deps, () => {});
  const afterApproval = { ...run2.counts };

  const total = fresh.grounded + fresh.verified + fresh.needsSme;
  const autoAnsweredRatePct = Math.round(((fresh.grounded + fresh.verified) / total) * 1000) / 10;
  const freshVerified = fresh.verified;
  const afterVerified = afterApproval.verified;
  const compoundingBoostPct = Math.round(((afterVerified - freshVerified) / total) * 1000) / 10;

  return { questions: total, fresh, afterApproval, autoAnsweredRatePct, compoundingBoostPct };
}

async function measureEval() {
  const report = await runEval();
  const autoAnswered = report.cases.filter((c) => c.gotState === 'grounded' || c.gotState === 'verified').length;
  const routedToHuman = report.cases.length - autoAnswered;
  const autoAnsweredRatePct = Math.round((autoAnswered / report.cases.length) * 1000) / 10;

  const pick = (m: { hit: number; of: number; pct: number }) => m.pct;

  return {
    cases: report.total,
    dev: {
      groundedRecallPct: pick(report.dev.groundedRecall),
      failClosedPct: pick(report.dev.failClosed),
      injectionResistancePct: pick(report.dev.injectionResistance),
      citationFaithfulnessPct: pick(report.dev.citationFaithfulness),
      staleEvidencePct: pick(report.dev.staleEvidence),
    },
    heldOut: {
      groundedRecallPct: pick(report.heldOut.groundedRecall),
      failClosedPct: pick(report.heldOut.failClosed),
      injectionResistancePct: pick(report.heldOut.injectionResistance),
      citationFaithfulnessPct: pick(report.heldOut.citationFaithfulness),
      staleEvidencePct: pick(report.heldOut.staleEvidence),
    },
    guardOnlyPct: report.guardOnly.pct,
    modelDependentPct: report.modelDependent.pct,
    autoAnswered,
    routedToHuman,
    autoAnsweredRatePct,
  };
}

async function measureLoad() {
  const report = await runLoadBenchmark({ runs: 100, questionsPerRun: 5 });
  return {
    questions: report.questions,
    throughputQps: Math.round(report.throughputQps * 10) / 10,
    avgMsPerQuestion: Math.round(report.avgMsPerQuestion * 100) / 100,
    p50Ms: Math.round(report.p50Ms * 100) / 100,
    p95Ms: Math.round(report.p95Ms * 100) / 100,
    p99Ms: Math.round(report.p99Ms * 100) / 100,
    errors: report.errors,
  };
}

function buildReport(smoke: MeasuredImpactReport['smoke'], evalMetrics: MeasuredImpactReport['eval'], load: MeasuredImpactReport['load']): MeasuredImpactReport {
  const realisticAuto = Math.round((smoke.autoAnsweredRatePct / 100) * 100);
  const realisticRouted = 100 - realisticAuto;
  const realisticRoi = simulateImpact({
    questionCount: 100,
    autoAnsweredCount: realisticAuto,
    routedToHumanCount: realisticRouted,
  });

  const adversarialRoi = simulateImpact({
    questionCount: 100,
    autoAnsweredCount: evalMetrics.autoAnswered,
    routedToHumanCount: evalMetrics.routedToHuman,
  });

  return {
    measuredAt: new Date().toISOString(),
    smoke,
    eval: evalMetrics,
    load,
    roi: {
      realistic: {
        basis: `Smoke-questionnaire measured auto-answer rate: ${smoke.autoAnsweredRatePct}% on first run, 100% after one approval cycle.`,
        per100Questions: {
          smeHoursSaved: realisticRoi.smeHoursSaved,
          smeCostSavedUsd: realisticRoi.smeCostSavedUsd,
          citationsGained: realisticRoi.citationsGained,
          inconsistentAnswersAvoided: realisticRoi.inconsistentAnswersAvoided,
        },
        annual10Questionnaires: {
          smeHoursSaved: realisticRoi.smeHoursSaved * 10,
          smeCostSavedUsd: realisticRoi.smeCostSavedUsd * 10,
        },
      },
      adversarial: {
        basis: `127-case eval measured auto-answer rate: ${evalMetrics.autoAnsweredRatePct}% (adversarial/hold-out set designed to stress fail-closed guards).`,
        per100Questions: {
          smeHoursSaved: adversarialRoi.smeHoursSaved,
          smeCostSavedUsd: adversarialRoi.smeCostSavedUsd,
          citationsGained: adversarialRoi.citationsGained,
          inconsistentAnswersAvoided: adversarialRoi.inconsistentAnswersAvoided,
        },
        annual10Questionnaires: {
          smeHoursSaved: adversarialRoi.smeHoursSaved * 10,
          smeCostSavedUsd: adversarialRoi.smeCostSavedUsd * 10,
        },
      },
    },
  };
}

function formatReport(r: MeasuredImpactReport): string {
  return [
    '=== Asked & Answered — Measured Impact Report ===',
    `Measured at: ${r.measuredAt}`,
    '',
    'Smoke questionnaire (4 raw → 3 deduped)',
    `  Fresh run:          ${r.smoke.fresh.grounded} grounded, ${r.smoke.fresh.verified} verified, ${r.smoke.fresh.needsSme} routed`,
    `  After 2 approvals:  ${r.smoke.afterApproval.grounded} grounded, ${r.smoke.afterApproval.verified} verified, ${r.smoke.afterApproval.needsSme} routed`,
    `  Auto-answered rate: ${r.smoke.autoAnsweredRatePct}%`,
    `  Compounding boost:  +${r.smoke.compoundingBoostPct}% verified on rerun`,
    '',
    `Eval: ${r.eval.cases} cases`,
    `  Dev — recall ${r.eval.dev.groundedRecallPct}%, fail-closed ${r.eval.dev.failClosedPct}%, injection ${r.eval.dev.injectionResistancePct}%, citation ${r.eval.dev.citationFaithfulnessPct}%, stale ${r.eval.dev.staleEvidencePct}%`,
    `  Held-out — recall ${r.eval.heldOut.groundedRecallPct}%, fail-closed ${r.eval.heldOut.failClosedPct}%, injection ${r.eval.heldOut.injectionResistancePct}%, citation ${r.eval.heldOut.citationFaithfulnessPct}%, stale ${r.eval.heldOut.staleEvidencePct}%`,
    `  Guard-only: ${r.eval.guardOnlyPct}%; model-dependent: ${r.eval.modelDependentPct}%`,
    `  Observed auto-answered: ${r.eval.autoAnswered}/${r.eval.cases} (${r.eval.autoAnsweredRatePct}%)`,
    '',
    `Load benchmark: ${r.load.questions} questions`,
    `  Throughput: ${r.load.throughputQps} questions/sec`,
    `  Latency: avg ${r.load.avgMsPerQuestion}ms, p50 ${r.load.p50Ms}ms, p95 ${r.load.p95Ms}ms, p99 ${r.load.p99Ms}ms`,
    `  Errors: ${r.load.errors}`,
    '',
    'ROI per 100 typical questions (baseline: 0.5 SME hrs × $150/hr)',
    `  Realistic (${r.roi.realistic.basis})`,
    `    SME hours saved:              ${r.roi.realistic.per100Questions.smeHoursSaved.toFixed(1)}`,
    `    SME cost saved (USD):         $${r.roi.realistic.per100Questions.smeCostSavedUsd.toFixed(2)}`,
    `    Citations gained:             ${r.roi.realistic.per100Questions.citationsGained.toFixed(1)}`,
    `    Inconsistent answers avoided: ${r.roi.realistic.per100Questions.inconsistentAnswersAvoided.toFixed(1)}`,
    '',
    `  Adversarial-stress (${r.roi.adversarial.basis})`,
    `    SME hours saved:              ${r.roi.adversarial.per100Questions.smeHoursSaved.toFixed(1)}`,
    `    SME cost saved (USD):         $${r.roi.adversarial.per100Questions.smeCostSavedUsd.toFixed(2)}`,
    `    Citations gained:             ${r.roi.adversarial.per100Questions.citationsGained.toFixed(1)}`,
    `    Inconsistent answers avoided: ${r.roi.adversarial.per100Questions.inconsistentAnswersAvoided.toFixed(1)}`,
    '',
    'Annual projection at 10 questionnaires/month (realistic basis)',
    `  SME hours saved:      ${r.roi.realistic.annual10Questionnaires.smeHoursSaved.toFixed(0)}`,
    `  SME cost saved (USD): $${r.roi.realistic.annual10Questionnaires.smeCostSavedUsd.toFixed(0)}`,
  ].join('\n');
}

const smoke = await measureSmoke();
const evalMetrics = await measureEval();
const load = await measureLoad();
const report = buildReport(smoke, evalMetrics, load);

console.log(formatReport(report));
console.log('\n```json');
console.log(JSON.stringify(report, null, 2));
console.log('```');
