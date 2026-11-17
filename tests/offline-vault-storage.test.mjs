import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(
  new URL("../src/micro_helper/static/offline-vault-storage.js", import.meta.url),
  "utf8"
);

function makeIndexedDB() {
  const databases = new Map();
  let openCount = 0;

  const factory = {
    open(name, version) {
      openCount += 1;
      const request = {};
      queueMicrotask(() => {
        let state = databases.get(name);
        const isNew = !state;
        if (!state) {
          state = { version, stores: new Map() };
          databases.set(name, state);
        }
        const database = {
          objectStoreNames: {
            contains(storeName) {
              return state.stores.has(storeName);
            }
          },
          createObjectStore(storeName, options) {
            const records = new Map();
            state.stores.set(storeName, { keyPath: options.keyPath, records });
            return records;
          },
          transaction(storeName) {
            const store = state.stores.get(storeName);
            const transaction = {
              oncomplete: null,
              onerror: null,
              onabort: null,
              objectStore() {
                return {
                  get(key) {
                    const result = {};
                    queueMicrotask(() => {
                      result.result = store.records.get(key) ?? null;
                      result.onsuccess?.();
                      queueMicrotask(() => transaction.oncomplete?.());
                    });
                    return result;
                  },
                  put(value) {
                    const result = {};
                    queueMicrotask(() => {
                      store.records.set(value[store.keyPath], JSON.parse(JSON.stringify(value)));
                      result.result = value[store.keyPath];
                      result.onsuccess?.();
                      queueMicrotask(() => transaction.oncomplete?.());
                    });
                    return result;
                  }
                };
              },
              abort() {
                transaction.onabort?.();
              }
            };
            return transaction;
          },
          close() {}
        };
        request.result = database;
        if (isNew) request.onupgradeneeded?.();
        request.onsuccess?.();
      });
      return request;
    }
  };

  return {
    factory,
    get openCount() { return openCount; },
    dump() {
      const state = databases.get("micro-helper-offline-vault");
      const store = state?.stores.get("vaults");
      return JSON.stringify(store ? Array.from(store.records.entries()) : []);
    }
  };
}

function loadStorage(indexedDB) {
  const context = vm.createContext({ indexedDB, queueMicrotask, JSON, Object, Array, String, Error, TypeError, RangeError });
  vm.runInContext(source, context);
  return context.MicroHelperOfflineVaultStorage.createStore({ indexedDB });
}

const envelope = {
  format: "micro-helper-offline-vault",
  version: 1,
  kdf: { name: "PBKDF2", hash: "SHA-256", iterations: 600000 },
  cipher: { name: "AES-GCM", length: 256 },
  salt: "A".repeat(22),
  iv: "B".repeat(16),
  ciphertext: "C".repeat(64)
};

test("returns null when no encrypted vault has been saved", async () => {
  const indexedDB = makeIndexedDB();
  const store = loadStorage(indexedDB.factory);
  assert.equal(await store.load(), null);
  assert.equal(indexedDB.openCount, 1);
  store.close();
});

test("persists only the validated encrypted envelope across store instances", async () => {
  const indexedDB = makeIndexedDB();
  const first = loadStorage(indexedDB.factory);
  await first.save(envelope);
  first.close();

  const second = loadStorage(indexedDB.factory);
  assert.deepEqual(await second.load(), envelope);
  assert.equal(indexedDB.openCount, 2);
  assert.equal(indexedDB.dump().includes("soukromá testovací vzpomínka"), false);
  assert.equal(indexedDB.dump().includes("testovací historie"), false);
  second.close();
});

test("rejects malformed and unsupported envelopes before opening IndexedDB", async () => {
  const indexedDB = makeIndexedDB();
  const store = loadStorage(indexedDB.factory);
  await assert.rejects(
    () => store.save({ ...envelope, version: 2 }),
    /nepodporovaný obal/
  );
  await assert.rejects(
    () => store.save({ ...envelope, plaintext: "must never persist" }),
    /nepodporovaný obal/
  );
  assert.equal(indexedDB.openCount, 0);
  store.close();
});

test("fails closed when IndexedDB is unavailable", async () => {
  const store = loadStorage(undefined);
  await assert.rejects(() => store.load(), /nepodporuje IndexedDB/);
});

test("rejects a corrupted stored record without overwriting it", async () => {
  const indexedDB = makeIndexedDB();
  const store = loadStorage(indexedDB.factory);
  await store.save(envelope);
  const before = indexedDB.dump();
  store.close();

  const state = loadStorage(indexedDB.factory);
  const originalOpen = indexedDB.factory.open.bind(indexedDB.factory);
  indexedDB.factory.open = (name, version) => {
    const request = originalOpen(name, version);
    const success = request.onsuccess;
    request.onsuccess = () => {
      const db = request.result;
      const transaction = db.transaction("vaults", "readwrite");
      transaction.objectStore("vaults").put({
        id: "primary",
        envelope: { ...envelope, version: 99 }
      });
      success?.();
    };
    return request;
  };

  await assert.rejects(() => state.load(), /poškozený nebo nepodporovaný/);
  assert.notEqual(indexedDB.dump(), before);
  state.close();
});
