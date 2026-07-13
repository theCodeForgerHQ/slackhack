// Orchestrates Flow A (spec §12): fetch -> extract -> list -> rts -> canvas ->
// summary -> run card. Every artifact failure degrades politely (spec §15).
const crypto = require('crypto');
const store = require('./store');
const llm = require('./llm');
const canvas = require('./canvas');
const lists = require('./lists');
const rts = require('./rts');
const blocks = require('./blocks');

const MAX_MESSAGES = 150; // spec §15: beyond this keep root + last 100
const MIN_SUBSTANTIVE = 3;

const nameCache = new Map(); // user_id -> display name (process lifetime)

async function fetchThread(client, channel, threadTs) {
  const messages = [];
  let cursor;
  do {
    const res = await client.conversations.replies({
      channel,
      ts: threadTs,
      limit: 200,
      cursor,
    });
    messages.push(...(res.messages || []));
    cursor = res.response_metadata && res.response_metadata.next_cursor;
  } while (cursor);
  return messages;
}

async function resolveNames(client, userIds) {
  const names = new Map();
  for (const id of userIds) {
    if (!id) continue;
    if (!nameCache.has(id)) {
      try {
        const res = await client.users.info({ user: id });
        const p = res.user.profile || {};
        nameCache.set(id, p.display_name || p.real_name || res.user.name || id);
      } catch {
        nameCache.set(id, id);
      }
    }
    names.set(id, nameCache.get(id));
  }
  return names;
}

function messageText(m) {
  if (m.text && m.text.trim()) return m.text.trim();
  if ((m.files && m.files.length) || (m.attachments && m.attachments.length)) {
    return '[shared a file/attachment]';
  }
  return null;
}

function buildTranscript(messages, names) {
  const lines = [];
  for (const m of messages) {
    const text = messageText(m);
    if (!text) continue;
    const uid = m.user || m.bot_id || 'unknown';
    const name = names.get(m.user) || m.username || uid;
    lines.push(`[${m.ts}] ${name} (${uid}): ${text}`);
  }
  return lines.join('\n');
}

