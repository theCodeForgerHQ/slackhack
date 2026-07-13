import type { DraftingLlm } from '../core/pipeline.js';
import { JuryDrafter } from '../core/jury.js';
import { AnthropicDrafter } from './anthropic.js';
import { OpenAiDrafter } from './openai.js';
import { createDrafterByName, parseProviderNames } from './providerRegistry.js';

/**
 * Create the production drafting LLM from environment variables.
 *
 *   LLM_PROVIDER=anthropic (default) → ANTHROPIC_API_KEY
 *   LLM_PROVIDER=openai             → OPENAI_API_KEY, optionally OPENAI_MODEL / OPENAI_BASE_URL
 *   LLM_PROVIDER=azure              → AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT
 *
 * Multi-agent jury mode:
 *   AA_JURY_PROVIDERS=anthropic,openai  → JuryDrafter with heterogeneous panel
 *   AA_JURY_SYNTHESIZER=anthropic       → optional LLM synthesizer (default: deterministic vote)
 */
export function createDrafter(): DraftingLlm {
  const juryProviders = parseProviderNames();
  if (juryProviders.length > 1) {
    const drafters = juryProviders.map((name) => createDrafterByName(name));
    const synthesizerName = process.env.AA_JURY_SYNTHESIZER;
    return new JuryDrafter({
      drafters,
      labels: juryProviders,
      ...(synthesizerName ? { synthesizer: createDrafterByName(synthesizerName) } : {}),
    });
  }

  const provider = process.env.LLM_PROVIDER ?? 'anthropic';
  switch (provider) {
    case 'openai':
    case 'azure':
      return new OpenAiDrafter();
    case 'anthropic':
    default:
      return new AnthropicDrafter();
  }
}
