import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { readFile, appendFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const exec = promisify(execFile);
const registry = 'https://npm.pkg.github.com';
function releaseTag(version) {
  assert.match(version || '', /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/, 'Release requires an exact stable version');
  return `v${version}`;
}
async function tagCommit(tag, cwd) {
  try { return (await exec('git', ['rev-parse', '--verify', '--quiet', `refs/tags/${tag}^{commit}`], { cwd })).stdout.trim(); }
  catch (error) { if (error.code === 1) return null; throw error; }
}
export function planRelease({ version, commit, tagCommit: existing, publishedIntegrity: published, artifactIntegrity }) {
  const tag = releaseTag(version); assert.match(commit || '', /^[0-9a-f]{40}$/i, 'Release requires a commit SHA');
  assert.ok(artifactIntegrity, 'Release requires the packed artifact integrity');
  if (existing && existing !== commit) {
    assert.ok(published, 'Release tag points to a different commit but its package is not published');
    return { release: false, publish: false, tag };
  }
  assert.ok(!published || published === artifactIntegrity, 'This version is already published with a different artifact; bump the package version');
  return { release: true, publish: !published, tag };
}
export async function publishedIntegrity(name, version, runner = exec) {
  try {
    const result = await runner('npm', ['view', `${name}@${version}`, 'dist.integrity', '--json', '--registry', registry], { timeout: 30000 });
    const integrity = JSON.parse(result.stdout); assert.equal(typeof integrity, 'string'); return integrity;
  } catch (error) {
    let response; try { response = JSON.parse(error.stdout); } catch {}
    if (response?.error?.code === 'E404') return null;
    throw new Error('Registry version check failed; verify package access, authentication, and network connectivity');
  }
}
export async function tagRelease({ version, commit, cwd = process.cwd() }) {
  const tag = releaseTag(version); assert.match(commit || '', /^[0-9a-f]{40}$/i, 'Release requires a commit SHA');
  const existing = await tagCommit(tag, cwd);
  assert.ok(!existing || existing === commit, 'Release tag already points to a different commit; it will not be moved');
  if (!existing) await exec('git', ['-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com', 'tag', '-a', tag, commit, '-m', `Release ${version}`], { cwd });
  await exec('git', ['push', 'origin', `refs/tags/${tag}`], { cwd });
  return tag;
}
async function run() {
  const pkg = JSON.parse(await readFile(new URL('../../package.json', import.meta.url), 'utf8'));
  const version = process.env.RELEASE_VERSION || pkg.version, commit = process.env.GITHUB_SHA;
  if (process.argv[2] === 'tag') { console.log(`Published tag ${await tagRelease({ version, commit })}`); return; }
  assert.equal(process.argv[2], 'plan', 'Use release.mjs plan or release.mjs tag');
  const tag = releaseTag(version);
  const plan = planRelease({ version, commit, artifactIntegrity: process.env.RELEASE_INTEGRITY, tagCommit: await tagCommit(tag), publishedIntegrity: await publishedIntegrity(pkg.name, version) });
  assert.ok(process.env.GITHUB_OUTPUT, 'GITHUB_OUTPUT is required');
  await appendFile(process.env.GITHUB_OUTPUT, `release=${plan.release}\npublish=${plan.publish}\n`);
  console.log(plan.release ? `Verify release ${version}; npm publication ${plan.publish ? 'required' : 'already complete'}` : `Version ${version} is already released; bump the package version in a release PR to publish again`);
}
if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  run().catch(error => { process.stderr.write(`Release automation failed: ${error.message}\n`); process.exitCode = 1; });
}
