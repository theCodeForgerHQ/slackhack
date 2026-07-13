// All LLM calls: extract (Prompt A), draft (Prompt B), relevanceNotes (Prompt C).
// JSON validation + single retry lives here (spec §11).
// Provider: OpenRouter (OpenAI-compatible), Claude models. Node >=18 built-in fetch.
const MODEL = process.env.LLM_MODEL || 'anthropic/claude-sonnet-5';
const API_KEY = process.env.LLM_API_KEY;
const BASE_URL = 'https://openrouter.ai/api/v1/chat/completions';

class ExtractionError extends Error {}

const WORKPOST_SCHEMA = `{
  "title": "string, <=80 chars, imperative or noun phrase",
  "tldr": "string, <=3 sentences",
  "status_guess": "open | investigating | decided | blocked",
  "decisions": [
    { "text": "string", "decided_by": "slack_user_id | null", "evidence_ts": "message ts" }
  ],
  "open_questions": [ { "text": "string" } ],
  "tasks": [
    {
      "id": "t1",
      "text": "string, imperative",
      "suggested_owner": "slack_user_id | null",
      "due_hint": "YYYY-MM-DD | null",
      "automatable": true,
      "evidence_ts": "message ts"
    }
  ],
  "proposed_agent_task": {
    "task_id": "t3",
    "action_description": "one sentence: what the agent will produce",
    "deliverable_type": "status_update | draft_reply | postmortem_section | checklist"
  },
  "participants": ["slack_user_id"],
  "related_search_query": "one natural-language question ending in ? for RTS",
  "related_search_keywords": "2-4 word distinctive topic phrase for keyword search"
}`;

// Spec §11 Prompt A, verbatim starting point
const PROMPT_A = `You convert a raw Slack thread transcript into a structured work post.
Output ONLY valid JSON matching the provided schema. No prose, no markdown fences.

Rules:
- Extract only what is present or clearly implied in the transcript. Do not invent facts, owners, or dates.
- decisions: statements the group treated as settled ("let's do X", "agreed", explicit approvals). Include who said it (user id) and the message ts as evidence_ts.
- tasks: concrete next actions. suggested_owner only if a specific person volunteered or was asked; otherwise null. Max 8, prefer fewer high-confidence items.
- open_questions: raised but unresolved. Max 5.
- automatable=true only for tasks an AI could complete as a written deliverable using ONLY this thread's content (drafting an update, summarizing findings, writing a checklist). Tasks needing code changes, external systems, or human judgment are automatable=false.
- proposed_agent_task: pick exactly one automatable task (the most useful). If none are automatable, propose deliverable_type "status_update" synthesizing current state, and add it as a new task.
- related_search_query: ONE short natural-language question, ending in "?", that would find PAST Slack discussions about this same underlying topic. Topic words only (systems, features, symptoms). No dates, no names.
- related_search_keywords: the single most distinctive 2-4 word topic phrase, exactly as people would type it in chat (e.g. "connection pool exhaustion", not "database connectivity problems"). Every word must be likely to literally appear in a related message.
- title: specific and searchable ("Checkout latency spike for IN users after deploy"), never generic ("Thread summary").

Schema: ${WORKPOST_SCHEMA}
Transcript format: each line is "[ts] DisplayName (user_id): text".`;

const DELIVERABLE_TYPES = ['status_update', 'draft_reply', 'postmortem_section', 'checklist'];
const STATUSES = ['open', 'investigating', 'decided', 'blocked'];

function parseJson(raw) {
  let text = raw.trim();
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fence) text = fence[1].trim();
  return JSON.parse(text);
}

