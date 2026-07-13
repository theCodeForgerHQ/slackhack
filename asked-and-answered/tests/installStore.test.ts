import { describe, test, expect } from 'vitest';
import { InMemoryInstallationStore, SqliteInstallationStore } from '../src/slack/installStore.js';

describe('InstallationStore', () => {
  testStore('InMemoryInstallationStore', () => new InMemoryInstallationStore());
  testStore('SqliteInstallationStore', () => SqliteInstallationStore.inMemory());
});

function testStore(name: string, create: () => InMemoryInstallationStore | SqliteInstallationStore) {
  describe(name, () => {
    test('saves and retrieves an installation', () => {
      const store = create();
      store.saveInstallation({
        teamId: 'T1',
        teamName: 'Team One',
        botToken: 'xoxb-1',
        botId: 'B1',
        botUserId: 'U1',
        scopes: ['chat:write', 'canvases:write'],
        installedAt: new Date().toISOString(),
      });
      const installed = store.getInstallation('T1');
      expect(installed).toBeDefined();
      expect(installed!.teamId).toBe('T1');
      expect(installed!.teamName).toBe('Team One');
      expect(installed!.scopes).toEqual(['chat:write', 'canvases:write']);
    });

    test('updates an existing installation', () => {
      const store = create();
      store.saveInstallation({
        teamId: 'T1',
        botToken: 'xoxb-old',
        scopes: ['chat:write'],
        installedAt: '2026-01-01T00:00:00.000Z',
      });
      store.saveInstallation({
        teamId: 'T1',
        botToken: 'xoxb-new',
        scopes: ['chat:write', 'canvases:write'],
        installedAt: '2026-07-14T00:00:00.000Z',
      });
      const installed = store.getInstallation('T1');
      expect(installed!.botToken).toBe('xoxb-new');
      expect(installed!.scopes).toEqual(['chat:write', 'canvases:write']);
    });

    test('returns undefined for unknown teams', () => {
      const store = create();
      expect(store.getInstallation('T_UNKNOWN')).toBeUndefined();
    });

    test('lists all installations', () => {
      const store = create();
      store.saveInstallation({
        teamId: 'T1',
        botToken: 'xoxb-1',
        scopes: ['chat:write'],
        installedAt: new Date().toISOString(),
      });
      store.saveInstallation({
        teamId: 'T2',
        botToken: 'xoxb-2',
        scopes: ['chat:write'],
        installedAt: new Date().toISOString(),
      });
      expect(store.getAllInstallations()).toHaveLength(2);
    });
  });
}
