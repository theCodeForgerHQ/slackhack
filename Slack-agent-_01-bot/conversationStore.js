import { createClient } from '@supabase/supabase-js';
import { config } from '../config/index.js';

/**
 * Supabase persistence layer for conversation history and query logs.
 * Stores every agent interaction for audit, analytics, and context continuity.
 */
export class ConversationStore {
  constructor() {
    this.client = createClient(config.supabase.url, config.supabase.anonKey);
  }

  /**
   * Save a conversation exchange (user query + agent response + sources).
   */
  async saveExchange(exchange) {
    const { data, error } = await this.client
      .from('agent_conversations')
      .insert({
        user_id: exchange.userId,
        channel_id: exchange.channelId,
        thread_ts: exchange.threadTs,
        query: exchange.query,
        response: exchange.response,
        sources: exchange.sources,
        created_at: new Date().toISOString(),
      })
      .select()
      .single();

    if (error) throw new Error(`Failed to save exchange: ${error.message}`);
    return data;
  }

  /**
   * Retrieve recent conversation history for a thread (context continuity).
   */
  async getThreadHistory(threadTs, limit = 10) {
    const { data, error } = await this.client
      .from('agent_conversations')
      .select('query, response, created_at')
      .eq('thread_ts', threadTs)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) throw new Error(`Failed to fetch history: ${error.message}`);
    return data || [];
  }

  /**
   * Get conversation statistics for analytics.
   */
  async getStats(days = 7) {
    const since = new Date(Date.now() - days * 86400000).toISOString();

    const { data, error } = await this.client
      .from('agent_conversations')
      .select('id, created_at')
      .gte('created_at', since);

    if (error) throw new Error(`Failed to fetch stats: ${error.message}`);
    return { totalQueries: data?.length || 0, queries: data || [] };
  }
}
