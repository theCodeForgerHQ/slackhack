import bolt from '@slack/bolt';
import { AnswerLibrary } from './core/library.js';
import { ConformalMatcher } from './core/conformal.js';
import { DEFAULT_CALIBRATION_PAIRS } from './core/calibrationData.js';
import calibrationArtifact from './core/calibration.json' with { type: 'json' };
import { EvidenceGraph } from './core/evidenceGraph.js';
import { Ledger } from './core/ledger.js';
import { LedgerV2 } from './core/ledgerV2.js';
import { QueryPlanner, RateBudget } from './core/planner.js';
import { parseCsv, parseText, parseXlsx } from './core/parse.js';
import { exportXlsx } from './core/export.js';
import { createDrafter } from './llm/index.js';
import { invariantHealthCheck } from './core/invariant.js';
import {
  answerCardBlocks,
  agentRunCardBlocks,
  planSummaryText,
  reviewTableBlocks,
  smeRequestBlocks,
  staleAlertBlocks,
} from './slack/blocks.js';
import { appHomeBlocks, gatherHomeStats } from './slack/appHome.js';
import { reviewModalView } from './slack/dataTable.js';
import { buildCanvasDocument } from './slack/canvasExport.js';
import { createCanvasOrFallback } from './slack/canvasCreate.js';
import { exportToSlackList } from './slack/listsExport.js';
import { registerWorkflowStep } from './slack/workflowStep.js';
import { verifyPipelineCodeLevel } from '../scripts/verifyPipelineCodeLevel.js';
import { verifyInvariantWithZ3 } from '../scripts/verifyInvariantZ3.js';
import { runQuestionnaire, ReviewSession, type RunDeps } from './slack/flows.js';
import { ActionTokenStore, SlackRtsClient } from './slack/rts.js';
import { Watcher } from './core/watcher.js';
import { ChannelMembershipChecker } from './slack/visibility.js';
import { InMemorySessionStore, SqliteSessionStore, type SessionStore } from './slack/sessionStore.js';
import { InMemoryUserTokenStore, SqliteUserTokenStore, type UserTokenStore, buildUserOAuthUrl } from './slack/oauth.js';
import {
  InMemoryInstallationStore,
  SqliteInstallationStore,
  type InstallationStore,
} from './slack/installStore.js';
import { buildInstallOAuthUrl, handleInstallOAuthCallback } from './slack/installOAuth.js';
import { probeCapabilities, type CapabilityMap } from './core/capabilityProbe.js';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const { App } = bolt;

function serveDoc(res: import('node:http').ServerResponse, relativePath: string): void {
  try {
    const md = readFileSync(resolve(relativePath), 'utf8');
    res.writeHead(200, { 'Content-Type': 'text/markdown; charset=utf-8' });
    res.end(md);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  }
}

function servePublicFile(res: import('node:http').ServerResponse, relativePath: string, contentType = 'text/html'): void {
  try {
    const data = readFileSync(resolve(relativePath), 'utf8');
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  } catch {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  }
}

/**
 * Asked & Answered — Bolt wiring (App A, internal install).
 *
 * Listeners follow the agent_view event model (post June 30 2026):
 * conversations live in the app's Messages tab; message.im carries user
 * turns; app_home_opened (tab=messages) greets first-time users.
 * TODO(S1): verify event payloads against the live sandbox and wire
 * chat.startStream / task cards / Data Table where available.
 */

function required(name: string): string {
  const v = process.env[name];
  if (!v) throw new Error(`${name} is required`);
  return v;
}

// Fail fast if the ledger's HMAC key is unset in a real deployment — a
// hardcoded fallback would defeat the dictionary-attack protection.
required('AA_LEDGER_KEY');

const dbPath = process.env.AA_DB_PATH ?? 'asked-and-answered.db';
const publicUrl = process.env.AA_PUBLIC_URL ?? '';

const installationStore: InstallationStore =
  process.env.AA_SESSION_STORE === 'memory'
    ? new InMemoryInstallationStore()
    : SqliteInstallationStore.atPath(dbPath.replace(/\.db$/, '-installations.db'));

const defaultCapabilities: CapabilityMap = {
  // Default to optimistic when no installation record exists yet, so
  // single-workspace deployments that boot with SLACK_BOT_TOKEN keep
  // behaving as before. The probe will downgrade these once it sees scopes.
  canvas: true,
  lists: true,
  dataTable: true,
  userSearch: false,
};
let capabilities: CapabilityMap = defaultCapabilities;

