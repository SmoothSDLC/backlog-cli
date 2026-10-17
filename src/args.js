import { input } from './errors.js';
import { texts, lists, guid } from './schema.js';
const booleans = ['json', 'ask', 'help', 'version', 'force', 'top', 'higher'];
const values = ['branch', ...texts, ...lists, 'state', 'priority'];
export function parse(argv) {
  const flags = {}, args = [];
  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];
    if (token === '--') { args.push(...argv.slice(i + 1)); break; }
    if (!token.startsWith('--')) { args.push(token); continue; }
    const at = token.indexOf('='); const key = token.slice(2, at < 0 ? undefined : at); const inline = at < 0 ? undefined : token.slice(at + 1);
    input([...booleans, ...values].includes(key), `Unknown option --${key}. Use backlog --help.`);
    input(!(key in flags), `Option --${key} was supplied twice.`);
    if (booleans.includes(key)) { input(inline === undefined, `--${key} does not take a value.`); flags[key] = true; }
    else { const value = inline ?? argv[++i]; input(value !== undefined && !value.startsWith('--'), `--${key} requires a value.`); flags[key] = value; }
  }
  if (flags.help || flags.version) return { command: flags.help ? 'help' : 'version', args: [], flags };
  if (args.length > 1 && (/^\d+$/.test(args[0]) || guid.test(args[0]))) { const selector = args.shift(); const command = args.shift(); args.unshift(command, selector); }
  let command = args.shift() ?? 'next';
  if (command === 'branch' && args[0] === 'import') { args.shift(); command = 'import'; }
  const grammar = { next: [0, 0], init: [0, 2], list: [0, 1], new: [0, 2], set: [2, 3], add: [2, 3], replace: [3, 3], remove: [3, 3], priority: [1, 4], done: [1, 1], move: [2, 2], import: [0, 1], archive: [1, 1], branch: [0, 0], update: [0, 1] };
  input(command in grammar, `Unknown command ${command}. Use backlog --help.`);
  const [min, max] = grammar[command]; input(args.length >= min && args.length <= max, `Invalid arguments for ${command}; use backlog --help.`);
  const allowed = new Set(['json', 'ask']);
  if (['list', 'import'].includes(command)) allowed.add('branch');
  // Branch is also a fallback when Git cannot discover a named branch; context enforces the distinction.
  allowed.add('branch');
  if (command === 'new') for (const key of [...texts.filter(x => x !== 'name'), ...lists, 'state', 'priority']) allowed.add(key);
  if (command === 'set') allowed.add('force');
  if (command === 'add') allowed.add('top');
  if (command === 'import') allowed.add('higher');
  for (const key of Object.keys(flags)) input(allowed.has(key), `--${key} is not supported by ${command}.`);
  return { command, args, flags };
}
