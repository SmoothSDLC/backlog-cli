import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fixture, bin } from './helpers.js';
const python = process.platform === 'win32' ? 'python' : 'python3';
test('all four detected agent integrations install a working snapshot helper', t => {
  const f = fixture(t);
  for (const name of ['.agents', '.claude', '.github', '.qwen']) mkdirSync(join(f.root, name));
  assert.equal(f.cli('init').installed_agents.length, 4); f.create('Task'); f.cli('add', '0', 'tasks', 'Implement,Tests pass');
  for (const name of ['.agents', '.claude', '.github', '.qwen']) {
    const script = join(f.root, name, 'skills/backlog/scripts/snapshot.py');
    const p = spawnSync(python, [script, '--cli', bin], { cwd: f.root, env: f.env, encoding: 'utf8' });
    assert.equal(p.status, 0, p.stderr); const result = JSON.parse(p.stdout);
    assert.equal(result.data.items[0].name, 'Task'); assert.equal(result.data.summary.tasks, 1);
  }
  const manifest = f.json('skills/agent-types/manifest.json'); assert.equal(manifest.agents.length, 4);
});
test('skill snapshot supports done/archive and reports errors without mutating data', t => {
  const f = fixture(t); f.cli('init'); const item = f.create('Done'); f.cli('done', item.id);
  const script = f.file('skills/backlog/scripts/snapshot.py');
  const result = spawnSync(python, [script, '--cli', bin, '--state', 'done'], { cwd: f.root, env: f.env, encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr); assert.equal(JSON.parse(result.stdout).data.items[0].id, item.id);
  const text = readFileSync(f.file('backlog_manifest.json'), 'utf8');
  const error = spawnSync(python, [script, '--cli', bin, '--branch', 'missing'], { cwd: f.root, env: f.env, encoding: 'utf8' });
  assert.equal(error.status, 0); assert.equal(JSON.parse(error.stdout).data.summary.items, 0);
  assert.equal(readFileSync(f.file('backlog_manifest.json'), 'utf8'), text);
});
test('refresh replaces backlog skill edits and leaves unrelated vendor skills alone', t => {
  const f = fixture(t); mkdirSync(join(f.root, '.qwen/skills/other'), { recursive: true });
  writeFileSync(join(f.root, '.qwen/skills/other/SKILL.md'), 'unrelated'); f.cli('init');
  writeFileSync(join(f.root, '.qwen/skills/backlog/SKILL.md'), 'user edit'); f.cli('init', 'backup');
  assert.match(readFileSync(join(f.root, '.qwen/skills/backlog/SKILL.md'), 'utf8'), /name: backlog/);
  assert.equal(readFileSync(join(f.root, '.qwen/skills/other/SKILL.md'), 'utf8'), 'unrelated');
});
test('product skill self-validator checks the complete installed bundle', t => {
  const script = resolve('templates/skills/backlog/scripts/validate-skill.py');
  const result = spawnSync(python, [script], { encoding: 'utf8' }); assert.equal(result.status, 0, result.stderr || result.stdout);
});
test('using a new CLI version refreshes stale generated integrations', async t => {
  const { refreshIntegrations } = await import('../../src/integrations.js'); const f = fixture(t); f.cli('init');
  const config = f.json('config.json'); config.generated_version = '0.9.0'; writeFileSync(f.file('config.json'), JSON.stringify(config));
  writeFileSync(f.file('skills/backlog/SKILL.md'), 'old generated skill');
  await refreshIntegrations({ root: f.root }, '1.0.0');
  assert.match(readFileSync(f.file('skills/backlog/SKILL.md'), 'utf8'), /name: backlog/);
  assert.equal(f.json('config.json').generated_version, '1.0.0');
});
