// ALL Block Kit builders (spec §13): summary message, run card states.
function summary(wp, canvasPermalink, listPermalink, related) {
  const blocks = [
    { type: 'header', text: { type: 'plain_text', text: `📌 ${wp.title}`.slice(0, 150) } },
    { type: 'section', text: { type: 'mrkdwn', text: wp.tldr } },
    {
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `✅ *${wp.decisions.length}* decisions   ·   ❓ *${wp.open_questions.length}* open questions   ·   📋 *${wp.tasks.length}* tasks   ·   👥 *${wp.participants.length}* people`,
        },
      ],
    },
  ];

  const buttons = [];
  if (canvasPermalink) {
    buttons.push({
      type: 'button',
      text: { type: 'plain_text', text: '📄 Open Work Post' },
      url: canvasPermalink,
      action_id: 'open_canvas',
    });
  }
  if (listPermalink) {
    buttons.push({
      type: 'button',
      text: { type: 'plain_text', text: '✅ Task List' },
      url: listPermalink,
      action_id: 'open_list',
    });
  }
  if (buttons.length) blocks.push({ type: 'actions', elements: buttons });

  if (related && related.length > 0) {
    const lines = related.map(
      (r) => `• <${r.permalink}|#${r.channel} · ${r.date}>${r.note ? ` — ${r.note}` : ''}`
    );
    blocks.push({ type: 'divider' });
    blocks.push({
      type: 'section',
      text: { type: 'mrkdwn', text: `*🔁 Previously discussed*\n${lines.join('\n')}` },
    });
  }

  blocks.push({
    type: 'context',
    elements: [{ type: 'mrkdwn', text: '📌 Structured by Threadwork · a work post, not a summary — it outlives this thread' }],
  });

  return { text: `📌 ${wp.title}`, blocks };
}

// One card, changing state, is the whole accountability story (spec §13).
// state: needs_approval | running | completed | cancelled | failed
function runCard(run, wp, state, extras = {}) {
  const task = wp.tasks.find((t) => t.id === wp.proposed_agent_task.task_id) || { text: wp.proposed_agent_task.action_description };
  const status = {
    needs_approval: '🟡 Waiting for approval',
    running: `⏳ Running — approved by <@${extras.approvedBy}>`,
    completed: `✅ Completed — ${extras.canvasPermalink ? `<${extras.canvasPermalink}|output added to the Work Post>` : 'output added to the Work Post'}${extras.mcpRef ? ` · filed as \`${extras.mcpRef}\` via MCP` : ''}`,
    cancelled: `🚫 Cancelled by <@${extras.cancelledBy}>`,
    failed: '⚠️ Run failed — mention me again to retry',
  }[state];

  const blocks = [
    {
      type: 'header',
      text: { type: 'plain_text', text: `🤖 Agent Run — ${state === 'needs_approval' ? 'needs approval' : state}`.slice(0, 150) },
    },
    {
      type: 'section',
      fields: [
        { type: 'mrkdwn', text: `*Task:*\n${task.text}` },
        { type: 'mrkdwn', text: `*Deliverable:*\n${wp.proposed_agent_task.action_description}` },
        { type: 'mrkdwn', text: '*Scope:*\nRead this thread only · write to the Work Post' },
        { type: 'mrkdwn', text: `*Status:*\n${status}` },
      ],
    },
  ];

  if (state === 'needs_approval') {
    blocks.push({ type: 'divider' });
    blocks.push({
      type: 'actions',
      elements: [
        {
          type: 'button',
          style: 'primary',
          text: { type: 'plain_text', text: '✅ Approve' },
          action_id: 'agent_run_approve',
          value: run.run_id,
        },
        {
          type: 'button',
          style: 'danger',
          text: { type: 'plain_text', text: '❌ Deny' },
          action_id: 'agent_run_deny',
          value: run.run_id,
        },
      ],
    });
  }

  blocks.push({
    type: 'context',
    elements: [{ type: 'mrkdwn', text: '🔒 Nothing runs without a human click — this card is the audit trail.' }],
  });

  return { text: `🤖 Agent Run — ${status}`, blocks };
}

// App Home tab (views.publish) - the judge-facing front door.
// status: { rts: bool, mcp: bool } - live capability flags, shown as proof.
function homeView(status = {}) {
  const light = (ok) => (ok ? '🟢' : '⚪');
  return {
    type: 'home',
    blocks: [
      { type: 'header', text: { type: 'plain_text', text: '📌 Threadwork' } },
      {
        type: 'section',
        text: { type: 'mrkdwn', text: '*Conversation in. Accountable work out.*\nThreadwork turns any messy thread into structured, durable work — without leaving Slack.' },
      },
      {
        type: 'context',
        elements: [
          {
            type: 'mrkdwn',
            text: `*Live right now:*   ${light(status.rts)} Real-Time Search — ${status.rts ? 'semantic search connected' : 'unavailable on this plan'}   ·   ${light(status.mcp)} MCP tracker — ${status.mcp ? 'connected' : 'offline'}   ·   🟢 Supervised agent runs — armed`,
          },
        ],
      },
      { type: 'divider' },
      { type: 'header', text: { type: 'plain_text', text: '🚀 How to use' } },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: [
            '*1.* Open any thread worth keeping — an incident, a debate, a planning spiral.',
            '*2.* Mention `@Threadwork structure this` inside the thread.',
            '*3.* Seconds later: a work post, a task list, related history, and a proposed agent run.',
            '*4.* Click *✅ Approve* on the run card — the agent executes one task, on the record.',
          ].join('\n'),
        },
      },
      { type: 'divider' },
      { type: 'header', text: { type: 'plain_text', text: '📦 What you get' } },
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: [
            '📄  *Canvas work post* — decisions with who + evidence links, open questions, status.',
            '✅  *Slack List of tasks* — owners, due dates, checkboxes. Real, trackable work.',
            '🔁  *Previously discussed* — related past threads found semantically via Real-Time Search, cited by permalink.',
            '🤖  *Supervised agent run* — proposes one task, runs only after a human approves, files it in the tracker via MCP, and records who approved what.',
          ].join('\n\n'),
        },
      },
      { type: 'divider' },
      {
        type: 'context',
        elements: [
          {
            type: 'mrkdwn',
            text: '🧵 Not a summarizer — a work-post generator. Everything stays in Slack. Mention it again in the same thread to refresh.',
          },
        ],
      },
    ],
  };
}

module.exports = { summary, runCard, homeView };
