import { describe, test, expect } from 'vitest';
import { InMemoryUserTokenStore, SqliteUserTokenStore, buildUserOAuthUrl } from '../src/slack/oauth.js';

describe('UserTokenStore', () => {
  testStore('InMemoryUserTokenStore', () => new InMemoryUserTokenStore());
  testStore('SqliteUserTokenStore', () => SqliteUserTokenStore.inMemory());
});

function testStore(name: string, create: () => InMemoryUserTokenStore | SqliteUserTokenStore) {
  describe(name, () => {
    test('saves and retrieves a user token', () => {
      const store = create();
      store.saveUserToken('U1', 'xoxp-secret', ['search:read']);
      expect(store.getUserToken('U1')).toBe('xoxp-secret');
    });

    test('returns undefined for unknown users', () => {
      const store = create();
      expect(store.getUserToken('U_UNKNOWN')).toBeUndefined();
    });

    test('revokes a token', () => {
      const store = create();
      store.saveUserToken('U1', 'xoxp-secret', ['search:read']);
      store.revokeUserToken('U1');
      expect(store.getUserToken('U1')).toBeUndefined();
    });

    test('updates an existing token', () => {
      const store = create();
      store.saveUserToken('U1', 'old', ['search:read']);
      store.saveUserToken('U1', 'new', ['search:read', 'channels:read']);
      expect(store.getUserToken('U1')).toBe('new');
    });
  });
}

describe('buildUserOAuthUrl', () => {
  test('includes client id, redirect uri, scopes, and state', () => {
    const url = buildUserOAuthUrl({
      clientId: '123',
      redirectUri: 'https://example.com/oauth',
      scopes: ['search:read'],
      userId: 'U1',
      stateSecret: 'shh',
    });
    expect(url).toContain('client_id=123');
    expect(url).toContain('redirect_uri=');
    expect(url).toContain('scope=search%3Aread');
    expect(url).toContain('state=');
  });
});
