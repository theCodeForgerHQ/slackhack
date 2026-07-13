import Anthropic from '@anthropic-ai/sdk';
import type { DraftingLlm, LlmDraft } from '../core/pipeline.js';
import type { RtsHit } from '../core/planner.js';
import type { Question } from '../core/types.js';
import { buildDraftPrompt, parseDraftReply } from './prompt.js';

const MODEL = process.env.AA_MODEL ?? 'claude-haiku-4-5-20251001';

/** Production DraftingLlm backed by Anthropic. All hardening lives in prompt.ts + pipeline.ts. */
export class AnthropicDrafter implements DraftingLlm {
  private readonly client: Anthropic;

  constructor(apiKey = process.env.ANTHROPIC_API_KEY) {
    if (!apiKey) throw new Error('ANTHROPIC_API_KEY is required');
    this.client = new Anthropic({ apiKey });
  }

  async draft(question: Question, hits: RtsHit[]): Promise<LlmDraft> {
    const message = await this.client.messages.create({
      model: MODEL,
      max_tokens: 2000,
      messages: [{ role: 'user', content: buildDraftPrompt(question, hits) }],
    });
    const text = message.content
      .filter((b): b is Anthropic.TextBlock => b.type === 'text')
      .map((b) => b.text)
      .join('\n');
    return parseDraftReply(text);
  }
}
