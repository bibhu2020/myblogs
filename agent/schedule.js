import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

dotenv.config({ path: resolve(dirname(fileURLToPath(import.meta.url)), '../.env') });

import cron from 'node-cron';
import { runAgent } from './index.js';

const schedule = process.env.CRON_SCHEDULE;
if (!schedule) {
  console.error('Error: CRON_SCHEDULE environment variable is required');
  process.exit(1);
}

if (!cron.validate(schedule)) {
  console.error(`Error: Invalid cron expression: "${schedule}"`);
  console.error('Examples: "0 8 * * 1" (Monday 8am), "0 8 * * 1,4" (Mon+Thu 8am)');
  process.exit(1);
}

console.log(`⏰ Meridian AI Agent scheduler started`);
console.log(`   Schedule: ${schedule} (UTC)`);
console.log(`   Press Ctrl+C to stop\n`);

let running = false;

cron.schedule(
  schedule,
  async () => {
    if (running) {
      console.log(`[${new Date().toISOString()}] Skipping: previous run still in progress`);
      return;
    }
    running = true;
    console.log(`\n[${new Date().toISOString()}] Scheduled run triggered`);
    try {
      await runAgent();
    } catch (err) {
      console.error(`Scheduled run failed: ${err.message}`);
    } finally {
      running = false;
    }
  },
  { scheduled: true, timezone: 'UTC' },
);
