import { simulateImpact, formatImpactReport } from '../evals/counterfactual.js';

const report = simulateImpact({
  questionCount: 100,
  autoAnsweredCount: 75,
  routedToHumanCount: 25,
});

console.log(formatImpactReport(report));
