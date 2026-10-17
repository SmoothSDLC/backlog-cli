import { randomUUID } from 'node:crypto';
import { input } from './errors.js';
import { active, queue, lists, texts, writable, scalar, listValue, jsonValue, integer, states } from './schema.js';
export function find(store, selector, context, allowArchived = false) {
  const item = /^\d+$/.test(selector) ? queue(store, context.branch).find(x => x.priority === integer(selector)) : [...store.manifest, ...store.archive].find(x => x.id.toLowerCase() === selector.toLowerCase());
  input(item, `No item matches ${selector} on this branch. Use a current priority or permanent GUID.`);
  input(item.branch === context.branch, `Item belongs to branch ${item.branch}. Work in that branch to modify it.`);
  input(allowArchived || item.state !== 'archived', 'Archived items are read-only.'); return item;
}
function place(store, item, position) {
  const ordered = queue(store, item.branch).filter(x => x.id !== item.id);
  input(position <= ordered.length, `Priority must be between 0 and ${ordered.length}.`);
  ordered.splice(position, 0, item); ordered.forEach((x, i) => x.priority = i);
}
function normalize(store, branch) { queue(store, branch).forEach((x, i) => x.priority = i); }
function csv(value) {
  const entries = []; let part = '', quoted = false, closed = false;
  for (let i = 0; i < value.length; i++) {
    const c = value[i];
    if (c === '"') {
      if (quoted && value[i + 1] === '"') { part += '"'; i++; }
      else if (quoted) { quoted = false; closed = true; }
      else { input(part.length === 0 && !closed, 'Malformed task CSV quoting.'); quoted = true; }
    } else if (c === ',' && !quoted) { entries.push(part || '_'); part = ''; closed = false; }
    else { input(!closed, 'Unexpected characters after a quoted task field.'); part += c; }
  }
  input(!quoted, 'Unterminated task CSV quote.'); entries.push(part || '_'); input(entries.length <= 2, 'Tasks accept name,goal; quote components containing commas.'); return entries;
}
function entries(property, value = '_') {
  if (value.trimStart().startsWith('[')) return listValue(property, jsonValue(value, property));
  if (property === 'tasks') {
    if (value.trimStart().startsWith('{')) return listValue(property, [jsonValue(value, 'Task')]);
    const [name, goal = '_'] = csv(value); return [{ name, goal }];
  }
  if (value.startsWith('"')) { const decoded = jsonValue(value, property); input(typeof decoded === 'string', 'List entry must be text.'); return [decoded]; }
  return [value];
}
export function creation(args, flags) {
  const [name, payload] = args;
  const data = payload === undefined ? {} : jsonValue(payload, 'Creation payload');
  input(data && typeof data === 'object' && !Array.isArray(data), 'Creation payload must be a JSON object.');
  for (const key of Object.keys(data)) input(writable.includes(key) && key !== 'name', `Unknown, duplicate, or generated creation field: ${key}.`);
  for (const key of writable.filter(x => x !== 'name')) if (flags[key] !== undefined) { input(data[key] === undefined, `${key} supplied more than once.`); data[key] = lists.includes(key) ? jsonValue(flags[key], key) : flags[key]; }
  return { ...data, ...(name === undefined ? {} : { name }) };
}
export function execute(parsed, context, store) {
  const { command, args, flags } = parsed;
  if (command === 'next') return queue(store, context.branch)[0] ?? null;
  if (command === 'list' || command === 'branch') {
    if (command === 'branch' || args[0] === 'branch') {
      const counts = new Map();
      for (const item of [...store.manifest, ...store.archive]) {
        const row = counts.get(item.branch) ?? { branch: item.branch, active: 0, done: 0, archived: 0, total: 0 };
        row.total++; row[active(item) ? 'active' : item.state]++; counts.set(item.branch, row);
      }
      return [...counts.values()].sort((a, b) => a.branch.localeCompare(b.branch));
    }
    const state = args[0] === 'archive' ? 'archived' : args[0]; input(state === undefined || states.includes(state), `Unknown state ${state}. Use new, open, done, or archive.`);
    const branch = flags.branch || context.branch;
    const rows = (state === 'archived' ? store.archive : store.manifest).filter(x => x.branch === branch && (state ? x.state === state : active(x)));
    return rows.sort(state === 'done' || state === 'archived' ? (a, b) => (b[state === 'done' ? 'item_completed_at' : 'item_archived_at']).localeCompare(a[state === 'done' ? 'item_completed_at' : 'item_archived_at']) || a.id.localeCompare(b.id) : (a, b) => a.priority - b.priority);
  }
  if (command === 'new') {
    const data = parsed.data ?? creation(args, flags);
    for (const property of ['name', 'description', 'ac']) input(typeof data[property] === 'string' && data[property].trim(), `${property} is required. Supply --${property === 'name' ? 'ask' : property} or use --ask.`);
    const now = new Date().toISOString();
    const item = { id: randomUUID(), priority: null, name: data.name, branch: context.branch, state: 'new', 'item-state-description': '_', description: data.description, ac: data.ac, tasks: [], outcomes: [], evidence: [], references: [], work_item_id: '_', item_created_at: now, item_updated_at: now, item_completed_at: null, item_archived_at: null };
    for (const [key, value] of Object.entries(data)) item[key] = key === 'priority' && value === null && data.state === 'done' ? null : lists.includes(key) ? listValue(key, value) : scalar(key, value);
    if (active(item)) { const position = data.priority === undefined ? queue(store, context.branch).length : integer(data.priority, 'Priority'); place(store, item, position); }
    else { input(data.priority === undefined || data.priority === null, 'Done items have null priority.'); item.priority = null; item.item_completed_at = now; }
    store.manifest.push(item); return item;
  }
  if (command === 'import') {
    input(!(args[0] && flags.branch), 'Supply the import source once, positionally or with --branch.');
    const source = args[0] || flags.branch; input(source, 'Import requires --branch <source> or a source branch argument.'); input(source !== context.branch, 'Cannot import a branch into itself.');
    const moved = store.manifest.filter(x => x.branch === source), current = queue(store, context.branch), incoming = queue(store, source);
    for (const item of moved) item.branch = context.branch;
    const ordered = flags.higher ? [...incoming, ...current] : [...current, ...incoming]; ordered.forEach((x, i) => x.priority = i); return moved;
  }
  if (command === 'archive') {
    const items = args[0] === 'done' ? store.manifest.filter(x => x.branch === context.branch && x.state === 'done') : [find(store, args[0], context, true)];
    for (const item of items) {
      if (item.state === 'archived') continue;
      item.state = 'archived'; item.priority = null; item.item_archived_at = new Date().toISOString();
      store.manifest = store.manifest.filter(x => x.id !== item.id); store.archive.push(item);
    }
    normalize(store, context.branch); return args[0] === 'done' ? items : items[0];
  }
  const item = find(store, args[0], context);
  if (command === 'move') {
    const destination = args[1]; input(destination && destination !== item.branch, 'Move requires a different destination branch.');
    const previous = item.branch; const position = queue(store, destination).length; item.branch = destination;
    if (active(item)) place(store, item, position); normalize(store, previous); return item;
  }
  if (command === 'priority') {
    if (args.length <= 2) { input(active(item), 'Only active items have priority.'); place(store, item, integer(args[1] ?? 0)); return item; }
    input(args.length === 4 && lists.includes(args[1]), 'Use priority <item> <list> <entry-number> <position>.');
    const list = item[args[1]], from = integer(args[2]), to = integer(args[3]); input(from >= 1 && to >= 1 && from <= list.length && to <= list.length, 'List positions start at 1 and must reference existing entries.');
    const [entry] = list.splice(from - 1, 1); list.splice(to - 1, 0, entry); return item;
  }
  if (['add', 'replace', 'remove'].includes(command)) {
    const property = args[1]; input(lists.includes(property), `${command} requires a list property: ${lists.join(', ')}.`);
    if (command === 'remove') { const index = integer(args[2], 'Entry number'); input(index >= 1 && index <= item[property].length, 'Entry number must reference an existing entry, starting at 1.'); item[property].splice(index - 1, 1); }
    else if (command === 'replace') item[property] = listValue(property, jsonValue(args[2], property));
    else { const added = entries(property, args[2]); item[property][flags.top ? 'unshift' : 'push'](...added); }
    return item;
  }
  input(command === 'set' || command === 'done', `Unknown item operation ${command}.`);
  const property = command === 'done' ? 'state' : args[1]; let value = command === 'done' ? 'done' : args[2];
  input(writable.includes(property), `Unknown or immutable property ${property}; branch changes require move/import.`);
  if (lists.includes(property)) {
    if (flags.force) item[property] = listValue(property, jsonValue(value, property));
    else item[property].push(...entries(property, value)); return item;
  }
  input(!flags.force, '--force is supported only for whole-list set replacement.');
  input(value !== undefined || property === 'priority', `set ${property} requires a value or --ask.`);
  value = scalar(property, value ?? '0');
  if (property === 'priority') { input(active(item), 'Only active items have priority.'); place(store, item, value); }
  else if (property === 'state' && item.state !== value) {
    const wasActive = active(item); item.state = value;
    if (value === 'done') { item.priority = null; item.item_completed_at = new Date().toISOString(); normalize(store, item.branch); }
    else { item.item_completed_at = null; if (!wasActive) place(store, item, 0); }
  } else item[property] = value;
  return item;
}
