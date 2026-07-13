/**
 * Generates a realistic ~40-row security questionnaire as xlsx for the demo
 * and judge sandbox. `npx tsx scripts/make-sample-xlsx.ts`.
 */
import ExcelJS from 'exceljs';
import { writeFileSync } from 'node:fs';

const QUESTIONS: Array<[string, string]> = [
  ['Data Protection', 'Do you encrypt customer data at rest?'],
  ['Data Protection', 'Do you encrypt data in transit?'],
  ['Data Protection', 'Where is production customer data hosted geographically?'],
  ['Data Protection', 'Do you have a documented data retention policy?'],
  ['Data Protection', 'Can customers request deletion of their data?'],
  ['Access Control', 'Is multi-factor authentication enforced for all employees?'],
  ['Access Control', 'Do you enforce least-privilege access?'],
  ['Access Control', 'Is access reviewed at least quarterly?'],
  ['Access Control', 'Do you support SSO via SAML or OIDC?'],
  ['Access Control', 'How are offboarded employees deprovisioned?'],
  ['Compliance', 'Do you have a SOC 2 Type II report?'],
  ['Compliance', 'Are you ISO 27001 certified?'],
  ['Compliance', 'Do you comply with GDPR?'],
  ['Compliance', 'Do you have a documented information security policy?'],
  ['Compliance', 'When was your last policy review?'],
  ['Resilience', 'Are backups tested at least quarterly?'],
  ['Resilience', 'What is your RTO and RPO?'],
  ['Resilience', 'Do you have a documented business continuity plan?'],
  ['Resilience', 'Do you run disaster recovery drills?'],
  ['Security Testing', 'Do you perform annual penetration testing?'],
  ['Security Testing', 'Do you run a vulnerability management program?'],
  ['Security Testing', 'Do you operate a bug bounty program?'],
  ['Security Testing', 'How quickly do you patch critical vulnerabilities?'],
  ['Incident Response', 'Do you have an incident response plan?'],
  ['Incident Response', 'What is your breach notification SLA in hours?'],
  ['Incident Response', 'Have you had a breach in the last 24 months?'],
  ['Vendor Management', 'Do you assess the security of your subprocessors?'],
  ['Vendor Management', 'Do you maintain a list of subprocessors?'],
  ['Application Security', 'Do you follow a secure SDLC?'],
  ['Application Security', 'Do you perform code review on all changes?'],
  ['Application Security', 'Do you use static analysis (SAST)?'],
  ['Application Security', 'Do you scan dependencies for vulnerabilities?'],
  ['Insurance', 'Do you carry cyber liability insurance?'],
  ['Insurance', 'What is your cyber insurance coverage limit?'],
  ['Cryptography', 'Do you use FIPS 140-2 validated cryptographic modules?'],
  ['Cryptography', 'Do you have a quantum-safe cryptography roadmap?'],
  ['Privacy', 'Do you maintain a Data Protection Officer?'],
  ['Privacy', 'Do you conduct Data Protection Impact Assessments?'],
  ['Personnel', 'Do employees complete security awareness training?'],
  ['Personnel', 'Do you perform background checks on employees?'],
];

const wb = new ExcelJS.Workbook();
const ws = wb.addWorksheet('Security Questionnaire');
ws.addRow(['#', 'Category', 'Question', 'Vendor Response']);
ws.getRow(1).font = { bold: true };
ws.columns = [{ width: 5 }, { width: 22 }, { width: 70 }, { width: 40 }];
QUESTIONS.forEach(([cat, q], i) => ws.addRow([i + 1, cat, q, '']));

const out = 'sample-questionnaire.xlsx';
const buf = await wb.xlsx.writeBuffer();
writeFileSync(out, Buffer.from(buf));
console.log(`Wrote ${out} — ${QUESTIONS.length} questions`);
