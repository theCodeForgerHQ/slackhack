import type { InstallationStore } from '../slack/installStore.js';
import type { UserTokenStore } from '../slack/oauth.js';

/**
 * Runtime capability map for Slack features used by the app.
 *
 * Probed once at startup so the bot can gracefully fall back when a workspace
 * is missing a scope or a block type is not yet supported. All flags are
 * best-effort; the app remains safe when a flag is wrong because each call site
 * still has its own error handling.
 */

export interface CapabilityMap {
  /** Native Canvas creation via canvases.create (requires canvases:write). */
  canvas: boolean;
  /** Native Slack List creation via lists.create (requires lists:write). */
  lists: boolean;
  /** Data Table block rendering (probed via views.publish). */
  dataTable: boolean;
  /** Private-channel search via a user OAuth token (requires search:read). */
  userSearch: boolean;
}

export interface CapabilityProbeDeps {
  /** Slack WebClient-like object. */
  client: {
    apiCall(method: string, args?: Record<string, unknown>): Promise<unknown>;
  };
  installationStore: InstallationStore;
  userTokenStore: UserTokenStore;
  /** Workspace to probe. Defaults to the first stored installation. */
  teamId?: string | undefined;
  /** Real workspace user_id used for the data_table views.publish probe. */
  probeUserId?: string | undefined;
}

const DEFAULT_CAPABILITIES: CapabilityMap = {
  canvas: false,
  lists: false,
  dataTable: true,
  userSearch: false,
};

function getBotScopes(store: InstallationStore, teamId?: string): string[] {
  const installation = teamId
    ? store.getInstallation(teamId)
    : store.getAllInstallations()[0];
  return installation?.scopes ?? [];
}

/**
 * Probes the workspace for available Slack capabilities.
 *
 * The probe is safe to run at startup: it does not mutate workspace state and
 * falls back to disabled flags on any error.
 */
export async function probeCapabilities(deps: CapabilityProbeDeps): Promise<CapabilityMap> {
  const botScopes = getBotScopes(deps.installationStore, deps.teamId);

  const canvas = botScopes.includes('canvases:write');
  const lists = botScopes.includes('lists:write');
  const userSearch = deps.userTokenStore.hasUserTokenWithScope('search:read');

  let dataTable = DEFAULT_CAPABILITIES.dataTable;
  if (deps.probeUserId) {
    try {
      await deps.client.apiCall('views.publish', {
        user_id: deps.probeUserId,
        view: {
          type: 'home',
          blocks: [
            {
              type: 'data_table',
              columns: [{ name: 'probe', title: 'Probe', width: 100 }],
              rows: [{ probe: 'ok' }],
            },
          ],
        },
      });
      dataTable = true;
    } catch {
      dataTable = false;
    }
  }

  return { canvas, lists, dataTable, userSearch };
}
