const JSON_HEADERS = { "Content-Type": "application/json" };
const DEFAULT_TIMEOUT_MS = 15_000;
const UPLOAD_TIMEOUT_MS = 60_000;

export class TimeoutError extends Error {
  constructor(timeoutMs) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = "TimeoutError";
    this.timeoutMs = timeoutMs;
  }
}

function combineSignals(externalSignal, timeoutMs) {
  const timeoutController = new AbortController();
  const timer = setTimeout(() => {
    timeoutController.abort(new TimeoutError(timeoutMs));
  }, timeoutMs);

  if (externalSignal) {
    if (externalSignal.aborted) {
      timeoutController.abort(externalSignal.reason);
    } else {
      externalSignal.addEventListener(
        "abort",
        () => timeoutController.abort(externalSignal.reason),
        { once: true },
      );
    }
  }

  return {
    signal: timeoutController.signal,
    cleanup: () => clearTimeout(timer),
  };
}

async function request(path, init = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const { signal: externalSignal, ...rest } = init;
  const { signal, cleanup } = combineSignals(externalSignal, timeoutMs);
  try {
    return await fetch(path, { credentials: "include", ...rest, signal });
  } catch (err) {
    if (signal.reason instanceof TimeoutError) {
      throw signal.reason;
    }
    throw err;
  } finally {
    cleanup();
  }
}

export function apiGet(path, init = {}) {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...rest } = init;
  return request(path, rest, timeoutMs);
}

export function apiPost(path, body, init = {}) {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...rest } = init;
  const fetchInit = { method: "POST", headers: JSON_HEADERS, ...rest };
  if (body !== undefined) fetchInit.body = JSON.stringify(body);
  return request(path, fetchInit, timeoutMs);
}

export function apiPostForm(path, formData, init = {}) {
  const { timeoutMs = UPLOAD_TIMEOUT_MS, ...rest } = init;
  return request(
    path,
    { method: "POST", body: formData, ...rest },
    timeoutMs,
  );
}
