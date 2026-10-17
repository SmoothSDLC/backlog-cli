import { promises as fs, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { exists, safePath, atomicWrite, locked, dataFiles, readJSON, recover, withStore } from './storage.js';
import { operation, input } from './errors.js';
import { validateStore } from './schema.js';
const packageVersion = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')).version;
export const templateRoot = fileURLToPath(new URL('../templates/', import.meta.url));
export const adapters = [
  { name: 'codex', detect: '.agents', destination: '.agents/skills/backlog', instructions: 'Use this repository-scoped Codex skill from .agents/skills/backlog. CLI execution handles update policy.' },
  { name: 'claude-code', detect: '.claude', destination: '.claude/skills/backlog', instructions: 'Use this repository-scoped Claude Code skill from .claude/skills/backlog. No hooks or home configuration are needed.' },
  { name: 'github-copilot', detect: '.github', destination: '.github/skills/backlog', instructions: 'Use this repository-scoped GitHub Copilot agent skill from .github/skills/backlog. Do not append instructions to unrelated Copilot files.' },
  { name: 'qwen-code', detect: '.qwen', destination: '.qwen/skills/backlog', instructions: 'Use this repository-scoped Qwen Code skill from .qwen/skills/backlog. Do not modify QWEN.md or user-level settings.' },
];
export async function safeTree(root, path) {
  await safePath(root, path);
  if (await exists(path) && (await fs.lstat(path)).isDirectory()) for (const entry of await fs.readdir(path)) await safeTree(root, join(path, entry));
}
export async function installSkills(root) {
  const base = join(root, '.backlog/skills'); await safeTree(root, base);
  const destinations = [];
  for (const adapter of adapters) if (await exists(join(root, adapter.detect))) {
    await safePath(root, join(root, adapter.detect)); operation((await fs.stat(join(root, adapter.detect))).isDirectory(), `${adapter.detect} must be a directory.`);
    await safeTree(root, join(root, adapter.destination)); destinations.push(adapter);
  }
  await fs.mkdir(base, { recursive: true });
  await fs.rm(join(base, 'backlog'), { recursive: true, force: true });
  await fs.cp(join(templateRoot, 'skills/backlog'), join(base, 'backlog'), { recursive: true });
  await fs.mkdir(join(base, 'agent-types'), { recursive: true });
  await atomicWrite(join(base, 'agent-types/manifest.json'), JSON.stringify({ schema_version: 1, agents: adapters.map(x => ({ ...x, adapter: `${x.name}.md`, activation_updates: false })) }, null, 2) + '\n');
  for (const adapter of adapters) await atomicWrite(join(base, `agent-types/${adapter.name}.md`), `# ${adapter.name}\n\n${adapter.instructions}\n\nDetect: ${adapter.detect}/\nDestination: ${adapter.destination}/\n`);
  for (const adapter of destinations) {
    const target = join(root, adapter.destination); await fs.mkdir(dirname(target), { recursive: true });
    await fs.rm(target, { recursive: true, force: true }); await fs.cp(join(templateRoot, 'skills/backlog'), target, { recursive: true });
  }
  return destinations.map(x => x.name);
}
export async function initialize(context, args) {
  let mode = 'new'; const rest = [...args];
  if (['clean', 'backup'].includes(rest[0])) mode = rest.shift();
  input(rest.length <= 1, 'Use init [repo-name], init clean [repo-name], or init backup [repo-name].');
  const explicitName = rest[0]; if (explicitName !== undefined) input(explicitName.trim().length > 0, 'Repository name cannot be empty.');
  const lock = join(context.root, '.backlog-cli.lock'); await safePath(context.root, lock);
  return locked(lock, async () => {
    const dir = join(context.root, '.backlog'); await safeTree(context.root, dir); const present = await exists(dir);
    operation(!(mode === 'new' && present), '.backlog already exists. Use backlog init clean to remove and recreate the entire backlog, or backlog init backup to back up existing files and replace skills.');
    // Preflight every generated destination before destructive initialization.
    for (const adapter of adapters) if (await exists(join(context.root, adapter.detect))) await safeTree(context.root, join(context.root, adapter.destination));
    let backup = null, config;
    if (mode === 'backup' && present) {
      await recover(context.root); const store = {};
      for (const [key, filename] of Object.entries(dataFiles)) store[key] = await readJSON(join(dir, filename));
      validateStore(store); config = store.config;
      const date = new Date(); const stamp = [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0'), String(date.getHours()).padStart(2, '0'), String(date.getMinutes()).padStart(2, '0')].join('');
      const prefix = join(dir, `backup-${stamp}`); backup = prefix; let index = 1;
      while (await exists(backup)) backup = `${prefix}-${index++}`;
      const contents = await fs.readdir(dir); await fs.mkdir(backup);
      for (const entry of contents) if (!entry.startsWith('backup-')) await fs.cp(join(dir, entry), join(backup, entry), { recursive: true });
      for (const adapter of adapters) if (await exists(join(context.root, adapter.destination))) await fs.cp(join(context.root, adapter.destination), join(backup, 'agent-skills', adapter.name), { recursive: true });
    }
    if (mode === 'clean' && present) await fs.rm(dir, { recursive: true });
    await fs.mkdir(dir, { recursive: true });
    if (!config) {
      config = { owner: 'backlog-cli', schema_version: 1, repo_name: explicitName || context.name, default_branch: context.defaultBranch, generated_version: packageVersion };
      for (const [filename, value] of [['config.json', config], ['backlog_manifest.json', []], ['backlog_archive.json', []]]) await atomicWrite(join(dir, filename), JSON.stringify(value, null, 2) + '\n');
      await atomicWrite(join(dir, 'README.md'), '# Repository backlog\n\nUse `backlog --help` for commands. Backlog data and generated skills belong in Git. Commit initialization changes. Init clean removes this entire folder, including backups.\n');
      await atomicWrite(join(dir, 'agent.instructions.md'), '# Backlog agent instructions\n\nRead skills/backlog/SKILL.md before using the backlog. Numeric selectors are current priorities; retain GUIDs for permanent references. Only list/import and an explicit move cross branch boundaries.\n');
    } else if (explicitName) { config.repo_name = explicitName; await atomicWrite(join(dir, 'config.json'), JSON.stringify(config, null, 2) + '\n'); }
    const installed = await installSkills(context.root); process.env.BACKLOG_CLI_REPONAME = config.repo_name;
    return { initialized: true, mode, repository: config.repo_name, root: context.root, backup, installed_agents: installed, message: 'Commit the initialization changes to Git.' };
  });
}

export async function refreshIntegrations(context, version = packageVersion) {
  return withStore(context, async store => {
    if (store.config.generated_version === version) return false;
    await installSkills(context.root); store.config.generated_version = version; return true;
  });
}