async function run({ event, client, mode, threadKey }) {
  const channel = event.channel;
  const threadTs = event.thread_ts;
  try {
    // 1. Fetch the full thread
    let messages;
    try {
      messages = await fetchThread(client, channel, threadTs);
    } catch (err) {
      const code = err.data && err.data.error;
      if (code === 'not_in_channel' || code === 'channel_not_found' || code === 'missing_scope') {
        await client.chat
          .postEphemeral({
            channel,
            user: event.user,
            text: 'I need to be in this channel - /invite me first.',
          })
          .catch(() => {});
        return;
      }
      throw err;
    }

    // Guard: too thin (ignore the triggering mention and system/subtype messages)
    const substantive = messages.filter(
      (m) => m.ts !== event.ts && !m.subtype && m.text && m.text.trim()
    );
    if (substantive.length < MIN_SUBSTANTIVE) {
      await client.chat.postMessage({
        channel,
        thread_ts: threadTs,
        text: 'Not enough discussion to structure yet - mention me once the thread develops.',
      });
      return;
    }

    // Guard: too long -> root + most recent 100
    let truncated = false;
    if (messages.length > MAX_MESSAGES) {
      messages = [messages[0], ...messages.slice(-100)];
      truncated = true;
    }

    // 2. Resolve names, build transcript
    const userIds = [...new Set(messages.map((m) => m.user).filter(Boolean))];
    const names = await resolveNames(client, userIds);
    const transcript = buildTranscript(messages, names);
    console.log(`[pipeline] mode=${mode} thread=${threadKey} messages=${messages.length} truncated=${truncated}`);

    // 3. Extract the WorkPost (Prompt A, validated, one retry inside llm.js)
    let wp;
    try {
      wp = await llm.extract(transcript);
    } catch (err) {
      if (err instanceof llm.ExtractionError) {
        console.error('[pipeline] extraction failed twice:', err.message);
        await client.chat.postMessage({
          channel,
          thread_ts: threadTs,
          text: "I couldn't structure this thread just now - please mention me again to retry.",
        });
        return;
      }
      throw err;
    }
    console.log('[pipeline] WorkPost extracted:', wp.title);

    const existing = store.get(threadKey) || {};

    // 4. Slack List (F4) - reuse on refresh, fall back to canvas checklist on failure
    let listInfo = existing.list_id
      ? { list_id: existing.list_id, permalink: existing.list_permalink }
      : await lists.createWithItems(client, wp, channel);

    // 5. Related history via RTS (F5) - always an array, never an error
    const related = await rts.findRelated(client, wp, event, threadTs);

    // 6. Canvas work post (F3)
    const permalinkOf = async (ts) => {
      try {
        return (await client.chat.getPermalink({ channel, message_ts: ts })).permalink;
      } catch {
        return null;
      }
    };
    const evidenceLinks = {};
    for (const d of wp.decisions) {
      if (d.evidence_ts && !evidenceLinks[d.evidence_ts]) {
        evidenceLinks[d.evidence_ts] = await permalinkOf(d.evidence_ts);
      }
    }
    const meta = {
      channelId: channel,
      threadPermalink: await permalinkOf(threadTs),
      createdDate: new Date().toISOString().slice(0, 10),
      names: Object.fromEntries(names),
      truncated,
      listPermalink: (listInfo && listInfo.permalink) || null,
      related,
      evidenceLinks,
      agentOutput: (existing.canvas_meta && existing.canvas_meta.agentOutput) || null,
    };
    const cv = await canvas.createOrReplace(client, wp, meta, existing.canvas_id);

    const canvasPermalink = cv.permalink || null;
    if (cv.fallback === 'blocks') {
      // Last-resort work post as a message (spec §15)
      await client.chat.postMessage({
        channel,
        thread_ts: threadTs,
        text: `📌 *${wp.title}*\n\n${cv.markdown.slice(0, 3500)}`,
      });
    }

    // 7. Summary message + run card (CREATE) or refresh note (REFRESH)
    if (mode === 'REFRESH') {
      await client.chat.postMessage({
        channel,
        thread_ts: threadTs,
        text: `♻️ Updated the existing work post${canvasPermalink ? `: ${canvasPermalink}` : ''}`,
      });
      store.save(threadKey, {
        workpost_json: wp,
        canvas_id: cv.canvas_id || existing.canvas_id || null,
        canvas_meta: meta,
        transcript,
        list_id: (listInfo && listInfo.list_id) || null,
        list_permalink: (listInfo && listInfo.permalink) || null,
        last_activity: new Date().toISOString(),
      });
      return;
    }

    await client.chat.postMessage({
      channel,
      thread_ts: threadTs,
      ...blocks.summary(wp, canvasPermalink, listInfo && listInfo.permalink, related),
    });

    const runId = crypto.randomUUID();
    const runRecord = {
      run_id: runId,
      thread_key: threadKey,
      task_id: wp.proposed_agent_task.task_id,
      status: 'needs_approval',
      approved_by: null,
      card_ts: null,
      channel,
      output_location: null,
      timestamps: { created: new Date().toISOString(), resolved: null },
    };
    const card = await client.chat.postMessage({
      channel,
      thread_ts: threadTs,
      ...blocks.runCard(runRecord, wp, 'needs_approval'),
    });
    runRecord.card_ts = card.ts;

    store.save(threadKey, {
      workpost_json: wp,
      canvas_id: cv.canvas_id || null,
      canvas_meta: meta,
      transcript,
      list_id: (listInfo && listInfo.list_id) || null,
      list_permalink: (listInfo && listInfo.permalink) || null,
      run: runRecord,
      last_activity: new Date().toISOString(),
    });
    console.log(`[pipeline] done: canvas=${cv.canvas_id} list=${listInfo && listInfo.list_id} related=${related.length} run=${runId}`);
  } catch (err) {
    console.error('[pipeline] failed:', err);
    // Never a stack trace in Slack (spec §15)
    await client.chat
      .postMessage({
        channel,
        thread_ts: threadTs,
        text: 'Something went wrong structuring this thread - please try again.',
      })
      .catch(() => {});
  }
}

module.exports = { run, buildTranscript, resolveNames, fetchThread };
