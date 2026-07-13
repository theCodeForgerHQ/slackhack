import { describe, test, expect, vi } from 'vitest';
import { EvidenceGraph } from '../src/core/evidenceGraph.js';
import { AnswerLibrary } from '../src/core/library.js';
import { Watcher, type StaleAlert } from '../src/core/watcher.js';

describe('Watcher', () => {
  function setup() {
    const graph = new EvidenceGraph();
    const library = AnswerLibrary.inMemory(graph);
    const alerts: StaleAlert[] = [];
    const watcher = new Watcher(library, graph, {
      now: () => 0,
      onStale: (a) => {
        alerts.push(a);
      },
    });
    return { graph, library, watcher, alerts };
  }

  test('emits a StaleAlert when new evidence contradicts an approved answer claim', () => {
    const { library, graph, watcher, alerts } = setup();

    library.saveApproved({
      questionText: 'Do you encrypt data at rest?',
      answerText: 'Yes, we encrypt all data at rest.',
      citations: [{ permalink: 'https://s.example/old', channelId: 'C1', ts: '1.0' }],
      approvedBy: 'U_APPROVER',
    });

    // Backfill the actual snippet so the graph can reason about the citation.
    library.observeEvidence('https://s.example/old', 'C1', '1.0', 'we encrypt data at rest');

    // Newer workspace evidence contradicts the claim.
    library.observeEvidence('https://s.example/new', 'C2', '2.0', 'we do not encrypt data at rest');

    watcher.scan();

    expect(alerts).toHaveLength(1);
    expect(alerts[0]?.answerId).toBe(1);
    expect(alerts[0]?.contradictions.length).toBeGreaterThan(0);
    expect(alerts[0]?.contradictions[0]?.evidence.permalink).toBe('https://s.example/new');
  });

  test('emits a StaleAlert when an answer citation is superseded by newer evidence', () => {
    const { library, graph, watcher, alerts } = setup();

    library.saveApproved({
      questionText: 'What MFA provider do you use?',
      answerText: 'We use Okta for MFA.',
      citations: [{ permalink: 'https://s.example/old-mfa', channelId: 'C1', ts: '1.0' }],
      approvedBy: 'U_APPROVER',
    });

    const newerId = 'evidence:https://s.example/new-mfa';
    graph.addEvidence({
      id: newerId,
      kind: 'evidence',
      permalink: 'https://s.example/new-mfa',
      channelId: 'C2',
      ts: '2.0',
      snippet: 'we migrated MFA to Duo in 2026',
      observedAt: '2026-07-14T00:00:00.000Z',
    });
    graph.supersedes(newerId, 'evidence:https://s.example/old-mfa');

    watcher.scan();

    expect(alerts).toHaveLength(1);
    expect(alerts[0]?.supersessions.length).toBe(1);
    expect(alerts[0]?.supersessions[0]?.newEvidence.permalink).toBe('https://s.example/new-mfa');
  });

  test('dedupes alerts for the same answer across repeated scans', () => {
    const { library, graph, watcher, alerts } = setup();

    library.saveApproved({
      questionText: 'Do you encrypt data at rest?',
      answerText: 'Yes, we encrypt all data at rest.',
      citations: [{ permalink: 'https://s.example/old', channelId: 'C1', ts: '1.0' }],
      approvedBy: 'U_APPROVER',
    });
    library.observeEvidence('https://s.example/old', 'C1', '1.0', 'we encrypt data at rest');
    library.observeEvidence('https://s.example/new', 'C2', '2.0', 'we do not encrypt data at rest');

    watcher.scan();
    watcher.scan();

    expect(alerts).toHaveLength(1);
    expect(watcher.getPendingAlerts()).toHaveLength(1);
  });

  test('fires async callbacks without crashing on rejection', async () => {
    const { library, graph, watcher } = setup();
    const bad = vi.fn().mockRejectedValue(new Error('boom'));
    const good = vi.fn();
    const w = new Watcher(library, graph, {
      now: () => 0,
      onStale: (a) => {
        bad(a);
        good(a);
      },
    });

    library.saveApproved({
      questionText: 'Do you encrypt data at rest?',
      answerText: 'Yes, we encrypt all data at rest.',
      citations: [{ permalink: 'https://s.example/old', channelId: 'C1', ts: '1.0' }],
      approvedBy: 'U_APPROVER',
    });
    library.observeEvidence('https://s.example/old', 'C1', '1.0', 'we encrypt data at rest');
    library.observeEvidence('https://s.example/new', 'C2', '2.0', 'we do not encrypt data at rest');

    w.scan();
    // Give the microtask queue a chance to run the rejected promise handler.
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(good).toHaveBeenCalledTimes(1);
  });
});