// Lenient fixes where safe, throws with a precise message where the model must retry.
function validateWorkPost(wp) {
  if (!wp || typeof wp !== 'object') throw new Error('output is not a JSON object');
  for (const key of ['title', 'tldr', 'related_search_query']) {
    if (typeof wp[key] !== 'string' || !wp[key].trim()) throw new Error(`missing or empty string "${key}"`);
  }
  wp.title = wp.title.slice(0, 80);
  if (!wp.related_search_query.trim().endsWith('?')) wp.related_search_query = wp.related_search_query.trim() + '?';
  if (typeof wp.related_search_keywords !== 'string' || !wp.related_search_keywords.trim()) {
    wp.related_search_keywords = wp.related_search_query.replace(/\?+$/, ''); // degraded fallback
  }
  if (!STATUSES.includes(wp.status_guess)) wp.status_guess = 'open';

  if (!Array.isArray(wp.participants)) throw new Error('"participants" must be an array of user ids');
  for (const key of ['decisions', 'open_questions', 'tasks']) {
    if (!Array.isArray(wp[key])) throw new Error(`"${key}" must be an array`);
  }
  wp.decisions = wp.decisions.slice(0, 5);
  wp.open_questions = wp.open_questions.slice(0, 5);
  wp.tasks = wp.tasks.slice(0, 8);

  for (const d of wp.decisions) {
    if (typeof d.text !== 'string') throw new Error('every decision needs a "text" string');
    if (d.decided_by && !wp.participants.includes(d.decided_by)) d.decided_by = null;
  }
  for (const q of wp.open_questions) {
    if (typeof q.text !== 'string') throw new Error('every open_question needs a "text" string');
  }
  if (wp.tasks.length === 0) throw new Error('"tasks" must contain at least one task');
  for (const t of wp.tasks) {
    if (typeof t.id !== 'string' || typeof t.text !== 'string') throw new Error('every task needs string "id" and "text"');
    if (typeof t.automatable !== 'boolean') throw new Error(`task ${t.id}: "automatable" must be a boolean`);
    if (t.suggested_owner && !wp.participants.includes(t.suggested_owner)) t.suggested_owner = null;
    if (t.due_hint && !/^\d{4}-\d{2}-\d{2}$/.test(t.due_hint)) t.due_hint = null;
  }

  const pat = wp.proposed_agent_task;
  if (!pat || typeof pat !== 'object') throw new Error('missing "proposed_agent_task"');
  const target = wp.tasks.find((t) => t.id === pat.task_id);
  if (!target) throw new Error(`proposed_agent_task.task_id "${pat.task_id}" does not match any task id`);
  if (!target.automatable) throw new Error(`proposed task ${pat.task_id} must have automatable=true`);
  if (typeof pat.action_description !== 'string') throw new Error('proposed_agent_task needs "action_description"');
  if (!DELIVERABLE_TYPES.includes(pat.deliverable_type)) {
    throw new Error(`deliverable_type must be one of ${DELIVERABLE_TYPES.join('|')}`);
  }
  return wp;
}

async function complete(system, user, maxTokens) {
  const res = await fetch(BASE_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: maxTokens,
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: user },
      ],
    }),
  });
  if (!res.ok) throw new Error(`LLM API ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const data = await res.json();
  const content = data.choices && data.choices[0] && data.choices[0].message.content;
  if (!content) throw new Error(`LLM API returned no content: ${JSON.stringify(data).slice(0, 300)}`);
  return content;
}

async function extract(transcript) {
  let userMsg = transcript;
  let lastError;
  for (let attempt = 1; attempt <= 2; attempt++) {
    const raw = await complete(PROMPT_A, userMsg, 2000);
    try {
      return validateWorkPost(parseJson(raw));
    } catch (err) {
      lastError = err;
      console.warn(`[llm] extraction attempt ${attempt} invalid: ${err.message}`);
      userMsg = `${transcript}\n\nYour previous output failed validation: ${err.message}. Return corrected JSON only.`;
    }
  }
  throw new ExtractionError(`extraction failed after retry: ${lastError.message}`);
}

// Prompt B - agent-run drafting (Phase 6 wires this in)
async function draft(wp, transcript) {
  const system = `You draft a "${wp.proposed_agent_task.deliverable_type}" deliverable for a team, based ONLY on the provided work post JSON and Slack thread transcript. Do not invent facts, names, dates, or numbers.
For a status_update: 150-250 words covering what happened, current status, decisions so far, and next steps with owners.
For other types, produce the equivalent concise, complete deliverable.
Output clean markdown only (headings, bullets allowed). No preamble, no sign-off, addressed to the team.`;
  const user = `WORK POST JSON:\n${JSON.stringify(wp, null, 2)}\n\nTRANSCRIPT:\n${transcript}`;
  return (await complete(system, user, 1500)).trim();
}

// Prompt C - relevance notes; template fallback handled by the caller (rts.js)
async function relevanceNotes(title, results) {
  const system = `Given a work post title and Slack search result snippets, write one relevance note per result: <=12 words, why it relates. Output ONLY a JSON array of strings, same order as the results.`;
  const user = `Title: ${title}\n\nResults:\n${results
    .map((r, i) => `${i + 1}. [#${r.channel} · ${r.date}] ${r.snippet || ''}`)
    .join('\n')}`;
  const raw = await complete(system, user, 300);
  const notes = parseJson(raw);
  if (!Array.isArray(notes)) throw new Error('notes not an array');
  return notes.map(String);
}

module.exports = { extract, draft, relevanceNotes, ExtractionError, validateWorkPost };
