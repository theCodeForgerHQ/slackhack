/**
 * One-command demo prep for the Asked & Answered explainer video.
 *
 *   SLACK_BOT_TOKEN=xoxb-... npx tsx scripts/prep-demo.ts [--user @tim_smith]
 *
 * This script:
 *   1. Creates public channels #security and #engineering if missing.
 *   2. Creates private channel #compliance-private if missing.
 *   3. Seeds evidence messages needed for the v5 demo script beats.
 *   4. Generates demo-questionnaire.xlsx with 47 rows matching the video.
 *   5. Optionally invites the demo user to public channels only, so private
 *      evidence stays invisible and the ACL-redaction beat triggers.
 *
 * It does NOT create Slack users (requires SCIM/admin). Pass an existing user
 * (e.g., @tim_smith) or create demo users manually in the workspace first.
 */
import bolt from '@slack/bolt';
import ExcelJS from 'exceljs';
import { writeFileSync } from 'node:fs';

const token = process.env.SLACK_BOT_TOKEN;
if (!token) throw new Error('SLACK_BOT_TOKEN required');
const client = new bolt.App({ token, signingSecret: 'unused-for-prep' }).client;

const userArg = process.argv.find((a) => a.startsWith('--user='))?.replace('--user=', '') ?? process.argv[process.argv.indexOf('--user') + 1];
async function resolveUser(name: string): Promise<string | undefined> {
  const clean = name.replace(/^@/, '');
  const list = await client.users.list({ limit: 200 });
  return list.members?.find((m: any) => m.name === clean || m.profile?.display_name === clean)?.id;
}

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
      'All customer data is encrypted at rest with AES-256 managed by AWS KMS. Encryption in transit is TLS 1.2+ everywhere.',
      'MFA is enforced for every employee via Okta — no exceptions since 2024. Offboarding deprovisions Okta within 1 hour.',
      'We support SSO via SAML and OIDC for all enterprise customers.',
      'Access reviews run quarterly; last review completed Q2 2026.',
      'Critical vulnerabilities are patched within 48 hours per policy.',
    ],
  },
  {
    channel: 'engineering',
    isPrivate: false,
    messages: [
      'Quarterly backup restore drill for Q2 2026 passed — RTO 4h, RPO 1h confirmed.',
      'Our secure SDLC requires code review on every change; SAST runs in CI and dependency scanning via Dependabot blocks merges on criticals.',
      'Production services run in AWS us-east-1 with failover to us-west-2.',
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

const DEMO_QUESTIONS: Array<[string, string]> = [
  ['Data Protection', 'Do you encrypt customer data at rest?'],
  ['Data Protection', 'Do you encrypt data in transit?'],
  ['Data Protection', 'Where is production customer data hosted geographically?'],
  ['Data Protection', 'Do you have a documented data retention policy?'],
  ['Data Protection', 'Can customers request deletion of their data?'],
  ['Data Protection', 'Do you classify data by sensitivity?'],
  ['Data Protection', 'Do you use tokenization or masking for sensitive data?'],
  ['Access Control', 'Is multi-factor authentication enforced for all employees?'],
  ['Access Control', 'Do you enforce least-privilege access?'],
  ['Access Control', 'Is access reviewed at least quarterly?'],
  ['Access Control', 'Do you support SSO via SAML or OIDC?'],
  ['Access Control', 'How are offboarded employees deprovisioned?'],
  ['Access Control', 'Do you enforce privileged access management?'],
  ['Compliance', 'Do you have a SOC 2 Type II report?'],
  ['Compliance', 'Are you ISO 27001 certified?'],
  ['Compliance', 'Do you comply with GDPR?'],
  ['Compliance', 'Do you have a documented information security policy?'],
  ['Compliance', 'When was your last policy review?'],
  ['Compliance', 'Do you undergo independent compliance audits?'],
  ['Compliance', 'Can you share your most recent audit report under NDA?'],
  ['Resilience', 'Are backups tested at least quarterly?'],
  ['Resilience', 'What is your RTO and RPO?'],
  ['Resilience', 'Do you have a documented business continuity plan?'],
  ['Resilience', 'Do you run disaster recovery drills?'],
  ['Resilience', 'Do you maintain an incident communication plan?'],
  ['Security Testing', 'Do you perform annual penetration testing?'],
  ['Security Testing', 'Do you run a vulnerability management program?'],
  ['Security Testing', 'Do you operate a bug bounty program?'],
  ['Security Testing', 'How quickly do you patch critical vulnerabilities?'],
  ['Security Testing', 'Do you perform regular red team exercises?'],
  ['Incident Response', 'Do you have an incident response plan?'],
  ['Incident Response', 'What is your breach notification SLA in hours?'],
  ['Incident Response', 'Have you had a breach in the last 24 months?'],
  ['Incident Response', 'Do you conduct post-incident reviews?'],
  ['Vendor Management', 'Do you assess the security of your subprocessors?'],
  ['Vendor Management', 'Do you maintain a list of subprocessors?'],
  ['Application Security', 'Do you follow a secure SDLC?'],
  ['Application Security', 'Do you perform code review on all changes?'],
  ['Application Security', 'Do you use static analysis (SAST)?'],
  ['Application Security', 'Do you scan dependencies for vulnerabilities?'],
  ['Application Security', 'Do you conduct threat modeling?'],
  ['Insurance', 'Do you carry cyber liability insurance?'],
  ['Insurance', 'What is your cyber insurance coverage limit?'],
  ['Cryptography', 'Do you use FIPS 140-2 validated cryptographic modules?'],
  ['Cryptography', 'Do you have a quantum-safe cryptography roadmap?'],
  ['Privacy', 'Do you conduct Data Protection Impact Assessments?'],
  ['Personnel', 'Do employees complete security awareness training?'],
];

console.log('=== Creating / verifying channels ===\n');
const channelMap: Record<string, string> = {};
for (const seed of SEEDS) {
  let channelId: string | undefined;
  try {
    const created = await client.conversations.create({ name: seed.channel, is_private: seed.isPrivate });
    channelId = created.channel?.id;
    console.log(`created #${seed.channel} (${channelId})`);
  } catch (err) {
    const list = await client.conversations.list({ types: seed.isPrivate ? 'private_channel' : 'public_channel', limit: 1000 });
    channelId = list.channels?.find((c) => c.name === seed.channel)?.id;
    console.log(`#${seed.channel} exists (${channelId})`);
  }
  if (!channelId) {
    console.warn(`skipping #${seed.channel}: no channel id`);
    continue;
  }
  channelMap[seed.channel] = channelId;
  for (const text of seed.messages) {
    await client.chat.postMessage({ channel: channelId, text });
  }
  console.log(`  posted ${seed.messages.length} evidence messages`);
}

console.log('\n=== Generating demo questionnaire ===\n');
const wb = new ExcelJS.Workbook();
const ws = wb.addWorksheet('Security Questionnaire');
ws.addRow(['#', 'Category', 'Question', 'Vendor Response']);
ws.getRow(1).font = { bold: true };
ws.columns = [{ width: 5 }, { width: 22 }, { width: 70 }, { width: 40 }];
DEMO_QUESTIONS.forEach(([cat, q], i) => ws.addRow([i + 1, cat, q, '']));
const buf = await wb.xlsx.writeBuffer();
const out = 'demo-questionnaire.xlsx';
writeFileSync(out, Buffer.from(buf));
console.log(`Wrote ${out} — ${DEMO_QUESTIONS.length} questions`);

console.log('\n=== Channel memberships ===\n');
for (const [name, id] of Object.entries(channelMap)) {
  try {
    const members = await client.conversations.members({ channel: id, limit: 200 });
    console.log(`#${name} (${id}): ${members.members?.length ?? 0} members`);
  } catch (err) {
    console.log(`#${name}: could not list members — ${(err as Error).message}`);
  }
}

if (userArg) {
  console.log(`\n=== Inviting demo user ${userArg} to public channels only ===\n`);
  const userId = await resolveUser(userArg);
  if (!userId) {
    console.warn(`Could not resolve user ${userArg}. Existing users in workspace:`);
    const list = await client.users.list({ limit: 200 });
    console.log(list.members?.filter((m: any) => !m.is_bot && !m.deleted).map((m: any) => `  @${m.name} (${m.real_name})`).join('\n'));
  } else {
    for (const [name, id] of Object.entries(channelMap)) {
      const seed = SEEDS.find((s) => s.channel === name);
      if (seed?.isPrivate) {
        console.log(`skipping private #${name}`);
        continue;
      }
      try {
        await client.conversations.invite({ channel: id, users: userId });
        console.log(`invited ${userArg} to #${name}`);
      } catch (err) {
        const msg = (err as Error).message;
        if (msg.includes('already_in_channel')) {
          console.log(`${userArg} already in #${name}`);
        } else {
          console.warn(`could not invite to #${name}: ${msg}`);
        }
      }
    }
  }
}

console.log('\n=== Next steps ===');
console.log('1. Ensure the demo user exists in the workspace (pass --user @username to auto-invite to public channels).');
console.log('2. The demo user must NOT be in #compliance-private so the ACL-redaction beat triggers.');
console.log('3. Open a DM with the Asked & Answered app as the demo user and upload demo-questionnaire.xlsx.');
console.log('4. Verify: encrypt-at-rest -> Verified/Grounded, MFA -> Grounded, cyber-liability -> Needs SME, EU hosting -> Needs SME (ACL).');
