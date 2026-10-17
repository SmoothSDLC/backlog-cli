import test from 'node:test';
import assert from 'node:assert/strict';
import { writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { fixture } from './helpers.js';
import { locked } from '../../src/storage.js';
test('stale owner detection never removes a lock acquired by a newer process', async t => {
  const f = fixture(t); const path = join(f.dir, 'race.lock'); const dead = 2147483647;
  writeFileSync(path, JSON.stringify({ pid: dead })); const original = process.kill; let released = false;
  process.kill = (pid, signal) => {
    if (pid === dead) {
      writeFileSync(path, JSON.stringify({ pid: process.pid }));
      setTimeout(() => { released = true; rmSync(path, { force: true }); }, 80);
      throw Object.assign(new Error('Stale owner exited'), { code: 'ESRCH' });
    }
    return original(pid, signal);
  };
  try { await locked(path, () => assert.equal(released, true, 'The newer owner must finish before another callback enters')); }
  finally { process.kill = original; }
});
test('a genuinely abandoned lock fails with recovery instructions and is never silently deleted', async t => {
  const f = fixture(t); const path = join(f.dir, 'abandoned.lock'); writeFileSync(path, JSON.stringify({ pid: 2147483647 }));
  await assert.rejects(locked(path, () => assert.fail('must not enter while a lock exists')), /remove.*then rerun/i);
});
