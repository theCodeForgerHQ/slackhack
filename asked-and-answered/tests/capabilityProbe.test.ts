import { describe, test, expect } from 'vitest';
import { probeCapabilities } from '../src/core/capabilityProbe.js';
import { InMemoryInstallationStore } from '../src/slack/installStore.js';
import { InMemoryUserTokenStore } from '../src/slack/oauth.js';

describe('probeCapabilities', () => {
  test('enables canvas and lists when stored installation scopes include them', async () => {
    const installationStore = new InMemoryInstallationStore();
    installationStore.saveInstallation({
      teamId: 'T1',
      botToken: 'xoxb-1',
      scopes: ['chat:write', 'canvases:write', 'lists:write'],
      installedAt: new Date().toISOString(),
    });

    const caps = await probeCapabilities({
      client: { apiCall: async () => ({ ok: true }) },
      installationStore,
      userTokenStore: new InMemoryUserTokenStore(),
    });

    expect(caps.canvas).toBe(true);
    expect(caps.lists).toBe(true);
    expect(caps.userSearch).toBe(false);
  });

  test('disables canvas and lists when stored scopes omit them', async () => {
    const installationStore = new InMemoryInstallationStore();
    installationStore.saveInstallation({
      teamId: 'T1',
      botToken: 'xoxb-1',
      scopes: ['chat:write'],
      installedAt: new Date().toISOString(),
    });

    const caps = await probeCapabilities({
      client: { apiCall: async () => ({ ok: true }) },
      installationStore,
      userTokenStore: new InMemoryUserTokenStore(),
    });

    expect(caps.canvas).toBe(false);
    expect(caps.lists).toBe(false);
  });

  test('enables userSearch when a user token has search:read', async () => {
    const userTokenStore = new InMemoryUserTokenStore();
    userTokenStore.saveUserToken('U1', 'xoxp-secret', ['search:read', 'channels:read']);

    const caps = await probeCapabilities({
      client: { apiCall: async () => ({ ok: true }) },
      installationStore: new InMemoryInstallationStore(),
      userTokenStore,
    });

    expect(caps.userSearch).toBe(true);
  });

  test('probes dataTable via views.publish when probe user is provided', async () => {
    const installationStore = new InMemoryInstallationStore();
    installationStore.saveInstallation({
      teamId: 'T1',
      botToken: 'xoxb-1',
      scopes: ['chat:write'],
      installedAt: new Date().toISOString(),
    });

    const calls: { method: string; args: Record<string, unknown> }[] = [];
    const caps = await probeCapabilities({
      client: {
        apiCall: async (method, args) => {
          calls.push({ method, args: args ?? {} });
          if (method === 'views.publish') return { ok: true };
          return { ok: true };
        },
      },
      installationStore,
      userTokenStore: new InMemoryUserTokenStore(),
      probeUserId: 'U_PROBE',
    });

    expect(caps.dataTable).toBe(true);
    expect(calls.some((c) => c.method === 'views.publish' && c.args.user_id === 'U_PROBE')).toBe(true);
  });

  test('disables dataTable when views.publish fails', async () => {
    const installationStore = new InMemoryInstallationStore();
    installationStore.saveInstallation({
      teamId: 'T1',
      botToken: 'xoxb-1',
      scopes: ['chat:write'],
      installedAt: new Date().toISOString(),
    });

    const caps = await probeCapabilities({
      client: {
        apiCall: async (method) => {
          if (method === 'views.publish') throw new Error('invalid_block');
          return { ok: true };
        },
      },
      installationStore,
      userTokenStore: new InMemoryUserTokenStore(),
      probeUserId: 'U_PROBE',
    });

    expect(caps.dataTable).toBe(false);
  });

  test('defaults dataTable to true when no probe user is configured', async () => {
    const caps = await probeCapabilities({
      client: { apiCall: async () => ({ ok: true }) },
      installationStore: new InMemoryInstallationStore(),
      userTokenStore: new InMemoryUserTokenStore(),
    });

    expect(caps.dataTable).toBe(true);
  });
});
