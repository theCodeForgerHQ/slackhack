/**
 * Calibrate the ConformalMatcher on the eval dataset and approved-answer
 * paraphrases, then print the learned q_hat threshold.
 *
 * Run with:
 *   npx tsx scripts/calibrateMatching.ts
 */

import { ConformalMatcher, type CalibrationPair } from '../src/core/conformal.js';

const PAIRS: CalibrationPair[] = [
  // Same questions, exact or near-exact.
  { query: 'Do you encrypt customer data at rest?', candidate: 'Do you encrypt customer data at rest?', same: true },
  { query: 'Is customer data encrypted at rest?', candidate: 'Do you encrypt customer data at rest?', same: true },
  { query: 'Do you use encryption at rest?', candidate: 'Do you encrypt customer data at rest?', same: true },
  { query: 'Is multi-factor authentication enforced for all employees?', candidate: 'Is MFA enforced for all employees?', same: true },
  { query: 'Are backups tested at least quarterly?', candidate: 'Do you run quarterly backup restore drills?', same: true },
  { query: 'Do you perform annual penetration testing?', candidate: 'Is penetration testing performed annually?', same: true },
  { query: 'Do you have a SOC 2 Type II report?', candidate: 'Is there a SOC 2 Type II report?', same: true },
  { query: 'Where is production data hosted geographically?', candidate: 'Which region hosts production data?', same: true },
  { query: 'Are access certifications reviewed quarterly?', candidate: 'Is access reviewed quarterly?', same: true },
  { query: 'Are administrative actions logged to a SIEM?', candidate: 'Are admin actions logged?', same: true },
  { query: 'Is the incident response plan tested annually?', candidate: 'Do you test incident response annually?', same: true },
  { query: 'Do employees complete security awareness training?', candidate: 'Is security training required annually?', same: true },

  // Different questions.
  { query: 'Do you encrypt customer data at rest?', candidate: 'Do you carry cyber liability insurance?', same: false },
  { query: 'Is MFA enforced?', candidate: 'Do you use FIPS 140-2 modules?', same: false },
  { query: 'Are backups tested quarterly?', candidate: 'Do you have a bug bounty program?', same: false },
  { query: 'Do you have a SOC 2 report?', candidate: 'What is your data retention policy?', same: false },
  { query: 'Where is production data hosted?', candidate: 'Do you encrypt data in transit?', same: false },
  { query: 'Are access certifications reviewed quarterly?', candidate: 'Do you use homomorphic encryption?', same: false },
  { query: 'Is there a business continuity plan?', candidate: 'Do you have a red-team program?', same: false },
  { query: 'Are mobile devices enrolled in MDM?', candidate: 'Do you have an AI ethics board?', same: false },
];

const alpha = Number(process.env.AA_CONFORMAL_ALPHA ?? 0.1);
const matcher = new ConformalMatcher(alpha);
matcher.calibrate(PAIRS);

console.log(`Calibration pairs: ${PAIRS.length}`);
console.log(`Alpha (miscoverage target): ${alpha}`);
console.log(`Learned q_hat: ${matcher.qHat ?? 'not calibrated'}`);

// Print empirical coverage on the calibration set.
let correct = 0;
let total = 0;
for (const p of PAIRS.filter((p) => p.same)) {
  const score = matcher.score(p.query, p.candidate);
  const passed = matcher.qHat !== undefined && score <= matcher.qHat;
  correct += passed ? 1 : 0;
  total++;
  console.log(`  ${p.query.slice(0, 40).padEnd(42)} score=${score.toFixed(3)} ${passed ? 'PASS' : 'FAIL'}`);
}
console.log(`Empirical same-question coverage: ${correct}/${total}`);
