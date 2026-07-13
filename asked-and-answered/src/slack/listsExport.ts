import type { DraftResult } from '../core/pipeline.js';

export interface ListExportResult {
  ok: boolean;
  listId?: string;
  url?: string;
  fallbackReason?: string;
}

interface SlackListClient {
  apiCall(method: string, options?: Record<string, unknown>): Promise<unknown>;
}

/**
 * Sync approved/grounded answers to a native Slack List.
 *
 * Slack Lists are durable, workspace-visible artifacts. This function tries to
 * create a list and populate it with one item per result. If the bot token
 * lacks lists:write (the common case today), it returns ok=false with the
 * reason so the caller can surface a graceful fallback.
 */
export async function exportToSlackList(
  client: SlackListClient,
  results: DraftResult[],
  opts: { runId: string; requesterId: string; title?: string },
): Promise<ListExportResult> {
  const title = opts.title ?? 'Questionnaire — Asked & Answered';
  const description = `Approved/grounded answers from run ${opts.runId}`;

  let listId: string;
  try {
    const createRes = (await client.apiCall('lists.create', {
      title,
      description,
    })) as { ok?: boolean; list_id?: string; error?: string };
    if (!createRes.ok) {
      return { ok: false, fallbackReason: createRes.error ?? 'lists.create failed' };
    }
    listId = createRes.list_id!;
  } catch (err) {
    const reason = (err as { data?: { error?: string }; message?: string }).data?.error ?? (err as Error).message;
    return { ok: false, fallbackReason: reason };
  }

  for (const r of results) {
    if (r.state === 'needs_sme') continue;
    const text = r.state === 'verified' ? `Verified answer` : `Grounded answer`;
    const citationLinks = (r.citations ?? []).map((c) => `<${c.permalink}|evidence>`).join(' · ');
    try {
      await client.apiCall('lists.edit', {
        list_id: listId,
        title: r.questionText.slice(0, 100),
        note: `${text}\n${r.answerText ?? ''}\n${citationLinks}`.slice(0, 3000),
      });
    } catch {
      // Best-effort: one failed item should not abort the whole export.
    }
  }

  return { ok: true, listId };
}
