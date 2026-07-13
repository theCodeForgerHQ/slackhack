import type { DraftingLlm, LlmDraft } from './pipeline.js';
import type { RtsHit } from './planner.js';
import type { Question } from './types.js';

export interface JuryDrafterCall {
  /** Identifier for the panel member (provider name or custom label). */
  provider: string;
  /** Optional model name for telemetry. */
  model?: string;
  /** Wall-clock latency of the call in milliseconds. */
  latencyMs: number;
  /** The draft produced by this panel member. */
  draft: LlmDraft;
  /** Optional cost in USD (set by callers that track pricing). */
  costUsd?: number;
}

export interface JuryDrafterConfig {
  /** Heterogeneous panel of drafters. Each implements the same interface. */
  drafters: DraftingLlm[];
  /** Human-readable labels for telemetry, one per drafter. */
  labels?: string[];
  /**
   * Optional LLM-based synthesizer. If omitted, a deterministic majority vote
   * is used, which requires no extra API call and keeps tests hermetic.
   */
  synthesizer?: DraftingLlm;
  /**
   * Self-consistency runs for the synthesizer. If > 1, the synthesizer is run
   * multiple times and a majority vote is taken. Ignored when no synthesizer
   * is provided.
   */
  synthesizerRuns?: number;
}

/**
 * Multi-agent jury drafter.
 *
 * Matches Arbiter's pattern of heterogeneous verification, then hardens it:
 * the jury's output is still fed through the deterministic citation-subset,
 * ACL, and grounding gates in DraftingPipeline. Even a unanimous panel
 * hallucination is caught before it reaches the user.
 *
 * Two synthesis modes:
 *   1. Deterministic vote (default): picks the answer cited by the majority of
 *      panelists, requiring citation consensus. Fast, free, reproducible.
 *   2. LLM synthesizer: feeds all drafts to a separate model and asks it to
 *      reconcile them. Optional self-consistency runs smooth out sampling noise.
 *
 * Telemetry for every call is exposed on `lastCallLog` for cost/quality
 * observability.
 */
export class JuryDrafter implements DraftingLlm {
  /** Telemetry for the most recent draft() call. */
  lastCallLog: JuryDrafterCall[] = [];

  constructor(private readonly config: JuryDrafterConfig) {
    if (config.drafters.length === 0) throw new Error('JuryDrafter requires at least one drafter');
  }

  async draft(question: Question, hits: RtsHit[]): Promise<LlmDraft> {
    // 1. Run every panelist in parallel.
    const start = performance.now();
    const memberResults = await Promise.all(
      this.config.drafters.map(async (drafter, i) => {
        const t0 = performance.now();
        const draft = await drafter.draft(question, hits);
        return {
          provider: this.config.labels?.[i] ?? `drafter-${i}`,
          latencyMs: Math.round(performance.now() - t0),
          draft,
        } as JuryDrafterCall;
      }),
    );
    this.lastCallLog = memberResults;

    // 2. Synthesize.
    if (this.config.synthesizer) {
      const runs = Math.max(1, this.config.synthesizerRuns ?? 1);
      const syntheses: LlmDraft[] = [];
      for (let i = 0; i < runs; i++) {
        syntheses.push(await this.runSynthesizer(this.config.synthesizer, question, hits, memberResults));
      }
      return majorityVote(syntheses);
    }

    // 3. Deterministic majority vote over the raw panel drafts.
    return majorityVote(memberResults.map((m) => m.draft));
  }

  private async runSynthesizer(
    synthesizer: DraftingLlm,
    question: Question,
    hits: RtsHit[],
    memberResults: JuryDrafterCall[],
  ): Promise<LlmDraft> {
    const evidence = hits
      .map((h, i) => `<evidence index="${i + 1}" permalink="${h.permalink}">\n${h.snippet}\n</evidence>`)
      .join('\n');

    const drafts = memberResults
      .map(
        (m, i) =>
          `<draft panelist="${m.provider}">\n` +
          (m.draft.kind === 'refuse'
            ? `{"refuse": true, "reason": "${m.draft.reason}"}`
            : `{"answer": "${m.draft.answerText}", "citations": ${JSON.stringify(m.draft.citedPermalinks)}}`) +
          `\n</draft>`,
      )
      .join('\n');

    const synthesisQuestion: Question = {
      id: `${question.id}-synthesize`,
      text:
        `You are the synthesizer in a multi-agent panel. Review the following independent drafts for the question and produce a single, conservative final answer.\n\n` +
        `Question: ${question.text}\n\n` +
        `${evidence}\n\n` +
        `${drafts}\n\n` +
        `Rules:\n` +
        `- Prefer drafts that are well-supported by the evidence.\n` +
        `- If the panel disagrees on a material fact, refuse and explain why.\n` +
        `- Cite only permalinks from the evidence above.\n\n` +
        `Respond with EXACTLY one JSON object:\n` +
        `  {"answer": "<the answer>", "citations": ["<permalink>", ...]}\n` +
        `or to refuse:\n` +
        `  {"refuse": true, "reason": "<why>"}`,
      sourceRef: question.sourceRef,
      ...(question.section ? { section: question.section } : {}),
    };

    return synthesizer.draft(synthesisQuestion, hits);
  }
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function draftKey(draft: LlmDraft): string {
  if (draft.kind === 'refuse') return `__REFUSE__:${draft.reason}`;
  return normalize(draft.answerText);
}

function citationOverlap(a: string[], b: string[]): number {
  const sa = new Set(a);
  let overlap = 0;
  for (const c of b) if (sa.has(c)) overlap++;
  return overlap;
}

function scoreDraftPair(a: LlmDraft, b: LlmDraft): number {
  if (a.kind === 'refuse' || b.kind === 'refuse') return 0;
  const textScore = draftKey(a) === draftKey(b) ? 1 : 0;
  const citeScore =
    a.citedPermalinks.length === 0 || b.citedPermalinks.length === 0
      ? 0
      : citationOverlap(a.citedPermalinks, b.citedPermalinks) / Math.max(a.citedPermalinks.length, b.citedPermalinks.length);
  return textScore * 0.7 + citeScore * 0.3;
}

/** Majority vote weighted by answer-citation agreement. Refuse if no consensus. */
function majorityVote(drafts: LlmDraft[]): LlmDraft {
  if (drafts.length === 0) return { kind: 'refuse', reason: 'empty jury' };

  // Score each draft by how many other drafts agree with it.
  const scores = drafts.map((draft, i) => {
    let score = 0;
    for (let j = 0; j < drafts.length; j++) {
      if (i === j) continue;
      score += scoreDraftPair(draft, drafts[j]!);
    }
    return { draft, score };
  });

  scores.sort((a, b) => b.score - a.score);
  const winner = scores[0]!;

  // Require at least one other draft to agree; a lone draft is not a consensus.
  if (winner.score < 0.5 && drafts.length > 1) {
    return { kind: 'refuse', reason: 'jury could not reach consensus' };
  }

  if (winner.draft.kind === 'refuse') {
    return winner.draft;
  }

  // Build a citation set from all drafts that agree with the winner's answer.
  const agreedCitations = new Set<string>();
  for (const { draft, score } of scores) {
    if (draft.kind === 'answer' && scoreDraftPair(winner.draft, draft) >= 0.7) {
      for (const c of draft.citedPermalinks) agreedCitations.add(c);
    }
  }

  return {
    kind: 'answer',
    answerText: winner.draft.answerText.trim(),
    citedPermalinks: [...agreedCitations],
  };
}
