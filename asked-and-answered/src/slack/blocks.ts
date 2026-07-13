import { createHash } from 'node:crypto';
import type { DraftResult, NeedsSmeReason } from '../core/pipeline.js';
import type { VerifyResult } from '../core/ledger.js';
import type { StaleAlert } from '../core/watcher.js';

/**
 * Block Kit builders — the fallback review surface (sections + buttons,
 * paginated). The Data Table block variant is wired behind the same
 * call sites once verified against the live sandbox (spike S3); nothing
 * else in the app knows which surface rendered.
 */

type Block = Record<string, unknown>;

export const PAGE_SIZE = 20;

const STATE_EMOJI: Record<DraftResult['state'], string> = {
  verified: ':white_check_mark:',
  grounded: ':mag:',
  needs_sme: ':raised_hand:',
};

const STATE_LABEL: Record<DraftResult['state'], string> = {
  verified: 'Verified',
  grounded: 'Grounded',
  needs_sme: 'Needs SME',
};

const REASON_LABEL: Record<NeedsSmeReason, string> = {
  no_evidence: 'no evidence found in this workspace',
  search_failed: 'workspace search failed',
  llm_refused: 'evidence was insufficient to answer',
  invalid_citations: 'draft failed citation validation',
  ungrounded_citations: 'draft cited evidence that does not support the answer',
  acl_degraded: 'approved answer exists, but you cannot see its evidence',
  stale_evidence: 'approved answer is contradicted by newer workspace evidence',
  llm_error: 'drafting error',
  rejected: 'draft rejected by a reviewer',
};

export interface PlanCounts {
  total: number;
  deduped: number;
  verified: number;
  grounded: number;
  needsSme: number;
}

export function planSummaryText(c: PlanCounts): string {
  return (
    `Parsed *${c.total}* questions → *${c.deduped}* after dedupe.\n` +
    `:white_check_mark: ${c.verified} verified from the approved library · ` +
    `:mag: ${c.grounded} grounded in workspace evidence · ` +
    `:raised_hand: ${c.needsSme} need a human`
  );
}

/** Encodes run + question into a button value so a stale button can't cross runs. */
function actionValue(runId: string, questionId: string): string {
  return `${runId}:${questionId}`;
}

