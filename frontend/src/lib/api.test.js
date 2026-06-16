import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiGet, apiPost, apiPostForm, TimeoutError } from "./api";

describe("api fetch timeout", () => {
  let originalFetch;

  beforeEach(() => {
    vi.useFakeTimers();
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    vi.useRealTimers();
    globalThis.fetch = originalFetch;
  });

  it("apiGet resolves when fetch completes within the timeout", async () => {
    const expected = { ok: true, status: 200 };
    globalThis.fetch = vi.fn(() => Promise.resolve(expected));

    const result = await apiGet("/api/ping");

    expect(result).toBe(expected);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/ping",
      expect.objectContaining({
        credentials: "include",
        signal: expect.any(AbortSignal),
      }),
    );
  });

  it("apiGet aborts and throws TimeoutError after timeoutMs", async () => {
    globalThis.fetch = vi.fn(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init.signal.addEventListener("abort", () => {
            const err = new Error("aborted");
            err.name = "AbortError";
            reject(err);
          });
        }),
    );

    const promise = apiGet("/api/slow", { timeoutMs: 100 });
    const expectation = expect(promise).rejects.toBeInstanceOf(TimeoutError);
    await vi.advanceTimersByTimeAsync(100);
    await expectation;
  });

  it("apiGet propagates a caller-provided signal abort", async () => {
    globalThis.fetch = vi.fn(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init.signal.addEventListener("abort", () => {
            const err = new Error("aborted");
            err.name = "AbortError";
            reject(err);
          });
        }),
    );

    const controller = new AbortController();
    const promise = apiGet("/api/slow", {
      signal: controller.signal,
      timeoutMs: 10_000,
    });
    controller.abort();

    await expect(promise).rejects.toMatchObject({ name: "AbortError" });
  });

  it("apiPost sends JSON body and respects timeout override", async () => {
    globalThis.fetch = vi.fn(() => Promise.resolve({ ok: true, status: 201 }));

    await apiPost("/api/things", { foo: "bar" }, { timeoutMs: 5_000 });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/things",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ foo: "bar" }),
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("apiPostForm uses the 60s upload default and times out past it", async () => {
    globalThis.fetch = vi.fn(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init.signal.addEventListener("abort", () => {
            const err = new Error("aborted");
            err.name = "AbortError";
            reject(err);
          });
        }),
    );

    const form = new FormData();
    const promise = apiPostForm("/api/uploads", form);
    const expectation = expect(promise).rejects.toBeInstanceOf(TimeoutError);
    await vi.advanceTimersByTimeAsync(60_000);
    await expectation;
  });
});
