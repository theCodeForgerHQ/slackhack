// JSON-file state at data/store.json, keyed by team:channel:thread_ts (spec §10).
// ponytail: single-file JSON store, swap internals for sqlite if state ever outgrows one process.
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'data', 'store.json');

let state = {};
try {
  state = JSON.parse(fs.readFileSync(FILE, 'utf8'));
} catch {
  state = {};
}

function persist() {
  fs.mkdirSync(path.dirname(FILE), { recursive: true });
  const tmp = FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(state, null, 2));
  fs.renameSync(tmp, FILE);
}

function getRun(runId) {
  for (const [key, record] of Object.entries(state)) {
    if (record.run && record.run.run_id === runId) return { key, record, run: record.run };
  }
  return null;
}

module.exports = {
  threadKey: (teamId, channelId, threadTs) => `${teamId}:${channelId}:${threadTs}`,
  has: (key) => Object.prototype.hasOwnProperty.call(state, key),
  get: (key) => state[key] || null,
  save(key, patch) {
    state[key] = { ...(state[key] || {}), ...patch };
    persist();
    return state[key];
  },
  getRun,
  updateRun(runId, patch) {
    const found = getRun(runId);
    if (!found) return null;
    Object.assign(found.run, patch);
    persist();
    return found;
  },
};
