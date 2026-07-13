/**
 * Slash command handlers.
 *
 * Registers /ask, /search, and /agent-stats commands.
 */
export function registerSlashCommands(app, agent, store) {
  app.command('/ask', async ({ command, client, respond }) => {
    await respond({ response_type: 'ephemeral', text: `:mag: Searching Slack...` });

    try {
      const { response } = await agent.processQuery(command.text, {
        channelName: command.channel_name,
        actionToken: command.action_token,
      });

      await client.chat.postMessage({
        channel: command.channel_id,
        text: `*Question:* ${command.text}\n\n*Answer:*\n${response}`,
      });
    } catch (error) {
      await respond({ response_type: 'ephemeral', text: `:x: Error: ${error.message}` });
    }
  });

  app.command('/search', async ({ command, respond }) => {
    await respond({ response_type: 'ephemeral', text: `:mag: Searching Slack for "${command.text}"...` });

    try {
      const { sources } = await agent.processQuery(command.text, {});
      const messageCount = sources.messages.length;
      const fileCount = sources.files.length;
      const channelCount = sources.channels.length;

      let summary = `Found ${messageCount} messages, ${fileCount} files, ${channelCount} channels.\n\n`;

      if (sources.messages.length > 0) {
        summary += '*Top Messages:*\n';
        for (const m of sources.messages.slice(0, 5)) {
          summary += `• <${m.permalink}|#${m.channel}>: ${m.text?.slice(0, 100)}...\n`;
        }
      }

      await respond({ response_type: 'ephemeral', text: summary });
    } catch (error) {
      await respond({ response_type: 'ephemeral', text: `:x: Error: ${error.message}` });
    }
  });

  app.command('/agent-stats', async ({ respond }) => {
    if (!store) {
      await respond({ response_type: 'ephemeral', text: 'Analytics not configured.' });
      return;
    }

    try {
      const stats = await store.getStats(7);
      await respond({
        response_type: 'ephemeral',
        text: `:bar_chart: *Agent Stats (7 days)*\nTotal queries: ${stats.totalQueries}`,
      });
    } catch (error) {
      await respond({ response_type: 'ephemeral', text: `:x: Error: ${error.message}` });
    }
  });
}
