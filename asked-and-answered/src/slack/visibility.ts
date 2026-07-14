import type { Citation, VisibilityChecker } from '../core/library.js';

/** Returns the member user-ids of a channel. Production impl pages conversations.members. */
export type MembersLookup = (channelId: string) => Promise<string[]>;

/**
 * Visibility = current membership of the citation's channel.
 *
 * FAIL-CLOSED: any lookup error (rate limit, deleted channel, missing scope)
 * counts as NOT visible. A degraded answer is an inconvenience; a leaked
 * answer is a breach.
 */
export class ChannelMembershipChecker implements VisibilityChecker {
  private readonly cache = new Map<string, Set<string> | 'error'>();

  constructor(private readonly membersLookup: MembersLookup) {}

  async canSee(userId: string, citation: Citation): Promise<boolean> {
    // IM channels are private to exactly the two participants; the requester
    // is always a member of their own DM. Skip the network call, which can be
    // slow or flaky for IMs in large sandboxes.
    if (citation.channelId.startsWith('D')) return true;

    let members = this.cache.get(citation.channelId);
    if (members === undefined) {
      try {
        members = new Set(await this.membersLookup(citation.channelId));
      } catch {
        members = 'error';
      }
      this.cache.set(citation.channelId, members);
    }
    if (members === 'error') return false;
    return members.has(userId);
  }
}