const socketMode = Boolean(process.env.SLACK_APP_TOKEN);
const app = new App({
  token: required('SLACK_BOT_TOKEN'),
  signingSecret: required('SLACK_SIGNING_SECRET'),
  socketMode,
  ...(socketMode ? { appToken: process.env.SLACK_APP_TOKEN! } : { endpoints: ['/slack/events', '/slack/actions'] }),
  port: Number(process.env.PORT ?? 3000),
  customRoutes: [
    {
      path: '/health',
      method: ['GET'],
      handler: (req, res) => {
        const accept = req.headers.accept ?? '';
        if (accept.includes('application/json')) {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ status: 'ok', capabilities }));
        } else {
          res.writeHead(200);
          res.end('ok');
        }
      },
    },
    {
      path: '/invariant',
      method: ['GET'],
      handler: async (_req, res) => {
        const result = await invariantHealthCheck();
        res.writeHead(result.status === 'pass' ? 200 : 500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result));
      },
    },
    {
      path: '/verify-ledger',
      method: ['GET'],
      handler: async (_req, res) => {
        const [v1, v2, invariant, abstractZ3, codeZ3] = await Promise.all([
          ledger.verify(),
          ledgerV2.verify(),
          invariantHealthCheck(),
          verifyInvariantWithZ3(),
          verifyPipelineCodeLevel(),
        ]);
        const ok = v1.ok && v2.ok && invariant.status === 'pass' && abstractZ3.proved && codeZ3.proved;
        res.writeHead(ok ? 200 : 500, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({
            status: ok ? 'ok' : 'failed',
            ledger: { version: 'legacy', ok: v1.ok, entriesChecked: v1.entriesChecked, firstBadSeq: v1.firstBadSeq },
            ledgerV2: { version: 'event-sourced', ok: v2.ok, entriesChecked: v2.entriesChecked, firstBadSeq: v2.firstBadSeq, metadataMismatch: v2.metadataMismatch },
            invariant: { ok: invariant.status === 'pass', casesRun: invariant.casesRun, detail: invariant.detail },
            proofs: {
              abstractZ3: { proved: abstractZ3.proved, status: abstractZ3.status, detail: abstractZ3.detail },
              codeLevelZ3: { proved: codeZ3.proved, status: codeZ3.status, detail: codeZ3.detail },
            },
          }),
        );
      },
    },
    {
      path: '/',
      method: ['GET'],
      handler: (_req, res) => {
        try {
          const html = readFileSync(resolve('public/index.html'), 'utf8');
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(html);
        } catch {
          res.writeHead(200);
          res.end('Asked & Answered');
        }
      },
    },
    {
      path: '/oauth/user',
      method: ['GET'],
      handler: async (req, res) => {
        // User OAuth callback for private-channel RTS scopes.
        const url = new URL(req.url ?? '/', `http://${req.headers.host}`);
        const code = url.searchParams.get('code');
        const state = url.searchParams.get('state') ?? '';
        const error = url.searchParams.get('error');
        if (error) {
          res.writeHead(400, { 'Content-Type': 'text/plain' });
          res.end(`OAuth error: ${error}`);
          return;
        }
        if (!code) {
          res.writeHead(400, { 'Content-Type': 'text/plain' });
          res.end('Missing OAuth code');
          return;
        }
        try {
          const clientId = process.env.SLACK_CLIENT_ID;
          const clientSecret = process.env.SLACK_CLIENT_SECRET;
          const redirectUri = process.env.AA_PUBLIC_URL
            ? `${process.env.AA_PUBLIC_URL}/oauth/user`
            : `http://localhost:${process.env.PORT ?? 3000}/oauth/user`;
          if (!clientId || !clientSecret) {
            res.writeHead(500, { 'Content-Type': 'text/plain' });
            res.end('Server missing OAuth credentials');
            return;
          }
          const tokenRes = await fetch('https://slack.com/api/oauth.v2.access', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ client_id: clientId, client_secret: clientSecret, code, redirect_uri: redirectUri }),
          });
          const tokenData = (await tokenRes.json()) as {
            ok?: boolean;
            error?: string;
            authed_user?: { id?: string; access_token?: string; scope?: string };
          };
          if (!tokenData.ok) {
            res.writeHead(400, { 'Content-Type': 'text/plain' });
            res.end(`Slack OAuth error: ${tokenData.error ?? 'unknown'}`);
            return;
          }
          const userId = tokenData.authed_user?.id;
          const accessToken = tokenData.authed_user?.access_token;
          const scopes = tokenData.authed_user?.scope?.split(',') ?? [];
          if (!userId || !accessToken) {
            res.writeHead(400, { 'Content-Type': 'text/plain' });
            res.end('OAuth response missing user token');
            return;
          }
          userTokenStore.saveUserToken(userId, accessToken, scopes);
          res.writeHead(200, { 'Content-Type': 'text/plain' });
          res.end('Private-channel search authorized. You can now return to Slack.');
        } catch (err) {
          res.writeHead(500, { 'Content-Type': 'text/plain' });
          res.end(`OAuth callback failed: ${(err as Error).message}`);
        }
      },
    },
    {
      path: '/slack/install',
      method: ['GET'],
      handler: (_req, res) => {
        const clientId = process.env.SLACK_CLIENT_ID;
        if (!clientId) {
          res.writeHead(500, { 'Content-Type': 'text/plain' });
          res.end('Server missing SLACK_CLIENT_ID');
          return;
        }
        const redirectUri = process.env.AA_PUBLIC_URL
          ? `${process.env.AA_PUBLIC_URL}/slack/oauth/callback`
          : `http://localhost:${process.env.PORT ?? 3000}/slack/oauth/callback`;
        const url = buildInstallOAuthUrl({
          clientId,
          redirectUri,
          stateSecret: process.env.SLACK_SIGNING_SECRET ?? '',
          teamId: process.env.SLACK_TEAM_ID,
        });
        res.writeHead(302, { Location: url });
        res.end();
      },
    },
    {
      path: '/slack/oauth/callback',
      method: ['GET'],
      handler: async (req, res) => {
        const clientId = process.env.SLACK_CLIENT_ID;
        const clientSecret = process.env.SLACK_CLIENT_SECRET;
        if (!clientId || !clientSecret) {
          res.writeHead(500, { 'Content-Type': 'text/plain' });
          res.end('Server missing OAuth credentials');
          return;
        }
        const redirectUri = process.env.AA_PUBLIC_URL
          ? `${process.env.AA_PUBLIC_URL}/slack/oauth/callback`
          : `http://localhost:${process.env.PORT ?? 3000}/slack/oauth/callback`;
        const successUrl = process.env.AA_PUBLIC_URL
          ? `${process.env.AA_PUBLIC_URL}/slack/install/success`
          : `http://localhost:${process.env.PORT ?? 3000}/slack/install/success`;
        await handleInstallOAuthCallback(req, res, {
          installationStore,
          clientId,
          clientSecret,
          redirectUri,
          stateSecret: process.env.SLACK_SIGNING_SECRET ?? '',
          successUrl,
        });
      },
    },
    {
      path: '/slack/install/success',
      method: ['GET'],
      handler: (_req, res) => {
        try {
          const html = readFileSync(resolve('public/install-success.html'), 'utf8');
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end(html);
        } catch {
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end('<h1>Installation successful</h1><p>You can now return to Slack.</p>');
        }
      },
    },
    {
      path: '/docs/SUBMISSION.md',
      method: ['GET'],
      handler: (_req, res) => serveDoc(res, 'docs/SUBMISSION.md'),
    },
    {
      path: '/docs/IMPACT.md',
      method: ['GET'],
      handler: (_req, res) => serveDoc(res, 'docs/IMPACT.md'),
    },
    {
      path: '/docs/EVALS.md',
      method: ['GET'],
      handler: (_req, res) => serveDoc(res, 'docs/EVALS.md'),
    },
    {
      path: '/case-studies/',
      method: ['GET'],
      handler: (_req, res) => servePublicFile(res, 'public/case-studies/index.html'),
    },
    {
      path: '/case-studies/soc2-renewal.html',
      method: ['GET'],
      handler: (_req, res) => servePublicFile(res, 'public/case-studies/soc2-renewal.html'),
    },
    {
      path: '/case-studies/fintech-vendor.html',
      method: ['GET'],
      handler: (_req, res) => servePublicFile(res, 'public/case-studies/fintech-vendor.html'),
    },
    {
      path: '/case-studies/enterprise-rfp.html',
      method: ['GET'],
      handler: (_req, res) => servePublicFile(res, 'public/case-studies/enterprise-rfp.html'),
    },
    {
      path: '/case-studies/internal-audit.html',
      method: ['GET'],
      handler: (_req, res) => servePublicFile(res, 'public/case-studies/internal-audit.html'),
    },
    {
      path: '/safety-report',
      method: ['GET'],
      handler: (_req, res) => servePublicFile(res, 'public/safety-report.html'),
    },
  ],
});

