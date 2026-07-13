import { describe, test, expect, vi } from 'vitest';
import type { IncomingMessage } from 'node:http';
import {
  buildInstallOAuthUrl,
  handleInstallOAuthCallback,
  INSTALL_BOT_SCOPES,
} from '../src/slack/installOAuth.js';
import { InMemoryInstallationStore } from '../src/slack/installStore.js';

describe('buildInstallOAuthUrl', () => {
  test('includes client id, redirect uri, bot scopes, and state', () => {
    const url = buildInstallOAuthUrl({
      clientId: '123',
      redirectUri: 'https://example.com/slack/oauth/callback',
      stateSecret: 'shh',
    });
    expect(url).toContain('client_id=123');
    expect(url).toContain('redirect_uri=');
    expect(url).toContain(`scope=${encodeURIComponent(INSTALL_BOT_SCOPES.join(','))}`);
    expect(url).toContain('state=');
    expect(url).toContain('https://slack.com/oauth/v2/authorize');
  });

  test('includes team hint when provided', () => {
    const url = buildInstallOAuthUrl({
      clientId: '123',
      redirectUri: 'https://example.com/slack/oauth/callback',
      stateSecret: 'shh',
      teamId: 'T123',
    });
    expect(url).toContain('team=T123');
  });
});

function mockReq(url: string): IncomingMessage {
  return { url, headers: { host: 'example.com' } } as IncomingMessage;
}

function validState(secret: string): string {
  return Buffer.from(`${secret}:${Date.now() - 1000}`).toString('base64url');
}

interface MockResponse {
  statusCode: number;
  headers: Record<string, string>;
  body: string;
  writeHead(status: number, headers?: Record<string, string>): void;
  end(body?: string): void;
}

function mockRes(): MockResponse {
  const res: MockResponse = {
    statusCode: 0,
    headers: {},
    body: '',
    writeHead(status: number, headers?: Record<string, string>) {
      this.statusCode = status;
      if (headers) this.headers = headers;
    },
    end(body?: string) {
      this.body = body ?? '';
    },
  };
  return res;
}

describe('handleInstallOAuthCallback', () => {
  test('exchanges code and stores installation, then redirects', async () => {
    const store = new InMemoryInstallationStore();
    const fetcher = vi.fn().mockResolvedValue({
      json: async () => ({
        ok: true,
        team: { id: 'T123', name: 'Test Team' },
        bot: {
          token: 'xoxb-bot-token',
          id: 'B1',
          user_id: 'U1',
          scopes: ['chat:write', 'canvases:write'],
        },
      }),
    });

    const state = validState('shh');
    const res = mockRes();
    await handleInstallOAuthCallback(
      mockReq(`/slack/oauth/callback?code=cc&state=${state}`),
      res as unknown as import('node:http').ServerResponse,
      {
        installationStore: store,
        clientId: '123',
        clientSecret: 'secret',
        redirectUri: 'https://example.com/slack/oauth/callback',
        stateSecret: 'shh',
        successUrl: 'https://example.com/success',
        fetcher,
      },
    );

    expect(res.statusCode).toBe(302);
    expect(res.headers['Location']).toBe('https://example.com/success');

    const installed = store.getInstallation('T123');
    expect(installed).toBeDefined();
    expect(installed!.botToken).toBe('xoxb-bot-token');
    expect(installed!.scopes).toContain('canvases:write');

    expect(fetcher).toHaveBeenCalledTimes(1);
    const call = fetcher.mock.calls[0]!;
    expect(call[0]).toBe('https://slack.com/api/oauth.v2.access');
    const body = new URLSearchParams(call[1]!.body as string);
    expect(body.get('client_id')).toBe('123');
    expect(body.get('client_secret')).toBe('secret');
    expect(body.get('code')).toBe('cc');
  });

  test('rejects invalid state', async () => {
    const store = new InMemoryInstallationStore();
    const fetcher = vi.fn();
    const res = mockRes();
    await handleInstallOAuthCallback(
      mockReq('/slack/oauth/callback?code=cc&state=bad'),
      res as unknown as import('node:http').ServerResponse,
      {
        installationStore: store,
        clientId: '123',
        clientSecret: 'secret',
        redirectUri: 'https://example.com/slack/oauth/callback',
        stateSecret: 'shh',
        successUrl: 'https://example.com/success',
        fetcher,
      },
    );

    expect(res.statusCode).toBe(400);
    expect(res.body).toContain('Invalid or expired OAuth state');
    expect(fetcher).not.toHaveBeenCalled();
    expect(store.getAllInstallations()).toHaveLength(0);
  });

  test('surfaces Slack OAuth error', async () => {
    const store = new InMemoryInstallationStore();
    const fetcher = vi.fn().mockResolvedValue({
      json: async () => ({ ok: false, error: 'invalid_code' }),
    });
    const state = validState('shh');
    const res = mockRes();
    await handleInstallOAuthCallback(
      mockReq(`/slack/oauth/callback?code=cc&state=${state}`),
      res as unknown as import('node:http').ServerResponse,
      {
        installationStore: store,
        clientId: '123',
        clientSecret: 'secret',
        redirectUri: 'https://example.com/slack/oauth/callback',
        stateSecret: 'shh',
        successUrl: 'https://example.com/success',
        fetcher,
      },
    );

    expect(res.statusCode).toBe(400);
    expect(res.body).toContain('invalid_code');
    expect(store.getAllInstallations()).toHaveLength(0);
  });

  test('surfaces network errors gracefully', async () => {
    const store = new InMemoryInstallationStore();
    const fetcher = vi.fn().mockRejectedValue(new Error('network down'));
    const state = validState('shh');
    const res = mockRes();
    await handleInstallOAuthCallback(
      mockReq(`/slack/oauth/callback?code=cc&state=${state}`),
      res as unknown as import('node:http').ServerResponse,
      {
        installationStore: store,
        clientId: '123',
        clientSecret: 'secret',
        redirectUri: 'https://example.com/slack/oauth/callback',
        stateSecret: 'shh',
        successUrl: 'https://example.com/success',
        fetcher,
      },
    );

    expect(res.statusCode).toBe(500);
    expect(res.body).toContain('network down');
    expect(store.getAllInstallations()).toHaveLength(0);
  });
});
