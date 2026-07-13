/**
 * Evidence graph: typed claims, evidence, and approved answers with
 * SUPPORTS / CONTRADICTS / SUPERSEDES edges.
 *
 * This is A&A's answer to Consensus's flat decision ledger and Arbiter's
 * Neo4j claim graph. It lets the agent detect when newer workspace evidence
 * contradicts an approved answer before that answer is reused.
 */

export interface EvidenceNode {
  id: string;
  kind: 'evidence';
  permalink: string;
  channelId: string;
  ts: string;
  snippet: string;
  /** ISO timestamp when this evidence was observed. */
  observedAt: string;
}

export interface ClaimNode {
  id: string;
  kind: 'claim';
  /** The claim text, extracted from an answer or evidence snippet. */
  text: string;
  /** ID of the source node (evidence or answer) that produced this claim. */
  sourceId: string;
}

export interface AnswerNode {
  id: string;
  kind: 'answer';
  /** Matches the AnswerLibrary row id. */
  answerId: number;
  questionText: string;
  answerText: string;
}

export type Node = EvidenceNode | ClaimNode | AnswerNode;
export type EdgeKind = 'SUPPORTS' | 'CONTRADICTS' | 'SUPERSEDES';

export interface Edge {
  from: string;
  to: string;
  kind: EdgeKind;
}

export interface Contradiction {
  claim: ClaimNode;
  conflictingEvidence: EvidenceNode;
}

/**
 * Simple deterministic contradiction signal.
 *
 * A new evidence snippet contradicts an existing claim when:
 *   1. They share high character-trigram overlap (same topic), AND
 *   2. The evidence contains a negation word ("not", "no", "never") that the
 *      claim does not, or vice versa.
 *
 * This is intentionally conservative: false positives degrade to a human,
 * which is safe; false negatives are caught by manual contradiction links.
 */
function containsNegation(text: string): boolean {
  return /\b(not|no|never|none|nothing|nowhere|neither|nobody)\b/.test(text.toLowerCase());
}

function trigrams(text: string): Set<string> {
  const set = new Set<string>();
  const chars = [...text.toLowerCase().replace(/[^a-z0-9]/g, '')];
  for (let i = 0; i <= chars.length - 3; i++) {
    set.add(chars.slice(i, i + 3).join(''));
  }
  return set;
}

function trigramJaccard(a: string, b: string): number {
  const ta = trigrams(a);
  const tb = trigrams(b);
  if (ta.size === 0 || tb.size === 0) return 0;
  let intersection = 0;
  for (const g of ta) if (tb.has(g)) intersection++;
  return intersection / (ta.size + tb.size - intersection);
}

