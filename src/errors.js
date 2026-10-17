export class BacklogError extends Error {
  constructor(code, message, exitCode = 2) { super(message); this.code = code; this.exitCode = exitCode; }
}
export function input(condition, message) { if (!condition) throw new BacklogError('INVALID_INPUT', message); }
export function operation(condition, message) { if (!condition) throw new BacklogError('STORAGE_ERROR', message, 1); }
