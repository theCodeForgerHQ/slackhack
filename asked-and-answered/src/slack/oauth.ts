import Database from 'better-sqlite3';

/**
 * Per-user OAuth token store for private-channel RTS.
 *
 * The Slack bot token with `search:read.public` only sees public workspace
 * content. To search private channels on behalf of a user, we need a user
 * OAuth token with the `search:read` user scope. This store persists those
 * tokens after the user completes the OAuth flow.
 *
 * Tokens are stored encrypted at rest only when AA_USER_TOKEN_ENCRYPTION_KEY
 * is set; otherwise they are stored as plain rows in a dedicated table. In
 * either case the interface is the same: getUserToken(userId) returns the
 * active token or undefined.
 */

export interface UserTokenStore {
  getUserToken(userId: string): string | undefined;
  saveUserToken(userId: string, token: string, scopes: string[]): void;
  revokeUserToken(userId: string): void;
  hasUserTokenWithScope(scope: string): boolean;
}

/** In-memory fallback for tests and single-process dev. */
export class InMemoryUserTokenStore implements UserTokenStore {
  private readonly tokens = new Map<string, { token: string; scopes: string[] }>();

  getUserToken(userId: string): string | undefined {
    return this.tokens.get(userId)?.token;
  }

  saveUserToken(userId: string, token: string, scopes: string[]): void {
    this.tokens.set(userId, { token, scopes });
  }

  revokeUserToken(userId: string): void {
    this.tokens.delete(userId);
  }

  hasUserTokenWithScope(scope: string): boolean {
    for (const entry of this.tokens.values()) {
      if (entry.scopes.includes(scope)) return true;
    }
    return false;
  }
}

/** SQLite-backed token store with optional simple XOR obfuscation. */
export class SqliteUserTokenStore implements UserTokenStore {
  private readonly db: Database.Database;

  private constructor(db: Database.Database) {
    this.db = db;
    this.db
      .prepare(
        `CREATE TABLE IF NOT EXISTS user_tokens (
           user_id TEXT PRIMARY KEY,
           token TEXT NOT NULL,
           scopes TEXT NOT NULL,
           updated_at TEXT NOT NULL
         )`,
      )
      .run();
  }

  static inMemory(): SqliteUserTokenStore {
    return new SqliteUserTokenStore(new Database(':memory:'));
  }

  static atPath(path: string): SqliteUserTokenStore {
    return new SqliteUserTokenStore(new Database(path));
  }

  getUserToken(userId: string): string | undefined {
    const row = this.db.prepare('SELECT token FROM user_tokens WHERE user_id = ?').get(userId) as
      | { token: string }
      | undefined;
    if (!row) return undefined;
    return this.decrypt(row.token);
  }

  saveUserToken(userId: string, token: string, scopes: string[]): void {
    this.db
      .prepare(
        `INSERT INTO user_tokens (user_id, token, scopes, updated_at)
         VALUES (?, ?, ?, ?)
         ON CONFLICT(user_id) DO UPDATE SET
           token = excluded.token,
           scopes = excluded.scopes,
           updated_at = excluded.updated_at`,
      )
      .run(userId, this.encrypt(token), scopes.join(','), new Date().toISOString());
  }

  revokeUserToken(userId: string): void {
    this.db.prepare('DELETE FROM user_tokens WHERE user_id = ?').run(userId);
  }

  hasUserTokenWithScope(scope: string): boolean {
    const row = this.db
      .prepare("SELECT 1 as found FROM user_tokens WHERE scopes LIKE '%' || ? || '%' LIMIT 1")
      .get(scope) as { found: number } | undefined;
    return row?.found === 1;
  }

  private encrypt(plain: string): string {
    const key = process.env.AA_USER_TOKEN_ENCRYPTION_KEY;
    if (!key) return plain;
    const buf = Buffer.from(plain, 'utf8');
    const keyBuf = Buffer.from(key, 'utf8');
    if (keyBuf.length === 0) return plain;
    const out = Buffer.alloc(buf.length);
    for (let i = 0; i < buf.length; i++) {
      out[i] = buf[i]! ^ keyBuf[i % keyBuf.length]!;
    }
    return out.toString('base64');
  }

  private decrypt(cipher: string): string {
    const key = process.env.AA_USER_TOKEN_ENCRYPTION_KEY;
    if (!key) return cipher;
    const buf = Buffer.from(cipher, 'base64');
    const keyBuf = Buffer.from(key, 'utf8');
    if (keyBuf.length === 0) return cipher;
    const out = Buffer.alloc(buf.length);
    for (let i = 0; i < buf.length; i++) {
      out[i] = buf[i]! ^ keyBuf[i % keyBuf.length]!;
    }
    return out.toString('utf8');
  }
}

/**
 * Builds the Slack OAuth v2 authorization URL for a user token.
 * The user must already have a bot install; this is the *user* scope flow.
 */
export function buildUserOAuthUrl(args: {
  clientId: string;
  redirectUri: string;
  scopes: string[];
  userId: string;
  stateSecret: string;
}): string {
  const state = Buffer.from(`${args.userId}:${args.stateSecret}:${Date.now()}`).toString('base64');
  const params = new URLSearchParams({
    client_id: args.clientId,
    redirect_uri: args.redirectUri,
    scope: args.scopes.join(','),
    state,
  });
  return `https://slack.com/oauth/v2/authorize?${params.toString()}`;
}
