const JSON_HEADERS = { "Content-Type": "application/json" };

function request(path, init = {}) {
  return fetch(path, { credentials: "include", ...init });
}

export function apiGet(path, init = {}) {
  return request(path, init);
}

export function apiPost(path, body) {
  const init = { method: "POST", headers: JSON_HEADERS };
  if (body !== undefined) init.body = JSON.stringify(body);
  return request(path, init);
}

export function apiPostForm(path, formData) {
  return request(path, { method: "POST", body: formData });
}
