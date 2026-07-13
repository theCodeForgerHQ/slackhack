import { describe, test, expect } from 'vitest';
import { simulateImpact, DEFAULT_BASELINE, formatImpactReport } from '../evals/counterfactual.js';

describe('Counterfactual impact simulator', () => {
  test('saves SME hours for auto-answered questions', () => {
    const report = simulateImpact({ questionCount: 100, autoAnsweredCount: 80, routedToHumanCount: 20 });
    expect(report.smeHoursSaved).toBe(80 * DEFAULT_BASELINE.smeHoursPerQuestion);
    expect(report.smeCostSavedUsd).toBe(report.smeHoursSaved * DEFAULT_BASELINE.smeHourlyCost);
  });

  test('reports zero savings when nothing is auto-answered', () => {
    const report = simulateImpact({ questionCount: 10, autoAnsweredCount: 0, routedToHumanCount: 10 });
    expect(report.smeHoursSaved).toBe(0);
    expect(report.smeCostSavedUsd).toBe(0);
  });

  test('marks report as simulated', () => {
    const report = simulateImpact({ questionCount: 10, autoAnsweredCount: 5, routedToHumanCount: 5 });
    expect(report.note).toContain('SIMULATED');
    expect(formatImpactReport(report)).toContain('SIMULATED');
  });

  test('custom baseline rules are respected', () => {
    const report = simulateImpact(
      { questionCount: 10, autoAnsweredCount: 10, routedToHumanCount: 0 },
      { smeHoursPerQuestion: 1, manualUncitedProbability: 0.5, manualInconsistentProbability: 0.2, smeHourlyCost: 200 },
    );
    expect(report.smeHoursSaved).toBe(10);
    expect(report.smeCostSavedUsd).toBe(2000);
  });
});
