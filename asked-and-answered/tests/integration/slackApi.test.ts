import { describe, test, expect, beforeAll } from 'vitest';
import { WebClient } from '@slack/web-api';

const token = process.env.SLACK_BOT_TOKEN;
const describeOrSkip = token ? describe : describe.skip;

describeOrSkip('Live Slack sandbox API integration', () => {
  let client: WebClient;
  let botUserId: string;
  let generalChannelId: string;
  let dmChannelId: string;

  beforeAll(async () => {
    client = new WebClient(token!);
    const auth = await client.auth.test();
    expect(auth.ok).toBe(true);
    botUserId = auth.user_id!;

    const channels = await client.conversations.list({ types: 'public_channel', limit: 50 });
    const general = channels.channels?.find((c) => c.name === 'general');
    expect(general?.id).toBeDefined();
    generalChannelId = general!.id!;

    const users = await client.users.list({ limit: 20 });
    const testUser = users.members?.find((m) => !m.is_bot && m.id !== 'USLACKBOT');
    expect(testUser?.id).toBeDefined();
    const dm = await client.conversations.open({ users: testUser!.id! });
    expect(dm.channel?.id).toBeDefined();
    dmChannelId = dm.channel!.id!;
  });

  test('bot token is valid and has expected scopes', () => {
    expect(botUserId).toMatch(/^U/);
  });

  test('bot can read public channel membership', async () => {
    const members = await client.conversations.members({ channel: generalChannelId, limit: 50 });
    expect(Array.isArray(members.members)).toBe(true);
  });

  test('bot can post a message to a public channel', async () => {
    const res = await client.chat.postMessage({
      channel: generalChannelId,
      text: 'Integration test message — asked-and-answered',
    });
    expect(res.ok).toBe(true);
    expect(res.ts).toBeDefined();
  });

  test('bot token cannot use user-scoped search.messages', async () => {
    await expect(client.search.messages({ query: 'integration test', count: 5 })).rejects.toThrow(
      /not_allowed_token_type/,
    );
  });

  test('bot can upload a file to a DM', async () => {
    const buf = Buffer.from('integration test export', 'utf8');
    const res = await client.files.uploadV2({
      channel_id: dmChannelId,
      filename: 'aa-integration-test.txt',
      file: buf,
      initial_comment: 'Integration test file upload',
    });
    expect(res.ok).toBe(true);
  });

  test('Canvas API returns missing_scope because bot token lacks canvases:write', async () => {
    await expect(
      client.apiCall('canvases.create', {
        title: 'Integration test canvas',
        document_content: { type: 'canvas', sections: [] },
      }),
    ).rejects.toThrow(/missing_scope/);
  });

  test('Lists API returns missing_scope because bot token lacks lists:write', async () => {
    await expect(
      client.apiCall('lists.create', {
        title: 'Integration test list',
      }),
    ).rejects.toThrow(/missing_scope/);
  });
});