// V3 components: evidence graph + conformal matcher power the approved library.
const graph = new EvidenceGraph();
const matcher = new ConformalMatcher();
const conformalLoaded = matcher.loadArtifact(calibrationArtifact);
if (!conformalLoaded) {
  console.warn('Conformal calibration artifact invalid; falling back to in-memory pairs.');
  matcher.calibrate(DEFAULT_CALIBRATION_PAIRS);
}
const library = AnswerLibrary.atPath(dbPath, graph, matcher);
library.rebuildGraph(); // re-index existing DB answers for stale-evidence detection

const ledger = Ledger.atPath(dbPath.replace(/\.db$/, '-ledger.db'));
const ledgerV2 = LedgerV2.atPath(dbPath.replace(/\.db$/, '-ledger-v2.db'));
const tokens = new ActionTokenStore();
const drafter = createDrafter();

const sessionStore: SessionStore =
  process.env.AA_SESSION_STORE === 'memory'
    ? new InMemorySessionStore()
    : SqliteSessionStore.atPath(dbPath.replace(/\.db$/, '-sessions.db'));

const userTokenStore: UserTokenStore =
  process.env.AA_SESSION_STORE === 'memory'
    ? new InMemoryUserTokenStore()
    : SqliteUserTokenStore.atPath(dbPath.replace(/\.db$/, '-user-tokens.db'));

registerWorkflowStep({
  app,
  library,
  ledger,
  ledgerV2,
  llm: drafter,
  visibility: new ChannelMembershipChecker(async (channelId) => {
    const members: string[] = [];
    let cursor: string | undefined;
    do {
      const page = await app.client.conversations.members({ channel: channelId, limit: 200, ...(cursor ? { cursor } : {}) });
      members.push(...(page.members ?? []));
      cursor = page.response_metadata?.next_cursor || undefined;
    } while (cursor);
    return members;
  }),
  planner: new QueryPlanner(new SlackRtsClient((method, args) => app.client.apiCall(method, args), tokens, process.env.SLACK_BOT_USER_ID ?? 'U_WORKFLOW'), {
    budget: new RateBudget({ maxPerWindow: 9, windowMs: 60_000 }),
    sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  }),
});

/**
 * Sessions keyed by runId (unique per questionnaire run), so a stale button
 * from an earlier run in the same thread can never resolve to a newer run.
 * TTL-evicted to bound memory.
 */
const SESSION_TTL_MS = 6 * 60 * 60 * 1000;

function putSession(session: ReviewSession): void {
  sessionStore.prune(SESSION_TTL_MS);
  sessionStore.save({
    runId: session.runId,
    requesterId: session.requesterId,
    results: session.results,
    counts: session.recount(),
    confirmedQuestionIds: Array.from(session.confirmedQuestionIds),
    confirmedBy: Object.fromEntries(session.confirmedBy),
    updatedAt: new Date().toISOString(),
  });
}

/** Parse a button value of the form `runId:questionId`. */
function parseValue(value: string | undefined): { runId: string; questionId: string } | undefined {
  if (!value) return undefined;
  const idx = value.indexOf(':');
  if (idx === -1) return undefined;
  return { runId: value.slice(0, idx), questionId: value.slice(idx + 1) };
}

/** Resolve the session a button belongs to (by its embedded runId). Expired
 *  sessions are evicted at lookup time so a stale button stops working after TTL. */
function sessionForValue(
  value: string | undefined,
  actorUserId: string,
): { session: ReviewSession; questionId: string } | undefined {
  const parsed = parseValue(value);
  if (!parsed) return undefined;
  const record = sessionStore.load(parsed.runId);
  if (!record) return undefined;
  if (Date.now() - new Date(record.updatedAt).getTime() > SESSION_TTL_MS) {
    sessionStore.delete(parsed.runId);
    return undefined;
  }
  const session = ReviewSession.fromState(record, depsForUser(actorUserId));
  return { session, questionId: parsed.questionId };
}

