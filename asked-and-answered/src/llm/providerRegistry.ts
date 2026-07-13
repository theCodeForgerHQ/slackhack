import type { DraftingLlm } from '../core/pipeline.js';
import { AnthropicDrafter } from './anthropic.js';
import { OpenAiDrafter } from './openai.js';

export type ProviderName = 'anthropic' | 'openai' | 'azure';

/**
 * Factory registry for heterogeneous model providers.
 *
 * Used by the multi-agent jury to assemble a panel of drafters from different
 * model families. Each provider is instantiated lazily so missing credentials
 * for one provider do not block another.
 */
export function createDrafterByName(name: ProviderName | string): DraftingLlm {
  switch (name) {
    case 'anthropic':
      return new AnthropicDrafter();
    case 'openai':
      return new OpenAiDrafter('openai');
    case 'azure':
      return new OpenAiDrafter('azure');
    default:
      throw new Error(`Unknown provider: ${name}`);
  }
}

/** Parse a comma-separated list of provider names (e.g. "anthropic,openai"). */
export function parseProviderNames(spec = process.env.AA_JURY_PROVIDERS ?? ''): ProviderName[] {
  const names = spec
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  for (const name of names) {
    if (!['anthropic', 'openai', 'azure'].includes(name)) {
      throw new Error(`Unknown provider in AA_JURY_PROVIDERS: ${name}`);
    }
  }
  return names as ProviderName[];
}
