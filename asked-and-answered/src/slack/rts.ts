import type { RtsClient, RtsHit, RtsSearchParams } from '../core/planner.js';

/**
 * action_token plumbing. Bot-token RTS calls must carry an action token
 * harvested from a *fresh* user-interaction event (message.im, app_mention…).
 * We record the latest token per user as events arrive and attach it to
 * every search that user triggers. (Spike S2 verifies lifetime/reuse
 * semantics against the live sandbox.)
 */
export class ActionTokenStore {
  private readonly tokens = new Map<string, string>();

  record(userId: string, token: string): void {
    this.tokens.set(userId, token);
  }

  latest(userId: string): string | undefined {
    return this.tokens.get(userId);
  }
}

/** Minimal facade over WebClient.apiCall so tests can inject a fake. */
export type SlackApiCall = (
  method: string,
  args: Record<string, unknown>,
  token?: string,
) => Promise<unknown>;

/**
 * Defensive parser for assistant.search.context responses. The exact result
 * shape varies across docs/SDK versions, so we accept the field spellings
 * seen in the wild and skip anything incomplete rather than crash a run.
 */
export function parseRtsResponse(raw: unknown): RtsHit[] {
  if (typeof raw !== 'object' || raw === null) return [];
  const results = (raw as { results?: unknown }).results;
  if (typeof results !== 'object' || results === null) return [];
  const messages = (results as { messages?: unknown }).messages;
  if (!Array.isArray(messages)) return [];

  const hits: RtsHit[] = [];
  for (const m of messages) {
    if (typeof m !== 'object' || m === null) continue;
    const msg = m as Record<string, unknown>;
    const permalink = typeof msg.permalink === 'string' ? msg.permalink : undefined;
    const channelId =
      typeof msg.channel_id === 'string'
        ? msg.channel_id
        : typeof (msg.channel as { id?: unknown })?.id === 'string'
          ? ((msg.channel as { id: string }).id)
          : undefined;
    const ts =
      typeof msg.ts === 'string' ? msg.ts : typeof msg.message_ts === 'string' ? msg.message_ts : undefined;
    const snippet =
      typeof msg.content === 'string' ? msg.content : typeof msg.text === 'string' ? msg.text : undefined;

    if (!permalink || !snippet) continue;
    hits.push({ permalink, channelId: channelId ?? '', ts: ts ?? '', snippet });
  }
  return hits;
}

/** Fall back to public-channel history when RTS assistant.search.context fails.
 *  This keeps the demo working in DMs or sandboxes where action tokens are not
 *  issued, while preserving the real RTS path wherever it is available.
 */
async function historyFallback(
  apiCall: SlackApiCall,
  query: string,
  limit: number,
): Promise<RtsHit[]> {
  const queryTerms = new Set(
    query
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .split(/\s+/)
      .filter((w) => w.length > 2),
  );
  if (queryTerms.size === 0) return [];

  try {
    const list = (await apiCall('conversations.list', {
      types: 'public_channel',
      exclude_archived: true,
      limit: 100,
    })) as { channels?: Array<{ id: string; name?: string; is_member?: boolean }> };
    const hits: RtsHit[] = [];
    const channels = (list.channels ?? []).filter((ch) => ch.is_member);
    for (const channel of channels.slice(0, 5)) {
      try {
        const history = (await apiCall('conversations.history', {
          channel: channel.id,
          limit: 100,
        })) as { messages?: Array<{ text?: string; ts?: string; user?: string }> };
        const messages = history.messages ?? [];
        for (const msg of messages) {
          const text = msg.text ?? '';
          const textTerms = new Set(
            text
              .toLowerCase()
              .replace(/[^a-z0-9\s]/g, ' ')
              .split(/\s+/)
              .filter((w) => w.length > 2),
          );
          let overlap = 0;
          for (const t of queryTerms) if (textTerms.has(t)) overlap++;
          if (overlap === 0) continue;
          // Resolve a real permalink so exports and reviewers can open the citation.
          let permalink = '';
          try {
            const permalinkRes = (await apiCall('chat.getPermalink', {
              channel: channel.id,
              message_ts: msg.ts,
            })) as { permalink?: string };
            permalink = permalinkRes.permalink ?? '';
          } catch {
            permalink = '';
          }
          if (!permalink) continue;
          hits.push({ permalink, channelId: channel.id, ts: msg.ts ?? '', snippet: text });
          if (hits.length >= limit) return hits;
        }
      } catch {
        // Ignore per-channel errors; keep scanning other channels.
      }
    }
    return hits;
  } catch {
    return [];
  }
}

/** Production RtsClient bound to one requesting user (permission scoping). */
export class SlackRtsClient implements RtsClient {
  constructor(
    private readonly apiCall: SlackApiCall,
    private readonly tokens: ActionTokenStore,
    private readonly userId: string,
    private readonly userToken?: string,
  ) {}

  async searchContext(params: RtsSearchParams): Promise<{ hits: RtsHit[] }> {
    const args: Record<string, unknown> = {
      query: params.query,
      // Keyword mode is the sandbox-safe default; semantic engages
      // automatically on plans that support it.
      limit: params.limit ?? 15,
      include_context_messages: true,
    };
    const token = this.tokens.latest(this.userId);
    if (token) args.action_token = token;
    if (this.userToken) args.token = this.userToken;

    try {
      const raw = await this.apiCall('assistant.search.context', args);
      const hits = parseRtsResponse(raw);
      if (hits.length > 0) return { hits };
      // Empty RTS result: try fallback once before giving up.
      const fallback = await historyFallback(this.apiCall, params.query, params.limit ?? 15);
      return { hits: fallback };
    } catch {
      // RTS failed (likely missing action token). Fall back to public-channel history.
      const fallback = await historyFallback(this.apiCall, params.query, params.limit ?? 15);
      return { hits: fallback };
    }
  }
}
