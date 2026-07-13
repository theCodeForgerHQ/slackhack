/**
 * Event handler: direct messages
 *
 * Fires when a user sends a DM to the bot. Processes the message
 * through the AI agent pipeline.
 */
export function registerMessageHandler(app, agent, store) {
  app.message(async ({ message, client, say }) => {
    if (message.subtype || message.bot_id) return;

    const query = message.text?.trim();
    if (!query) return;

    const thinking = await say({ text: `:thinking_face: Let me search Slack for that...` });

    try {
      const { response, sources } = await agent.processQuery(query, {
        channelName: 'DM',
        threadTs: message.thread_ts || message.ts,
        actionToken: message.action_token,
      });

      await client.chat.update({
        channel: message.channel,
        ts: thinking.ts,
        text: response,
      });

      if (store) {
        await store.saveExchange({
          userId: message.user,
          channelId: message.channel,
          threadTs: message.thread_ts || message.ts,
          query,
          response,
          sources: { messageCount: sources.messages.length, fileCount: sources.files.length },
        });
      }
    } catch (error) {
      console.error('[message] Error:', error.message);
      await client.chat.update({
        channel: message.channel,
        ts: thinking.ts,
        text: `:x: Error: ${error.message}`,
      });
    }
  });
}
