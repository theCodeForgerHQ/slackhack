/**
 * Default calibration pairs for the ConformalMatcher.
 *
 * These pairs are intentionally small and domain-specific to the security
 * questionnaire workflow. They cover exact matches, paraphrases, and clearly
 * different questions. The matcher is calibrated at startup from these pairs
 * and falls back to a hand-tuned threshold if calibration is unavailable.
 */

import type { CalibrationPair } from './conformal.js';

export const DEFAULT_CALIBRATION_PAIRS: CalibrationPair[] = [
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
