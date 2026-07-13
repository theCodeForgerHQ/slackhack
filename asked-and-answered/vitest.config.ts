import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    include: ['tests/**/*.test.ts'],
    // Hermetic: no network, no real Slack. Anything hitting the network is a bug.
    environment: 'node',
    testTimeout: 15_000,
  },
});
