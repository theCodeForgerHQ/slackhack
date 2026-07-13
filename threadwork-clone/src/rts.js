// assistant.search.context wrapper. RTS call discipline lives here and only here:
// one call per invocation (hard cap 2 by design; we use 1), action_token from the
// triggering interaction, filtering, top-3.
const llm = require('./llm');

let FEATURE_RTS = false;
let authInfo = null;

async function checkAvailability(client) {
  try {
    const info = await client.apiCall('assistant.search.info');
    FEATURE_RTS = !!info.ok;
    console.log(`[rts] available=${FEATURE_RTS} ai_search=${info.is_ai_search_enabled ? 'semantic' : 'keyword'}`);
  } catch (err) {
    FEATURE_RTS = false;
    console.log('[rts] unavailable:', (err.data && err.data.error) || err.message);
  }
  return FEATURE_RTS;
}

const available = () => FEATURE_RTS;

function fmtDate(ts) {
  try {
    return new Date(parseFloat(ts) * 1000).toISOString().slice(0, 10);
  } catch {
    return '';
  }
}

// Returns [{permalink, channel, date, note}] - always an array, never throws.
async function findRelated(client, wp, event, currentThreadTs) {
  if (!FEATURE_RTS) return [];
  try {
    // action_token comes from the triggering app_mention event (verified need:
    // bot-token calls fail with invalid_action_token without it).
    const actionToken = event.action_token;
    if (!actionToken) {
      console.warn('[rts] no action_token on the mention event - skipping search. Event keys:', Object.keys(event).join(','));
      return [];
    }
    // Two calls (the spec's hard cap): semantic (question form) + keyword
    // (same query, no "?") - semantic understands the topic, keyword nails
    // literal terms ("pool exhaustion") that semantic can rank below noise.
    // Keyword results get priority in the merge for exactly that reason.
    const search = async (query, extra = {}) => {
      const resp = await client.apiCall('assistant.search.context', {
        query,
        action_token: actionToken,
        limit: 20,
        include_bots: true, // seeded/demo history can be bot-authored
        ...extra,
      });
      return (resp.results && resp.results.messages) || resp.messages || [];
    };
    const semantic = await search(wp.related_search_query);
    let keyword = [];
    try {
      keyword = await search(wp.related_search_keywords, {
        disable_semantic_search: true, // true keyword mode (verified param, docs.slack.dev)
      });
    } catch (err) {
      console.warn('[rts] keyword call failed:', (err.data && err.data.error) || err.message);
    }
    console.log(`[rts] semantic: ${semantic.map((m) => m.channel_name).join(',')}`);
    console.log(`[rts] keyword:  ${keyword.map((m) => m.channel_name).join(',')}`);
    const seen = new Set();
    const messages = [...keyword, ...semantic].filter((m) => {
      const key = m.permalink || `${m.channel_id}:${m.message_ts}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    if (!authInfo) authInfo = await client.auth.test();
    const filtered = messages.filter((m) => {
      // Verified result shape (2026-07-04): message_ts (not ts), channel_id,
      // channel_name, author_user_id, is_author_bot, permalink, content (often empty).
      if (m.message_ts === currentThreadTs) return false;
      if (m.permalink && m.permalink.includes(currentThreadTs)) return false; // reply in current thread
      // ponytail: drop our own posts only in the invoking channel - own-bot posts
      // elsewhere are legitimate history (seeded demo threads are bot-authored).
      if (m.author_user_id === authInfo.user_id && m.channel_id === event.channel) return false;
      return true;
    });
    // one entry per conversation: dedupe by channel + thread root
    const threadSeen = new Set();
    const top = filtered
      .filter((m) => {
        const rootMatch = m.permalink && m.permalink.match(/thread_ts=([\d.]+)/);
        const key = `${m.channel_id}:${rootMatch ? rootMatch[1] : m.message_ts}`;
        if (threadSeen.has(key)) return false;
        threadSeen.add(key);
        return true;
      })
      .slice(0, 3);

    let results = top.map((m) => ({
      permalink: m.permalink,
      channel: m.channel_name || 'channel',
      date: fmtDate(m.message_ts),
      snippet: (m.content || '').slice(0, 300),
    }));
    // prefer fewer, higher-confidence entries: if any result has real content,
    // drop the empty-snippet ones (their relevance can't be judged or explained)
    if (results.some((r) => r.snippet)) results = results.filter((r) => r.snippet);

    // Prompt C relevance notes only when there is content to judge; template otherwise
    const withContent = results.some((r) => r.snippet);
    if (withContent) {
      try {
        const notes = await llm.relevanceNotes(wp.title, results);
        results.forEach((r, i) => (r.note = notes[i] || ''));
      } catch {
        results.forEach((r) => (r.note = ''));
      }
    } else {
      results.forEach((r) => (r.note = ''));
    }
    // A note that declares its own result irrelevant means the LLM judged it
    // unrelated - showing it undermines the section. Drop those entirely.
    results = results.filter((r) => !/unrelated|not related|no connection|irrelevant/i.test(r.note));
    return results.filter((r) => r.permalink);
  } catch (err) {
    console.warn('[rts] search failed, omitting section:', (err.data && err.data.error) || err.message);
    return [];
  }
}

module.exports = { checkAvailability, available, findRelated };