export function reviewTableBlocks(
  results: DraftResult[],
  opts: { page: number; runId?: string },
): Block[] {
  const runId = opts.runId ?? '';
  const start = opts.page * PAGE_SIZE;
  const pageResults = results.slice(start, start + PAGE_SIZE);
  const hasNext = start + PAGE_SIZE < results.length;

  const blocks: Block[] = [
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Review — ${results.length} questions* (page ${opts.page + 1} of ${Math.ceil(results.length / PAGE_SIZE)})`,
      },
    },
    { type: 'divider' },
  ];

  for (const r of pageResults) {
    const detail =
      r.state === 'needs_sme'
        ? `_${REASON_LABEL[r.reason ?? 'no_evidence']}_`
        : (r.answerText ?? '').slice(0, 120) + ((r.answerText?.length ?? 0) > 120 ? '…' : '');
    blocks.push({
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `${STATE_EMOJI[r.state]} *${r.questionText}*\n${STATE_LABEL[r.state]} — ${detail}`,
      },
      accessory: {
        type: 'button',
        action_id: 'open_answer_card',
        value: actionValue(runId, r.questionId),
        text: { type: 'plain_text', text: 'Review' },
      },
    });
    blocks.push({
      type: 'actions',
      elements: [
        {
          type: 'button',
          action_id: 'open_run_card',
          value: actionValue(runId, r.questionId),
          text: { type: 'plain_text', text: 'Agent Run Card' },
        },
      ],
    });
  }

  const toolbar: Block[] = [
    {
      type: 'button',
      action_id: 'open_review_modal',
      value: actionValue(runId, 'modal'),
      text: { type: 'plain_text', text: 'Open table view' },
    },
    {
      type: 'button',
      action_id: 'export_xlsx',
      value: actionValue(runId, 'export'),
      text: { type: 'plain_text', text: 'Export xlsx' },
    },
    {
      type: 'button',
      action_id: 'export_canvas',
      value: actionValue(runId, 'export'),
      text: { type: 'plain_text', text: 'Export Canvas' },
    },
    {
      type: 'button',
      action_id: 'export_list',
      value: actionValue(runId, 'export'),
      text: { type: 'plain_text', text: 'Export List' },
    },
  ];
  if (hasNext) {
    toolbar.unshift({
      type: 'button',
      action_id: 'table_next_page',
      // questionId slot carries the next page number for this run.
      value: actionValue(runId, String(opts.page + 1)),
      text: { type: 'plain_text', text: 'Next page →' },
    });
  }
  blocks.push({ type: 'actions', elements: toolbar });

  return blocks;
}

export function answerCardBlocks(r: DraftResult, runId = '', confirmed = false): Block[] {
  const value = actionValue(runId, r.questionId);
  const blocks: Block[] = [
    {
      type: 'section',
      text: { type: 'mrkdwn', text: `*${r.questionText}*\n${STATE_EMOJI[r.state]} ${STATE_LABEL[r.state]}` },
    },
  ];

  if (r.state === 'needs_sme') {
    blocks.push(
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `_No draft — ${REASON_LABEL[r.reason ?? 'no_evidence']}._\nAsked & Answered would rather ask a human than invent a compliance answer.`,
        },
      },
      {
        type: 'actions',
        elements: [
          {
            type: 'button',
            action_id: 'route_to_sme',
            value,
            style: 'primary',
            text: { type: 'plain_text', text: 'Route to an expert' },
          },
        ],
      },
    );
    return blocks;
  }

  blocks.push({ type: 'section', text: { type: 'mrkdwn', text: r.answerText ?? '' } });

  const citationLines = (r.citations ?? [])
    .map((c, i) => `<${c.permalink}|evidence ${i + 1}>`)
    .join('  ·  ');
  if (citationLines) {
    blocks.push({
      type: 'context',
      elements: [{ type: 'mrkdwn', text: `:link: ${citationLines}` }],
    });
  }

  if (r.state === 'verified') {
    blocks.push({
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `:shield: Verified — approved by <@${r.approvedBy}> on ${r.approvedAt ?? ''} · re-checked against your permissions`,
        },
      ],
    });
  }

  if (r.state !== 'verified') {
    const primaryButton = confirmed
      ? {
          type: 'button',
          action_id: 'approve_answer',
          value,
          style: 'primary',
          text: { type: 'plain_text', text: 'Approve' },
        }
      : {
          type: 'button',
          action_id: 'confirm_answer',
          value,
          style: 'primary',
          text: { type: 'plain_text', text: 'Confirm' },
        };
    blocks.push({
      type: 'actions',
      elements: [
        primaryButton,
        {
          type: 'button',
          action_id: 'edit_answer',
          value,
          text: { type: 'plain_text', text: 'Edit' },
        },
        {
          type: 'button',
          action_id: 'reject_answer',
          value,
          style: 'danger',
          text: { type: 'plain_text', text: 'Reject' },
        },
      ],
    });
  }

  return blocks;
}

export function smeRequestBlocks(input: {
  questionText: string;
  requesterId: string;
  /** Opaque `runId:questionId` ref, round-tripped back through the modal. */
  ref: string;
}): Block[] {
  return [
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text:
          `:raised_hand: <@${input.requesterId}> needs your expertise on a questionnaire question:\n` +
          `*${input.questionText}*\n\n_Asked & Answered found no sufficient evidence in the workspace, so it did not draft an answer._`,
      },
    },
    {
      type: 'actions',
      elements: [
        {
          type: 'button',
          action_id: 'sme_provide_answer',
          value: input.ref,
          style: 'primary',
          text: { type: 'plain_text', text: 'Provide an answer' },
        },
      ],
    },
  ];
}

export function verifyResultBlocks(result: VerifyResult): Block[] {
  if (result.ok) {
    return [
      {
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `:white_check_mark: *Ledger intact.* ${result.entriesChecked} entries verified — every hash chains cleanly to genesis.`,
        },
      },
    ];
  }
  return [
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text:
          `:rotating_light: *Ledger verification FAILED.* Tampering detected at entry *#${result.firstBadSeq}* ` +
          `(of ${result.entriesChecked} checked). The approval trail after this point cannot be trusted.`,
      },
    },
  ];
}

export interface RunSignatures {
  /** ISO timestamp of the run/audit event. */
  timestamp: string;
  /** User id that confirmed the draft. */
  confirmActor?: string | undefined;
  /** User id that gave final approval. */
  approveActor?: string | undefined;
}

