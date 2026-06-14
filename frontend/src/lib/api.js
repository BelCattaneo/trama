const JSON_HEADERS = { "Content-Type": "application/json" };

function request(path, init = {}) {
  return fetch(path, { credentials: "include", ...init });
}

export function apiGet(path) {
  return request(path);
}

export function apiPost(path, body) {
  const init = { method: "POST", headers: JSON_HEADERS };
  if (body !== undefined) init.body = JSON.stringify(body);
  return request(path, init);
}