function depsForUser(userId: string): RunDeps {
  const userToken = userTokenStore.getUserToken(userId);
  const rts = new SlackRtsClient(
    (method, args) => app.client.apiCall(method, args),
    tokens,
    userId,
    userToken,
  );
  const membership = new ChannelMembershipChecker(async (channelId) => {
    const members: string[] = [];
    let cursor: string | undefined;
    do {
      const page = await app.client.conversations.members({ channel: channelId, limit: 200, ...(cursor ? { cursor } : {}) });
      members.push(...(page.members ?? []));
      cursor = page.response_metadata?.next_cursor || undefined;
    } while (cursor);
    return members;
  });
  return {
    library,
    ledger,
    ledgerV2,
    llm: drafter,
    visibility: membership,
    planner: new QueryPlanner(rts, {
      budget: new RateBudget({ maxPerWindow: 9, windowMs: 60_000 }),
      sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
      cache: {
        ttlMs: Number(process.env.AA_RTS_CACHE_TTL_MS ?? 300_000),
        signature: () => graph.stateSignature(),
        requesterId: userId,
      },
    }),
  };
}

const WELCOME =
  'Hi — I turn questionnaires into evidence-cited answers from this workspace.\n' +
  '• Upload an *.xlsx/.csv* questionnaire or paste questions here.\n' +
  '• I only answer what the workspace can prove — everything else goes to a human.\n' +
  '• `verify ledger` checks the tamper-evident approval trail.';

app.event('app_home_opened', async ({ event, client }) => {
  const tab = (event as { tab?: string }).tab;
  const userId = (event as { user?: string }).user ?? '';

  if (tab === 'home') {
    const deps = depsForUser(userId);
    const stats = await gatherHomeStats(library, ledgerV2, userId, deps.visibility, sessionStore.countOpenReviews());
    const invariant = await invariantHealthCheck();
    stats.invariantOk = invariant.status === 'pass';
    const homeOpts: { invariantCheckUrl?: string; verifyLedgerUrl?: string; useDataTable?: boolean } = { useDataTable: capabilities.dataTable };
    if (process.env.AA_PUBLIC_URL) {
      homeOpts.invariantCheckUrl = `${process.env.AA_PUBLIC_URL}/invariant`;
      homeOpts.verifyLedgerUrl = `${process.env.AA_PUBLIC_URL}/verify-ledger`;
    }
    try {
      await client.views.publish({
        user_id: userId,
        view: {
          type: 'home',
          blocks: appHomeBlocks(stats, homeOpts) as never,
        },
      });
    } catch {
      /* App Home render is cosmetic */
    }
    return;
  }

  if (tab === 'messages') {
    // Greet only if the conversation is empty (best-effort; ignore failures).
    try {
      const history = await client.conversations.history({ channel: event.channel ?? '', limit: 1 });
      if ((history.messages ?? []).length === 0) {
        await client.chat.postMessage({ channel: event.channel ?? '', text: WELCOME });
      }
    } catch {
      /* greeting is cosmetic */
    }
  }
});

app.event('assistant_thread_context_changed', async ({ body }) => {
  // Entity context (what the user is viewing) — recorded for future scoping.
  void body;
});

app.event('assistant_thread_started', async ({ event, client }) => {
  // Greet the user when they open a new assistant thread.
  try {
    const channelId = (event as { channel_id?: string }).channel_id;
    if (channelId) {
      await client.chat.postMessage({ channel: channelId, text: WELCOME });
    }
  } catch {
    /* greeting is cosmetic */
  }
});

app.message(async ({ message, client }) => {
  const msg = message as {
    channel: string;
    channel_type?: string;
    user?: string;
    text?: string;
    ts: string;
    thread_ts?: string;
    files?: Array<{ url_private_download?: string; filetype?: string; name?: string }>;
    assistant_thread?: { action_token?: string };
    bot_id?: string;
  };
  if (msg.bot_id || !msg.user || msg.channel_type !== 'im') return;

  // Harvest the action token for RTS (spike S2 verifies exact location).
  const token = (msg as unknown as Record<string, unknown>).action_token;
  if (typeof token === 'string') tokens.record(msg.user, token);
  if (msg.assistant_thread?.action_token) tokens.record(msg.user, msg.assistant_thread.action_token);

  const threadTs = msg.thread_ts ?? msg.ts;
  const say = (text: string, blocks?: unknown[]) =>
    client.chat.postMessage({
      channel: msg.channel,
      thread_ts: threadTs,
      text,
      ...(blocks ? { blocks: blocks as never } : {}),
    });

  // `verify ledger` command surface (works in DM without a slash command).
  if ((msg.text ?? '').trim().toLowerCase() === 'verify ledger') {
    const v1 = ledger.verify();
    const v2 = ledgerV2.verify();
    const ok = v1.ok && v2.ok;
    await say(
      'Ledger verification',
      [
        {
          type: 'section',
          text: {
            type: 'mrkdwn',
            text: ok
              ? `:white_check_mark: *Ledgers intact.* Legacy: ${v1.entriesChecked} entries. Event-sourced: ${v2.entriesChecked} entries.`
              : `:rotating_light: *Ledger verification FAILED.* Legacy ok=${v1.ok} (seq ${v1.firstBadSeq ?? '-'}); event-sourced ok=${v2.ok} (seq ${v2.firstBadSeq ?? '-'}; ${v2.metadataMismatch ?? ''})`,
          },
        },
      ] as unknown[],
    );
    return;
  }

  // Intake: attached questionnaire file, or pasted questions.
  let parsed;
  const file = msg.files?.[0];
  try {
    if (file?.url_private_download) {
      const response = await fetch(file.url_private_download, {
        headers: { Authorization: `Bearer ${process.env.SLACK_BOT_TOKEN}` },
        signal: AbortSignal.timeout(15_000),
      });
      const MAX_BYTES = 10 * 1024 * 1024;
      const declared = Number(response.headers.get('content-length') ?? '0');
      if (declared > MAX_BYTES) throw new Error('file too large (max 10 MB)');
      const buf = Buffer.from(await response.arrayBuffer());
      if (buf.length > MAX_BYTES) throw new Error('file too large (max 10 MB)');
      parsed =
        file.filetype === 'csv' || file.name?.endsWith('.csv')
          ? parseCsv(buf.toString('utf8'))
          : await parseXlsx(buf);
    } else if (msg.text && msg.text.trim().length > 0) {
      parsed = parseText(msg.text);
    } else {
      return;
    }
  } catch (err) {
    await say(`I couldn't read that file (${(err as Error).message}). xlsx and csv are supported.`);
    return;
  }

  if (parsed.questions.length === 0) {
    await say("I didn't find any questions in that. Upload an xlsx/csv questionnaire or paste the questions as text.");
    return;
  }

  try {
    const session = await runQuestionnaire(parsed, msg.user, depsForUser(msg.user), (progress) => {
      void say(progress);
    });
    putSession(session);
    await say(planSummaryText(session.counts));
    await say('Review', reviewTableBlocks(session.results, { page: 0, runId: session.runId }) as unknown[]);

    // Default audit artifact: native Canvas when scope is present.
    if (process.env.AA_AUTO_CANVAS !== '0') {
      try {
        const doc = buildCanvasDocument(session.results, {
          runId: session.runId,
          requesterId: msg.user,
          title: 'Decision Log — Asked & Answered',
          decisionLog: true,
        });
        const channel = (msg as { channel?: string }).channel ?? '';
        const thread = (msg as { ts?: string }).ts ?? '';
        if (channel) {
          const canvasResult = await createCanvasOrFallback(
            app.client,
            channel,
            thread || undefined,
            doc,
            { forceFallback: !capabilities.canvas },
          );
          await app.client.chat.postMessage({
            channel,
            ...(thread ? { thread_ts: thread } : {}),
            text: canvasResult.message,
          });
        }
      } catch (err) {
        console.error('auto canvas export failed', err);
      }
    }
  } catch (err) {
    await say(`Something went wrong during the run: ${(err as Error).message}`);
  }
});

