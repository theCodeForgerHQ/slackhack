// Day-1 capability spike (throwaway). Probes every plan-gated Slack capability
// and prints PASS/FAIL per item plus a feature-flag summary.
// Usage: node scripts/spike.js [channel_id]   (channel falls back to SPIKE_CHANNEL_ID)
require('dotenv').config();
const { WebClient } = require('@slack/web-api');

const client = new WebClient(process.env.SLACK_BOT_TOKEN);
const channelId = process.argv[2] || process.env.SPIKE_CHANNEL_ID || null;

const flags = { FEATURE_RTS: false, FEATURE_LISTS: false, FEATURE_CANVAS: false };
const pass = (name, extra = '') => console.log(`PASS  ${name}${extra ? ' - ' + extra : ''}`);
const fail = (name, err) =>
  console.log(`FAIL  ${name} - ${err.data ? JSON.stringify(err.data) : err.message}`);

async function probeAuth() {
  const res = await client.auth.test();
  pass('auth.test', `team=${res.team} bot_user=${res.user_id}`);
  return res;
}

async function probeRtsInfo() {
  try {
    const res = await client.apiCall('assistant.search.info');
    pass('assistant.search.info', JSON.stringify(res));
    flags.FEATURE_RTS = true;
  } catch (err) {
    fail('assistant.search.info', err);
  }
}

async function probeRtsContext() {
  // NOTE: bot-token RTS calls require an action_token from a recent user
  // interaction (e.g. the triggering app_mention). A standalone script has
  // none, so a failure here that names action_token is EXPECTED and
  // informative - it confirms the auth mechanics. Print the error verbatim.
  try {
    const res = await client.apiCall('assistant.search.context', {
      query: 'What discussions have we had about deployments?',
      limit: 5,
    });
    const n = (res.results && res.results.messages ? res.results.messages : res.messages || []).length;
    pass('assistant.search.context (no action_token)', `${n} results`);
  } catch (err) {
    fail('assistant.search.context (no action_token - failure may be expected)', err);
  }
}

async function probeLists() {
  try {
    const created = await client.apiCall('slackLists.create', {
      name: 'Threadwork spike (safe to delete)',
      todo_mode: true,
    });
    const listId = created.list_id || (created.list && created.list.id);
    pass('slackLists.create', `list_id=${listId}`);
    try {
      const item = await client.apiCall('slackLists.items.create', {
        list_id: listId,
        initial_fields: [
          {
            column_id: 'name',
            rich_text: [
              {
                type: 'rich_text',
                elements: [
                  {
                    type: 'rich_text_section',
                    elements: [{ type: 'text', text: 'Spike test item' }],
                  },
                ],
              },
            ],
          },
        ],
      });
      pass('slackLists.items.create (rich_text)', `item ok`);
    } catch (err) {
      fail('slackLists.items.create (rich_text) - note exact error for field addressing', err);
    }
    flags.FEATURE_LISTS = true;
    console.log(`      -> spike list left in place; delete "Threadwork spike (safe to delete)" manually`);
  } catch (err) {
    fail('slackLists.create', err);
  }
}

async function probeCanvas() {
  try {
    const created = await client.apiCall('canvases.create', {
      title: 'Threadwork spike (safe to delete)',
      document_content: {
        type: 'markdown',
        markdown: '# Spike\n\nCreated by scripts/spike.js - safe to delete.',
      },
    });
    pass('canvases.create', `canvas_id=${created.canvas_id}`);
    flags.FEATURE_CANVAS = true;
    if (channelId) {
      try {
        await client.apiCall('canvases.access.set', {
          canvas_id: created.canvas_id,
          access_level: 'read',
          channel_ids: [channelId],
        });
        pass('canvases.access.set', `channel=${channelId} access_level=read`);
      } catch (err) {
        fail('canvases.access.set - note exact working args', err);
      }
    } else {
      console.log('SKIP  canvases.access.set - pass a channel id (arg or SPIKE_CHANNEL_ID) to test');
    }
  } catch (err) {
    fail('canvases.create (standalone) - fallback chain will engage', err);
  }
}

(async () => {
  console.log('--- Threadwork Day-1 spike ---\n');
  try {
    await probeAuth();
  } catch (err) {
    fail('auth.test', err);
    console.log('\nBot token invalid or missing - fix .env before anything else.');
    process.exit(1);
  }
  await probeRtsInfo();
  await probeRtsContext();
  await probeLists();
  await probeCanvas();

  console.log('\n--- Summary (set these in your head; app.js re-checks at startup later) ---');
  for (const [k, v] of Object.entries(flags)) console.log(`${k}=${v}`);
  console.log('\nNext: verify the action_token field on a real app_mention event (Phase 1),');
  console.log('per https://docs.slack.dev/apis/web-api/real-time-search-api/');
})();
