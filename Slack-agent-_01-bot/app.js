import { App, ExpressReceiver } from '@slack/bolt';
import { config } from './config/index.js';
import { RealTimeSearchClient } from './services/rtsClient.js';
import { AIAgent } from './services/aiAgent.js';
import { ConversationStore } from './services/conversationStore.js';
import { WorkflowAutomation } from './services/workflowAutomation.js';
import { registerMentionHandler } from './handlers/mentionHandler.js';
import { registerMessageHandler } from './handlers/messageHandler.js';
import { registerSlashCommands } from './handlers/slashCommands.js';

/**
 * Initialize the Slack Bolt app.
 *
 * Supports two modes:
 * 1. Socket Mode (recommended for development) — uses WebSocket, no public URL needed
 * 2. HTTP Mode (production) — uses Express receiver with Slack Events API
 */
function createApp() {
  if (config.slack.socketMode && config.slack.appToken) {
    return new App({
      token: config.slack.botToken,
      appToken: config.slack.appToken,
      socketMode: true,
    });
  }

  const receiver = new ExpressReceiver({
    signingSecret: config.slack.signingSecret,
    port: config.slack.port,
  });

  const app = new App({
    token: config.slack.botToken,
    receiver,
  });

  app.receiver.app.get('/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
  });

  return app;
}

async function main() {
  const app = createApp();

  const rtsClient = new RealTimeSearchClient(app.client);
  const agent = new AIAgent(rtsClient);
  const store = config.supabase.url ? new ConversationStore() : null;
  const workflows = new WorkflowAutomation(app, agent);

  registerMentionHandler(app, agent, store);
  registerMessageHandler(app, agent, store);
  registerSlashCommands(app, agent, store);

  // Example scheduled workflow (uncomment and configure):
  // workflows.register({
  //   name: 'Daily Standup Summary',
  //   intervalMs: 86400000, // 24 hours
  //   channelId: 'C12345678',
  //   query: 'standup updates from today',
  //   prompt: 'Summarize the team standup updates',
  // });

  await app.start(config.slack.socketMode ? undefined : config.slack.port);
  console.log(`[Slack AI Agent] Running in ${config.slack.socketMode ? 'Socket Mode' : 'HTTP Mode'}`);
  console.log(`[Slack AI Agent] AI Provider: ${config.ai.provider} (${config.ai.apiKey ? 'active' : 'fallback mode'})`);
  console.log(`[Slack AI Agent] Persistence: ${store ? 'Supabase' : 'disabled'}`);
}

main().catch((error) => {
  console.error('Failed to start Slack AI Agent:', error);
  process.exit(1);
});
