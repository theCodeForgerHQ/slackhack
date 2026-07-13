/**
 * Ephemeral decision knowledge graph.
 *
 * Inspired by Lore (drMurlly/lore-slack-agent): instead of treating retrieved
 * evidence as a flat hit list, this module extracts typed values from snippets,
 * links them to topics and timestamps, and builds chronological supersession
 * edges so the pipeline can detect when a newer answer reverses an older one.
 *
 * The graph is rebuilt per questionnaire run from the retrieved evidence. It is
 * intentionally lightweight and deterministic: no LLM calls, only regex-based
 * value extraction and token overlap.
 */

export interface EvidenceNode {
  id: string;
  kind: 'evidence';
  permalink: string;
  channelId: string;
  ts: string;
  snippet: string;
}

export interface TopicNode {
  id: string;
  kind: 'topic';
  text: string;
  normalized: string;
}

export interface ValueNode {
  id: string;
  kind: 'value';
  text: string;
  /** 'boolean' | 'number' | 'money' | 'date' | 'region' | 'text' */
  valueClass: string;
  ts: string;
  permalink: string;
}

export interface SupportsEdge {
  kind: 'supports';
  from: string;
  to: string;
}

export interface SupersedesEdge {
  kind: 'supersedes';
  from: string;
  to: string;
}

export type GraphNode = EvidenceNode | TopicNode | ValueNode;
export type GraphEdge = SupportsEdge | SupersedesEdge;

export interface DecisionRow {
  topic: string;
  currentValue: string;
  previousValue?: string;
  permalink: string;
  ts: string;
  reversed: boolean;
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function tokens(text: string): Set<string> {
  return new Set(normalize(text).split(' ').filter((t) => t.length > 2));
}

function overlap(a: string, b: string): number {
  const ta = tokens(a);
  const tb = tokens(b);
  if (ta.size === 0 || tb.size === 0) return 0;
  let shared = 0;
  for (const t of ta) if (tb.has(t)) shared++;
  return shared / Math.min(ta.size, tb.size);
}

/** Extract likely boolean/value statements from a snippet. */
function extractValues(snippet: string): Array<{ text: string; valueClass: string }> {
  const values: Array<{ text: string; valueClass: string }> = [];
  const norm = snippet.toLowerCase();

  // Boolean statements: explicit yes/no or "is (not) <state>" patterns.
  const yesNo = /\b(are|is|do|does|can|will|must|have|has)\b[^.!?]{0,60}\b(yes|no|not|never|always|enforced|required|optional)\b/gi;
  let m: RegExpExecArray | null;
  while ((m = yesNo.exec(snippet)) !== null) {
    values.push({ text: m[0].trim(), valueClass: 'boolean' });
  }

  // Passive/active state: "data is encrypted", "MFA is not enforced", "we use AES".
  const statePattern = /\b\w+[\s\w]*\s+(is|are|was|were)\s+(not\s+)?[\s\w]*(encrypted|enforced|protected|signed|logged|segmented|reviewed|tested|required|allowed)\b/gi;
  while ((m = statePattern.exec(snippet)) !== null) {
    values.push({ text: m[0].trim(), valueClass: 'boolean' });
  }

  // Action verbs that imply a policy state.
  const actionPattern = /\b(uses?|protects?|stores?|processes?|requires?)\s+[^.!?]{0,40}(AES|KMS|TLS|MFA|Okta|SIEM|MDM|VPN|encryption|authentication)\b/gi;
  while ((m = actionPattern.exec(snippet)) !== null) {
    values.push({ text: m[0].trim(), valueClass: 'boolean' });
  }

  // Numbers with units.
  const numbers = /\b(\d+(?:\.\d+)?)\s*(days?|months?|years?|hours?|minutes?|%|percent|\$[\d,]+m?|million?|billion?)\b/gi;
  while ((m = numbers.exec(snippet)) !== null) {
    values.push({ text: m[0].trim(), valueClass: 'number' });
  }

  // Regions / providers.
  if (/\b(us-east|us-west|eu-west|ap-south|aws|gcp|azure)\b/gi.test(norm)) {
    const regionMatch = snippet.match(/\b(us-east-[12]|us-west-[12]|eu-west-[123]|ap-south-1|aws|gcp|azure)\b/gi);
    if (regionMatch) values.push({ text: regionMatch[0]!, valueClass: 'region' });
  }

  return values.slice(0, 3); // cap to avoid noise
}

function topicOf(question: string): string {
  // Strip leading auxiliary verbs to get the topic stem.
  return normalize(question).replace(/^\b(do|does|is|are|can|will|have|has|did)\b\s*/, '').trim();
}

export class DecisionGraph {
  private nodes = new Map<string, GraphNode>();
  private edges: GraphEdge[] = [];

