import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(
  new URL("../src/micro_helper/static/offline-vault-ui.js", import.meta.url),
  "utf8"
);
const context = vm.createContext({});
vm.runInContext(source, context, {filename: "offline-vault-ui.js"});
const ui = context.MicroHelperOfflineVaultUI;

const backup = {
  format: "micro-helper-backup",
  version: 1,
  created_at: "2026-11-19T12:00:00Z",
  profile: {agent_name: "Micro Helper", language: "cs-CZ", style: "friendly", updated_at: "2026-11-19T12:00:00Z"},
  memories: [{id: 1, content: "soukromá testovací vzpomínka", category: "context", created_at: "2026-11-19T12:00:00Z"}],
  messages: [{id: 1, role: "user", content: "soukromá historie", created_at: "2026-11-19T12:00:00Z"}],
  tasks: [],
  learning_plans: [],
  preferences: []
};
const envelope = {
  format: "micro-helper-offline-vault",
  version: 1,
  kdf: {name: "PBKDF2", hash: "SHA-256", iterations: 600000},
  cipher: {name: "AES-GCM", length: 256},
  salt: "AAAAAAAAAAAAAAAAAAAAAA",
  iv: "BBBBBBBBBBBBBBBB",
  ciphertext: "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
};

function makeHarness(options = {}) {
  let stored = options.existing ?? null;
  const saves = [];
  const downloads = [];
  const requests = [];
  const lifecycle = {};
  let reloads = 0;
  let locked = false;
  const elements = {
    passphrase: {value: ""},
    passphraseConfirm: {value: "", hidden: false, focus() { this.focused = true; }},
    status: {textContent: ""},
    summary: {textContent: ""},
    create: {disabled: false},
    unlock: {disabled: false},
    lock: {disabled: false},
    restore: {disabled: false},
    export: {disabled: false},
    import: {disabled: false}
  };
  const storage = {
    async load() { return stored ? JSON.parse(JSON.stringify(stored)) : null; },
    async save(value) {
      if (value?.format !== "micro-helper-offline-vault") {
        throw new Error("invalid envelope");
      }
      stored = JSON.parse(JSON.stringify(value));
      saves.push(JSON.parse(JSON.stringify(value)));
    },
    close() { lifecycle.closed = true; }
  };
  const vault = {
    async create(passphrase, payload) {
      assert.equal(passphrase, "dostatecne-dlouhe-heslo");
      assert.deepEqual(JSON.parse(JSON.stringify(payload)), backup);
      return JSON.parse(JSON.stringify(envelope));
    },
    async unlock(passphrase, value) {
      if (options.rejectUnlock || passphrase !== "dostatecne-dlouhe-heslo") {
        throw new Error("wrong passphrase");
      }
      assert.deepEqual(JSON.parse(JSON.stringify(value)), envelope);
      locked = false;
      return {
        isLocked: () => locked,
        read: () => JSON.parse(JSON.stringify(backup)),
        lock() { locked = true; }
      };
    }
  };
  const fetchImpl = async (url, init = {}) => {
    requests.push({url, init});
    if (url === "/v1/backup" && init.method === "GET") {
      return {ok: true, async json() { return JSON.parse(JSON.stringify(backup)); }};
    }
    if (url === "/v1/backup/restore" && init.method === "POST") {
      return {ok: options.restoreFails !== true};
    }
    throw new Error("unexpected request");
  };
  const controller = ui.createController({
    vault,
    storage,
    fetchImpl,
    confirmImpl: options.confirmImpl ?? (() => true),
    downloadImpl: (value, filename) => downloads.push({value, filename}),
    reloadImpl: () => { reloads += 1; },
    lifecycle: {addEventListener(name, callback) { lifecycle[name] = callback; }},
    elements
  });
  return {
    controller, elements, storage, saves, downloads, requests, lifecycle,
    getStored: () => stored,
    getReloads: () => reloads,
    isSessionLocked: () => locked
  };
}

