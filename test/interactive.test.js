import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fixture, bin } from './helpers.js';
const driver = String.raw`
import pty, os, sys, select, time, json, signal
pid, fd = pty.fork()
if pid == 0:
    os.chdir(sys.argv[1])
    os.execvpe('node', ['node', sys.argv[2], 'new', '--ask', '--json'], os.environ)
steps = json.loads(sys.argv[3]); index = 0; output = b''; cursor = 0; deadline = time.monotonic() + 8
try:
    while time.monotonic() < deadline:
        if select.select([fd], [], [], .1)[0]:
            try: data = os.read(fd, 65536)
            except OSError: break
            if not data: break
            output += data
            if index < len(steps) and steps[index][0].encode() in output[cursor:]:
                os.write(fd, steps[index][1].encode()); cursor = len(output); index += 1
    else:
        os.kill(pid, signal.SIGKILL)
    _, status = os.waitpid(pid, 0)
    print(json.dumps({'code':os.waitstatus_to_exitcode(status), 'steps': index, 'output':output.decode(errors='replace')}))
finally:
    os.close(fd)
`;
test('interactive creation collects task entries and typed defaults through a real terminal', { skip: process.platform === 'win32' }, t => {
  const f = fixture(t); f.cli('init');
  const steps = [['name [_]', 'Interactive\n'], ['description [_]', 'Description\n'], ['ac [_]', 'Verifiable criteria\n'], ['item-state-description [_]', '\n'], ['work_item_id [_]', '\n'], ['tasks: add', 'a\n'], ['Task name', 'Implement\n'], ['Task goal', 'Test passes\n'], ['tasks: add', 'f\n'], ['outcomes: add', 'f\n'], ['evidence: add', 'f\n'], ['references: add', 'f\n'], ['state (', 'open\n'], ['priority (', '\n']];
  const p = spawnSync('python3', ['-c', driver, f.root, bin, JSON.stringify(steps)], { env: f.env, encoding: 'utf8', timeout: 12000 });
  assert.equal(p.status, 0, p.stderr); const result = JSON.parse(p.stdout); assert.equal(result.code, 0, result.output);
  const item = f.cli('list')[0]; assert.equal(item.name, 'Interactive'); assert.equal(item.state, 'open'); assert.deepEqual(item.tasks, [{ name: 'Implement', goal: 'Test passes' }]);
});
test('interactive cancellation leaves manifest unchanged', { skip: process.platform === 'win32' }, t => {
  const f = fixture(t); f.cli('init');
  const p = spawnSync('python3', ['-c', driver, f.root, bin, JSON.stringify([['name [_]', 'Cancelled\n'], ['description [_]', '\x03']])], { env: f.env, encoding: 'utf8', timeout: 12000 });
  assert.equal(p.status, 0, p.stderr); const result = JSON.parse(p.stdout); assert.notEqual(result.code, -9, result.output);
  assert.deepEqual(f.cli('list'), []);
});
