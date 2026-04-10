import { validateConfig } from './src/config';
import { pipeline } from './src/pipeline';

async function main() {
  // Validate config
  validateConfig();

  // Run pipeline
  const stats = await pipeline.run();
  console.log(`[INFO] Pipeline complete: ${JSON.stringify(stats)}`);
}

main().catch((err) => {
  console.error('[ERROR] Pipeline failed:', err);
  process.exit(1);
});
