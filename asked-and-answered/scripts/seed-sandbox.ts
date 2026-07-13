/**
 * Seeds a Slack sandbox workspace with a realistic company's security
 * evidence, so judges can run the full journey immediately.
 *
 *   SLACK_BOT_TOKEN=xoxb-... npx tsx scripts/seed-sandbox.ts
 *
 * Creates channels and posts evidence messages. Channels marked private model
 * the ACL story (put the judge's test user in the public ones only to see a
 * Needs-SME on the private-evidence question).
 *
 * Idempotent-ish: re-running re-posts messages; create channels once.
 */
import bolt from '@slack/bolt';

const token = process.env.SLACK_BOT_TOKEN;
if (!token) throw new Error('SLACK_BOT_TOKEN required');
const client = new bolt.App({ token, signingSecret: 'unused-for-seeding' }).client;

interface Seed {
  channel: string;
  isPrivate: boolean;
  messages: string[];
}

const SEEDS: Seed[] = [
  {
    channel: 'security',
    isPrivate: false,
    messages: [
      'Reminder: all customer data is encrypted at rest with AES-256 managed by AWS KMS. Encryption in transit is TLS 1.2+ everywhere.',
      'MFA is enforced for every employee via Okta — no exceptions since 2024. Offboarding deprovisions Okta within 1 hour.',
      'We support SSO via SAML and OIDC for all enterprise customers.',
      'Access reviews run quarterly; last review completed Q2 2026.',
    ],
  },
  {
    channel: 'engineering',
    isPrivate: false,
    messages: [
      'Quarterly backup restore drill for Q2 2026 passed — RTO 4h, RPO 1h confirmed.',
      'Our secure SDLC requires code review on every change; SAST runs in CI and dependency scanning via Dependabot blocks merges on criticals.',
      'Critical vulnerabilities are patched within 48 hours per policy.',
    ],
  },
  {
    channel: 'compliance-private',
    isPrivate: true,
    messages: [
      'SOC 2 Type II report issued January 2026, covering Security and Availability. ISO 27001 certification renewed 2026.',
      'Annual third-party penetration test completed by NCC Group in March 2026; all highs remediated.',
      'Production data resides in AWS eu-west-1 ONLY. Do not share region details outside this channel.',
      'Cyber liability insurance: $5M coverage via Acme Insurance, renewed annually.',
    ],
  },
];

for (const seed of SEEDS) {
  let channelId: string | undefined;
  try {
    const created = await client.conversations.create({ name: seed.channel, is_private: seed.isPrivate });
    channelId = created.channel?.id;
    console.log(`created #${seed.channel} (${channelId})`);
  } catch (err) {
    // Likely name_taken — look it up.
    const list = await client.conversations.list({ types: seed.isPrivate ? 'private_channel' : 'public_channel', limit: 1000 });
    channelId = list.channels?.find((c) => c.name === seed.channel)?.id;
    console.log(`#${seed.channel} exists (${channelId}) — ${(err as Error).message}`);
  }
  if (!channelId) {
    console.warn(`skipping #${seed.channel}: no channel id`);
    continue;
  }
  for (const text of seed.messages) {
    await client.chat.postMessage({ channel: channelId, text });
  }
  console.log(`  posted ${seed.messages.length} evidence messages`);
}

console.log('\nSeed complete. Add the judge test user to the PUBLIC channels only to demo the ACL degrade.');
