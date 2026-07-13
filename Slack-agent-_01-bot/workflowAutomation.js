/**
 * Workflow automation module.
 *
 * Provides scheduled task execution and automated action triggers
 * that run alongside the AI agent. Uses setInterval for simplicity;
 * in production, replace with a proper job queue (BullMQ, etc.).
 */
export class WorkflowAutomation {
  constructor(app, agent) {
    this.app = app;
    this.agent = agent;
    this.jobs = [];
  }

  /**
   * Register a scheduled workflow.
   *
   * @param {object} workflow - Workflow definition
   * @param {string} workflow.name - Unique name
   * @param {number} workflow.intervalMs - Run frequency in milliseconds
   * @param {string} workflow.channelId - Target Slack channel
   * @param {string} workflow.query - Search query for the agent
   * @param {string} workflow.prompt - Instructions for the agent
   */
  register(workflow) {
    const job = {
      ...workflow,
      timerId: setInterval(() => this.execute(workflow), workflow.intervalMs),
    };
    this.jobs.push(job);
    console.log(`[Workflow] Registered: ${workflow.name} (every ${workflow.intervalMs}ms)`);
  }

  /**
   * Execute a single workflow run.
   */
  async execute(workflow) {
    try {
      console.log(`[Workflow] Running: ${workflow.name}`);
      const { response } = await this.agent.processQuery(workflow.query, {
        channelName: workflow.channelId,
      });

      await this.app.client.chat.postMessage({
        channel: workflow.channelId,
        text: `*Automated Update: ${workflow.name}*\n\n${response}`,
      });

      console.log(`[Workflow] Completed: ${workflow.name}`);
    } catch (error) {
      console.error(`[Workflow] Failed: ${workflow.name}`, error.message);
    }
  }

  /**
   * Stop all scheduled workflows.
   */
  stopAll() {
    for (const job of this.jobs) {
      clearInterval(job.timerId);
    }
    this.jobs = [];
    console.log('[Workflow] All jobs stopped.');
  }
}
