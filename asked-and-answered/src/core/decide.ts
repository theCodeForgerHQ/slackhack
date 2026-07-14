import type { Citation } from './library.js';
import type { DomainEvent, AnswerApproved, AnswerConfirmed, AnswerEdited, AnswerProposed } from './events.js';
import { canApplyTransition, type ActorType } from './stateMachine.js';
import { DEFAULT_POLICY, type ApprovalPolicy, isFinalApproval } from './policy.js';

export interface DraftResultLike {
  questionId: string;
  questionText: string;
  state: 'verified' | 'grounded' | 'needs_sme';
  answerText?: string;
  citations?: Citation[];
  reason?: string;
}

export type Command =
  | { type: 'Approve'; questionId: string; actor: string; actorType: ActorType; result: DraftResultLike; answerId?: number; policy?: ApprovalPolicy }
  | { type: 'Confirm'; questionId: string; actor: string; actorType: ActorType; result: DraftResultLike; answerId?: number }
  | { type: 'Reject'; questionId: string; actor: string; actorType: ActorType; result: DraftResultLike }
  | { type: 'Edit'; questionId: string; actor: string; actorType: ActorType; newText: string; result: DraftResultLike; answerId?: number }
  | { type: 'SmeProvide'; questionId: string; actor: string; actorType: ActorType; answerText: string; result: DraftResultLike }
  | { type: 'Export'; runId: string; actor: string; actorType: ActorType }
  | { type: 'Propose'; answerId: number; questionText: string; answerText: string; citations: Citation[] };

export interface DecideResult {
  ok: boolean;
  events?: DomainEvent[];
  error?: string;
  /** For N-of-M policies: true only when enough distinct approvers have approved. */
  finalApproval?: boolean;
}

function now(): string {
  return new Date().toISOString();
}

function latestApproveEvent(events: DomainEvent[], questionId: string): AnswerApproved | undefined {
  return events
    .filter((e): e is AnswerApproved => e.type === 'AnswerApproved')
    .filter((e) => e.questionText === questionId)
    .at(-1);
}

function isRejected(events: DomainEvent[], questionId: string): boolean {
  return events.some(
    (e) => e.type === 'AnswerRejected' && e.questionId === questionId,
  );
}

function latestConfirmEvent(events: DomainEvent[], questionId: string, questionText: string): AnswerConfirmed | undefined {
  return events
    .filter((e): e is AnswerConfirmed => e.type === 'AnswerConfirmed')
    .filter((e) => e.questionId === questionId || e.questionId === questionText)
    .at(-1);
}

function isProposed(events: DomainEvent[], answerId: number): boolean {
  return events.some(
    (e) => e.type === 'AnswerProposed' && e.answerId === answerId,
  );
}

function isApproved(events: DomainEvent[], answerId: number): boolean {
  return events.some(
    (e) => e.type === 'AnswerApproved' && e.answerId === answerId,
  );
}

/**
 * Pure decision engine. Given the current event log and a command, returns the
 * events that should be appended if the command is valid, or an error if it
 * violates the lifecycle rules.
 *
 * Rules enforced:
 *   - Approve requires answer text and citations.
 *   - Re-approving the same answer is idempotent.
 *   - Agent proposals (AnswerProposed) must be approved by a human; the agent
 *     cannot emit AnswerApproved.
 *   - Editing is allowed before final approval or after an explicit edit event.
 *   - Rejecting a rejected question is idempotent.
 */
