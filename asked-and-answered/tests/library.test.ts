import { describe, test, expect, beforeEach } from 'vitest';
import fc from 'fast-check';
import { AnswerLibrary, type VisibilityChecker, type Citation } from '../src/core/library.js';

/** Fake ACL: a map of userId -> set of visible permalinks. */
function fakeChecker(acl: Record<string, string[]>): VisibilityChecker {
  return {
    async canSee(userId: string, citation: Citation): Promise<boolean> {
      return (acl[userId] ?? []).includes(citation.permalink);
    },
  };
}

const C1: Citation = { permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' };
const C2: Citation = { permalink: 'https://s.example/p2', channelId: 'C2', ts: '2.0' };

describe('AnswerLibrary', () => {
  let lib: AnswerLibrary;

  beforeEach(() => {
    lib = AnswerLibrary.inMemory();
  });

  test('stores an approved answer and finds it for an identically-normalized question', async () => {
    lib.saveApproved({
      questionText: 'Do you encrypt data at rest?',
      answerText: 'Yes — AES-256 via cloud KMS.',
      citations: [C1],
      approvedBy: 'U_SME',
    });

    const checker = fakeChecker({ U_REQ: [C1.permalink] });
    const hit = await lib.findVerified('do you encrypt data at rest', 'U_REQ', checker);

    expect(hit.status).toBe('verified');
    if (hit.status === 'verified') {
      expect(hit.answer.answerText).toBe('Yes — AES-256 via cloud KMS.');
      expect(hit.answer.approvedBy).toBe('U_SME');
    }
  });

  test('misses for an unrelated question', async () => {
    lib.saveApproved({
      questionText: 'Do you encrypt data at rest?',
      answerText: 'Yes.',
      citations: [C1],
      approvedBy: 'U_SME',
    });

    const checker = fakeChecker({ U_REQ: [C1.permalink] });
    const hit = await lib.findVerified('Do you run a bug bounty program?', 'U_REQ', checker);

    expect(hit.status).toBe('miss');
  });

  test('THE INVARIANT: degrades when the requester cannot see every citation', async () => {
    lib.saveApproved({
      questionText: 'Where is customer data hosted?',
      answerText: 'AWS eu-west-1, discussed in #infra-private.',
      citations: [C1, C2],
      approvedBy: 'U_SME',
    });

    // Requester can see C1 but not C2 (private channel evidence).
    const checker = fakeChecker({ U_REQ: [C1.permalink] });
    const hit = await lib.findVerified('Where is customer data hosted?', 'U_REQ', checker);

    expect(hit.status).toBe('degraded');
    if (hit.status === 'degraded') {
      expect(hit.blockedCitations).toEqual([C2.permalink]);
      // The result must not carry the answer text anywhere.
      expect(JSON.stringify(hit)).not.toContain('AWS eu-west-1');
    }
  });

  test('a requester with full visibility still gets the verified answer', async () => {
    lib.saveApproved({
      questionText: 'Where is customer data hosted?',
      answerText: 'AWS eu-west-1.',
      citations: [C1, C2],
      approvedBy: 'U_SME',
    });

    const checker = fakeChecker({ U_PRIV: [C1.permalink, C2.permalink] });
    const hit = await lib.findVerified('Where is customer data hosted?', 'U_PRIV', checker);

    expect(hit.status).toBe('verified');
  });

  test('near-duplicate question phrasing still matches (token overlap)', async () => {
    lib.saveApproved({
      questionText: 'Is multi-factor authentication enforced for all employees?',
      answerText: 'Yes, via Okta.',
      citations: [C1],
      approvedBy: 'U_SME',
    });

    const checker = fakeChecker({ U_REQ: [C1.permalink] });
    const hit = await lib.findVerified(
      'Is multi-factor authentication enforced for employees?',
      'U_REQ',
      checker,
    );

    expect(hit.status).toBe('verified');
  });

  test('PROPERTY: answer text is returned iff the requester can see ALL citations', async () => {
    await fc.assert(
      fc.asyncProperty(
        // 1-4 citations for the stored answer
        fc.uniqueArray(fc.integer({ min: 0, max: 9 }), { minLength: 1, maxLength: 4 }),
        // the subset of permalink indices the requester can see (0-9 universe)
        fc.uniqueArray(fc.integer({ min: 0, max: 9 })),
        async (citationIdxs, visibleIdxs) => {
          const lib2 = AnswerLibrary.inMemory();
          const citations: Citation[] = citationIdxs.map((i) => ({
            permalink: `https://s.example/p${i}`,
            channelId: `C${i}`,
            ts: `${i}.0`,
          }));
          const SECRET = 'SECRET_ANSWER_TEXT_DO_NOT_LEAK';
          lib2.saveApproved({
            questionText: 'The canonical question?',
            answerText: SECRET,
            citations,
            approvedBy: 'U_SME',
          });

          const visible = new Set(visibleIdxs.map((i) => `https://s.example/p${i}`));
          const checker: VisibilityChecker = {
            async canSee(_u, c) {
              return visible.has(c.permalink);
            },
          };

          const hit = await lib2.findVerified('The canonical question?', 'U_REQ', checker);
          const allVisible = citations.every((c) => visible.has(c.permalink));

          if (allVisible) {
            expect(hit.status).toBe('verified');
          } else {
            expect(hit.status).toBe('degraded');
            expect(JSON.stringify(hit)).not.toContain(SECRET);
          }
        },
      ),
      { numRuns: 200 },
    );
  });
});
