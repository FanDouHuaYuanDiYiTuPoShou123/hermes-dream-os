/**
 * Hermes Dream OS - CLI Entry Point
 * Usage: node cli.js <module> <workspace> <action> [args...]
 */

import { dayMode, DAY_ACTIONS } from './day-mode.js';
import { nightMode, NIGHT_PHASES } from './night-mode.js';
import { MemoryHub } from './memory-hub.js';

const MODULE = process.argv[2];
const WORKSPACE = process.argv[3];
const ACTION = process.argv[4];
const ARGS = process.argv.slice(5);

if (!MODULE || !WORKSPACE || !ACTION) {
  console.log(`
Hermes Dream OS CLI
===================

Usage: node cli.js <module> <workspace> <action> [args...]

Modules:
  day-mode    - Day Mode operations
  night-mode  - Night Mode operations
  memory-hub  - Memory Hub operations

Examples:
  node cli.js day-mode /path/to/workspace briefing
  node cli.js day-mode /path/to/workspace checkin high 8 "工作顺利"
  node cli.js day-mode /path/to/workspace win "完成项目X"
  node cli.js night-mode /path/to/workspace light
  node cli.js night-mode /path/to/workspace deep
  node cli.js night-mode /path/to/workspace rem
`);
  process.exit(1);
}

async function main() {
  try {
    let result;

    if (MODULE === 'day-mode') {
      result = dayMode(WORKSPACE, ACTION, ...ARGS);
    } else if (MODULE === 'night-mode') {
      result = nightMode(WORKSPACE, ACTION);
    } else if (MODULE === 'memory-hub') {
      const hub = new MemoryHub(WORKSPACE);

      if (ACTION === 'record-mood') {
        const [score, note, triggers] = ARGS;
        result = hub.recordMood(
          parseFloat(score || 5),
          note || '',
          triggers ? triggers.split(',') : []
        );
      } else if (ACTION === 'record-energy') {
        const [level, context, productivity] = ARGS;
        result = hub.recordEnergy(
          level || 'medium',
          context || '',
          productivity ? parseFloat(productivity) : null
        );
      } else if (ACTION === 'record-insight') {
        const [observation, confidence, source] = ARGS;
        result = hub.recordInsight(observation, parseFloat(confidence || 0.5), source || 'manual');
      } else if (ACTION === 'record-win') {
        result = hub.recordWin(ARGS[0] || '');
      } else if (ACTION === 'record-struggle') {
        const [description, resolved] = ARGS;
        result = hub.recordStruggle(description || '', resolved === 'true');
      } else if (ACTION === 'update-habit') {
        const [name, completed, note] = ARGS;
        result = hub.updateHabit(name || '', completed === 'true', note || '');
      } else if (ACTION === 'update-goal') {
        const [name, progress, deadline] = ARGS;
        result = hub.updateGoal(name || '', parseFloat(progress) || null, deadline || null);
      } else if (ACTION === 'read-moods') {
        result = hub.getRecentMoods(parseInt(ARGS[0] || 7));
      } else if (ACTION === 'read-energy') {
        result = hub.getRecentEnergy(parseInt(ARGS[0] || 7));
      } else if (ACTION === 'read-insights') {
        result = hub.getRecentInsights(parseInt(ARGS[0] || 7), parseFloat(ARGS[1] || 0));
      } else {
        console.log('Unknown memory-hub action:', ACTION);
        process.exit(1);
      }
    } else {
      console.log('Unknown module:', MODULE);
      process.exit(1);
    }

    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    console.error('Error:', e.message);
    process.exit(1);
  }
}

main();
