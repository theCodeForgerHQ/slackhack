import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import type { AnswerLibrary, Citation } from '../core/library.js';
import type { LedgerV2 } from '../core/ledgerV2.js';
import { decide } from '../core/decide.js';
import { buildMcpServer, type McpServerOptions } from './server.js';

export interface McpServerV2Options extends McpServerOptions {
  /** Event-sourced ledger for agent proposals. */
  ledgerV2: LedgerV2;
  /** Disable the write tool unless this flag is set. */
  writesEnabled?: boolean;
}

/**
 * MCP server v2: read-only library tools plus a human-gated write path.
 *
 * The `propose_answer` tool lets an agent file an answer as a pending proposal.
 * It is stored as an `AnswerProposed` event in LedgerV2 — it does NOT enter the
 * approved library. A human must approve it through the Slack review UI before
 * it can be served to requesters.
 */
export function buildMcpServerV2(library: AnswerLibrary, opts: McpServerV2Options): McpServer {
  const server = buildMcpServer(library, opts);

  // Always register the write tool so the "writes disabled" path is discoverable
  // and tested (Relay pattern). When disabled, the tool returns a clear status
  // and logs nothing; when enabled, the proposal flows through decide() with the
  // agent actor type and the human-gated state machine.
  server.registerTool(
    'propose_answer',
    {
      title: 'Propose a new approved answer',
      description: opts.writesEnabled
        ? 'Propose a security-questionnaire answer for human approval. The proposal is logged but NOT published until a human approves it in Slack.'
        : 'Currently disabled. Set MCP_WRITES_ENABLED=1 to allow agent-proposed answers. No state is changed when this tool is called.',
      inputSchema: {
        questionText: z.string().min(5).describe('The exact question text'),
        answerText: z.string().min(5).describe('The proposed answer text'),
        citations: z
          .array(
            z.object({
              permalink: z.string(),
              channelId: z.string(),
              ts: z.string(),
            }),
          )
          .optional()
          .describe('Slack evidence citations backing the answer'),
      },
      annotations: { readOnlyHint: !opts.writesEnabled },
    },
    async ({ questionText, answerText, citations }) => {
      if (!opts.writesEnabled) {
        return {
          content: [
            { type: 'text', text: 'writes_disabled: agent proposals are disabled by policy. No state changed.' },
          ],
        };
      }

      const answerId = Math.floor(Date.now() + Math.random() * 1000);
      const decision = decide(opts.ledgerV2.entries(), {
        type: 'Propose',
        answerId,
        questionText,
        answerText,
        citations: (citations ?? []) as Citation[],
      });

      if (!decision.ok) {
        return {
          isError: true,
          content: [{ type: 'text', text: decision.error ?? 'proposal rejected by policy' }],
        };
      }

      for (const ev of decision.events ?? []) {
        opts.ledgerV2.append(ev);
      }

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                proposalId: answerId,
                status: 'pending_human_approval',
                questionText,
                answerText,
                citations: citations ?? [],
              },
              null,
              2,
            ),
          },
        ],
      };
    },
  );

  return server;
}
