import { OpenAiDrafter } from '../src/llm/openai.js';

const drafter = new OpenAiDrafter('azure');

const result = await drafter.draft(
  { id: 'q1', text: 'Do we encrypt data at rest?', sourceRef: 'test' },
  [
    {
      permalink: 'https://example.com/encrypt',
      channelId: 'C1',
      ts: '1.0',
      snippet: 'All customer data is encrypted at rest using AES-256.',
    },
  ],
);

console.log(JSON.stringify(result, null, 2));