function normalizeForContradiction(text: string): string {
  return text
    .toLowerCase()
    .replace(/^(no|yes),?\s+/i, '')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function stemWord(w: string): string {
  // Very light stemming: remove trailing 's' and common suffixes.
  return w.replace(/(s|es|ing|ed)$/, '');
}

function wordTokens(text: string): Set<string> {
  return new Set(
    normalizeForContradiction(text)
      .split(/\s+/)
      .filter((w) => w.length > 2 && !['the', 'and', 'are', 'for', 'with', 'this', 'that', 'you', 'our'].includes(w))
      .map(stemWord),
  );
}

function tokenJaccard(a: string, b: string): number {
  const ta = wordTokens(a);
  const tb = wordTokens(b);
  if (ta.size === 0 || tb.size === 0) return 0;
  let intersection = 0;
  for (const t of ta) if (tb.has(t)) intersection++;
  return intersection / (ta.size + tb.size - intersection);
}

function looksContradictory(claimText: string, evidenceSnippet: string): boolean {
  // Strong topic overlap: either word-level (better for short claims) or
  // trigram-level (better for longer paraphrases).
  const topicOverlap = tokenJaccard(claimText, evidenceSnippet) >= 0.3 || trigramJaccard(claimText, evidenceSnippet) >= 0.2;
  if (!topicOverlap) return false;
  const claimNeg = containsNegation(claimText);
  const evidenceNeg = containsNegation(evidenceSnippet);
  return claimNeg !== evidenceNeg;
}

export class EvidenceGraph {
  private readonly nodes = new Map<string, Node>();
  private readonly edges = new Map<string, Edge[]>();

  addNode(node: Node): void {
    this.nodes.set(node.id, node);
    if (!this.edges.has(node.id)) this.edges.set(node.id, []);
  }

  link(from: string, to: string, kind: EdgeKind): void {
    if (!this.nodes.has(from)) throw new Error(`unknown node ${from}`);
    if (!this.nodes.has(to)) throw new Error(`unknown node ${to}`);
    const list = this.edges.get(from) ?? [];
    list.push({ from, to, kind });
    this.edges.set(from, list);
  }

  getNode(id: string): Node | undefined {
    return this.nodes.get(id);
  }

  edgesFrom(id: string): Edge[] {
    return [...(this.edges.get(id) ?? [])];
  }

  /** Add an evidence node and auto-detect contradictions against existing claims. */
  addEvidence(node: EvidenceNode): void {
    this.addNode(node);
    for (const n of this.nodes.values()) {
      if (n.kind === 'claim' && looksContradictory(n.text, node.snippet)) {
        this.link(node.id, n.id, 'CONTRADICTS');
      }
    }
  }

  /** Add a claim node and auto-detect contradictions against existing evidence. */
  addClaim(node: ClaimNode): void {
    this.addNode(node);
    for (const n of this.nodes.values()) {
      if (n.kind === 'evidence' && looksContradictory(node.text, n.snippet)) {
        this.link(n.id, node.id, 'CONTRADICTS');
      }
    }
  }

  addAnswer(node: AnswerNode): void {
    this.addNode(node);
  }

  /** Link evidence to a claim it supports. */
  supports(evidenceId: string, claimId: string): void {
    this.link(evidenceId, claimId, 'SUPPORTS');
  }

  /** Link newer evidence to older evidence it supersedes. */
  supersedes(newerEvidenceId: string, olderEvidenceId: string): void {
    this.link(newerEvidenceId, olderEvidenceId, 'SUPERSEDES');
  }

  /** Manual contradiction link for cases the heuristic misses. */
  contradicts(evidenceId: string, claimId: string): void {
    this.link(evidenceId, claimId, 'CONTRADICTS');
  }

  /** Find all claims contradicted by any evidence in the graph. */
  contradictedClaims(): ClaimNode[] {
    const out: ClaimNode[] = [];
    const seen = new Set<string>();
    for (const edges of this.edges.values()) {
      for (const e of edges) {
        if (e.kind === 'CONTRADICTS') {
          const target = this.nodes.get(e.to);
          if (target?.kind === 'claim' && !seen.has(target.id)) {
            out.push(target);
            seen.add(target.id);
          }
        }
      }
    }
    return out;
  }

  /** Return contradictions relevant to a specific approved answer. */
  contradictionsForAnswer(answerId: number): Contradiction[] {
    const answerNode = [...this.nodes.values()].find(
      (n): n is AnswerNode => n.kind === 'answer' && n.answerId === answerId,
    );
    if (!answerNode) return [];

    const claimIds = new Set<string>();
    // Claims directly attached to the answer via an outgoing or incoming edge.
    for (const e of this.edgesFrom(answerNode.id)) {
      if (e.kind === 'SUPPORTS' || e.kind === 'CONTRADICTS') claimIds.add(e.to);
    }
    for (const edges of this.edges.values()) {
      for (const e of edges) {
        if (e.to === answerNode.id && (e.kind === 'SUPPORTS' || e.kind === 'CONTRADICTS')) {
          claimIds.add(e.from);
        }
      }
    }

    const out: Contradiction[] = [];
    for (const claimId of claimIds) {
      const claim = this.nodes.get(claimId);
      if (claim?.kind !== 'claim') continue;
      // Contradiction edges point FROM evidence TO claim.
      const conflicting: EvidenceNode[] = [];
      for (const edges of this.edges.values()) {
        for (const e of edges) {
          if (e.to === claimId && e.kind === 'CONTRADICTS') {
            const node = this.nodes.get(e.from);
            if (node?.kind === 'evidence') conflicting.push(node);
          }
        }
      }
      for (const ev of conflicting) {
        out.push({ claim, conflictingEvidence: ev });
      }
    }
    return out;
  }

  /** True if any claim supporting the answer is contradicted by newer evidence. */
  isStale(answerId: number): boolean {
    return this.contradictionsForAnswer(answerId).length > 0;
  }
}
