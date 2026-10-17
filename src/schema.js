import { input, operation } from './errors.js';
export const lists = ['tasks', 'outcomes', 'evidence', 'references'];
export const texts = ['name', 'description', 'ac', 'item-state-description', 'work_item_id'];
export const writable = [...texts, ...lists, 'state', 'priority'];
export const states = ['new', 'open', 'done', 'archived'];
export const guid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export const active = item => ['new', 'open'].includes(item.state);
export const queue = (store, branch) => store.manifest.filter(x => x.branch === branch && active(x)).sort((a, b) => a.priority - b.priority);
export const integer = (value, label = 'Position') => { input(/^(0|[1-9]\d*)$/.test(String(value)) && Number.isSafeInteger(Number(value)), `${label} must be a nonnegative integer.`); return Number(value); };
export function jsonValue(value, label) { try { return JSON.parse(value); } catch { input(false, `${label} must be valid JSON.`); } }
export function listValue(property, value) {
  input(Array.isArray(value), `${property} must be a JSON array.`);
  if (property === 'tasks') return value.map(task => {
    input(task && typeof task === 'object' && !Array.isArray(task), 'Each task must be an object with name and goal.');
    input(Object.keys(task).every(k => ['name', 'goal'].includes(k)), 'Tasks support only name and goal.');
    const normalized = { name: task.name ?? '_', goal: task.goal ?? '_' };
    input(Object.values(normalized).every(x => typeof x === 'string'), 'Task name and goal must be text.'); return normalized;
  });
  input(value.every(x => typeof x === 'string'), `${property} entries must be strings.`); return value;
}
export function scalar(property, value) {
  if (property === 'priority') return integer(value, 'Priority');
  if (property === 'state') { input(['new', 'open', 'done'].includes(value), 'State must be new, open, or done; use archive to archive an item.'); return value; }
  input(texts.includes(property) && typeof value === 'string', `Unknown or immutable property: ${property}.`);
  if (['name', 'description', 'ac'].includes(property)) input(value.trim().length > 0, `${property} is required and cannot be empty.`);
  return value;
}
export function validateStore(store) {
  const { config, manifest, archive } = store;
  operation(config && config.owner === 'backlog-cli', 'Unidentified .backlog configuration; use backlog init clean or backlog init backup.');
  operation(config.schema_version === 1, `Unsupported schema version ${config.schema_version}; use a compatible CLI or supported migration.`);
  operation(typeof config.repo_name === 'string' && config.repo_name.length > 0, 'Invalid repository name in config.json.');
  operation(Array.isArray(manifest) && Array.isArray(archive), 'Manifest and archive must be JSON arrays.');
  const seen = new Set();
  const date = x => typeof x === 'string' && /^\d{4}-\d\d-\d\dT/.test(x) && Number.isFinite(Date.parse(x));
  for (const [items, archived] of [[manifest, false], [archive, true]]) {
    for (const item of items) {
      operation(item && typeof item === 'object' && guid.test(item.id), 'Every item requires a GUID id.');
      operation(!seen.has(item.id.toLowerCase()), `Duplicate item GUID: ${item.id}. Resolve the data conflict.`); seen.add(item.id.toLowerCase());
      operation(typeof item.branch === 'string' && item.branch.length > 0 && states.includes(item.state), `Invalid branch/state for ${item.id}.`);
      operation((item.state === 'archived') === archived, `Item ${item.id} is in the wrong storage file.`);
      operation(texts.every(k => typeof item[k] === 'string') && ['name', 'description', 'ac'].every(k => item[k].trim()), `Invalid required text for ${item.id}.`);
      operation(lists.every(k => Array.isArray(item[k])), `Invalid list fields for ${item.id}.`);
      try { for (const property of lists) listValue(property, item[property]); } catch (error) { operation(false, `${item.id}: ${error.message}`); }
      operation(date(item.item_created_at) && date(item.item_updated_at), `Invalid generated date for ${item.id}.`);
      operation(item.item_completed_at === null || date(item.item_completed_at), `Invalid completion date for ${item.id}.`);
      operation(item.state !== 'done' || date(item.item_completed_at), `Done item ${item.id} requires a completion timestamp.`);
      operation(archived ? date(item.item_archived_at) : item.item_archived_at === null, `Invalid archive date for ${item.id}.`);
      operation(active(item) ? Number.isSafeInteger(item.priority) && item.priority >= 0 : item.priority === null, `Invalid priority for ${item.id}.`);
    }
  }
  for (const branch of new Set(manifest.map(x => x.branch))) {
    operation(queue(store, branch).every((x, i) => x.priority === i), `Nonsequential priorities on branch ${branch}; resolve the data conflict.`);
  }
}
