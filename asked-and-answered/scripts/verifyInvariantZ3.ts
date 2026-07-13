/**
 * Formal verification of the permission invariant using Z3.
 *
 * Models the pipeline as two safety properties:
 *   1. RETURN-GUARD: returned(u, a) => every citation of a is checked for u.
 *   2. CHECKER-SOUND: checked(u, c) => visible(u, c).
 *
 * Then asks Z3 whether the invariant can be violated:
 *   returned(u, a) && cites(a, c) && !visible(u, c)
 *
 * If Z3 returns unsat, the invariant is formally entailed.
 */

import { init } from 'z3-solver';

export interface Z3VerificationResult {
  proved: boolean;
  status: 'unsat' | 'sat' | 'unknown' | 'error';
  detail?: string;
}

export async function verifyInvariantWithZ3(): Promise<Z3VerificationResult> {
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
  const checked = Z3.Function.declare('checked', User, Citation, Z3.Bool.sort());

  const u = Z3.Const('u', User);
  const a = Z3.Const('a', Answer);
  const c = Z3.Const('c', Citation);

  const guard = Z3.ForAll(
    [u, a],
    Z3.Implies(returned.call(u, a), Z3.ForAll([c], Z3.Implies(cites.call(a, c), checked.call(u, c)))),
  );

  const checkerSound = Z3.ForAll([u, c], Z3.Implies(checked.call(u, c), visible.call(u, c)));

  const invariant = Z3.ForAll(
    [u, a],
    Z3.Implies(returned.call(u, a), Z3.ForAll([c], Z3.Implies(cites.call(a, c), visible.call(u, c)))),
  );

  const solver = new Z3.Solver();
  solver.add(guard);
  solver.add(checkerSound);
  solver.add(Z3.Not(invariant));

  const result = await solver.check();
  if (result === 'unsat') {
    return { proved: true, status: 'unsat', detail: 'Invariant is entailed by RETURN-GUARD + CHECKER-SOUND.' };
  }
  return { proved: false, status: result, detail: `Z3 returned ${result}; invariant not proved under this model.` };
}

async function main(): Promise<void> {
  const result = await verifyInvariantWithZ3();
  console.log(`Z3 invariant proof: ${result.proved ? 'PROVED' : 'NOT PROVED'} (${result.status})`);
  if (result.detail) console.log(result.detail);
  process.exit(result.proved ? 0 : 1);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
