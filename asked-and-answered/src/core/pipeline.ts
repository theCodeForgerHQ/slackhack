import type { AnswerLibrary, Citation, VisibilityChecker } from './library.js';
import { GroundingGate } from './grounding.js';
import type { QuestionEvidence, RtsHit } from './planner.js';
import type { Question } from './types.js';
import { sanitizeHits, sanitizeQuestion } from './sanitize.js';
import { detectDrift } from './driftResolver.js';

export type LlmDraft =
  | { kind: 'answer'; answerText: string; citedPermalinks: string[] }
  | { kind: 'refuse'; reason: string };

/** Production adapter wraps Anthropic; tests inject a scripted fake. */
export interface DraftingLlm {
  draft(question: Question, hits: RtsHit[]): Promise<LlmDraft>;
}

export type DraftState = 'verified' | 'grounded' | 'needs_sme';

export type NeedsSmeReason =
  | 'no_evidence'
  | 'search_failed'
  | 'llm_refused'
  | 'invalid_citations'
  | 'ungrounded_citations'
  | 'acl_degraded'
  | 'stale_evidence'
  | 'llm_error'
  | 'rejected';

export interface DraftResult {
  questionId: string;
  questionText: string;
  state: DraftState;
  /** Present only for verified/grounded — never for needs_sme. */
  answerText?: string;
  citations?: Citation[];
  /** Present only for needs_sme. */
  reason?: NeedsSmeReason;
  /** Provenance for verified answers. */
  approvedBy?: string;
  approvedAt?: string;
}

/**
 * The three-state drafting pipeline. Fail-closed by construction:
 *
 * 1. Library first — an SME-approved answer is reused ONLY after every one
 *    of its citations is re-validated against the current requester.
 * 2. No evidence (or failed search) → needs_sme. The LLM is never consulted
 *    without evidence, so it cannot invent a compliance answer.
 * 3. With evidence, the LLM may draft — but its citations must be a subset
 *    of the evidence we handed it. Anything else (including prompt-injected
 *    citations) is discarded and routed to a human.
 * 4. Even valid permalinks must be *grounded*: the cited snippet text must
 *    actually appear in the drafted answer. Paraphrases and fabrications are
 *    caught deterministically by GroundingGate.
 */
export class DraftingPipeline {
  constructor(
    private readonly library: AnswerLibrary,
    private readonly llm: DraftingLlm,
    private readonly visibility: VisibilityChecker,
    private readonly grounding: GroundingGate = new GroundingGate(),
  ) {}

  async run(
    questions: Question[],
    evidenceByQuestion: Map<string, QuestionEvidence>,
    requesterId: string,
  ): Promise<DraftResult[]> {
    const results: DraftResult[] = [];
    for (const question of questions) {
      results.push(await this.runOne(question, evidenceByQuestion.get(question.id), requesterId));
    }
    return results;
  }

  private async runOne(
    question: Question,
    evidence: QuestionEvidence | undefined,
    requesterId: string,
  ): Promise<DraftResult> {
    const base = { questionId: question.id, questionText: question.text };

    // 1) Approved-answer library, with per-requester ACL revalidation.
    // A failing visibility check is indistinguishable from "not visible":
    // degrade this question, never crash the run, never fail open.
    let lookup;
    try {
      lookup = await this.library.findVerified(question.text, requesterId, this.visibility);
    } catch {
      return { ...base, state: 'needs_sme', reason: 'acl_degraded' };
    }
    if (lookup.status === 'verified') {
      // Lore-style deterministic drift resolver: even if the answer's own
      // citations are visible, newer workspace evidence may reverse the value.
      const hits = evidence?.hits ?? [];
      const drift = detectDrift(lookup.answer, hits);
      if (drift.drift) {
        return { ...base, state: 'needs_sme', reason: 'stale_evidence' };
      }
      return {
        ...base,
        state: 'verified',
        answerText: lookup.answer.answerText,
        citations: lookup.answer.citations,
        approvedBy: lookup.answer.approvedBy,
        approvedAt: lookup.answer.approvedAt,
      };
    }
    if (lookup.status === 'degraded') {
      return {
        ...base,
        state: 'needs_sme',
        reason: lookup.reason === 'stale_evidence' ? 'stale_evidence' : 'acl_degraded',
      };
    }

    // 2) Fail-closed on missing or failed evidence.
    if (!evidence || evidence.searchFailed) {
      return { ...base, state: 'needs_sme', reason: evidence?.searchFailed ? 'search_failed' : 'no_evidence' };
    }
    if (evidence.hits.length === 0) {
      return { ...base, state: 'needs_sme', reason: 'no_evidence' };
    }

    // 3) Evidence-grounded drafting.
    // Sanitize model inputs: NFKC + strip zero-width/directional chars. The
    // original citations remain untouched; this only hardens the prompt.
    const sanitizedHits = sanitizeHits(evidence.hits);
    const sanitizedQuestion = { ...question, text: sanitizeQuestion(question.text) };
    let draft: LlmDraft;
    try {
      draft = await this.llm.draft(sanitizedQuestion, sanitizedHits);
    } catch {
      return { ...base, state: 'needs_sme', reason: 'llm_error' };
    }

    if (draft.kind === 'refuse' || draft.answerText.trim().length === 0) {
      return { ...base, state: 'needs_sme', reason: 'llm_refused' };
    }

    // Injection guard: cited permalinks must be a subset of what we provided.
    const allowed = new Map(evidence.hits.map((h) => [h.permalink, h]));
    const cited = [...new Set(draft.citedPermalinks)].filter((p) => p.length > 0);
    if (cited.length === 0 || cited.some((p) => !allowed.has(p))) {
      return { ...base, state: 'needs_sme', reason: 'invalid_citations' };
    }

    const citations: Citation[] = cited.map((p) => {
      const h = allowed.get(p) as RtsHit;
      return { permalink: h.permalink, channelId: h.channelId, ts: h.ts };
    });

    // THE INVARIANT applies to fresh drafts too: RTS results are normally
    // scoped to the requesting user, but we do not trust that plumbing —
    // every cited channel is re-checked for this requester before any
    // drafted text is released. Check errors count as not visible.
    for (const citation of citations) {
      let visible = false;
      try {
        visible = await this.visibility.canSee(requesterId, citation);
      } catch {
        visible = false;
      }
      if (!visible) return { ...base, state: 'needs_sme', reason: 'acl_degraded' };
    }

    // Grounding guard: the cited snippet must actually support the answer text.
    // Runs after the invariant so invisible citations are reported as ACL
    // degradation, not as a grounding failure.
    const grounding = this.grounding.verify(draft.answerText, evidence.hits, cited);
    if (!grounding.ok) {
      return { ...base, state: 'needs_sme', reason: 'ungrounded_citations' };
    }

    return { ...base, state: 'grounded', answerText: draft.answerText.trim(), citations };
  }
}
