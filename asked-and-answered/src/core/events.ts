import type { Citation } from './library.js';
import type { RtsHit } from './planner.js';
import type { Question } from './types.js';
import type { ActorType } from './stateMachine.js';

/**
 * Event-sourced domain events for the Asked & Answered lifecycle.
 *
 * Every human decision and every agent proposal is captured as an immutable
 * event. The pure `decide()` function in decide.ts validates commands against
 * the current event log and emits zero or more events.
 */

export interface QuestionnaireIntaken {
  type: 'QuestionnaireIntaken';
  runId: string;
  questions: Question[];
  requesterId: string;
  ts: string;
}

export interface EvidenceRetrieved {
  type: 'EvidenceRetrieved';
  runId: string;
  questionId: string;
  hits: RtsHit[];
  ts: string;
}

export interface DraftProduced {
  type: 'DraftProduced';
  runId: string;
  questionId: string;
  answerText: string;
  citations: Citation[];
  ts: string;
}

export interface CitationValidated {
  type: 'CitationValidated';
  runId: string;
  questionId: string;
  valid: boolean;
  ts: string;
}

export interface VisibilityChecked {
  type: 'VisibilityChecked';
  runId: string;
  questionId: string;
  visible: boolean;
  ts: string;
}

export interface AnswerApproved {
  type: 'AnswerApproved';
  answerId: number;
  questionText: string;
  answerText: string;
  citations: Citation[];
  actor: string;
  actorType: 'human';
  ts: string;
}

export interface AnswerEdited {
  type: 'AnswerEdited';
  answerId: number;
  newText: string;
  actor: string;
  actorType: 'human';
  ts: string;
}

export interface AnswerRejected {
  type: 'AnswerRejected';
  answerId?: number;
  questionId: string;
  actor: string;
  actorType: 'human';
  ts: string;
}

export interface AnswerConfirmed {
  type: 'AnswerConfirmed';
  answerId?: number;
  questionId: string;
  actor: string;
  actorType: 'human';
  ts: string;
}

export interface AnswerProposed {
  type: 'AnswerProposed';
  answerId: number;
  questionText: string;
  answerText: string;
  citations: Citation[];
  actor: 'agent';
  actorType: 'agent';
  ts: string;
}

export interface Exported {
  type: 'Exported';
  runId: string;
  actor: string;
  actorType: ActorType;
  ts: string;
}

export type DomainEvent =
  | QuestionnaireIntaken
  | EvidenceRetrieved
  | DraftProduced
  | CitationValidated
  | VisibilityChecked
  | AnswerApproved
  | AnswerEdited
  | AnswerRejected
  | AnswerConfirmed
  | AnswerProposed
  | Exported;
