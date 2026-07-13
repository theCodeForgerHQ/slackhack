// Threadwork - Bolt entry: init, routing, ack discipline. Logic lives in pipeline.js.
require('dotenv').config();
const { App } = require('@slack/bolt');
const store = require('./store');
const pipeline = require('./pipeline');
const rts = require('./rts');
const mcp = require('./mcp');
const canvas = require('./canvas');
const llm = require('./llm');
const blocks = require('./blocks');

const inFlight = new Set(); // threadKeys currently being structured

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  appToken: process.env.SLACK_APP_TOKEN,
  socketMode: true,
});

app.event('app_mention', async ({ event, client, context }) => {
  // Top-level mention (not in a thread): ephemeral hint, nothing else (spec F1)
  if (!event.thread_ts) {
    await client.chat
      .postEphemeral({
        channel: event.channel,
        user: event.user,
        text: 'Mention me inside a thread you want structured.',
      })
      .catch(() => {});
    return;
  }

  // Instant ack before any slow work
  await client.reactions
    .add({ channel: event.channel, timestamp: event.ts, name: 'eyes' })
    .catch(() => {}); // already_reacted etc - never block on the ack

  const threadKey = store.threadKey(
    context.teamId || event.team,
    event.channel,
    event.thread_ts
  );
  // ponytail: in-memory guard - two mentions in quick succession both read the
  // store before the first run saves, producing duplicate artifacts. Single
  // process, so a Set is enough.
  if (inFlight.has(threadKey)) return;
  inFlight.add(threadKey);
  try {
    const mode = store.has(threadKey) ? 'REFRESH' : 'CREATE';
    await pipeline.run({ event, client, mode, threadKey });
  } finally {
    inFlight.delete(threadKey);
  }
});

async function displayName(client, userId) {
  try {
    const res = await client.users.info({ user: userId });
    const p = res.user.profile || {};
    return p.display_name || p.real_name || res.user.name || userId;
  } catch {
    return userId;
  }
}

// F6 Flow B (spec §12): ack first, idempotent on run status, card updated in place.
app.action('agent_run_approve', async ({ ack, body, action, client }) => {
  await ack();
  const found = store.getRun(action.value);
  if (!found || found.run.status !== 'needs_approval') return; // double-click / stale card safe
  const { key, record, run } = found;
  const wp = record.workpost_json;
  const approver = body.user.id;

  try {
    store.updateRun(run.run_id, {
      status: 'running',
      approved_by: approver,
      timestamps: { ...run.timestamps },
    });
    await client.chat.update({
      channel: run.channel,
      ts: run.card_ts,
      ...blocks.runCard(run, wp, 'running', { approvedBy: approver }),
    });

    const draft = await llm.draft(wp, record.transcript);
    const approvedByName = await displayName(client, approver);
    const timestamp = new Date().toISOString().replace('T', ' ').slice(0, 16) + ' UTC';
    const canvasPermalink = await canvas.appendAgentOutput(
      client,
      key,
      draft,
      approvedByName,
      timestamp
    );

    // MCP: also file the executed task in the external tracker (silent skip on failure)
    const task = wp.tasks.find((t) => t.id === wp.proposed_agent_task.task_id);
    const mcpRef = await mcp.fileTask({
      title: (task && task.text) || wp.proposed_agent_task.action_description,
      description: `${wp.proposed_agent_task.action_description}\nCompleted by Threadwork agent run, approved by ${approvedByName}.`,
      owner: approvedByName,
      source: record.canvas_meta && record.canvas_meta.threadPermalink,
    });

    await client.chat.update({
      channel: run.channel,
      ts: run.card_ts,
      ...blocks.runCard(run, wp, 'completed', { canvasPermalink, mcpRef }),
    });
    store.updateRun(run.run_id, {
      status: 'completed',
      output_location: `canvas:${record.canvas_id}#agent-output`,
      mcp_ref: mcpRef,
      timestamps: { ...run.timestamps, resolved: new Date().toISOString() },
    });
  } catch (err) {
    console.error('[run] approve failed:', err);
    store.updateRun(run.run_id, {
      status: 'failed',
      timestamps: { ...run.timestamps, resolved: new Date().toISOString() },
    });
    await client.chat
      .update({
        channel: run.channel,
        ts: run.card_ts,
        ...blocks.runCard(run, wp, 'failed'),
      })
      .catch(() => {});
  }
});

app.action('agent_run_deny', async ({ ack, body, action, client }) => {
  await ack();
  const found = store.getRun(action.value);
  if (!found || found.run.status !== 'needs_approval') return;
  const { record, run } = found;

  store.updateRun(run.run_id, {
    status: 'denied',
    timestamps: { ...run.timestamps, resolved: new Date().toISOString() },
  });
  await client.chat
    .update({
      channel: run.channel,
      ts: run.card_ts,
      ...blocks.runCard(run, record.workpost_json, 'cancelled', { cancelledBy: body.user.id }),
    })
    .catch(() => {});
});

// App Home tab - published fresh on every open (view is static, publish is idempotent).
app.event('app_home_opened', async ({ event, client }) => {
  if (event.tab !== 'home') return;
  try {
    await client.views.publish({
      user_id: event.user,
      view: blocks.homeView({ rts: rts.available(), mcp: mcp.available() }),
    });
  } catch (err) {
    console.warn('[home] publish failed silently:', (err.data && err.data.error) || err.message);
  }
});

// URL buttons still emit block_actions - ack them so Bolt doesn't warn.
app.action('open_canvas', async ({ ack }) => ack());
app.action('open_list', async ({ ack }) => ack());

// F7 - resurfacing: a human reply lands in a tracked thread that has been
// quiet >=24h -> one "active again" note + Canvas "Last activity" refresh.
// Posting updates last_activity, so at most one note per quiet period.
const RESURFACE_QUIET_MS = 24 * 60 * 60 * 1000;
app.event('message', async ({ event, client, context }) => {
  if (event.subtype || event.bot_id || !event.thread_ts || !event.text) return;
  if (event.text.includes(`<@`) && event.text.includes('structure')) return; // the mention handler owns this
  const threadKey = store.threadKey(
    context.teamId || event.team,
    event.channel,
    event.thread_ts
  );
  const record = store.get(threadKey);
  if (!record || !record.workpost_json) return;
  const last = record.last_activity ? Date.parse(record.last_activity) : 0;
  store.save(threadKey, { last_activity: new Date().toISOString() });
  if (!last || Date.now() - last < RESURFACE_QUIET_MS) return;
  try {
    const dateStr = new Date().toISOString().slice(0, 10);
    const permalink = await canvas.touchLastActivity(client, threadKey, dateStr);
    await client.chat.postMessage({
      channel: event.channel,
      thread_ts: event.thread_ts,
      text: `🔁 This work item is active again${permalink ? ` — <${permalink}|Work Post>` : ''}`,
    });
  } catch (err) {
    console.warn('[resurface] failed silently:', (err.data && err.data.error) || err.message);
  }
});

(async () => {
  await app.start();
  await rts.checkAvailability(app.client);
  await mcp.connect();
  console.log('⚡ Threadwork running (Socket Mode)');
})();
