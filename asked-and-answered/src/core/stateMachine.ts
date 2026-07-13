/**
 * Guarded finite-state machine for the answer lifecycle.
 *
 * Inspired by Kept (kaviyakumar23/kept) and Relay-Crisis: every consequential
 * transition lists its source states, required actor type, and required
 * evidence. The pure decide() engine checks these rules before emitting any
 * event, so the LLM/model can *propose* but never *approve*.
 */

import type { DomainEvent } from './events.js';

export type ActorType = 'human' | 'agent' | 'system';

export type LifecycleState =
  | 'draft'
  | 'proposed'
  | 'confirmed'
  | 'approved'
  | 'rejected'
  | 'edited';

export interface Transition {
  eventType: DomainEvent['type'];
  from: LifecycleState[];
  to: LifecycleState;
  requiresHuman: boolean;
  requiresEvidence: boolean;
}

export const ANSWER_LIFECYCLE: Transition[] = [
  { eventType: 'DraftProduced', from: ['draft'], to: 'draft', requiresHuman: false, requiresEvidence: false },
  { eventType: 'AnswerProposed', from: ['draft'], to: 'proposed', requiresHuman: false, requiresEvidence: false },
  { eventType: 'AnswerConfirmed', from: ['draft', 'proposed', 'edited'], to: 'confirmed', requiresHuman: true, requiresEvidence: false },
  { eventType: 'AnswerApproved', from: ['confirmed'], to: 'approved', requiresHuman: true, requiresEvidence: true },
  { eventType: 'AnswerRejected', from: ['draft', 'proposed', 'confirmed', 'edited'], to: 'rejected', requiresHuman: true, requiresEvidence: false },
  { eventType: 'AnswerEdited', from: ['draft', 'proposed', 'confirmed', 'edited'], to: 'edited', requiresHuman: true, requiresEvidence: false },
];

export const HUMAN_GATES: DomainEvent['type'][] = ANSWER_LIFECYCLE
  .filter((t) => t.requiresHuman)
  .map((t) => t.eventType);

export function lifecycleState(events: DomainEvent[], questionText: string, questionId?: string): LifecycleState {
  const relevant = events.filter(
    (e) =>
      ('questionText' in e && e.questionText === questionText) ||
      ('questionId' in e && (e.questionId === questionText || (questionId && e.questionId === questionId))),
  );
  let state: LifecycleState = 'draft';
  for (const e of relevant) {
    const t = ANSWER_LIFECYCLE.find((x) => x.eventType === e.type);
    if (t && t.from.includes(state)) {
      state = t.to;
    }
  }
  return state;
}

export function canApplyTransition(
  events: DomainEvent[],
  eventType: DomainEvent['type'],
  actorType: ActorType,
  questionText: string,
  hasEvidence: boolean,
  questionId?: string,
): { ok: true } | { ok: false; error: string } {
  const transition = ANSWER_LIFECYCLE.find((t) => t.eventType === eventType);
  if (!transition) return { ok: true }; // events outside the answer lifecycle are unrestricted

  const current = lifecycleState(events, questionText, questionId);
  if (!transition.from.includes(current)) {
    return { ok: false, error: `${eventType} not allowed from state ${current}` };
  }
  if (transition.requiresHuman && actorType !== 'human') {
    return { ok: false, error: `${eventType} requires a human actor` };
  }
  if (transition.requiresEvidence && !hasEvidence) {
    return { ok: false, error: `${eventType} requires evidence` };
  }
  return { ok: true };
}
