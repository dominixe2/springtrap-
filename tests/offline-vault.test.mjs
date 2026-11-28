import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import { webcrypto } from "node:crypto";

const source = await readFile(new URL("../src/micro_helper/static/offline-vault.js", import.meta.url), "utf8");
const activeTimers = new Map();
let nextTimerId = 0;
const context = vm.createContext({
  crypto: webcrypto,
  TextEncoder,
  TextDecoder,
  Uint8Array,
  btoa,
  atob,
  setTimeout(callback, delay) {
    const id = ++nextTimerId;
    activeTimers.set(id, { callback, delay });
    return id;
  },
  clearTimeout(id) {
    activeTimers.delete(id);
  }
});
vm.runInContext(source, context);
const vault = context.MicroHelperOfflineVault;
const passphrase = "test-only-passphrase-2026";
const payload = {
  memories: [{ id: 1, content: "soukromá testovací vzpomínka" }],
  messages: [{ role: "user", content: "testovací historie" }],
  preferences: { language: "cs-CZ" }
};

test("creates an authenticated AES-GCM envelope without plaintext records", async () => {
  const envelope = await vault.create(passphrase, payload);
  assert.equal(envelope.format, "micro-helper-offline-vault");
  assert.equal(envelope.version, 1);
  assert.equal(envelope.kdf.name, "PBKDF2");
  assert.equal(envelope.kdf.hash, "SHA-256");
  assert.equal(envelope.kdf.iterations, 600000);
  assert.equal(envelope.cipher.name, "AES-GCM");
  assert.equal(envelope.cipher.length, 256);
  assert.equal(JSON.stringify(envelope).includes("soukromá testovací vzpomínka"), false);
  assert.equal(JSON.stringify(envelope).includes("testovací historie"), false);
  assert.equal((await vault.unlock(passphrase, envelope)).isLocked(), false);
});

test("rejects a wrong passphrase without returning plaintext", async () => {
  const envelope = await vault.create(passphrase, payload);
  await assert.rejects(
    () => vault.unlock("wrong-test-passphrase", envelope),
    /Heslo nesouhlasí nebo je šifrovaný trezor poškozený/
  );
});

test("rejects modified ciphertext through AES-GCM authentication", async () => {
  const envelope = JSON.parse(JSON.stringify(await vault.create(passphrase, payload)));
  const first = envelope.ciphertext[0];
  envelope.ciphertext = (first === "A" ? "B" : "A") + envelope.ciphertext.slice(1);
  await assert.rejects(
    () => vault.unlock(passphrase, envelope),
    /Heslo nesouhlasí nebo je šifrovaný trezor poškozený/
  );
});

test("rejects malformed and unsupported envelope versions before decryption", async () => {
  const envelope = JSON.parse(JSON.stringify(await vault.create(passphrase, payload)));
  await assert.rejects(() => vault.unlock(passphrase, { ...envelope, version: 2 }), /Nepodporovaná verze/);
  await assert.rejects(() => vault.unlock(passphrase, { ...envelope, iv: "AA" }), /Neplatná délka/);
  await assert.rejects(() => vault.unlock(passphrase, { ...envelope, extra: true }), /Neplatný formát/);
});

test("rejects oversized base64url ciphertext before decoding it", async () => {
  const envelope = JSON.parse(JSON.stringify(await vault.create(passphrase, payload)));
  const maxEncodedLength = Math.ceil((vault.maxPlaintextBytes + 16) * 4 / 3);
  const oversized = { ...envelope, ciphertext: "A".repeat(maxEncodedLength + 1) };
  await assert.rejects(() => vault.unlock(passphrase, oversized), /trezor je příliš velký/);
});

test("supports in-memory read, write, reseal and explicit lock", async () => {
  const envelope = await vault.create(passphrase, payload);
  const session = await vault.unlock(passphrase, envelope);
  const updated = { ...payload, memories: [{ id: 2, content: "nová soukromá hodnota" }] };
  session.write(updated);
  assert.equal(JSON.stringify(session.read()), JSON.stringify(updated));

  const resealed = await session.seal();
  assert.notEqual(resealed.iv, envelope.iv, "each save must use a fresh AES-GCM nonce");
  const reopened = await vault.unlock(passphrase, resealed);
  assert.equal(JSON.stringify(reopened.read()), JSON.stringify(updated));

  session.lock();
  assert.equal(session.isLocked(), true);
  assert.throws(() => session.read(), /trezor je uzamčený/);
  assert.throws(() => session.write(payload), /trezor je uzamčený/);
  await assert.rejects(() => session.seal(), /trezor je uzamčený/);
});

test("rejects weak passphrases and keeps persistence outside the crypto module", async () => {
  await assert.rejects(() => vault.create("short", payload), /alespoň 12 znaků/);
  assert.doesNotMatch(source, /localStorage|sessionStorage|indexedDB/);
});


test("locks automatically after the configured inactivity timeout", async () => {
  const envelope = await vault.create(passphrase, payload);
  const before = activeTimers.size;
  const session = await vault.unlock(passphrase, envelope, { idleTimeoutMs: 15000 });
  assert.equal(activeTimers.size, before + 1);
  const firstTimerId = Array.from(activeTimers.keys()).at(-1);
  assert.equal(activeTimers.get(firstTimerId).delay, 15000);

  session.read();
  assert.equal(activeTimers.has(firstTimerId), false, "activity must replace the previous timer");
  const currentTimerId = Array.from(activeTimers.keys()).at(-1);
  activeTimers.get(currentTimerId).callback();

  assert.equal(session.isLocked(), true);
  assert.throws(() => session.read(), /trezor je uzamčený/);
});

test("notifies subscribers when inactivity locks an unlocked session", async () => {
  const envelope = await vault.create(passphrase, payload);
  const session = await vault.unlock(passphrase, envelope, { idleTimeoutMs: 12000 });
  let notifications = 0;
  const unsubscribe = session.onLock(() => { notifications += 1; });
  const timerId = Array.from(activeTimers.keys()).at(-1);
  activeTimers.get(timerId).callback();
  assert.equal(session.isLocked(), true);
  assert.equal(notifications, 1);
  unsubscribe();
  session.lock();
  assert.equal(notifications, 1, "a lock notification is delivered only once");
});

test("rejects unsafe or unsupported inactivity timeout values", async () => {
  const envelope = await vault.create(passphrase, payload);
  await assert.rejects(() => vault.unlock(passphrase, envelope, { idleTimeoutMs: 999 }), /mezi 1 sekundou/);
  await assert.rejects(() => vault.unlock(passphrase, envelope, { idleTimeoutMs: 86400001 }), /mezi 1 sekundou/);
  await assert.rejects(() => vault.unlock(passphrase, envelope, { idleTimeoutMs: "60000" }), /mezi 1 sekundou/);
});
