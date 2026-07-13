// Posts the demo threads (spec §18): #infra older incident thread (the one RTS
// must find), #checkout main chaotic thread, #general noise.
// Personas are name prefixes in one bot's messages (no chat:write.customize needed).
// Usage: node scripts/seed.js  (channel ids from env: SEED_CHECKOUT_ID, SEED_INFRA_ID, SEED_GENERAL_ID;
//        SEED_CHECKOUT_ID falls back to SPIKE_CHANNEL_ID)
require('dotenv').config();
const { WebClient } = require('@slack/web-api');

const client = new WebClient(process.env.SLACK_BOT_TOKEN);
const CHECKOUT = process.env.SEED_CHECKOUT_ID || process.env.SPIKE_CHANNEL_ID;
const INFRA = process.env.SEED_INFRA_ID;
const GENERAL = process.env.SEED_GENERAL_ID;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function postThread(channel, rootText, replies) {
  const root = await client.chat.postMessage({ channel, text: rootText });
  for (const text of replies) {
    await client.chat.postMessage({ channel, thread_ts: root.ts, text });
    await sleep(400); // keep message order stable
  }
  const { permalink } = await client.chat.getPermalink({ channel, message_ts: root.ts });
  return permalink;
}

// Older #infra thread - overlapping vocabulary (pool, latency, checkout), different sentences.
const INFRA_ROOT = `[Marco]: heads up - seeing DB connection pool exhaustion on the primary. app servers are queueing, some checkout requests timing out`;
const INFRA_REPLIES = [
  `[Tara]: how many connections are we capped at right now?`,
  `[Marco]: pool max is 50 per instance, all 50 busy, acquire timeouts everywhere in the logs`,
  `[Tara]: last time this happened it was a leaked transaction holding connections open`,
  `[Marco]: checked - no leaks this time. it's genuine load, the promo traffic doubled our qps`,
  `[Dev]: we bumped pool max to 80 and latency recovered. checkout back to normal p95`,
  `[Tara]: let's document this - pool sizing needs to scale with instance count, adding it to the runbook`,
  `[Marco]: done. closing this out, incident lasted ~40 min`,
];

// Main #checkout demo thread (~15 messages): three theories, logs, one easy-to-miss
// decision, two implied tasks, trailing confusion.
const CHECKOUT_ROOT = `[Priya]: is anyone else seeing checkout being super slow? multiple customer complaints in the last hour, mostly from India`;
const CHECKOUT_REPLIES = [
  `[Dev]: looking... p95 on /checkout/complete is 8.4s, normally under 2s`,
  `[Sam]: could this be the DB connection pool config change we shipped yesterday?`,
  `[Marco]: or Stripe? their status page shows elevated API latency in ap-south-1`,
  `[Priya]: some users on twitter saying the payment page just spins forever`,
  `[Sam]: also possible it's the CDN - we moved the India edge config last week, could be routing through Singapore now`,
  `[Dev]: logs from app-7: pool.acquire timeout after 5000ms, ConnectionPoolExhausted x 214 in the last 30 min`,
  `[Marco]: that looks like the pool change then, not Stripe`,
  `[Sam]: stripe latency is elevated but only 200ms above baseline, doesn't explain 8s`,
  `[Dev]: yeah the pool change dropped max connections from 80 to 40, that lines up with the exhaustion warnings`,
  `[Priya]: ok let's roll back the pool config change`,
  `[Dev]: on it`,
  `[Marco]: someone should check p95 by region after the rollback lands, India specifically`,
  `[Priya]: and we should update the status page, support is drowning - let's have both done by Friday`,
  `[Sam]: wait is the CDN thing still worth checking? the Singapore routing?`,
  `[Dev]: rollback is deploying now, watching the graphs`,
];

const GENERAL_NOISE = [
  `[Tara]: reminder: demo day slides due friday`,
  `[Marco]: anyone want the extra standing desk on floor 3?`,
  `[Priya]: coffee machine on 2 is fixed 🎉`,
  `[Sam]: TIL you can pin messages in slack, game changer`,
  `[Dev]: lunch train to the taco place at 12:30, reply here`,
];

(async () => {
  if (!CHECKOUT) {
    console.error('Set SEED_CHECKOUT_ID (or SPIKE_CHANNEL_ID) in .env');
    process.exit(1);
  }

  if (INFRA) {
    const link = await postThread(INFRA, INFRA_ROOT, INFRA_REPLIES);
    console.log('#infra thread (RTS should find this):', link);
  } else {
    console.log('SKIP #infra - set SEED_INFRA_ID in .env');
  }

  const link = await postThread(CHECKOUT, CHECKOUT_ROOT, CHECKOUT_REPLIES);
  console.log('#checkout demo thread (mention @Threadwork here):', link);

  if (GENERAL) {
    for (const text of GENERAL_NOISE) {
      await client.chat.postMessage({ channel: GENERAL, text });
      await sleep(300);
    }
    console.log('#general noise posted');
  } else {
    console.log('SKIP #general - set SEED_GENERAL_ID in .env');
  }
})().catch((e) => {
  console.error('seed failed:', (e.data && e.data.error) || e.message);
  process.exit(1);
});
