/**
 * Code-level formal verification of the permission invariant.
 *
 * Unlike scripts/verifyInvariantZ3.ts, this model names the actual pipeline
 * components (GroundingGate, DraftingPipeline ACL check, AnswerLibrary ACL
 * revalidation, EvidenceGraph stale degradation) and proves that their
 * composition entails the invariant.
 */

import { init } from 'z3-solver';

export interface Z3VerificationResult {
  proved: boolean;
  status: 'unsat' | 'sat' | 'unknown' | 'error';
  detail?: string;
}

export async function verifyPipelineCodeLevel(): Promise<Z3VerificationResult> {
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

  const visible = Z3.Function.declare('visible', User, Citation, Z3.Bool.sort());
  const returned = Z3.Function.declare('returned', User, Answer, Z3.Bool.sort());
  const cites = Z3.Function.declare('cites', Answer, Citation, Z3.Bool.sort());
  const grounded = Z3.Function.declare('grounded', Answer, Z3.Bool.sort());
  const verified = Z3.Function.declare('verified', Answer, Z3.Bool.sort());
  const groundingGateValid = Z3.Function.declare('groundingGateValid', Answer, Z3.Bool.sort());
  const aclFreshDraftPassed = Z3.Function.declare('aclFreshDraftPassed', User, Answer, Z3.Bool.sort());
  const libraryAclPassed = Z3.Function.declare('libraryAclPassed', User, Answer, Z3.Bool.sort());
  const stale = Z3.Function.declare('stale', Answer, Z3.Bool.sort());
  const degradedToSme = Z3.Function.declare('degradedToSme', Answer, Z3.Bool.sort());

  const u = Z3.Const('u', User);
  const a = Z3.Const('a', Answer);
  const c = Z3.Const('c', Citation);

  const a1 = Z3.ForAll(
    [u, a],
    Z3.Implies(returned.call(u, a), Z3.Or(grounded.call(a), verified.call(a))),
  );

  const a2 = Z3.ForAll(
    [u, a],
    Z3.Implies(
      grounded.call(a),
      Z3.And(groundingGateValid.call(a), aclFreshDraftPassed.call(u, a)),
    ),
  );

  const a3 = Z3.ForAll(
    [u, a],
    Z3.Implies(
      verified.call(a),
      Z3.And(libraryAclPassed.call(u, a), Z3.Not(stale.call(a))),
    ),
  );

  const a5 = Z3.ForAll(
    [u, a, c],
    Z3.Implies(
      Z3.And(aclFreshDraftPassed.call(u, a), cites.call(a, c)),
      visible.call(u, c),
    ),
  );

  const a6 = Z3.ForAll(
    [u, a, c],
    Z3.Implies(
      Z3.And(libraryAclPassed.call(u, a), cites.call(a, c)),
      visible.call(u, c),
    ),
  );

  const a7 = Z3.ForAll(
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
  solver.add(a1);
  solver.add(a2);
  solver.add(a3);
  solver.add(a5);
  solver.add(a6);
  solver.add(a7);
  solver.add(Z3.Not(invariant));

  const result = await solver.check();
  if (result === 'unsat') {
    return {
      proved: true,
      status: 'unsat',
      detail:
        'Code-level invariant holds: returned answers are grounded (GroundingGate + ACL) or verified (library ACL + not stale), and both ACL checks imply visibility.',
    };
  }
  return { proved: false, status: result, detail: `Z3 returned ${result}; code-level invariant not proved under this model.` };
}

async function main(): Promise<void> {
  const result = await verifyPipelineCodeLevel();
  console.log(`Z3 code-level invariant proof: ${result.proved ? 'PROVED' : 'NOT PROVED'} (${result.status})`);
  if (result.detail) console.log(result.detail);
  process.exit(result.proved ? 0 : 1);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
