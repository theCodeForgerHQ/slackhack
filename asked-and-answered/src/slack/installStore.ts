import Database from 'better-sqlite3';

/**
 * Per-workspace Slack app installation store.
 *
 * When the app is installed into a new workspace via the app-level OAuth v2
 * flow, the resulting bot token and metadata are persisted here keyed by
 * team_id. This enables multi-workspace deployments without requiring a
 * separate Bolt receiver or external OAuth service.
 */

export interface Installation {
  teamId: string;
  teamName?: string | undefined;
  enterpriseId?: string | undefined;
  botToken: string;
  botId?: string | undefined;
  botUserId?: string | undefined;
  scopes: string[];
  installedAt: string;
}

export interface InstallationStore {
  saveInstallation(installation: Installation): void;
  getInstallation(teamId: string): Installation | undefined;
  getAllInstallations(): Installation[];
}

/** In-memory store for tests and single-process deployments. */
export class InMemoryInstallationStore implements InstallationStore {
  private readonly installations = new Map<string, Installation>();

  saveInstallation(installation: Installation): void {
    this.installations.set(installation.teamId, installation);
  }

  getInstallation(teamId: string): Installation | undefined {
    return this.installations.get(teamId);
  }

  getAllInstallations(): Installation[] {
    return Array.from(this.installations.values());
  }
}

/** SQLite-backed installation store. */
export class SqliteInstallationStore implements InstallationStore {
  private constructor(private readonly db: Database.Database) {
    this.db
      .prepare(
        `CREATE TABLE IF NOT EXISTS installations (
           team_id TEXT PRIMARY KEY,
           team_name TEXT,
           enterprise_id TEXT,
           bot_token TEXT NOT NULL,
           bot_id TEXT,
           bot_user_id TEXT,
           scopes TEXT NOT NULL,
           installed_at TEXT NOT NULL
         )`,
      )
      .run();
  }

  static inMemory(): SqliteInstallationStore {
    return new SqliteInstallationStore(new Database(':memory:'));
  }

  static atPath(path: string): SqliteInstallationStore {
    return new SqliteInstallationStore(new Database(path));
  }

  saveInstallation(installation: Installation): void {
    this.db
      .prepare(
        `INSERT INTO installations (team_id, team_name, enterprise_id, bot_token, bot_id, bot_user_id, scopes, installed_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(team_id) DO UPDATE SET
           team_name = excluded.team_name,
           enterprise_id = excluded.enterprise_id,
           bot_token = excluded.bot_token,
           bot_id = excluded.bot_id,
           bot_user_id = excluded.bot_user_id,
           scopes = excluded.scopes,
           installed_at = excluded.installed_at`,
      )
      .run(
        installation.teamId,
        installation.teamName ?? null,
        installation.enterpriseId ?? null,
        installation.botToken,
        installation.botId ?? null,
        installation.botUserId ?? null,
        installation.scopes.join(','),
        installation.installedAt,
      );
  }

  getInstallation(teamId: string): Installation | undefined {
    const row = this.db.prepare('SELECT * FROM installations WHERE team_id = ?').get(teamId) as
      | {
          team_id: string;
          team_name: string | null;
          enterprise_id: string | null;
          bot_token: string;
          bot_id: string | null;
          bot_user_id: string | null;
          scopes: string;
          installed_at: string;
        }
      | undefined;
    if (!row) return undefined;
    return {
      teamId: row.team_id,
      teamName: row.team_name ?? undefined,
      enterpriseId: row.enterprise_id ?? undefined,
      botToken: row.bot_token,
      botId: row.bot_id ?? undefined,
      botUserId: row.bot_user_id ?? undefined,
      scopes: row.scopes.split(',').filter(Boolean),
      installedAt: row.installed_at,
    };
  }

  getAllInstallations(): Installation[] {
    const rows = this.db.prepare('SELECT * FROM installations').all() as Array<{
      team_id: string;
      team_name: string | null;
      enterprise_id: string | null;
      bot_token: string;
      bot_id: string | null;
      bot_user_id: string | null;
      scopes: string;
      installed_at: string;
    }>;
    return rows.map((row) => ({
      teamId: row.team_id,
      teamName: row.team_name ?? undefined,
      enterpriseId: row.enterprise_id ?? undefined,
      botToken: row.bot_token,
      botId: row.bot_id ?? undefined,
      botUserId: row.bot_user_id ?? undefined,
      scopes: row.scopes.split(',').filter(Boolean),
      installedAt: row.installed_at,
    }));
  }
}
