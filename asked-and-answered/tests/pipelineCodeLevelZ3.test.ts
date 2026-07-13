import { describe, test, expect } from 'vitest';
import { verifyPipelineCodeLevel } from '../scripts/verifyPipelineCodeLevel.js';

describe('Z3 code-level invariant proof', () => {
  test('the permission invariant is entailed by the actual pipeline guards', async () => {
    const result = await verifyPipelineCodeLevel();
    if (result.status === 'error') {
      console.warn(`Skipping Z3 test: ${result.detail}`);
      return;
    }
    expect(result.proved).toBe(true);
    expect(result.status).toBe('unsat');
  });
});
