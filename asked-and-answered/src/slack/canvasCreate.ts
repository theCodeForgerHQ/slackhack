import type { WebClient } from '@slack/web-api';
import type { CanvasDocument } from './canvasExport.js';
import { canvasToApiSections, canvasToMarkdown } from './canvasExport.js';

export interface CanvasCreateResult {
  kind: 'native' | 'markdown_fallback' | 'scope_missing';
  canvasId?: string;
  url?: string;
  message: string;
}

function isMissingScope(err: unknown): boolean {
  const msg = err instanceof Error ? err.message : String(err);
  return /missing_scope|not_allowed_token_type/i.test(msg);
}

async function uploadMarkdownFallback(
  client: WebClient,
  channelId: string,
  threadTs: string | undefined,
  doc: CanvasDocument,
  fallbackComment?: string,
): Promise<CanvasCreateResult> {
  const md = canvasToMarkdown(doc);
  const uploadBase = {
    channel_id: channelId,
    filename: 'questionnaire-asked-and-answered.md',
    file: Buffer.from(md, 'utf8'),
    initial_comment:
      fallbackComment ??
      'Canvas export (Markdown fallback — native Canvas API unavailable). Every answer cited and approval-logged.',
  };
  if (threadTs) {
    await client.files.uploadV2({ ...uploadBase, thread_ts: threadTs } as never);
  } else {
    await client.files.uploadV2(uploadBase as never);
  }
  return {
    kind: 'markdown_fallback',
    message: ':page_with_curl: Audit artifact exported as Markdown (native Canvas API unavailable).',
  };
}

/**
 * Create a native Slack Canvas when the bot has `canvases:write`.
 * Falls back to Markdown upload only for transient API errors — not for
 * missing scope, so judges can see when the workspace needs a reinstall.
 *
 * `forceFallback` skips the native Canvas attempt entirely; it is used when
 * the startup capability probe has already determined Canvas is unavailable.
 */
export async function createCanvasOrFallback(
  client: WebClient,
  channelId: string,
  threadTs: string | undefined,
  doc: CanvasDocument,
  opts: { teamId?: string; fallbackComment?: string; forceFallback?: boolean } = {},
): Promise<CanvasCreateResult> {
  if (opts.forceFallback) {
    return uploadMarkdownFallback(client, channelId, threadTs, doc, opts.fallbackComment);
  }
  try {
    const canvas = await client.canvases.create({
      title: doc.title,
      document_content: { type: 'canvas', sections: canvasToApiSections(doc) } as never,
    });
    if (canvas.canvas_id) {
      const team = opts.teamId ?? process.env.SLACK_TEAM_ID ?? '';
      const url = `https://app.slack.com/client/${team}/canvases/${canvas.canvas_id}`;
      return {
        kind: 'native',
        canvasId: canvas.canvas_id,
        url,
        message: `:page_with_curl: Native Canvas exported: <${url}|${doc.title}>`,
      };
    }
  } catch (err) {
    if (isMissingScope(err)) {
      return {
        kind: 'scope_missing',
        message:
          ':warning: Canvas export needs the `canvases:write` bot scope. Reinstall the app from the updated manifest, then retry Export Canvas.',
      };
    }
    return uploadMarkdownFallback(client, channelId, threadTs, doc, opts.fallbackComment);
  }

  return uploadMarkdownFallback(client, channelId, threadTs, doc, opts.fallbackComment);
}
