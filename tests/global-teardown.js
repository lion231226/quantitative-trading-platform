async function globalTeardown(config) {
  console.log('🧹 Starting global teardown for E2E tests...');

  // Clean up any test data if needed
  // This is where you could clean up test databases, reset states, etc.

  console.log('✅ Global teardown completed');
}

module.exports = globalTeardown;