/**
 * Slack Workflow Builder custom step.
 *
 * Exposes A&A's fail-closed questionnaire answering as a workflow step:
 * input a block of questions, output a structured result per question with
 * status (verified / grounded / needs_sme), answer text, and citations.
 *
 * Mirrors CornerCheck's workflow_step.py pattern: HALT on error so workflows
 * never silently proceed with an ungrounded compliance answer.
 */

import type { App } from '@slack/bolt';
import type { AnswerLibrary } from '../core/library.js';
import type { LedgerV2 } from '../core/ledgerV2.js';
import type { Ledger } from '../core/ledger.js';
import { QueryPlanner } from '../core/planner.js';
import { parseText } from '../core/parse.js';
import { runQuestionnaire } from './flows.js';
import type { RunDeps } from './flows.js';
import type { DraftingLlm } from '../core/pipeline.js';
import type { VisibilityChecker } from '../core/library.js';

export interface WorkflowStepContext {
  app: App;
  library: AnswerLibrary;
  ledger: Ledger;
  ledgerV2: LedgerV2;
  llm: DraftingLlm;
  visibility: VisibilityChecker;
  planner: QueryPlanner;
}

export function registerWorkflowStep(ctx: WorkflowStepContext): void {
  ctx.app.function('check_asked_answered', async ({ inputs, complete, fail, body }) => {
    const questions = (inputs as { questions?: string }).questions ?? '';
    const requesterId = body.user_id ?? 'workflow';

    if (!questions.trim()) {
      await fail({ error: 'questions input is required' });
      return;
    }

    try {
      const parsed = parseText(questions);
      if (parsed.questions.length === 0) {
        await fail({ error: 'no questions found in input' });
        return;
      }

      const deps: RunDeps = {
        library: ctx.library,
        ledger: ctx.ledger,
        ledgerV2: ctx.ledgerV2,
        llm: ctx.llm,
        visibility: ctx.visibility,
        planner: ctx.planner,
      };

      const session = await runQuestionnaire(parsed, requesterId, deps, () => {});

      const outputs = session.results.map((r) => ({
        question: r.questionText,
        status: r.state,
        answer: r.answerText ?? '',
        citations: (r.citations ?? []).map((c) => c.permalink),
        approvedBy: r.approvedBy ?? '',
      }));

      await complete({ outputs: { results: JSON.stringify(outputs) } });
    } catch (err) {
      await fail({ error: (err as Error).message });
    }
  });
}