export function decide(events: DomainEvent[], command: Command): DecideResult {
  switch (command.type) {
    case 'Approve': {
      const { result, actor, actorType, questionId } = command;
      const policy = command.policy ?? DEFAULT_POLICY;
      if (result.state === 'verified') {
        return { ok: true, events: [], finalApproval: true };
      }
      if (!result.answerText) {
        return { ok: false, error: 'cannot approve a draft with no answer text' };
      }
      if (isRejected(events, questionId)) {
        return { ok: false, error: 'cannot approve a rejected question without re-proposing' };
      }
      const confirm = latestConfirmEvent(events, questionId, result.questionText);
      if (!confirm) {
        return { ok: false, error: 'answer must be confirmed before it can be approved' };
      }
      if (confirm.actor === actor) {
        return { ok: false, error: 'approver must be a different human than the confirmer' };
      }
      const previousApprovals = events.filter(
        (e): e is AnswerApproved => e.type === 'AnswerApproved' && e.questionText === result.questionText,
      );
      const previous = previousApprovals.at(-1);
      const answerId = previous ? previous.answerId : command.answerId ?? Date.now();
      const alreadyApprovedByActor = previousApprovals.some((e) => e.actor === actor);
      const transition = canApplyTransition(
        events,
        'AnswerApproved',
        actorType,
        result.questionText,
        (result.citations ?? []).length > 0 || !!result.answerText,
        questionId,
      );
      if (!transition.ok) return { ok: false, error: transition.error };
      const approvers = previousApprovals.map((e) => e.actor);
      if (!alreadyApprovedByActor) approvers.push(actor);
      const finalApproval = isFinalApproval(approvers, policy);
      if (alreadyApprovedByActor) {
        return { ok: true, events: [], finalApproval };
      }
      const ev: AnswerApproved = {
        type: 'AnswerApproved',
        answerId,
        questionText: result.questionText,
        answerText: result.answerText,
        citations: result.citations ?? [],
        actor,
        actorType: 'human',
        ts: now(),
      };
      return { ok: true, events: [ev], finalApproval };
    }

    case 'Confirm': {
      const { result, actor, actorType, questionId } = command;
      if (result.state === 'verified') {
        return { ok: true, events: [] };
      }
      if (!result.answerText) {
        return { ok: false, error: 'cannot confirm a draft with no answer text' };
      }
      if (isRejected(events, questionId)) {
        return { ok: false, error: 'cannot confirm a rejected question without re-proposing' };
      }
      const previous = latestConfirmEvent(events, questionId, result.questionText);
      const answerId = previous ? previous.answerId : command.answerId ?? Date.now();
      const transition = canApplyTransition(
        events,
        'AnswerConfirmed',
        actorType,
        result.questionText,
        false,
        questionId,
      );
      if (!transition.ok) return { ok: false, error: transition.error };
      const ev: AnswerConfirmed = {
        type: 'AnswerConfirmed',
        answerId: answerId ?? Date.now(),
        questionId,
        actor,
        actorType: 'human',
        ts: now(),
      };
      return { ok: true, events: [ev] };
    }

    case 'Reject': {
      const { questionId, actor, actorType } = command;
      if (isRejected(events, questionId)) {
        return { ok: true, events: [] };
      }
      const transition = canApplyTransition(events, 'AnswerRejected', actorType, questionId, false, questionId);
      if (!transition.ok) return { ok: false, error: transition.error };
      const ev: DomainEvent = {
        type: 'AnswerRejected',
        questionId,
        actor,
        actorType: 'human',
        ts: now(),
      };
      return { ok: true, events: [ev] };
    }

    case 'Edit': {
      const { newText, actor, actorType, result, questionId } = command;
      const previous = latestApproveEvent(events, result.questionText);
      const answerId = previous ? previous.answerId : command.answerId ?? Date.now();
      const transition = canApplyTransition(events, 'AnswerEdited', actorType, result.questionText, false, questionId);
      if (!transition.ok) return { ok: false, error: transition.error };
      const ev: AnswerEdited = {
        type: 'AnswerEdited',
        answerId,
        newText,
        actor,
        actorType: 'human',
        ts: now(),
      };
      return { ok: true, events: [ev] };
    }

    case 'SmeProvide': {
      const { answerText, actor, actorType, result, questionId } = command;
      const provideEv: DomainEvent = {
        type: 'DraftProduced',
        runId: 'sme',
        questionId,
        answerText,
        citations: [],
        ts: now(),
      };
      const confirm = decide([...events, provideEv], {
        type: 'Confirm',
        questionId,
        actor,
        actorType,
        result: { ...result, state: 'grounded', answerText, citations: [] },
      });
      if (!confirm.ok) return confirm;
      return { ok: true, events: [provideEv, ...(confirm.events ?? [])] };
    }

    case 'Export': {
      const { runId, actor, actorType } = command;
      return { ok: true, events: [{ type: 'Exported', runId, actor, actorType, ts: now() }] };
    }

    case 'Propose': {
      const { answerId, questionText, answerText, citations } = command;
      if (isProposed(events, answerId)) {
        return { ok: false, error: 'answer already proposed' };
      }
      if (isApproved(events, answerId)) {
        return { ok: false, error: 'answer already approved' };
      }
      const transition = canApplyTransition(events, 'AnswerProposed', 'agent', questionText, citations.length > 0, String(answerId));
      if (!transition.ok) return { ok: false, error: transition.error };
      const ev: AnswerProposed = {
        type: 'AnswerProposed',
        answerId,
        questionText,
        answerText,
        citations,
        actor: 'agent',
        actorType: 'agent',
        ts: now(),
      };
      return { ok: true, events: [ev] };
    }
  }
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const command = decide;
