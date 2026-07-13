import { config } from '../config/index.js';

/**
 * AI Agent service — orchestrates RTS context retrieval and LLM response
 * generation. Supports pluggable AI providers (OpenAI, Anthropic, etc.)
 * via a simple interface.
 *
 * When no AI API key is configured, falls back to a rule-based responder
 * that uses RTS search results directly.
 */
export class AIAgent {
  constructor(rtsClient) {
    this.rtsClient = rtsClient;
    this.provider = this.initProvider();
  }

  initProvider() {
    if (!config.ai.apiKey) return null;

    switch (config.ai.provider) {
      case 'openai':
        return new OpenAIProvider(config.ai.apiKey, config.ai.model);
      case 'anthropic':
        return new AnthropicProvider(config.ai.apiKey, config.ai.model);
      default:
        return null;
    }
  }

  /**
   * Process a user query: search Slack for context, then generate a response.
   *
   * @param {string} query - User's question or request
   * @param {object} context - Slack event context (channel, user, thread_ts)
   * @returns {Promise<{response: string, sources: object}>}
   */
  async processQuery(query, context = {}) {
    const searchResults = await this.rtsClient.search(query, {
      actionToken: context.actionToken,
    });

    if (this.provider) {
      const response = await this.provider.generate(query, searchResults.summary, context);
      return { response, sources: searchResults };
    }

    return { response: this.fallbackResponse(query, searchResults), sources: searchResults };
  }

  /**
   * Rule-based fallback when no LLM is configured.
   * Returns a formatted summary of RTS search results.
   */
  fallbackResponse(query, searchResults) {
    const ctx = searchResults;

    if (ctx.messages.length === 0 && ctx.files.length === 0 && ctx.channels.length === 0) {
      return `I couldn't find any results in Slack for: "${query}". Try rephrasing or check if the information exists in your workspace.`;
    }

    let response = `Here's what I found in Slack for "${query}":\n\n`;

    if (ctx.messages.length > 0) {
      response += `*Relevant Messages (${ctx.messages.length}):*\n`;
      for (const m of ctx.messages.slice(0, 5)) {
        response += `• <${m.permalink}|#${m.channel || 'channel'}>: ${m.text?.slice(0, 150)}...\n`;
      }
      response += '\n';
    }

    if (ctx.files.length > 0) {
      response += `*Relevant Files (${ctx.files.length}):*\n`;
      for (const f of ctx.files.slice(0, 3)) {
        response += `• <${f.permalink}|${f.name}> (${f.filetype})\n`;
      }
      response += '\n';
    }

    if (ctx.channels.length > 0) {
      response += `*Relevant Channels (${ctx.channels.length}):*\n`;
      for (const c of ctx.channels.slice(0, 3)) {
        response += `• #${c.name} — ${c.purpose?.value || 'No description'}\n`;
      }
    }

    return response.trim();
  }
}

/**
 * OpenAI provider — calls the Chat Completions API with RTS context.
 */
class OpenAIProvider {
  constructor(apiKey, model) {
    this.apiKey = apiKey;
    this.model = model;
    this.endpoint = 'https://api.openai.com/v1/chat/completions';
  }

  async generate(query, searchContext, context) {
    const systemPrompt = `You are a helpful Slack AI assistant. Use the following Slack workspace context to answer the user's question accurately. If the context doesn't contain relevant information, say so clearly.

Slack Context:
${searchContext}

User is in: #${context.channelName || 'unknown'}
Thread: ${context.threadTs || 'new conversation'}`;

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: query },
        ],
        max_tokens: 1024,
        temperature: 0.7,
      }),
    });

    if (!response.ok) {
      throw new Error(`OpenAI API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data.choices[0].message.content;
  }
}

/**
 * Anthropic provider — calls the Messages API with RTS context.
 */
class AnthropicProvider {
  constructor(apiKey, model) {
    this.apiKey = apiKey;
    this.model = model;
    this.endpoint = 'https://api.anthropic.com/v1/messages';
  }

  async generate(query, searchContext, context) {
    const systemPrompt = `You are a helpful Slack AI assistant. Use the following Slack workspace context to answer the user's question accurately. If the context doesn't contain relevant information, say so clearly.

Slack Context:
${searchContext}

User is in: #${context.channelName || 'unknown'}
Thread: ${context.threadTs || 'new conversation'}`;

    const response = await fetch(this.endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: this.model,
        max_tokens: 1024,
        system: systemPrompt,
        messages: [{ role: 'user', content: query }],
      }),
    });

    if (!response.ok) {
      throw new Error(`Anthropic API error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data.content[0].text;
  }
}
