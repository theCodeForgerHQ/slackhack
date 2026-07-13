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

/**
 * Create a native Slack Canvas when the bot has `canvases:write`.
 * Falls back to Markdown upload only for transient API errors — not for
 * missing scope, so judges can see when the workspace needs a reinstall.
 */
export async function createCanvasOrFallback(
  client: WebClient,
  channelId: string,
  threadTs: string | undefined,
  doc: CanvasDocument,
  opts: { teamId?: string; fallbackComment?: string } = {},
): Promise<CanvasCreateResult> {
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
    // Transient / format errors: fall back to Markdown file upload.
    const md = canvasToMarkdown(doc);
    const uploadBase = {
      channel_id: channelId,
      filename: 'questionnaire-asked-and-answered.md',
      file: Buffer.from(md, 'utf8'),
      initial_comment:
        opts.fallbackComment ??
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

  const md = canvasToMarkdown(doc);
  const uploadBase = {
    channel_id: channelId,
    filename: 'questionnaire-asked-and-answered.md',
    file: Buffer.from(md, 'utf8'),
    initial_comment: opts.fallbackComment ?? 'Canvas export (Markdown fallback).',
  };
  if (threadTs) {
    await client.files.uploadV2({ ...uploadBase, thread_ts: threadTs } as never);
  } else {
    await client.files.uploadV2(uploadBase as never);
  }
  return { kind: 'markdown_fallback', message: ':page_with_curl: Audit artifact exported as Markdown.' };
}
