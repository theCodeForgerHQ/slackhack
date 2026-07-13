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

    const raw = await this.apiCall('assistant.search.context', args);
    return { hits: parseRtsResponse(raw) };
  }
}