/** Shorthand for the channel/thread on an interaction body. */
function target(body: unknown): { channel: string; thread: string } | undefined {
  const b = body as { channel?: { id?: string }; message?: { thread_ts?: string; ts?: string } };
  if (!b.channel?.id) return undefined;
  return { channel: b.channel.id, thread: b.message?.thread_ts ?? b.message?.ts ?? '' };
}

app.action('open_answer_card', async ({ ack, body, client, action }) => {
  await ack();
  try {
    const actorUserId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue((action as { value?: string }).value, actorUserId);
    const t = target(body);
    if (!resolved || !t) return;
    const result = resolved.session.results.find((r) => r.questionId === resolved.questionId);
    if (!result) return;
    const confirmed = resolved.session.confirmedQuestionIds.has(resolved.questionId);
    await client.chat.postMessage({
      channel: t.channel,
      thread_ts: t.thread,
      text: result.questionText,
      blocks: answerCardBlocks(result, resolved.session.runId, confirmed) as never,
    });
  } catch (err) {
    console.error('open_answer_card failed', err);
  }
});

app.action('open_run_card', async ({ ack, body, client, action }) => {
  await ack();
  try {
    const actorUserId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue((action as { value?: string }).value, actorUserId);
    const t = target(body);
    if (!resolved || !t) return;
    const result = resolved.session.results.find((r) => r.questionId === resolved.questionId);
    if (!result) return;
    const signatures = {
      timestamp: new Date().toISOString(),
      confirmActor: resolved.session.confirmedQuestionIds.has(resolved.questionId) ? actorUserId : undefined,
      approveActor: result.approvedBy,
    };
    await client.chat.postMessage({
      channel: t.channel,
      thread_ts: t.thread,
      text: `Agent Run Card — ${result.questionText}`,
      blocks: agentRunCardBlocks(result, resolved.session.runId, signatures, publicUrl) as never,
    });
  } catch (err) {
    console.error('open_run_card failed', err);
  }
});

app.action('table_next_page', async ({ ack, body, client, action }) => {
  await ack();
  try {
    const actorUserId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue((action as { value?: string }).value, actorUserId);
    const page = Number(parseValue((action as { value?: string }).value)?.questionId ?? '0');
    const t = target(body);
    if (!resolved || !t || Number.isNaN(page)) return;
    await client.chat.postMessage({
      channel: t.channel,
      thread_ts: t.thread,
      text: 'Review (continued)',
      blocks: reviewTableBlocks(resolved.session.results, { page, runId: resolved.session.runId }) as never,
    });
  } catch (err) {
    console.error('table_next_page failed', err);
  }
});

for (const [actionId, verb] of [
  ['approve_answer', 'approve'],
  ['reject_answer', 'reject'],
] as const) {
  app.action(actionId, async ({ ack, body, client, action }) => {
    await ack();
    const userId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue((action as { value?: string }).value, userId);
    const t = target(body);
    if (!resolved || !t) return;
    try {
      let text: string;
      if (verb === 'approve') {
        const resultBefore = resolved.session.results.find((r) => r.questionId === resolved.questionId);
        resolved.session.approve(resolved.questionId, userId, resolved.session.runId);
        const resultAfter = resolved.session.results.find((r) => r.questionId === resolved.questionId);
        if (resultAfter?.state === 'verified') {
          text = `:white_check_mark: Approved by <@${userId}> — saved to the answer library.\n${planSummaryText(resolved.session.recount())}`;
        } else {
          text = `:memo: Approved by <@${userId}> — this high-sensitivity answer needs one more distinct approver before it enters the library.\n${planSummaryText(resolved.session.recount())}`;
        }
      } else {
        resolved.session.reject(resolved.questionId, userId, resolved.session.runId);
        text = `:no_entry: Rejected by <@${userId}> — routed back to humans.\n${planSummaryText(resolved.session.recount())}`;
      }
      putSession(resolved.session);
      await client.chat.postMessage({
        channel: t.channel,
        thread_ts: t.thread,
        text,
      });
    } catch (err) {
      await client.chat.postMessage({
        channel: t.channel,
        thread_ts: t.thread,
        text: (err as Error).message,
      });
    }
  });
}