  addEvidence(permalink: string, channelId: string, ts: string, snippet: string): void {
    const evidenceId = `ev:${permalink}`;
    this.nodes.set(evidenceId, { id: evidenceId, kind: 'evidence', permalink, channelId, ts, snippet });

    const values = extractValues(snippet);
    for (const v of values) {
      const valueId = `val:${permalink}:${v.text}`;
      this.nodes.set(valueId, { id: valueId, kind: 'value', text: v.text, valueClass: v.valueClass, ts, permalink });
      this.edges.push({ kind: 'supports', from: evidenceId, to: valueId });
    }
  }

  /** Build supersedes edges between values of the same class on similar topics. */
  resolve(question: string): DecisionRow[] {
    const topic = topicOf(question);
    const values = [...this.nodes.values()].filter((n): n is ValueNode => n.kind === 'value');

    // Group values by class.
    const byClass = new Map<string, ValueNode[]>();
    for (const v of values) {
      const list = byClass.get(v.valueClass) ?? [];
      list.push(v);
      byClass.set(v.valueClass, list);
    }

    const rows: DecisionRow[] = [];
    for (const [valueClass, classValues] of byClass.entries()) {
      // Filter to values whose supporting evidence overlaps the question topic.
      const relevant = classValues.filter((v) => {
        const ev = this.nodes.get(`ev:${v.permalink}`);
        if (!ev || ev.kind !== 'evidence') return false;
        return overlap(ev.snippet, topic) >= 0.3;
      });

      if (relevant.length < 2) continue;

      // Sort oldest → newest.
      relevant.sort((a, b) => Number(a.ts) - Number(b.ts));

      // Build supersedes chain.
      for (let i = 1; i < relevant.length; i++) {
        const prev = relevant[i - 1]!;
        const curr = relevant[i]!;
        this.edges.push({ kind: 'supersedes', from: curr.id, to: prev.id });
      }

      const newest = relevant[relevant.length - 1]!;
      const oldest = relevant[0]!;
      rows.push({
        topic: valueClass,
        currentValue: newest.text,
        previousValue: oldest.text,
        permalink: newest.permalink,
        ts: newest.ts,
        reversed: relevant.some((v, i) => i > 0 && this.isContradictory(relevant[i - 1]!, v)),
      });
    }

    return rows;
  }

  private isContradictory(a: ValueNode, b: ValueNode): boolean {
    if (a.valueClass !== b.valueClass) return false;
    const ta = a.text.toLowerCase();
    const tb = b.text.toLowerCase();

    // Boolean flip detection.
    if (a.valueClass === 'boolean') {
      const yesA = /\b(yes|enforced|required|always|is|are|do|does)\b/.test(ta) && !/\b(no|not|never)\b/.test(ta);
      const noA = /\b(no|not|never)\b/.test(ta);
      const yesB = /\b(yes|enforced|required|always|is|are|do|does)\b/.test(tb) && !/\b(no|not|never)\b/.test(tb);
      const noB = /\b(no|not|never)\b/.test(tb);
      return (yesA && noB) || (noA && yesB);
    }

    // Different concrete values in same class are treated as drift.
    if (a.valueClass === 'region') {
      return normalize(ta) !== normalize(tb);
    }

    return false;
  }

  getNodes(): GraphNode[] {
    return [...this.nodes.values()];
  }

  getEdges(): GraphEdge[] {
    return this.edges;
  }
}
