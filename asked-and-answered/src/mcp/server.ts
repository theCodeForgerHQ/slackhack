import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { AnswerLibrary, type ApprovedAnswer, type VisibilityChecker } from '../core/library.js';

/**
 * asked-answered-mcp — exposes the approved-answer library as read-only MCP
 * tools, so the compliance knowledge your SMEs already approved in Slack is
 * reachable from Claude, Cursor, or the Slackbot MCP client.
 *
 * Both tools are readOnlyHint: this server can never write, approve, or
 * mutate anything. Writes happen only through the in-Slack approval flow.
 *
 * Identity binding: the server is bound at startup to ONE identity, and THE
 * INVARIANT applies to it exactly as in Slack — answer text is served only
 * when every citation is currently visible to the bound identity; anything
 * less is redacted (provenance metadata stays visible). MCP transports carry
 * no Slack identity per-call, so binding at startup is the control.
 */
export interface McpServerOptions {
  /** The identity every visibility check runs against (e.g. the installing admin's Slack user id). */
  identity: string;
  visibility: VisibilityChecker;
}

const REDACTED = '[redacted — evidence not verifiable for the bound identity]';

export function buildMcpServer(library: AnswerLibrary, opts?: McpServerOptions): McpServer {
  const identity = opts?.identity ?? 'unbound';
  // FAIL CLOSED: with no explicit visibility, evidence-backed answers are
  // redacted. An unconfigured server must never serve answer text it cannot
  // prove the caller may see. Callers opt into disclosure explicitly.
  const visibility: VisibilityChecker = opts?.visibility ?? { canSee: async () => false };

  async function redactIfBlocked(answer: ApprovedAnswer): Promise<string> {
    if (answer.kind === 'sme_testimony') return answer.answerText;
    for (const citation of answer.citations) {
      let visible = false;
      try {
        visible = await visibility.canSee(identity, citation);
      } catch {
        visible = false;
      }
      if (!visible) return REDACTED;
    }
    return answer.answerText;
  }

  const server = new McpServer({ name: 'asked-answered-mcp', version: '0.1.0' });

  server.registerTool(
    'search_answers',
    {
      title: 'Search approved answers',
      description:
        'Search the library of SME-approved security-questionnaire answers. Returns approved answers with their id, question, answer text, and approver.',
      inputSchema: { query: z.string().min(2).describe('Keywords or a question to search for') },
      annotations: { readOnlyHint: true },
    },
    async ({ query }) => {
      const results = await Promise.all(
        library.searchAnswers(query).map(async (a) => ({
          id: a.id,
          questionText: a.questionText,
          answerText: await redactIfBlocked(a),
          kind: a.kind,
          approvedBy: a.approvedBy,
          approvedAt: a.approvedAt,
        })),
      );
      return { content: [{ type: 'text', text: JSON.stringify(results, null, 2) }] };
    },
  );

  server.registerTool(
    'get_answer_provenance',
    {
      title: 'Get answer provenance',
      description:
        'Fetch the full provenance of an approved answer: its Slack evidence permalinks, approver, and approval timestamp.',
      inputSchema: { answerId: z.number().int().describe('The id returned by search_answers') },
      annotations: { readOnlyHint: true },
    },
    async ({ answerId }) => {
      const answer = library.getById(answerId);
      if (!answer) {
        return {
          isError: true,
          content: [{ type: 'text', text: `No approved answer with id ${answerId}` }],
        };
      }
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                id: answer.id,
                questionText: answer.questionText,
                kind: answer.kind,
                citations: answer.citations,
                approvedBy: answer.approvedBy,
                approvedAt: answer.approvedAt,
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

// Entrypoint: `npm run mcp` serves the library over stdio.
//
// Visibility must be chosen explicitly — the server refuses to guess:
// - AA_MCP_TRUST_LOCAL=1  → single-operator mode: the caller is the DB owner,
//   so all approved answers are disclosed (canSee = true). Use only for a
//   local, single-user MCP client against your own database.
// - otherwise             → fail closed: evidence-backed answers are redacted
//   (sme_testimony answers, which have no evidence to gate, still show).
const isMain = process.argv[1]?.endsWith('mcp/server.ts') || process.argv[1]?.endsWith('mcp/server.js');
if (isMain) {
  const dbPath = process.env.AA_DB_PATH ?? 'asked-and-answered.db';
  const trustLocal = process.env.AA_MCP_TRUST_LOCAL === '1';
  const server = buildMcpServer(AnswerLibrary.atPath(dbPath), {
    identity: process.env.AA_MCP_IDENTITY ?? 'local-operator',
    visibility: { canSee: async () => trustLocal },
  });
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(
    `asked-answered-mcp serving ${dbPath} over stdio — ` +
      (trustLocal ? 'LOCAL TRUST (all answers disclosed)' : 'fail-closed (evidence-backed answers redacted)'),
  );
}