app.action('confirm_answer', async ({ ack, body, client, action }) => {
  await ack();
  const userId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
  const resolved = sessionForValue((action as { value?: string }).value, userId);
  const t = target(body);
  if (!resolved || !t) return;
  try {
    resolved.session.confirm(resolved.questionId, userId, resolved.session.runId);
    putSession(resolved.session);
    const counts = resolved.session.recount();
    await client.chat.postMessage({
      channel: t.channel,
      thread_ts: t.thread,
      text: `:memo: Confirmed by <@${userId}> — this answer is now ready for final approval by a different human.\n${planSummaryText(counts)}`,
    });
  } catch (err) {
    await client.chat.postMessage({
      channel: t.channel,
      thread_ts: t.thread,
      text: (err as Error).message,
    });
  }
});

app.action('route_to_sme', async ({ ack, body, client, action }) => {
  await ack();
  try {
    const value = (action as { value?: string }).value;
    const requester = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue(value, requester);
    const t = target(body);
    if (!resolved || !t) return;
    const result = resolved.session.results.find((r) => r.questionId === resolved.questionId);
    if (!result) return;
    await client.chat.postMessage({
      channel: t.channel,
      thread_ts: t.thread,
      text: 'Pick the expert to ask',
      blocks: [
        {
          type: 'section',
          text: { type: 'mrkdwn', text: `Who should answer:\n*${result.questionText}*` },
          accessory: {
            type: 'users_select',
            action_id: 'sme_selected',
            placeholder: { type: 'plain_text', text: 'Choose an expert' },
          },
        },
        {
          type: 'context',
          // Carry the runId:questionId so the pick resolves to the exact run.
          elements: [{ type: 'mrkdwn', text: `ref:${value} requester:<@${requester}>` }],
        },
      ] as never,
    });
  } catch (err) {
    console.error('route_to_sme failed', err);
  }
});

app.action('sme_selected', async ({ ack, body, client, action }) => {
  await ack();
  try {
    const smeId = (action as { selected_user?: string }).selected_user;
    const b = body as {
      user?: { id?: string };
      channel?: { id?: string };
      message?: { thread_ts?: string; ts?: string; blocks?: Array<{ elements?: Array<{ text?: string }> }> };
    };
    const actorUserId = b.user?.id ?? 'unknown';
    const contextText = b.message?.blocks?.find((bl) => bl.elements)?.elements?.[0]?.text ?? '';
    const ref = /ref:(\S+)/.exec(contextText)?.[1];
    const resolved = sessionForValue(ref, actorUserId);
    if (!smeId || !resolved) return;
    const result = resolved.session.results.find((r) => r.questionId === resolved.questionId);
    if (!result) return;

    const dm = await client.conversations.open({ users: smeId });
    if (dm.channel?.id) {
      await client.chat.postMessage({
        channel: dm.channel.id,
        text: `You've been asked to answer a questionnaire question`,
        blocks: smeRequestBlocks({
          questionText: result.questionText,
          requesterId: b.user?.id ?? 'unknown',
          ref: ref ?? '',
        }) as never,
      });
    }
    const t = target(body);
    if (t) {
      await client.chat.postMessage({
        channel: t.channel,
        thread_ts: t.thread,
        text: `:incoming_envelope: Routed to <@${smeId}>.`,
      });
    }
  } catch (err) {
    console.error('sme_selected failed', err);
  }
});

app.action('sme_provide_answer', async ({ ack, body, client, action }) => {
  await ack();
  try {
    // value is the runId:questionId ref threaded from smeRequestBlocks.
    const ref = (action as { value?: string }).value ?? '';
    await openAnswerModal(client, (body as { trigger_id: string }).trigger_id, 'sme_answer_modal', ref, '');
  } catch (err) {
    console.error('sme_provide_answer failed', err);
  }
});

app.action('edit_answer', async ({ ack, body, client, action }) => {
  await ack();
  try {
    const value = (action as { value?: string }).value;
    const actorUserId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue(value, actorUserId);
    if (!resolved) return;
    const result = resolved.session.results.find((r) => r.questionId === resolved.questionId);
    await openAnswerModal(client, (body as { trigger_id: string }).trigger_id, 'edit_answer_modal', value ?? '', result?.answerText ?? '');
  } catch (err) {
    console.error('edit_answer failed', err);
  }
});

app.view('sme_answer_modal', async ({ ack, body, view }) => {
  await ack();
  try {
    const resolved = sessionForValue(view.private_metadata, body.user.id);
    const answer = view.state.values.answer_block?.answer_input?.value ?? '';
    if (!resolved || !answer.trim()) return;
    resolved.session.smeProvide(resolved.questionId, body.user.id, answer, resolved.session.runId);
    putSession(resolved.session);
  } catch (err) {
    console.error('sme_answer_modal failed', err);
  }
});

app.view('edit_answer_modal', async ({ ack, body, view }) => {
  await ack();
  try {
    const resolved = sessionForValue(view.private_metadata, body.user.id);
    const answer = view.state.values.answer_block?.answer_input?.value ?? '';
    if (!resolved || !answer.trim()) return;
    resolved.session.edit(resolved.questionId, body.user.id, answer, resolved.session.runId);
    putSession(resolved.session);
  } catch (err) {
    console.error('edit_answer_modal failed', err);
  }
});

