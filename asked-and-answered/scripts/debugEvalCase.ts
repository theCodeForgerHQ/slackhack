import { CASES, WORKSPACE } from '../evals/dataset.js';
import { OpenAiDrafter } from '../src/llm/openai.js';

function stems(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length > 3)
    .map((w) => w.slice(0, 5));
}

function retrieve(question: string) {
  const qStems = new Set(stems(question));
  const hits = [] as any[];
  for (const doc of WORKSPACE) {
    const dStems = new Set(stems(doc.snippet));
    let overlap = 0;
    for (const s of qStems) if (dStems.has(s)) overlap++;
    if (overlap >= 2 || (doc as any).adversarial) {
      hits.push({ permalink: doc.permalink, channelId: doc.channelId, ts: '1.0', snippet: doc.snippet });
    }
  }
  return hits;
}

const c = CASES.find((x) => x.id === process.argv[2]) ?? CASES.find((x) => x.expected.kind === 'grounded')!;
console.log('Case:', c.id, c.question);
const hits = retrieve(c.question);
console.log('Hits:', hits.length);

const drafter = new OpenAiDrafter('azure');
try {
  const result = await drafter.draft({ id: c.id, text: c.question, sourceRef: c.id }, hits);
  console.log('Parsed:', JSON.stringify(result, null, 2));
} catch (err) {
  console.error('Error:', (err as Error).message);
}
