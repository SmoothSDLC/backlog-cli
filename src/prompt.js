import { createInterface } from 'node:readline/promises';
import { input, BacklogError } from './errors.js';
import { creation } from './commands.js';
import { texts, lists } from './schema.js';
export async function promptMissing(parsed) {
  if (!parsed.flags.ask) return;
  const needsCreation = parsed.command === 'new';
  const needsValue = parsed.command === 'set' && parsed.args.length === 2;
  if (!needsCreation && !needsValue) return;
  input(process.stdin.isTTY && process.stderr.isTTY, '--ask requires an interactive terminal. Supply missing fields as arguments or JSON instead.');
  const rl = createInterface({ input: process.stdin, output: process.stderr });
  let cancelled = false; rl.on('SIGINT', () => { cancelled = true; rl.close(); });
  try {
    const ask = async (label, fallback = '_') => {
      let answer; try { answer = await rl.question(`${label} [${fallback}]: `); } catch { throw new BacklogError('CANCELLED', 'Input cancelled; nothing changed.'); }
      input(!cancelled, 'Input cancelled; nothing changed.'); return answer === '' ? fallback : answer;
    };
    if (needsValue) { const property = parsed.args[1]; parsed.args.push(await ask(property, lists.includes(property) ? '[]' : property === 'priority' ? '0' : '_')); return; }
    const data = creation(parsed.args, parsed.flags);
    for (const property of texts) if (data[property] === undefined) data[property] = await ask(property);
    for (const property of lists) if (data[property] === undefined) {
      data[property] = [];
      for (;;) {
        const action = await ask(`${property}: add entry or finish (a/f)`, 'f');
        input(['a', 'f'].includes(action), 'Choose a to add an entry or f to finish.'); if (action === 'f') break;
        if (property === 'tasks') data[property].push({ name: await ask('Task name'), goal: await ask('Task goal') });
        else data[property].push(await ask(`${property} text`));
      }
    }
    if (data.state === undefined) data.state = await ask('state (new/open/done)', 'new');
    if (data.priority === undefined && data.state !== 'done') { const priority = await ask('priority (bottom or nonnegative position)', 'bottom'); if (priority !== 'bottom') data.priority = priority; }
    parsed.data = data;
  } finally { rl.close(); }
}
