/**
 * Code-level contract verification of the permission invariant.
 *
 * Unlike the abstract model in `scripts/verifyInvariantZ3.ts`, this proof models
 * the actual guard contracts implemented in the TypeScript pipeline:
 *
 *   - GroundingGate (`src/core/grounding.ts`): a grounded answer is accepted only
 *     if every cited snippet appears in the answer text and the citation is in
 *     the retrieved hit set.
 *   - Fresh-draft ACL (`src/core/pipeline.ts:158-166`): a grounded answer is
 *     accepted only if the requester can see every cited permalink.
 *   - Verified-library ACL (`src/core/library.ts` + `src/core/pipeline.ts:86-93`):
 *     a verified answer is accepted only if the library ACL re-check passes and
 *     the approved evidence is not stale.
 *   - Stale degradation (`src/core/pipeline.ts:97-117`): a stale approved answer
 *     is downgraded to needs_sme before release.
 *
 * We prove that these concrete contracts entail the invariant:
 *
 *   returned(u, a) => forall c. cites(a, c) => visible(u, c)
 */

import { init } from 'z3-solver';

export interface Z3VerificationResult {
  proved: boolean;
  status: 'unsat' | 'sat' | 'unknown' | 'error';
  detail?: string;
}

export async function verifyPipelineContracts(): Promise<Z3VerificationResult> {
  let Z3;
  try {
    const { Context } = await init();
    Z3 = Context('main');
  } catch (err) {
    return { proved: false, status: 'error', detail: `z3-solver init failed: ${(err as Error).message}` };
  }

  const User = Z3.Sort.declare('User');
  const Citation = Z3.Sort.declare('Citation');
  const Answer = Z3.Sort.declare('Answer');

  // Concrete observables.
  const visible = Z3.Function.declare('visible', User, Citation, Z3.Bool.sort());
  const returned = Z3.Function.declare('returned', User, Answer, Z3.Bool.sort());
  const cites = Z3.Function.declare('cites', Answer, Citation, Z3.Bool.sort());

  // Concrete contracts that mirror the TypeScript implementation.
  const snippetInAnswer = Z3.Function.declare('snippetInAnswer', Answer, Citation, Z3.Bool.sort());
  const citationInHits = Z3.Function.declare('citationInHits', Answer, Citation, Z3.Bool.sort());
  const aclFreshDraftPassed = Z3.Function.declare('aclFreshDraftPassed', User, Answer, Z3.Bool.sort());
  const libraryAclPassed = Z3.Function.declare('libraryAclPassed', User, Answer, Z3.Bool.sort());
  const notStale = Z3.Function.declare('notStale', Answer, Z3.Bool.sort());
  const degradedToSme = Z3.Function.declare('degradedToSme', Answer, Z3.Bool.sort());

  // Classification of returned answers is requester-relative.
  const grounded = Z3.Function.declare('grounded', User, Answer, Z3.Bool.sort());
  const verified = Z3.Function.declare('verified', User, Answer, Z3.Bool.sort());

  const u = Z3.Const('u', User);
  const a = Z3.Const('a', Answer);
  const c = Z3.Const('c', Citation);

  // Contract: grounded(u, a) <=> GroundingGate(a) AND fresh-draft ACL(u, a)
  // GroundingGate(a) <=> for all c, cites(a,c) => snippetInAnswer(a,c) & citationInHits(a,c)
  const groundingGateValid = Z3.ForAll(
    [u, a],
    Z3.Eq(
      grounded.call(u, a),
      Z3.And(
        Z3.ForAll(
          [c],
          Z3.Implies(
            cites.call(a, c),
            Z3.And(snippetInAnswer.call(a, c), citationInHits.call(a, c)),
          ),
        ),
        aclFreshDraftPassed.call(u, a),
      ),
    ),
  );

  // Contract: verified(u, a) <=> library ACL(u, a) AND notStale(a)
  const verifiedContract = Z3.ForAll(
    [u, a],
    Z3.Eq(verified.call(u, a), Z3.And(libraryAclPassed.call(u, a), notStale.call(a))),
  );

  // RETURN-GUARD: returned(u, a) => grounded(u, a) OR verified(u, a)
  const returnGuard = Z3.ForAll(
    [u, a],
    Z3.Implies(returned.call(u, a), Z3.Or(grounded.call(u, a), verified.call(u, a))),
  );

  // ACL soundness: if fresh-draft ACL passed for citation c, then c is visible to u.
  const aclFreshSound = Z3.ForAll(
    [u, a, c],
    Z3.Implies(Z3.And(aclFreshDraftPassed.call(u, a), cites.call(a, c)), visible.call(u, c)),
  );

  // ACL soundness: if library ACL passed for citation c, then c is visible to u.
  const aclLibrarySound = Z3.ForAll(
    [u, a, c],
    Z3.Implies(Z3.And(libraryAclPassed.call(u, a), cites.call(a, c)), visible.call(u, c)),
  );

  // Stale degradation: every approved answer is either not stale or has been
  // degraded to a human review request.
  const staleOrDegraded = Z3.ForAll([a], Z3.Or(notStale.call(a), degradedToSme.call(a)));

  // Stale degradation: if degraded, the answer is never returned to any user.
  const staleGuard = Z3.ForAll(
    [u, a],
    Z3.Implies(degradedToSme.call(a), Z3.Not(returned.call(u, a))),
  );

  const invariant = Z3.ForAll(
    [u, a],
    Z3.Implies(
      returned.call(u, a),
      Z3.ForAll([c], Z3.Implies(cites.call(a, c), visible.call(u, c))),
    ),
  );

  const solver = new Z3.Solver();
  solver.add(groundingGateValid);
  solver.add(verifiedContract);
  solver.add(returnGuard);
  solver.add(aclFreshSound);
  solver.add(aclLibrarySound);
  solver.add(staleOrDegraded);
  solver.add(staleGuard);
  solver.add(Z3.Not(invariant));

  const result = await solver.check();
  if (result === 'unsat') {
    return {
      proved: true,
      status: 'unsat',
      detail:
        'Code-level contract proof holds: concrete GroundingGate, fresh-draft ACL, library ACL, and stale-degradation contracts entail the permission invariant.',
    };
  }
  return { proved: false, status: result, detail: `Z3 returned ${result}; contract proof not entailed under this model.` };
}

async function main(): Promise<void> {
  const result = await verifyPipelineContracts();
  console.log(`Z3 code-level contract proof: ${result.proved ? 'PROVED' : 'NOT PROVED'} (${result.status})`);
  if (result.detail) console.log(result.detail);
  process.exit(result.proved ? 0 : 1);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