test("creates an encrypted backup and stores only the ciphertext envelope", async () => {
  const h = makeHarness();
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  h.elements.passphraseConfirm.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.createBackup(), true);
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].url, "/v1/backup");
  assert.equal(h.requests[0].init.cache, "no-store");
  assert.deepEqual(h.getStored(), envelope);
  assert.equal(JSON.stringify(h.getStored()).includes("soukromá testovací vzpomínka"), false);
  assert.equal(JSON.stringify(h.getStored()).includes("soukromá historie"), false);
  assert.equal(h.elements.passphrase.value, "");
  assert.equal(h.controller.getState().unlocked, false);
});

test("rejects a short passphrase before fetching private backup data", async () => {
  const h = makeHarness();
  h.elements.passphrase.value = "kratke";
  assert.equal(await h.controller.createBackup(), false);
  assert.equal(h.requests.length, 0);
  assert.equal(h.getStored(), null);
  assert.equal(h.elements.passphrase.value, "");
});

test("rejects mismatched passphrase confirmation before fetching backup data", async () => {
  const h = makeHarness();
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  h.elements.passphraseConfirm.value = "jine-dostatecne-heslo";
  assert.equal(await h.controller.createBackup(), false);
  assert.equal(h.requests.length, 0);
  assert.equal(h.getStored(), null);
  assert.equal(h.elements.passphrase.value, "");
  assert.equal(h.elements.passphraseConfirm.value, "");
});

test("does not overwrite an existing encrypted vault when confirmation is declined", async () => {
  const h = makeHarness({existing: envelope, confirmImpl: () => false});
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  await h.controller.refresh();
  assert.equal(h.elements.passphraseConfirm.hidden, true);
  assert.equal(await h.controller.createBackup(), false);
  assert.equal(h.elements.passphraseConfirm.hidden, false);
  h.elements.passphraseConfirm.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.createBackup(), false);
  assert.equal(h.requests.length, 0);
  assert.deepEqual(h.getStored(), envelope);
});

test("wrong passphrase never unlocks or restores the stored backup", async () => {
  const h = makeHarness({existing: envelope, rejectUnlock: true});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), false);
  assert.equal(h.controller.getState().unlocked, false);
  assert.equal(await h.controller.restore(), false);
  assert.equal(h.requests.length, 0);
});

test("restores only after successful unlock through the guarded local API route", async () => {
  const h = makeHarness({existing: envelope});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  assert.equal(h.controller.getState().unlocked, true);
  assert.equal(await h.controller.restore(), true);
  const request = h.requests.at(-1);
  assert.equal(request.url, "/v1/backup/restore");
  assert.equal(request.init.method, "POST");
  assert.equal(request.init.credentials, "same-origin");
  assert.deepEqual(JSON.parse(request.init.body), {backup, confirm_replace: true});
  assert.equal(h.getReloads(), 1);
  assert.equal(h.controller.getState().unlocked, false);
});

test("exports the encrypted envelope and never exports the decrypted backup", async () => {
  const h = makeHarness({existing: envelope});
  assert.equal(await h.controller.exportEncrypted(), true);
  assert.equal(h.downloads.length, 1);
  assert.equal(h.downloads[0].filename, "micro-helper-encrypted-backup.json");
  assert.deepEqual(h.downloads[0].value, envelope);
  assert.equal(JSON.stringify(h.downloads[0].value).includes("soukromá historie"), false);
});

test("imports only an encrypted envelope and keeps the previous record on invalid input", async () => {
  const h = makeHarness({existing: envelope});
  const invalid = {size: 20, async text() { return JSON.stringify(backup); }};
  assert.equal(await h.controller.importEncryptedFile(invalid), false);
  assert.deepEqual(h.getStored(), envelope);
  assert.equal(h.saves.length, 0);
  const valid = {size: 300, async text() { return JSON.stringify(envelope); }};
  assert.equal(await h.controller.importEncryptedFile(valid), true);
  assert.deepEqual(h.getStored(), envelope);
  assert.equal(h.saves.length, 1);
});

test("pagehide locks the in-memory session and closes IndexedDB", async () => {
  const h = makeHarness({existing: envelope});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  h.lifecycle.pagehide();
  assert.equal(h.controller.getState().unlocked, false);
  assert.equal(h.isSessionLocked(), true);
  assert.equal(h.lifecycle.closed, true);
});
