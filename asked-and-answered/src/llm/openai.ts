import type { DraftingLlm, LlmDraft } from '../core/pipeline.js';
import type { RtsHit } from '../core/planner.js';
import type { Question } from '../core/types.js';
import { buildDraftPrompt, parseDraftReply } from './prompt.js';
import { GroundingGate } from '../core/grounding.js';

function isSelfGrounded(answerText: string, hits: RtsHit[], citedPermalinks: string[]): boolean {
  return new GroundingGate().verify(answerText, hits, citedPermalinks).ok;
}

interface ChatCompletionResponse {
  choices?: Array<{
    message?: {
      content?: string | null;
    };
  }>;
  error?: { message: string };
}

/**
 * OpenAI/Azure OpenAI drafter using raw fetch.
 *
 * Avoids the `openai` npm package because the version served by this registry
 * (6.46.0) does not match known-good releases and is treated as untrusted.
 */
export class OpenAiDrafter implements DraftingLlm {
  private readonly url: string;
  private readonly headers: Record<string, string>;
  private readonly model: string;

  constructor(provider: 'openai' | 'azure' = (process.env.LLM_PROVIDER as 'openai' | 'azure') ?? 'openai') {
    if (provider === 'azure') {
      const endpoint = required('AZURE_OPENAI_ENDPOINT').replace(/\/$/, '');
      const deployment = required('AZURE_OPENAI_DEPLOYMENT');
      const apiVersion = process.env.AZURE_OPENAI_API_VERSION ?? '2024-02-01';
      this.url = `${endpoint}/openai/deployments/${deployment}/chat/completions?api-version=${apiVersion}`;
      this.headers = {
        'api-key': required('AZURE_OPENAI_API_KEY'),
        'Content-Type': 'application/json',
      };
      this.model = process.env.AZURE_OPENAI_MODEL ?? deployment;
    } else {
      const baseURL = (process.env.OPENAI_BASE_URL ?? 'https://api.openai.com/v1').replace(/\/$/, '');
      this.url = `${baseURL}/chat/completions`;
      this.headers = {
        Authorization: `Bearer ${required('OPENAI_API_KEY')}`,
        'Content-Type': 'application/json',
      };
      this.model = process.env.OPENAI_MODEL ?? 'gpt-4o-mini';
    }
  }

  async draft(question: Question, hits: RtsHit[]): Promise<LlmDraft> {
    const basePrompt = buildDraftPrompt(question, hits);
    const strictPrompt =
      basePrompt +
      '\n\nCRITICAL: Your previous draft was rejected because it did not quote the evidence verbatim as one contiguous clause. ' +
      'This time, copy the relevant clause from the evidence into the answer exactly as written (keep it intact and contiguous), ' +
      'then answer the question around that quotation.';

    const maxRetries = 5;
    let attempt = 0;
    let lastResult: LlmDraft | undefined;

    while (true) {
      const useStrict = lastResult?.kind === 'answer' && !isSelfGrounded(lastResult.answerText, hits, lastResult.citedPermalinks);
      const body = {
        model: this.model,
        max_completion_tokens: 2000,
        messages: [{ role: 'user', content: useStrict ? strictPrompt : basePrompt }],
      };

      const res = await fetch(this.url, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(body),
      });

      if (res.status === 429 && attempt < maxRetries) {
        const retryAfter = res.headers.get('retry-after');
        const delayMs = retryAfter ? Math.max(500, parseInt(retryAfter, 10) * 1000) : 1000 * 2 ** attempt;
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        attempt++;
        continue;
      }

      const data = (await res.json()) as ChatCompletionResponse;
      if (!res.ok || data.error) {
        throw new Error(`OpenAI request failed: ${res.status} ${data.error?.message ?? ''}`);
      }

      const text = data.choices?.[0]?.message?.content ?? '';
      const rateLimitDelay = Number(process.env.AA_LLM_RATE_LIMIT_DELAY_MS ?? '0');
      if (rateLimitDelay > 0) {
        await new Promise((resolve) => setTimeout(resolve, rateLimitDelay));
      }

      const result = parseDraftReply(text);
      if (result.kind === 'answer' && lastResult?.kind === 'answer' && !useStrict) {
        // First attempt was an ungrounded answer; we just did the strict retry. Return strict result.
        return result;
      }
      if (result.kind === 'answer' && isSelfGrounded(result.answerText, hits, result.citedPermalinks)) {
        return result;
      }
      if (result.kind !== 'answer' || lastResult !== undefined) {
        // Refusal on first try, or second try already attempted.
        return result;
      }
      // Ungrounded answer on first try: retry once with the strict prompt.
      lastResult = result;
      attempt = 0;
    }
  }
}

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is required`);
  return v;
}
