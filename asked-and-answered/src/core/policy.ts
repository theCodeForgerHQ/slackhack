/**
 * Lightweight approval-policy engine.
 *
 * Asked & Answered already enforces two mandatory human gates (confirm + approve)
 * with distinct actors. This module adds configurable N-of-M approval for
 * high-sensitivity questions, matching the governance layers in Aegis and Kept.
 *
 * The policy is additive: the default remains one confirmer + one approver.
 * When a question matches a high-sensitivity pattern, two distinct approvers
 * are required after confirmation before the answer enters the reusable library.
 */

export interface ApprovalPolicy {
  mode: 'two_gate' | 'n_of_m';
  /** Number of distinct human approvers required after confirmation. */
  requiredApprovers: number;
}

export const DEFAULT_POLICY: ApprovalPolicy = { mode: 'two_gate', requiredApprovers: 1 };

export const HIGH_SENSITIVITY_POLICY: ApprovalPolicy = { mode: 'n_of_m', requiredApprovers: 2 };

const HIGH_SENSITIVITY_TERMS =
  /\b(breach|private|classified|secret|confidential|restriction|officer|executive|compromise|covert|privileged|sensitive|gdpr|hipaa|soc 2 type ii)\b/i;

/** Pick a policy based on question text. */
export function selectPolicy(questionText: string): ApprovalPolicy {
  return HIGH_SENSITIVITY_TERMS.test(questionText) ? HIGH_SENSITIVITY_POLICY : DEFAULT_POLICY;
}

/** True if the answer already has enough distinct human approvers under the policy. */
export function isFinalApproval(approvers: string[], policy: ApprovalPolicy): boolean {
  const distinct = new Set(approvers).size;
  return distinct >= policy.requiredApprovers;
}