app.action('export_xlsx', async ({ ack, body, client, action }) => {
  await ack();
  const t = target(body);
  try {
    // export button value is `runId:` (no question); fall back to any-in-thread not needed.
    const actorUserId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue((action as { value?: string }).value, actorUserId);
    if (!resolved || !t) return;
    const buf = await exportXlsx(resolved.session.results);
    await client.files.uploadV2({
      channel_id: t.channel,
      thread_ts: t.thread,
      filename: 'questionnaire-asked-and-answered.xlsx',
      file: buf,
      initial_comment: 'Completed questionnaire — every answer cited and approval-logged.',
    });
  } catch (err) {
    if (t) await client.chat.postMessage({ channel: t.channel, thread_ts: t.thread, text: `Export failed: ${(err as Error).message}` });
  }
});

app.action('open_review_modal', async ({ ack, body, client, action }) => {
  await ack();
  try {
    const actorUserId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue((action as { value?: string }).value, actorUserId);
    if (!resolved) return;
    await client.views.open({
      trigger_id: (body as { trigger_id: string }).trigger_id,
      view: reviewModalView(resolved.session.results, {
        runId: resolved.session.runId,
        title: 'Questionnaire review',
        useDataTable: capabilities.dataTable,
      }) as never,
    });
  } catch (err) {
    console.error('open_review_modal failed', err);
  }
});

app.action('export_canvas', async ({ ack, body, client, action }) => {
  await ack();
  const t = target(body);
  try {
    const actorUserId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue((action as { value?: string }).value, actorUserId);
    if (!resolved || !t) return;
    const doc = buildCanvasDocument(resolved.session.results, {
      runId: resolved.session.runId,
      requesterId: resolved.session.requesterId,
      title: 'Decision Log — Asked & Answered',
      decisionLog: true,
    });
    const result = await createCanvasOrFallback(client, t.channel, t.thread, doc, {
      forceFallback: !capabilities.canvas,
    });
    await client.chat.postMessage({
      channel: t.channel,
      thread_ts: t.thread,
      text: result.message,
    });
  } catch (err) {
    if (t) await client.chat.postMessage({ channel: t.channel, thread_ts: t.thread, text: `Canvas export failed: ${(err as Error).message}` });
  }
});

app.action('export_list', async ({ ack, body, client, action }) => {
  await ack();
  const t = target(body);
  try {
    const actorUserId = (body as { user?: { id?: string } }).user?.id ?? 'unknown';
    const resolved = sessionForValue((action as { value?: string }).value, actorUserId);
    if (!resolved || !t) return;
    if (!capabilities.lists) {
      await client.chat.postMessage({
        channel: t.channel,
        thread_ts: t.thread,
        text: ':warning: Slack List export is unavailable in this workspace (`lists:write` scope missing). Try Export xlsx or Canvas.',
      });
      return;
    }
    const result = await exportToSlackList(client, resolved.session.results, {
      runId: resolved.session.runId,
      requesterId: resolved.session.requesterId,
      title: 'Questionnaire — Asked & Answered',
    });
    await client.chat.postMessage({
      channel: t.channel,
      thread_ts: t.thread,
      text: result.ok
        ? `:clipboard: Exported to Slack List${result.listId ? ` (ID \`${result.listId}\`)` : ''}.`
        : `:warning: Slack List export unavailable (${result.fallbackReason}). Try Export xlsx or Canvas.`,
    });
  } catch (err) {
    if (t) await client.chat.postMessage({ channel: t.channel, thread_ts: t.thread, text: `List export failed: ${(err as Error).message}` });
  }
});

app.action('apphome_run_questionnaire', async ({ ack, body, client }) => {
  await ack();
  const userId = (body as { user?: { id?: string } }).user?.id;
  if (!userId) return;
  try {
    const dm = await client.conversations.open({ users: userId });
    if (dm.channel?.id) {
      await client.chat.postMessage({ channel: dm.channel.id, text: WELCOME });
    }
  } catch (err) {
    console.error('apphome_run_questionnaire failed', err);
  }
});

app.action('apphome_verify_ledger', async ({ ack, body, client }) => {
  await ack();
  const userId = (body as { user?: { id?: string } }).user?.id;
  if (!userId) return;
  const v1 = ledger.verify();
  const v2 = ledgerV2.verify();
  const ok = v1.ok && v2.ok;
  try {
    await client.views.publish({
      user_id: userId,
      view: {
        type: 'home',
        blocks: [
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: ok
                ? `:white_check_mark: *Ledgers intact.* Legacy: ${v1.entriesChecked} entries. Event-sourced: ${v2.entriesChecked} entries.`
                : `:rotating_light: *Ledger verification FAILED.* Legacy ok=${v1.ok} (seq ${v1.firstBadSeq ?? '-'}); event-sourced ok=${v2.ok} (seq ${v2.firstBadSeq ?? '-'}; ${v2.metadataMismatch ?? ''})`,
            },
          },
          {
            type: 'actions',
            elements: [
              {
                type: 'button',
                action_id: 'apphome_return_home',
                text: { type: 'plain_text', text: 'Back to dashboard' },
              },
            ],
          },
        ] as never,
      },
    });
  } catch (err) {
    console.error('apphome_verify_ledger failed', err);
  }
});

app.action('apphome_check_invariant', async ({ ack, body, client }) => {
  await ack();
  const userId = (body as { user?: { id?: string } }).user?.id;
  if (!userId) return;
  const result = await invariantHealthCheck();
  try {
    await client.views.publish({
      user_id: userId,
      view: {
        type: 'home',
        blocks: [
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text:
                result.status === 'pass'
                  ? `:white_check_mark: *Permission invariant holds.*\n> Answer text is returned to a requester only if that requester can currently see every citation backing the answer.`
                  : `:rotating_light: *Permission invariant FAILED.*\n> Answer text is returned to a requester only if that requester can currently see every citation backing the answer.`,
            },
          },
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text: `Z3 proof: \`scripts/verifyInvariantZ3.ts\` — the negation of the invariant is unsatisfiable under the safety model.`,
            },
          },
          {
            type: 'actions',
            elements: [
              {
                type: 'button',
                action_id: 'apphome_return_home',
                text: { type: 'plain_text', text: 'Back to dashboard' },
              },
            ],
          },
        ] as never,
      },
    });
  } catch (err) {
    console.error('apphome_check_invariant failed', err);
  }
});

