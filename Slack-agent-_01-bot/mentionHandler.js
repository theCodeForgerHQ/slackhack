/**
 * Event handler: app_mention
 *
 * Fires when a user @-mentions the bot in a channel.
 * Extracts the query, runs RTS search + AI generation, and replies
 * in the same thread.
 */
export function registerMentionHandler(app, agent, store) {
  app.event('app_mention', async ({ event, client, say }) => {
    const query = event.text.replace(/<@[^>]+>/g, '').trim();

    if (!query) {
      await say({
        text: "Hi! I'm your AI assistant. Mention me with a question and I'll search Slack to find the answer.\n\nExample: *@AI Agent What is the status of Project Gizmo?*",
      });
      return;
    }

    const thinking = await say({ text: `:thinking_face: Searching Slack for context...` });

    try {
      const { response, sources } = await agent.processQuery(query, {
        channelName: event.channel,
        threadTs: event.thread_ts || event.ts,
        actionToken: event.action_token,
      });

      await client.chat.update({
        channel: event.channel,
        ts: thinking.ts,
        text: response,
      });

      if (store) {
        await store.saveExchange({
          userId: event.user,
          channelId: event.channel,
          threadTs: event.thread_ts || event.ts,
          query,
          response,
          sources: { messageCount: sources.messages.length, fileCount: sources.files.length },
        });
      }
    } catch (error) {
      console.error('[app_mention] Error:', error.message);
      await client.chat.update({
        channel: event.channel,
        ts: thinking.ts,
        text: `:x: Sorry, I encountered an error while processing your request: ${error.message}`,
      });
    }
  });
}
