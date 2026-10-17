import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';
import { planRelease, tagRelease, publishedIntegrity } from '../scripts/release.mjs';
const commit = 'a'.repeat(40), previous = 'b'.repeat(40), artifactIntegrity = 'sha512-current';
test('new versions publish, while documentation-only pushes skip an already released version', () => {
  assert.deepEqual(planRelease({ version: '1.0.2', commit, artifactIntegrity }), { release: true, publish: true, tag: 'v1.0.2' });
  assert.deepEqual(planRelease({ version: '1.0.2', commit, artifactIntegrity, tagCommit: previous, publishedIntegrity: 'sha512-previous' }), { release: false, publish: false, tag: 'v1.0.2' });
});
test('rerunning a published commit verifies it again without overwriting its npm version', () => {
  for (const tagCommit of [undefined, commit]) {
    assert.deepEqual(planRelease({ version: '1.0.2', commit, artifactIntegrity, tagCommit, publishedIntegrity: artifactIntegrity }), { release: true, publish: false, tag: 'v1.0.2' });
  }
});
test('release planning rejects conflicting artifacts, conflicting unpublished tags, and unsafe versions', () => {
  assert.throws(() => planRelease({ version: '1.0.2', commit, artifactIntegrity, publishedIntegrity: 'sha512-other' }), /different artifact/i);
  assert.throws(() => planRelease({ version: '1.0.2', commit, artifactIntegrity, tagCommit: previous }), /tag.*different commit/i);
  assert.throws(() => planRelease({ version: '1.0.2; echo unsafe', commit, artifactIntegrity }), /stable version/i);
});
test('release tags are pushed to the exact validated commit and cannot be moved', async t => {
  const dir = mkdtempSync(join(tmpdir(), 'smooth-backlog-release-')); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const remote = join(dir, 'remote.git'), repo = join(dir, 'repo');
  execFileSync('git', ['init', '--bare', remote], { stdio: 'ignore' });
  execFileSync('git', ['init', '-b', 'main', repo], { stdio: 'ignore' });
  const git = args => execFileSync('git', args, { cwd: repo, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
  git(['config', 'user.name', 'Release test']); git(['config', 'user.email', 'release-test@example.invalid']);
  git(['remote', 'add', 'origin', remote]); git(['commit', '--allow-empty', '-m', 'validated release']);
  const sha = git(['rev-parse', 'HEAD']);
  assert.equal(await tagRelease({ version: '1.0.2', commit: sha, cwd: repo }), 'v1.0.2');
  assert.equal(git(['rev-parse', 'v1.0.2^{commit}']), sha);
  assert.match(git(['ls-remote', 'origin', 'refs/tags/v1.0.2^{}']), new RegExp('^' + sha));
  assert.equal(await tagRelease({ version: '1.0.2', commit: sha, cwd: repo }), 'v1.0.2');
  git(['commit', '--allow-empty', '-m', 'later change']);
  await assert.rejects(tagRelease({ version: '1.0.2', commit: git(['rev-parse', 'HEAD']), cwd: repo }), /tag.*different commit/i);
  assert.equal(git(['rev-parse', 'v1.0.2^{commit}']), sha);
});

test('registry absence is distinguished from authentication and network failures', async () => {
  assert.equal(await publishedIntegrity('pkg', '1.0.2', async () => ({ stdout: JSON.stringify('sha512-value') })), 'sha512-value');
  assert.equal(await publishedIntegrity('pkg', '1.0.2', async () => { throw { stdout: JSON.stringify({ error: { code: 'E404' } }) }; }), null);
  for (const code of ['E401', 'E403', 'ECONNRESET']) {
    await assert.rejects(publishedIntegrity('pkg', '1.0.2', async () => { throw { stdout: JSON.stringify({ error: { code } }) }; }), /registry version check failed/i);
  }
});
