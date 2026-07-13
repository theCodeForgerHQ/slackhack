import type { IncomingMessage, ServerResponse } from 'node:http';
import type { InstallationStore } from './installStore.js';

/**
 * App-level OAuth v2 install flow helpers.
 *
 * These functions build the "Add to Slack" URL and handle the callback so the
 * Bolt receiver can stay small. The user-scope flow remains in oauth.ts.
 */

/** Bot scopes required by the app manifest. Keep in sync with slack/manifest.json. */
export const INSTALL_BOT_SCOPES = [
  'assistant:write',
  'chat:write',
  'chat:write.public',
  'channels:read',
  'channels:manage',
  'groups:read',
  'groups:write',
  'files:read',
  'files:write',
  'search:read.public',
  'canvases:write',
  'users:read',
  'im:history',
  'im:read',
  'im:write',
];

export interface BuildInstallOAuthUrlArgs {
  clientId: string;
  redirectUri: string;
  stateSecret: string;
  /** Optional team hint to restrict the install to a specific workspace. */
  teamId?: string | undefined;
}

export interface InstallOAuthCallbackDeps {
  installationStore: InstallationStore;
  clientId: string;
  clientSecret: string;
  redirectUri: string;
  stateSecret: string;
  /** Where to redirect after a successful install. */
  successUrl: string;
  /** Override fetch for tests. */
  fetcher?: typeof fetch;
}

function makeState(secret: string): string {
  const payload = `${secret}:${Date.now()}`;
  return Buffer.from(payload).toString('base64url');
}

function validateState(state: string, secret: string): boolean {
  try {
    const payload = Buffer.from(state, 'base64url').toString('utf8');
    const [prefix, ts] = payload.split(':');
    if (prefix !== secret) return false;
    const ageMs = Date.now() - Number(ts);
    // 10-minute window to account for slow approval pages.
    return !Number.isNaN(ageMs) && ageMs >= 0 && ageMs <= 10 * 60 * 1000;
  } catch {
    return false;
  }
}

/**
 * Builds the Slack OAuth v2 authorization URL that starts an app-level install.
 */
export function buildInstallOAuthUrl(args: BuildInstallOAuthUrlArgs): string {
  const params = new URLSearchParams({
    client_id: args.clientId,
    redirect_uri: args.redirectUri,
    scope: INSTALL_BOT_SCOPES.join(','),
    state: makeState(args.stateSecret),
  });
  if (args.teamId) {
    params.set('team', args.teamId);
  }
  return `https://slack.com/oauth/v2/authorize?${params.toString()}`;
}

function send(res: ServerResponse, status: number, body: string, contentType = 'text/plain'): void {
  res.writeHead(status, { 'Content-Type': contentType });
  res.end(body);
}

/**
 * Handler for /slack/oauth/callback.
 *
 * Validates the state, exchanges the code, persists the installation, and
 * redirects to a success page.
 */
export async function handleInstallOAuthCallback(
  req: IncomingMessage,
  res: ServerResponse,
  deps: InstallOAuthCallbackDeps,
): Promise<void> {
  const url = new URL(req.url ?? '/', `http://${req.headers.host}`);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state') ?? '';
  const error = url.searchParams.get('error');

  if (error) {
    send(res, 400, `OAuth error: ${error}`);
    return;
  }
  if (!code) {
    send(res, 400, 'Missing OAuth code');
    return;
  }
  if (!validateState(state, deps.stateSecret)) {
    send(res, 400, 'Invalid or expired OAuth state');
    return;
  }

  const fetcher = deps.fetcher ?? fetch;
  let tokenData: unknown;
  try {
    const tokenRes = await fetcher('https://slack.com/api/oauth.v2.access', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: deps.clientId,
        client_secret: deps.clientSecret,
        code,
        redirect_uri: deps.redirectUri,
      }),
    });
    tokenData = await tokenRes.json();
  } catch (err) {
    send(res, 500, `OAuth token exchange failed: ${(err as Error).message}`);
    return;
  }

  const data = tokenData as {
    ok?: boolean;
    error?: string;
    team?: { id?: string; name?: string };
    enterprise?: { id?: string };
    bot?: { token?: string; id?: string; user_id?: string; scopes?: string[] };
  };

  if (!data.ok) {
    send(res, 400, `Slack OAuth error: ${data.error ?? 'unknown'}`);
    return;
  }

  const teamId = data.team?.id;
  const botToken = data.bot?.token;
  if (!teamId || !botToken) {
    send(res, 400, 'OAuth response missing team or bot token');
    return;
  }

  deps.installationStore.saveInstallation({
    teamId,
    teamName: data.team?.name,
    enterpriseId: data.enterprise?.id,
    botToken,
    botId: data.bot?.id,
    botUserId: data.bot?.user_id,
    scopes: data.bot?.scopes ?? [],
    installedAt: new Date().toISOString(),
  });

  res.writeHead(302, { Location: deps.successUrl });
  res.end();
}