app.action('run_z3_verify', async ({ ack, body, client }) => {
  await ack();
  const userId = (body as { user?: { id?: string } }).user?.id;
  if (!userId) return;
  const result = await verifyPipelineCodeLevel();
  try {
    await client.views.publish({
      user_id: userId,
      view: {
        type: 'home',
        blocks: [
          {
            type: 'section',
            text: {
              type: 'mrkdwn',
              text:
                result.proved
                  ? `:white_check_mark: *Code-level invariant proof holds.*\nZ3 returned \`${result.status}\`.\n> ${result.detail}`
                  : `:rotating_light: *Code-level invariant proof FAILED.*\n> ${result.detail}`,
            },
          },
          {
            type: 'actions',
            elements: [
              {
                type: 'button',
                action_id: 'apphome_return_home',
                text: { type: 'plain_text', text: 'Back to dashboard' },
              },
            ],
          },
        ] as never,
      },
    });
  } catch (err) {
    console.error('run_z3_verify failed', err);
  }
});

app.action('apphome_return_home', async ({ ack, body, client }) => {
  await ack();
  const userId = (body as { user?: { id?: string } }).user?.id;
  if (!userId) return;
  const deps = depsForUser(userId);
  const stats = await gatherHomeStats(library, ledgerV2, userId, deps.visibility, sessionStore.countOpenReviews());
  const invariant = await invariantHealthCheck();
  stats.invariantOk = invariant.status === 'pass';
  const homeOpts: { invariantCheckUrl?: string; verifyLedgerUrl?: string; useDataTable?: boolean } = { useDataTable: capabilities.dataTable };
  if (process.env.AA_PUBLIC_URL) {
    homeOpts.invariantCheckUrl = `${process.env.AA_PUBLIC_URL}/invariant`;
    homeOpts.verifyLedgerUrl = `${process.env.AA_PUBLIC_URL}/verify-ledger`;
  }
  try {
    await client.views.publish({
      user_id: userId,
      view: {
        type: 'home',
        blocks: appHomeBlocks(stats, homeOpts) as never,
      },
    });
  } catch (err) {
    console.error('apphome_return_home failed', err);
  }
});

/** Opens the shared answer-input modal, prefilled and tagged with a run ref. */
async function openAnswerModal(
  client: typeof app.client,
  triggerId: string,
  callbackId: string,
  ref: string,
  initial: string,
): Promise<void> {
  await client.views.open({
    trigger_id: triggerId,
    view: {
      type: 'modal',
      callback_id: callbackId,
      private_metadata: ref,
      title: { type: 'plain_text', text: 'Provide an answer' },
      submit: { type: 'plain_text', text: 'Approve & save' },
      blocks: [
        {
          type: 'input',
          block_id: 'answer_block',
          label: { type: 'plain_text', text: 'Your answer (saved as Verified)' },
          element: {
            type: 'plain_text_input',
            action_id: 'answer_input',
            multiline: true,
            ...(initial ? { initial_value: initial } : {}),
          },
        },
      ],
    },
  });
}


// Proactive stale/contradiction watcher: DM the original approver when an
// approved answer is contradicted or superseded by newer workspace evidence.
const watcher = new Watcher(library, graph, {
  intervalMs: Number(process.env.AA_WATCHER_INTERVAL_MS ?? 3_600_000),
  onStale: async (alert) => {
    try {
      const dm = await app.client.conversations.open({ users: alert.approvedBy });
      if (!dm.channel?.id) return;
      await app.client.chat.postMessage({
        channel: dm.channel.id,
        text: `Stale answer detected: ${alert.questionText}`,
        blocks: staleAlertBlocks(alert) as never,
      });
    } catch (err) {
      console.error('watcher stale DM failed', err);
    }
  },
});
watcher.start();

app.action('open_stale_review_modal', async ({ ack, body, client, action }) => {
  await ack();
  try {
    const answerId = Number((action as { value?: string }).value);
    if (Number.isNaN(answerId)) return;
    const answer = library.getById(answerId);
    if (!answer) return;
    const result = {
      questionId: String(answer.id),
      questionText: answer.questionText,
      state: 'verified' as const,
      answerText: answer.answerText,
      citations: answer.citations,
      approvedBy: answer.approvedBy,
      approvedAt: answer.approvedAt,
    };
    await client.views.open({
      trigger_id: (body as { trigger_id: string }).trigger_id,
      view: {
        type: 'modal',
        title: { type: 'plain_text', text: 'Stale answer review' },
        blocks: answerCardBlocks(result, '', true) as never,
      },
    });
  } catch (err) {
    console.error('open_stale_review_modal failed', err);
  }
});

// Probe Slack capabilities once at startup. Failures are logged but never
// prevent the app from starting; call sites fall back to safe behavior.
try {
  capabilities = await probeCapabilities({
    client: app.client,
    installationStore,
    userTokenStore,
    teamId: process.env.SLACK_TEAM_ID,
    probeUserId: process.env.AA_PROBE_USER_ID,
  });
  console.log('Capability probe complete', capabilities);
} catch (err) {
  console.error('Capability probe failed, using defaults', err);
}

const port = Number(process.env.PORT ?? 3000);
await app.start(port);
console.log(`⚡ Asked & Answered running (${process.env.SLACK_APP_TOKEN ? 'socket mode' : `http :${port}`})`);
