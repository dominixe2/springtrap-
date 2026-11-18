import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(
  new URL("../src/micro_helper/static/sw.js", import.meta.url),
  "utf8"
);

function createHarness() {
  const listeners = new Map();
  const calls = { cacheOpen: 0, cacheMatch: 0, cachePut: 0, fetch: 0 };
  const cache = {
    async addAll() {},
    async put() { calls.cachePut += 1; }
  };
  const caches = {
    async open() {
      calls.cacheOpen += 1;
      return cache;
    },
    async match() {
      calls.cacheMatch += 1;
      return null;
    },
    async keys() { return []; },
    async delete() { return true; }
  };
  const self = {
    location: { origin: "https://micro-helper.test" },
    clients: { async claim() {} },
    async skipWaiting() {},
    addEventListener(type, callback) {
      listeners.set(type, callback);
    }
  };
  const context = vm.createContext({
    self,
    caches,
    URL,
    Promise,
    async fetch() {
      calls.fetch += 1;
      return { ok: true, clone() { return this; } };
    }
  });
  vm.runInContext(source, context, { filename: "sw.js" });

  function dispatch(request) {
    let intercepted = false;
    let responsePromise = null;
    listeners.get("fetch")({
      request,
      respondWith(value) {
        intercepted = true;
        responsePromise = Promise.resolve(value);
      }
    });
    return { intercepted, responsePromise };
  }

  return { calls, dispatch };
}

test("service worker never intercepts or caches same-origin private API reads", async () => {
  const { calls, dispatch } = createHarness();
  const privatePaths = [
    "/v1/auth/status",
    "/v1/conversations?limit=100",
    "/v1/memories",
    "/v1/preferences",
    "/v1/backup",
    "/v1/tasks?limit=30",
    "/v1/learning-plans",
    "/v1/actions/confirm"
  ];

  for (const path of privatePaths) {
    const result = dispatch({
      url: "https://micro-helper.test" + path,
      method: "GET",
      mode: "cors"
    });
    assert.equal(result.intercepted, false, path);
  }

  assert.deepEqual(calls, { cacheOpen: 0, cacheMatch: 0, cachePut: 0, fetch: 0 });
});

test("service worker never intercepts private API writes or deletes", () => {
  const { calls, dispatch } = createHarness();
  for (const [method, path] of [
    ["POST", "/v1/memories"],
    ["PUT", "/v1/profile"],
    ["DELETE", "/v1/conversations"],
    ["PATCH", "/v1/learning-plans/plan-1/status"],
    ["POST", "/v1/backup/restore"]
  ]) {
    const result = dispatch({
      url: "https://micro-helper.test" + path,
      method,
      mode: "cors"
    });
    assert.equal(result.intercepted, false, method + " " + path);
  }
  assert.deepEqual(calls, { cacheOpen: 0, cacheMatch: 0, cachePut: 0, fetch: 0 });
});

test("service worker still handles same-origin static assets", async () => {
  const { calls, dispatch } = createHarness();
  const result = dispatch({
    url: "https://micro-helper.test/static/offline-vault.js",
    method: "GET",
    mode: "cors"
  });
  assert.equal(result.intercepted, true);
  await result.responsePromise;
  assert.equal(calls.cacheMatch, 1);
  assert.equal(calls.fetch, 1);
  assert.equal(calls.cacheOpen, 1);
  assert.equal(calls.cachePut, 1);
});

test("service worker does not intercept cross-origin resources", () => {
  const { calls, dispatch } = createHarness();
  const result = dispatch({
    url: "https://cdn.example.test/static/app.js",
    method: "GET",
    mode: "cors"
  });
  assert.equal(result.intercepted, false);
  assert.deepEqual(calls, { cacheOpen: 0, cacheMatch: 0, cachePut: 0, fetch: 0 });
});
