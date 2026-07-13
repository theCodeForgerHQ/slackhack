import { describe, test, expect } from 'vitest';
import { EvidenceGraph } from '../src/core/evidenceGraph.js';

describe('EvidenceGraph', () => {
  test('supports and contradicts links are stored', () => {
    const g = new EvidenceGraph();
    g.addEvidence({ id: 'e1', kind: 'evidence', permalink: 'p/enc', channelId: 'C1', ts: '1', snippet: 'AES-256', observedAt: '2026-01-01' });
    g.addClaim({ id: 'c1', kind: 'claim', text: 'We encrypt data at rest.', sourceId: 'a1' });
    g.supports('e1', 'c1');
    g.contradicts('e1', 'c1');

    expect(g.edgesFrom('e1').map((e) => e.kind)).toEqual(['SUPPORTS', 'CONTRADICTS']);
  });

  test('auto-detects contradiction via negation flip', () => {
    const g = new EvidenceGraph();
    g.addClaim({ id: 'c1', kind: 'claim', text: 'We encrypt data at rest with AES-256.', sourceId: 'a1' });
    g.addEvidence({ id: 'e1', kind: 'evidence', permalink: 'p/new', channelId: 'C1', ts: '2', snippet: 'We do not encrypt data at rest.', observedAt: '2026-02-01' });

    expect(g.contradictedClaims()).toHaveLength(1);
    expect(g.contradictedClaims()[0]?.id).toBe('c1');
  });

  test('auto-detects contradiction when claim is added after evidence', () => {
    const g = new EvidenceGraph();
    g.addEvidence({ id: 'e1', kind: 'evidence', permalink: 'p/new', channelId: 'C1', ts: '2', snippet: 'MFA is not enforced for any employee.', observedAt: '2026-02-01' });
    g.addClaim({ id: 'c1', kind: 'claim', text: 'MFA is enforced for every employee.', sourceId: 'a1' });

    expect(g.contradictedClaims()).toHaveLength(1);
  });

  test('no false contradiction when topics differ', () => {
    const g = new EvidenceGraph();
    g.addClaim({ id: 'c1', kind: 'claim', text: 'We encrypt data at rest.', sourceId: 'a1' });
    g.addEvidence({ id: 'e1', kind: 'evidence', permalink: 'p/mfa', channelId: 'C1', ts: '2', snippet: 'MFA is enforced for every employee.', observedAt: '2026-02-01' });

    expect(g.contradictedClaims()).toHaveLength(0);
  });

  test('contradictionsForAnswer returns conflicting evidence', () => {
    const g = new EvidenceGraph();
    g.addAnswer({ id: 'a1', kind: 'answer', answerId: 1, questionText: 'Q', answerText: 'Yes.' });
    g.addEvidence({ id: 'e1', kind: 'evidence', permalink: 'p/old', channelId: 'C1', ts: '1', snippet: 'We encrypt data at rest.', observedAt: '2026-01-01' });
    g.addClaim({ id: 'c1', kind: 'claim', text: 'We encrypt data at rest.', sourceId: 'a1' });
    g.supports('a1', 'c1');
    g.addEvidence({ id: 'e2', kind: 'evidence', permalink: 'p/new', channelId: 'C1', ts: '2', snippet: 'We do not encrypt data at rest.', observedAt: '2026-02-01' });

    const contradictions = g.contradictionsForAnswer(1);
    expect(contradictions).toHaveLength(1);
    expect(contradictions[0]?.conflictingEvidence.permalink).toBe('p/new');
    expect(g.isStale(1)).toBe(true);
  });

  test('manual contradiction link works for cases heuristic misses', () => {
    const g = new EvidenceGraph();
    g.addClaim({ id: 'c1', kind: 'claim', text: 'Backups are quarterly.', sourceId: 'a1' });
    g.addEvidence({ id: 'e1', kind: 'evidence', permalink: 'p/new', channelId: 'C1', ts: '2', snippet: 'Backup restore drills happen annually.', observedAt: '2026-02-01' });
    g.contradicts('e1', 'c1');

    expect(g.contradictedClaims()).toHaveLength(1);
  });

  test('supersedes link is stored and retrievable', () => {
    const g = new EvidenceGraph();
    g.addEvidence({ id: 'e1', kind: 'evidence', permalink: 'p/old', channelId: 'C1', ts: '1', snippet: 'old', observedAt: '2026-01-01' });
    g.addEvidence({ id: 'e2', kind: 'evidence', permalink: 'p/new', channelId: 'C1', ts: '2', snippet: 'new', observedAt: '2026-02-01' });
    g.supersedes('e2', 'e1');

    expect(g.edgesFrom('e2')[0]?.kind).toBe('SUPERSEDES');
  });
});
