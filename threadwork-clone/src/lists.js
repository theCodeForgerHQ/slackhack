// Slack List creation (todo_mode). The rich_text quirk lives here and only here:
// item text must be a Block Kit rich_text block, and column ids come from the
// create response's list_metadata.schema (never hardcode them).
let authInfo = null;

async function createWithItems(client, wp, channelId) {
  try {
    const created = await client.apiCall('slackLists.create', {
      name: wp.title.slice(0, 80),
      todo_mode: true,
    });
    const listId = created.list_id;
    const schema = (created.list_metadata && created.list_metadata.schema) || [];
    const col = (key) => {
      const c = schema.find((s) => s.key === key);
      return c && c.id;
    };

    for (const t of wp.tasks) {
      const fields = [
        {
          column_id: col('name'),
          rich_text: [
            {
              type: 'rich_text',
              elements: [
                { type: 'rich_text_section', elements: [{ type: 'text', text: t.text }] },
              ],
            },
          ],
        },
      ];
      if (t.suggested_owner && col('todo_assignee')) {
        fields.push({ column_id: col('todo_assignee'), user: [t.suggested_owner] });
      }
      if (t.due_hint && col('todo_due_date')) {
        fields.push({ column_id: col('todo_due_date'), date: [t.due_hint] });
      }
      await client.apiCall('slackLists.items.create', { list_id: listId, initial_fields: fields });
    }

    // Bot-created lists are private by default - share with the channel or the
    // "Task List" button lands members on "You don't have access".
    if (channelId) {
      try {
        await client.apiCall('slackLists.access.set', {
          list_id: listId,
          channel_ids: [channelId],
          access_level: 'write',
        });
      } catch (err) {
        console.warn('[lists] access.set failed (link may 403):', (err.data && err.data.error) || err.message);
      }
    }

    if (!authInfo) authInfo = await client.auth.test();
    return { list_id: listId, permalink: `${authInfo.url}lists/${authInfo.team_id}/${listId}` };
  } catch (err) {
    console.warn('[lists] failed, falling back to canvas checklist:', (err.data && err.data.error) || err.message);
    return null;
  }
}

module.exports = { createWithItems };
