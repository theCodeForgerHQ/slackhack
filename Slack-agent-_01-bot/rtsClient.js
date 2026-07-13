import { config } from '../config/index.js';

/**
 * Real-Time Search (RTS) API client.
 *
 * Uses Slack's `assistant.search.context` method — the permission-aware
 * search endpoint that returns live workspace context for grounding
 * AI agent responses. This replaces the legacy `search.messages` method.
 *
 * Required scopes: search:read.public, search:read.private,
 *                  search:read.files, search:read.users
 *
 * @see https://docs.slack.dev/reference/methods/assistant.search.context
 */
export class RealTimeSearchClient {
  constructor(client) {
    this.client = client;
  }

  /**
   * Search Slack workspace content for AI context.
   *
   * @param {string} query - User prompt or search query
   * @param {object} options - Optional search filters
   * @param {string} options.actionToken - Token from message event for user-scoped search
   * @param {string[]} options.channelTypes - Channel types to search
   * @param {string[]} options.contentTypes - Content types to include
   * @param {number} options.limit - Max results (default from config)
   * @param {number} options.before - UNIX timestamp filter (before)
   * @param {number} options.after - UNIX timestamp filter (after)
   * @returns {Promise<object>} Search results with messages, files, channels, users
   */
  async search(query, options = {}) {
    const {
      actionToken,
      channelTypes,
      contentTypes,
      limit = config.ai.maxSearchResults,
      before,
      after,
    } = options;

    const params = {
      query,
      count: limit,
      channel_types: channelTypes || config.rts.channelTypes.split(','),
      content_types: contentTypes || config.rts.contentTypes.split(','),
    };

    if (actionToken) params.action_token = actionToken;
    if (before) params.before = before;
    if (after) params.after = after;

    try {
      const response = await this.client.assistant.search.context(params);
      if (!response.ok) {
        throw new Error(`RTS search failed: ${response.error}`);
      }
      return this.parseResults(response);
    } catch (error) {
      console.error('[RTS] Search error:', error.message);
      throw error;
    }
  }

  /**
   * Parse the RTS response into a structured context object
   * suitable for feeding into an LLM prompt.
   */
  parseResults(response) {
    const context = {
      messages: [],
      files: [],
      channels: [],
      users: [],
      summary: '',
    };

    if (response.messages?.matches) {
      context.messages = response.messages.matches.map((m) => ({
        text: m.text,
        user: m.user,
        channel: m.channel?.name,
        channelId: m.channel?.id,
        timestamp: m.ts,
        permalink: m.permalink,
        score: m.score,
      }));
    }

    if (response.files?.matches) {
      context.files = response.files.matches.map((f) => ({
        name: f.name,
        filetype: f.filetype,
        size: f.size,
        permalink: f.permalink,
        channel: f.channel?.name,
      }));
    }

    if (response.channels?.matches) {
      context.channels = response.channels.matches.map((c) => ({
        name: c.name,
        id: c.id,
        topic: c.topic,
        purpose: c.purpose,
        memberCount: c.num_members,
      }));
    }

    if (response.users?.matches) {
      context.users = response.users.matches.map((u) => ({
        name: u.name,
        realName: u.real_name,
        title: u.title,
        email: u.email,
      }));
    }

    context.summary = this.buildSummary(context);
    return context;
  }

  /**
   * Build a concise text summary of search results for LLM context.
   */
  buildSummary(context) {
    const parts = [];

    if (context.messages.length > 0) {
      parts.push(`Found ${context.messages.length} relevant messages:`);
      for (const m of context.messages.slice(0, 5)) {
        parts.push(`  - [${m.channel || 'unknown'}] ${m.text?.slice(0, 200)}`);
      }
    }

    if (context.files.length > 0) {
      parts.push(`Found ${context.files.length} relevant files:`);
      for (const f of context.files.slice(0, 3)) {
        parts.push(`  - ${f.name} (${f.filetype})`);
      }
    }

    if (context.channels.length > 0) {
      parts.push(`Found ${context.channels.length} relevant channels:`);
      for (const c of context.channels.slice(0, 3)) {
        parts.push(`  - #${c.name}: ${c.purpose?.value || 'no purpose'}`);
      }
    }

    return parts.join('\n') || 'No results found.';
  }
}
