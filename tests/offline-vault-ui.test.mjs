import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

const source = await readFile(
  new URL("../src/micro_helper/static/offline-vault-ui.js", import.meta.url),
  "utf8"
);
const context = vm.createContext({AbortController});
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
  let saveCompleted = false;
  const saves = [];
  const downloads = [];
  const requests = [];
  const lifecycle = {};
  let markCreateStarted;
  const createStarted = new Promise(resolve => { markCreateStarted = resolve; });
  let markSaveStarted;
  const saveStarted = new Promise(resolve => { markSaveStarted = resolve; });
  const visibility = {
    visibilityState: "visible",
    listeners: new Map(),
    addEventListener(name, callback) { this.listeners.set(name, callback); },
    removeEventListener(name, callback) { this.listeners.delete(name); },
    setState(value) {
      this.visibilityState = value;
      this.listeners.get("visibilitychange")?.();
    }
  };
  let reloads = 0;
  let locked = false;
  let activeSession = null;
  let sessionData = null;
  let confirmImpl = options.confirmImpl ?? (() => true);
  let promptImpl = options.promptImpl ?? (() => "upravená offline hodnota");
  const makeElement = (tagName = "div") => ({
    tagName: tagName.toUpperCase(),
    value: "",
    textContent: "",
    hidden: false,
    disabled: false,
    children: [],
    listeners: {},
    replaceChildren(...children) {
      this.children = children;
      if (this.tagName === "SELECT") this.value = children[0]?.value ?? "";
    },
    addEventListener(name, callback) { this.listeners[name] = callback; }
  });
  const documentImpl = {createElement: makeElement};
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
    import: {disabled: false},
    workspace: makeElement("section"),
    workspaceSummary: makeElement("small"),
    workspaceMemoryForm: makeElement("form"),
    workspaceMemoryText: makeElement("input"),
    workspaceMemoryCategory: makeElement("select"),
    workspaceMemorySave: makeElement("button"),
    workspaceMemorySelect: makeElement("select"),
    workspaceMemoryEdit: makeElement("button"),
    workspaceMemoryDelete: makeElement("button"),
    workspaceMemoryList: makeElement("small"),
    workspacePreferenceForm: makeElement("form"),
    workspacePreferenceCategory: makeElement("select"),
    workspacePreferenceName: makeElement("input"),
    workspacePreferenceValue: makeElement("input"),
    workspacePreferenceSave: makeElement("button"),
    workspacePreferenceSelect: makeElement("select"),
    workspacePreferenceEdit: makeElement("button"),
    workspacePreferenceDelete: makeElement("button"),
    workspacePreferenceList: makeElement("small"),
    workspaceHistoryList: makeElement("pre"),
    workspaceClearHistory: makeElement("button"),
    workspaceTaskList: makeElement("small"),
    workspacePlanList: makeElement("small")
  };
  elements.workspace.hidden = true;
  const storage = {
    async load() {
      if (options.failLoadAfterSave && saveCompleted) throw new Error("simulated readback failure");
      return stored ? JSON.parse(JSON.stringify(stored)) : null;
    },
    async save(value, saveOptions = {}) {
      if (value?.format !== "micro-helper-offline-vault") {
        throw new Error("invalid envelope");
      }
      if (options.saveGate) {
        markSaveStarted();
        await new Promise((resolve, reject) => {
          let settled = false;
          const cleanup = () => saveOptions.signal?.removeEventListener("abort", onAbort);
          const onAbort = () => {
            if (settled) return;
            settled = true;
            cleanup();
            reject(new Error("aborted"));
          };
          saveOptions.signal?.addEventListener("abort", onAbort, {once: true});
          Promise.resolve(options.saveGate).then(() => {
            if (settled) return;
            settled = true;
            cleanup();
            resolve();
          }, reject);
          if (saveOptions.signal?.aborted) onAbort();
        });
      }
      if (saveOptions.signal?.aborted) throw new Error("aborted");
      if (options.failSave) throw new Error("simulated persistence failure");
      stored = JSON.parse(JSON.stringify(value));
      saves.push(JSON.parse(JSON.stringify(value)));
      saveCompleted = true;
    },
    close() { lifecycle.closed = true; }
  };
  const vault = {
    async create(passphrase, payload) {
      markCreateStarted();
      if (options.createGate) await options.createGate;
      assert.equal(passphrase, "dostatecne-dlouhe-heslo");
      assert.deepEqual(JSON.parse(JSON.stringify(payload)), backup);
      return JSON.parse(JSON.stringify(envelope));
    },
    async unlock(passphrase, value) {
      if (options.unlockGate) await options.unlockGate;
      if (options.rejectUnlock || passphrase !== "dostatecne-dlouhe-heslo") {
        throw new Error("wrong passphrase");
      }
      assert.equal(value?.format, "micro-helper-offline-vault");
      locked = false;
      sessionData = JSON.parse(JSON.stringify(backup));
      const listeners = new Set();
      activeSession = {
        isLocked: () => locked,
        read: () => {
          if (locked) throw new Error("locked");
          return JSON.parse(JSON.stringify(sessionData));
        },
        write(next) {
          if (locked) throw new Error("locked");
          sessionData = JSON.parse(JSON.stringify(next));
        },
        async seal() {
          if (locked) throw new Error("locked");
          return {...envelope, ciphertext: "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD"};
        },
        onLock(callback) {
          if (locked) { callback(); return () => {}; }
          listeners.add(callback);
          return () => listeners.delete(callback);
        },
        lock() {
          if (locked) return;
          locked = true;
          for (const listener of Array.from(listeners)) listener();
          listeners.clear();
        }
      };
      return activeSession;
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
    confirmImpl: message => confirmImpl(message),
    promptImpl: message => promptImpl(message),
    documentImpl,
    downloadImpl: (value, filename) => downloads.push({value, filename}),
    reloadImpl: () => { reloads += 1; },
    lifecycle: {addEventListener(name, callback) { lifecycle[name] = callback; }},
    visibility,
    abortControllerFactory: () => new AbortController(),
    elements
  });
  return {
    controller, elements, storage, saves, downloads, requests, lifecycle, visibility,
    waitForCreate: () => createStarted,
    waitForSave: () => saveStarted,
    getStored: () => stored,
    getSessionData: () => sessionData ? JSON.parse(JSON.stringify(sessionData)) : null,
    getReloads: () => reloads,
    expireSession: () => activeSession?.lock(),
    isSessionLocked: () => locked,
    setConfirmImpl: value => { confirmImpl = value; },
    setPromptImpl: value => { promptImpl = value; }
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

test("keeps the vault unlocked when the guarded restore is cancelled", async () => {
  const h = makeHarness({existing: envelope, restoreFails: true});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  assert.equal(h.elements.summary.textContent.includes("soukromá historie"), false);
  assert.equal(await h.controller.restore(), false);
  assert.equal(h.requests.at(-1).url, "/v1/backup/restore");
  assert.equal(h.getReloads(), 0);
  assert.equal(h.controller.getState().unlocked, true);
});

test("does not send a restore request after the vault inactivity lock expires", async () => {
  const h = makeHarness({existing: envelope});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  h.expireSession();
  assert.equal(await h.controller.restore(), false);
  assert.equal(h.requests.length, 0);
  assert.equal(h.controller.getState().unlocked, false);
});

test("rejects an oversized encrypted import before reading the file", async () => {
  const h = makeHarness();
  let read = false;
  const file = {
    size: 12 * 1024 * 1024 + 1,
    async text() { read = true; return JSON.stringify(envelope); }
  };
  assert.equal(await h.controller.importEncryptedFile(file), false);
  assert.equal(read, false);
  assert.equal(h.saves.length, 0);
  assert.equal(h.getStored(), null);
});

test("does not report a successful IndexedDB write as failed because of a redundant readback", async () => {
  const h = makeHarness({failLoadAfterSave: true});
  const file = {size: 300, async text() { return JSON.stringify(envelope); }};
  assert.equal(await h.controller.importEncryptedFile(file), true);
  assert.deepEqual(h.getStored(), envelope);
  assert.equal(h.saves.length, 1);
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

test("unlocked offline workspace reads and persists local-only memory and preferences", async () => {
  const h = makeHarness({existing: envelope});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  assert.equal(h.controller.getState().workspaceVisible, true);
  assert.match(h.elements.workspaceHistoryList.textContent, /soukromá historie/);

  assert.equal(await h.controller.addMemory("nová offline poznámka", "project"), true);
  assert.equal(await h.controller.addPreference("communication", "styl", "stručně"), true);
  const data = h.getSessionData();
  assert.equal(data.memories.at(-1).content, "nová offline poznámka");
  assert.equal(data.preferences.at(-1).value, "stručně");
  assert.equal(h.saves.length, 2);
  assert.equal(JSON.stringify(h.getStored()).includes("nová offline poznámka"), false);
  assert.equal(JSON.stringify(h.getStored()).includes("stručně"), false);
  assert.match(h.elements.workspaceMemoryList.textContent, /2 uložených poznámek/);
});

test("offline memory and preference edits and deletions require local explicit confirmation", async () => {
  const h = makeHarness({existing: envelope});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  assert.equal(await h.controller.editMemory(1), true);
  assert.equal(h.getSessionData().memories[0].content, "upravená offline hodnota");

  h.setConfirmImpl(() => false);
  assert.equal(await h.controller.deleteMemory(1), false);
  assert.equal(h.getSessionData().memories.length, 1);
  h.setConfirmImpl(() => true);
  assert.equal(await h.controller.deleteMemory(1), true);
  assert.equal(h.getSessionData().memories.length, 0);

  assert.equal(await h.controller.editPreference(1), false, "missing preference is not edited");
  assert.equal(await h.controller.addPreference("communication", "odpovědi", "česky"), true);
  const preference = h.getSessionData().preferences[0];
  assert.equal(await h.controller.editPreference(preference.id), true);
  assert.equal(h.getSessionData().preferences[0].value, "upravená offline hodnota");
  assert.equal(await h.controller.deletePreference(preference.id), true);
  assert.equal(h.getSessionData().preferences.length, 0);
});

test("clearing offline history is separately confirmed and does not call the server", async () => {
  const h = makeHarness({existing: envelope, confirmImpl: () => false});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  assert.equal(await h.controller.clearHistory(), false);
  assert.equal(h.getSessionData().messages.length, 1);
  h.setConfirmImpl(() => true);
  assert.equal(await h.controller.clearHistory(), true);
  assert.equal(h.getSessionData().messages.length, 0);
  assert.equal(h.requests.length, 0);
});

test("failed offline persistence rolls back the in-memory edit and preserves the stored envelope", async () => {
  const h = makeHarness({existing: envelope, failSave: true});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  assert.equal(await h.controller.addMemory("nesmí se uložit", "context"), false);
  assert.equal(h.getSessionData().memories.length, 1);
  assert.equal(h.getStored().ciphertext, envelope.ciphertext);
  assert.match(h.elements.status.textContent, /původní šifrovaná kopie zůstala zachována/i);
});

test("inactivity lock clears decrypted offline workspace content from the page", async () => {
  const h = makeHarness({existing: envelope});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  assert.equal(h.elements.workspace.hidden, false);
  assert.match(h.elements.workspaceHistoryList.textContent, /soukromá historie/);
  h.expireSession();
  assert.equal(h.controller.getState().unlocked, false);
  assert.equal(h.elements.workspace.hidden, true);
  assert.equal(h.elements.workspaceHistoryList.textContent, "");
  assert.equal(h.elements.workspaceMemoryList.textContent, "");
});

test("aborts a pending offline workspace save when the page becomes hidden", async () => {
  let releaseSave;
  const saveGate = new Promise(resolve => { releaseSave = resolve; });
  const h = makeHarness({existing: envelope, saveGate});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  const pending = h.controller.addMemory("přerušená offline změna", "context");
  await h.waitForSave();
  h.visibility.setState("hidden");
  h.visibility.setState("visible");
  assert.equal(await pending, false);
  assert.equal(h.getStored().ciphertext, envelope.ciphertext);
  assert.equal(h.controller.getState().unlocked, false);
  assert.equal(h.elements.workspace.hidden, true);
  releaseSave();
});

test("does not save a new encrypted backup when the page is hidden during encryption", async () => {
  let releaseCreate;
  const createGate = new Promise(resolve => { releaseCreate = resolve; });
  const h = makeHarness({createGate});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  h.elements.passphraseConfirm.value = "dostatecne-dlouhe-heslo";
  const pendingCreate = h.controller.createBackup();
  await h.waitForCreate();
  h.visibility.setState("hidden");
  h.visibility.setState("visible");
  releaseCreate();
  assert.equal(await pendingCreate, false);
  assert.equal(h.saves.length, 0);
  assert.equal(h.getStored(), null);
  assert.match(h.elements.status.textContent, /Záloha nebyla uložena/);
});

test("aborts a pending encrypted-backup save when the page becomes hidden", async () => {
  let releaseSave;
  const saveGate = new Promise(resolve => { releaseSave = resolve; });
  const h = makeHarness({saveGate});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  h.elements.passphraseConfirm.value = "dostatecne-dlouhe-heslo";
  const pendingCreate = h.controller.createBackup();
  await h.waitForSave();
  h.visibility.setState("hidden");
  h.visibility.setState("visible");
  assert.equal(await pendingCreate, false);
  assert.equal(h.saves.length, 0);
  assert.equal(h.getStored(), null);
  assert.match(h.elements.status.textContent, /Zálohování bylo přerušeno/);
  releaseSave();
});

test("locks the in-memory session as soon as the page becomes hidden", async () => {
  const h = makeHarness({existing: envelope});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true);
  h.elements.passphrase.value = "must be cleared";
  h.visibility.setState("hidden");
  assert.equal(h.controller.getState().unlocked, false);
  assert.equal(h.isSessionLocked(), true);
  assert.equal(h.elements.passphrase.value, "");
  assert.equal(h.elements.lock.disabled, true);
  assert.match(h.elements.status.textContent, /uzamčený/);
  assert.equal(await h.controller.restore(), false);
  assert.equal(h.requests.length, 0);
  h.visibility.setState("visible");
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  assert.equal(await h.controller.unlock(), true, "visibility returning must require a fresh unlock");
});

test("does not finish unlocking if the page was hidden during key derivation", async () => {
  let releaseUnlock;
  const unlockGate = new Promise(resolve => { releaseUnlock = resolve; });
  const h = makeHarness({existing: envelope, unlockGate});
  await h.controller.refresh();
  h.elements.passphrase.value = "dostatecne-dlouhe-heslo";
  const pendingUnlock = h.controller.unlock();
  await Promise.resolve();
  h.visibility.setState("hidden");
  h.visibility.setState("visible");
  releaseUnlock();
  assert.equal(await pendingUnlock, false);
  assert.equal(h.controller.getState().unlocked, false);
  assert.equal(h.isSessionLocked(), true);
  assert.match(h.elements.status.textContent, /během odemykání přešla do pozadí/);
  assert.equal(await h.controller.restore(), false);
  assert.equal(h.requests.length, 0);
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
  assert.equal(h.visibility.listeners.has("visibilitychange"), false);
});
