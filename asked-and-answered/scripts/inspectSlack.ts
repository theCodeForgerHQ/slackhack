import { WebClient } from '@slack/web-api';

const token = process.env.SLACK_BOT_TOKEN;
if (!token) {
  console.error('SLACK_BOT_TOKEN is required');
  process.exit(1);
}

const client = new WebClient(token);

const auth = await client.auth.test();
console.log('Bot identity:', JSON.stringify(auth, null, 2));

const channels = await client.conversations.list({ types: 'public_channel,private_channel', limit: 50 });
console.log('Channels:', JSON.stringify(channels.channels?.map((c) => ({ id: c.id, name: c.name, is_private: c.is_private })), null, 2));
