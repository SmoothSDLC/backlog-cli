import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { BacklogError } from './errors.js';
const exec = promisify(execFile);
export async function runNpm(args, options = {}) {
  let command = 'npm', commandArgs = args;
  if (process.platform === 'win32') {
    let candidates = [process.env.npm_execpath, join(dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js')].filter(Boolean);
    if (!candidates.some(x => x.endsWith('npm-cli.js') && existsSync(x))) {
      const result = await exec('where.exe', ['npm'], { windowsHide: true });
      candidates = candidates.concat(result.stdout.trim().split(/\r?\n/).map(path => join(dirname(path), 'node_modules/npm/bin/npm-cli.js')));
    }
    const script = candidates.find(x => x.endsWith('npm-cli.js') && existsSync(x));
    if (!script) throw new BacklogError('NPM_REQUIRED', 'Cannot locate npm-cli.js. Install Node.js with npm and retry.', 1);
    command = process.execPath; commandArgs = [script, ...args];
  }
  try {
    const result = await exec(command, commandArgs, { timeout: 20000, maxBuffer: 4 * 1024 * 1024, windowsHide: true, ...options, env: { ...process.env, npm_config_update_notifier: 'false', npm_config_loglevel: 'error' } });
    return result.stdout.trim();
  } catch (e) {
    // Do not echo npm output: registry authentication errors can contain credential-bearing URLs.
    throw new BacklogError('NPM_FAILED', `npm ${args[0]} failed (${e.code || e.signal || 'unknown error'}). Check network access, registry authentication and filesystem permissions. GitHub Packages requires read:packages access.`, 1);
  }
}
