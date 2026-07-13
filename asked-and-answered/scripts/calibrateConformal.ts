/**
 * Calibrate the ConformalMatcher and write a committed artifact.
 *
 * Run: npx tsx scripts/calibrateConformal.ts
 *
 * Mirrors CornerCheck's calibration script: loads labeled pairs, splits into
 * calibration/holdout, computes q_hat, validates it, and writes
 * src/core/calibration.json. The artifact is checked into the repo so the
 * matcher ships with a reproducible statistical guarantee.
 */

import { writeFileSync } from 'node:fs';
import { ConformalMatcher, type CalibrationPair } from '../src/core/conformal.js';
import { DEFAULT_CALIBRATION_PAIRS } from '../src/core/calibrationData.js';

function seededShuffle<T>(arr: T[], seed = 42): T[] {
  const rng = mulberry32(seed);
  const copy = [...arr];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [copy[i], copy[j]] = [copy[j]!, copy[i]!];
  }
  return copy;
}

function mulberry32(seed: number): () => number {
  return () => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function main(): void {
  const pairs = seededShuffle(DEFAULT_CALIBRATION_PAIRS);
  const split = Math.floor(pairs.length * 0.8);
  const calibrationPairs = pairs.slice(0, split);
  const holdoutPairs = pairs.slice(split);

  const matcher = new ConformalMatcher(0.1);
  matcher.calibrate(calibrationPairs);

  const qHat = matcher.qHat;
  if (qHat === undefined) {
    throw new Error('Calibration failed: q_hat is undefined');
  }
  if (qHat < 0 || qHat > 1) {
    throw new Error(`Calibration failed: q_hat ${qHat} is outside [0, 1]`);
  }

  // Coverage on holdout: fraction of same pairs whose nonconformity <= qHat.
  const sameHoldout = holdoutPairs.filter((p) => p.same);
  const covered = sameHoldout.filter((p) => matcher.score(p.query, p.candidate) <= qHat).length;
  const holdoutCoverage = sameHoldout.length === 0 ? 1 : covered / sameHoldout.length;

  // False positives on holdout: fraction of different pairs whose score <= qHat.
  const diffHoldout = holdoutPairs.filter((p) => !p.same);
  const falsePos = diffHoldout.filter((p) => matcher.score(p.query, p.candidate) <= qHat).length;
  const falsePositiveRate = diffHoldout.length === 0 ? 0 : falsePos / diffHoldout.length;

  const artifact = {
    qHat,
    alpha: 0.1,
    nCalibration: calibrationPairs.length,
    nHoldout: holdoutPairs.length,
    holdoutCoverage,
    falsePositiveRate,
    calibratedAt: new Date().toISOString(),
    note: 'Split-conformal quantile for token-Jaccard nonconformity. Matcher falls back to legacy threshold if this artifact is invalid.',
  };

  writeFileSync('src/core/calibration.json', JSON.stringify(artifact, null, 2) + '\n');
  console.log('Wrote src/core/calibration.json');
  console.log(JSON.stringify(artifact, null, 2));
}

main();