function runSignatureHash(
  runId: string,
  result: DraftResult,
  signatures: RunSignatures = { timestamp: new Date().toISOString() },
): string {
  const citations = (result.citations ?? []).map((c) => c.permalink).join(',');
  const actors = [signatures.confirmActor, signatures.approveActor].filter(Boolean).join('|');
  const payload = `${runId}:${result.questionId}:${result.answerText ?? result.reason ?? ''}:${citations}:${actors}`;
  return createHash('sha256').update(payload).digest('hex');
}

/** Render a single answer as a signed "Agent Run" audit card. */
export function agentRunCardBlocks(
  result: DraftResult,
  runId = '',
  signatures: RunSignatures = { timestamp: new Date().toISOString() },
): Block[] {
  const signature = runSignatureHash(runId, result, signatures);
  const blocks: Block[] = [
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*${result.questionText}*\n${STATE_EMOJI[result.state]} ${STATE_LABEL[result.state]}`,
      },
    },
  ];

  if (result.state === 'needs_sme') {
    blocks.push({
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `_No draft — ${REASON_LABEL[result.reason ?? 'no_evidence']}._`,
      },
    });
  } else {
    blocks.push({ type: 'section', text: { type: 'mrkdwn', text: result.answerText ?? '' } });
    const citationLines = (result.citations ?? [])
      .map((c, i) => `<${c.permalink}|evidence ${i + 1}>`)
      .join('  ·  ');
    if (citationLines) {
      blocks.push({
        type: 'context',
        elements: [{ type: 'mrkdwn', text: `:link: ${citationLines}` }],
      });
    }
  }

  const actorParts: string[] = [];
  if (signatures.confirmActor) actorParts.push(`Confirmed by <@${signatures.confirmActor}>`);
  if (signatures.approveActor) actorParts.push(`Approved by <@${signatures.approveActor}>`);

  const footerParts: string[] = [`Run \`${runId}\` · ${signatures.timestamp}`];
  if (actorParts.length > 0) footerParts.push(actorParts.join(' · '));
  footerParts.push(`Signature \`${signature}\``);

  blocks.push({
    type: 'context',
    elements: [{ type: 'mrkdwn', text: `:lock: ${footerParts.join(' · ')}` }],
  });

  return blocks;
}

/** Plain-text audit line suitable for exports and logs. */
export function signedAuditText(
  result: DraftResult,
  runId = '',
  signatures: RunSignatures = { timestamp: new Date().toISOString() },
): string {
  const signature = runSignatureHash(runId, result, signatures);
  const actors = [signatures.confirmActor, signatures.approveActor].filter(Boolean).join('|');
  return `[${signatures.timestamp}] run=${runId} q=${result.questionId} state=${result.state} actors=${actors} sig=${signature}`;
}

/** DM card for the proactive stale/contradiction watcher. */
export function staleAlertBlocks(alert: StaleAlert): Block[] {
  const contradictionLinks = alert.contradictions
    .map((c, i) => `<${c.evidence.permalink}|contradiction ${i + 1}>`)
    .join('  ·  ');
  const supersessionLinks = alert.supersessions
    .map((s, i) => `<${s.newEvidence.permalink}|superseder ${i + 1}>`)
    .join('  ·  ');

  const contextParts: string[] = [];
  if (contradictionLinks) contextParts.push(`:warning: New contradicting evidence: ${contradictionLinks}`);
  if (supersessionLinks) contextParts.push(`:new: Superseding evidence: ${supersessionLinks}`);

  const blocks: Block[] = [
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `:rotating_light: *Stale answer detected* · approved by <@${alert.approvedBy}> on ${alert.approvedAt}`,
      },
    },
    {
      type: 'section',
      text: {
        type: 'mrkdwn',
        text: `*Q:* ${alert.questionText}\n*A:* ${alert.answerText.slice(0, 200)}${alert.answerText.length > 200 ? '…' : ''}`,
      },
    },
  ];

  if (contextParts.length > 0) {
    blocks.push({
      type: 'context',
      elements: [{ type: 'mrkdwn', text: contextParts.join('\n') }],
    });
  }

  blocks.push({
    type: 'actions',
    elements: [
      {
        type: 'button',
        action_id: 'open_stale_review_modal',
        value: String(alert.answerId),
        text: { type: 'plain_text', text: 'Open review modal' },
      },
    ],
  });

  return blocks;
}
