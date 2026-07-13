import type { DraftingLlm, LlmDraft } from '../core/pipeline.js';
import type { RtsHit } from '../core/planner.js';
import type { Question } from '../core/types.js';
import { buildDraftPrompt, parseDraftReply } from './prompt.js';

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
    const body = {
      model: this.model,
      max_completion_tokens: 2000,
      messages: [{ role: 'user', content: buildDraftPrompt(question, hits) }],
    };

    const maxRetries = 5;
    let attempt = 0;
    while (true) {
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
      return parseDraftReply(text);
    }
  }
}

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is required`);
  return v;
}
