/* Versioned browser-side encrypted vault core. This module never persists data or keys. */
(() => {
  "use strict";

  const FORMAT = "micro-helper-offline-vault";
  const VERSION = 1;
  const KDF_NAME = "PBKDF2";
  const KDF_HASH = "SHA-256";
  const KDF_ITERATIONS = 600000;
  const CIPHER_NAME = "AES-GCM";
  const CIPHER_LENGTH = 256;
  const SALT_BYTES = 16;
  const IV_BYTES = 12;
  const MAX_PLAINTEXT_BYTES = 8 * 1024 * 1024;
  const DEFAULT_IDLE_TIMEOUT_MS = 5 * 60 * 1000;
  const MIN_IDLE_TIMEOUT_MS = 1000;
  const MAX_IDLE_TIMEOUT_MS = 24 * 60 * 60 * 1000;
  const AAD = new TextEncoder().encode(
    [FORMAT, VERSION, KDF_NAME, KDF_HASH, KDF_ITERATIONS, CIPHER_NAME, CIPHER_LENGTH].join("|")
  );

  function requireCrypto() {
    if (!globalThis.crypto || !globalThis.crypto.subtle || typeof globalThis.crypto.getRandomValues !== "function") {
      throw new Error("Tento prohlížeč nepodporuje potřebné Web Crypto API.");
    }
  }

  function validatePassphrase(passphrase) {
    if (typeof passphrase !== "string" || passphrase.length < 12) {
      throw new TypeError("Heslo trezoru musí mít alespoň 12 znaků.");
    }
    if (new TextEncoder().encode(passphrase).length > 1024) {
      throw new TypeError("Heslo trezoru je příliš dlouhé.");
    }
  }

  function serialize(value) {
    let json;
    try {
      json = JSON.stringify(value);
    } catch {
      throw new TypeError("Data trezoru nelze bezpečně převést do JSON.");
    }
    if (typeof json !== "string") {
      throw new TypeError("Data trezoru musí být platná hodnota JSON.");
    }
    const bytes = new TextEncoder().encode(json);
    if (bytes.length > MAX_PLAINTEXT_BYTES) {
      throw new RangeError("Offline trezor může obsahovat nejvýše 8 MiB dat.");
    }
    return bytes;
  }

  function cloneJson(value) {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(serialize(value)));
  }

  function encodeBase64Url(bytes) {
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 0x8000) {
      binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
    }
    return globalThis.btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  function decodeBase64Url(value, expectedLength, maxLength) {
    if (typeof value !== "string") {
      throw new TypeError("Neplatný formát šifrovaného trezoru.");
    }
    // Reject oversized encoded input before atob allocates a second large string.
    if (maxLength !== undefined && value.length > Math.ceil(maxLength * 4 / 3)) {
      throw new RangeError("Šifrovaný trezor je příliš velký.");
    }
    if (expectedLength !== undefined && value.length !== Math.ceil(expectedLength * 4 / 3)) {
      throw new TypeError("Neplatná délka kryptografických parametrů trezoru.");
    }
    if (!/^[A-Za-z0-9_-]+$/.test(value) || value.length % 4 === 1) {
      throw new TypeError("Neplatný formát šifrovaného trezoru.");
    }
    const padded = value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - value.length % 4) % 4);
    let binary;
    try {
      binary = globalThis.atob(padded);
    } catch {
      throw new TypeError("Neplatný formát šifrovaného trezoru.");
    }
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    if (encodeBase64Url(bytes) !== value) throw new TypeError("Neplatné kódování trezoru.");
    if (expectedLength !== undefined && bytes.length !== expectedLength) {
      throw new TypeError("Neplatná délka kryptografických parametrů trezoru.");
    }
    if (maxLength !== undefined && bytes.length > maxLength) {
      throw new RangeError("Šifrovaný trezor je příliš velký.");
    }
    return bytes;
  }

  function exactKeys(value, expected) {
    return value && typeof value === "object" && !Array.isArray(value) &&
      Object.keys(value).sort().join("|") === expected.slice().sort().join("|");
  }

  function validateEnvelope(envelope) {
    const envelopeKeys = ["format", "version", "kdf", "cipher", "salt", "iv", "ciphertext"];
    if (!exactKeys(envelope, envelopeKeys) || envelope.format !== FORMAT) {
      throw new TypeError("Neplatný formát šifrovaného trezoru.");
    }
    if (envelope.version !== VERSION) throw new TypeError("Nepodporovaná verze trezoru.");
    if (!exactKeys(envelope.kdf, ["name", "hash", "iterations"]) ||
        envelope.kdf.name !== KDF_NAME || envelope.kdf.hash !== KDF_HASH ||
        envelope.kdf.iterations !== KDF_ITERATIONS) {
      throw new TypeError("Nepodporované parametry odvození klíče.");
    }
    if (!exactKeys(envelope.cipher, ["name", "length"]) ||
        envelope.cipher.name !== CIPHER_NAME || envelope.cipher.length !== CIPHER_LENGTH) {
      throw new TypeError("Nepodporované šifrování trezoru.");
    }
    const salt = decodeBase64Url(envelope.salt, SALT_BYTES);
    const iv = decodeBase64Url(envelope.iv, IV_BYTES);
    const ciphertext = decodeBase64Url(envelope.ciphertext, undefined, MAX_PLAINTEXT_BYTES + 16);
    if (ciphertext.length < 16) throw new TypeError("Neplatný šifrovaný obsah trezoru.");
    return { salt, iv, ciphertext };
  }

  function resolveIdleTimeout(options) {
    if (options === undefined) return DEFAULT_IDLE_TIMEOUT_MS;
    if (!options || typeof options !== "object" || Array.isArray(options) ||
        Object.keys(options).some(key => key !== "idleTimeoutMs")) {
      throw new TypeError("Neplatné nastavení automatického uzamčení trezoru.");
    }
    const value = options.idleTimeoutMs === undefined ? DEFAULT_IDLE_TIMEOUT_MS : options.idleTimeoutMs;
    if (!Number.isSafeInteger(value) || value < MIN_IDLE_TIMEOUT_MS || value > MAX_IDLE_TIMEOUT_MS) {
      throw new RangeError("Čas nečinnosti musí být mezi 1 sekundou a 24 hodinami.");
    }
    return value;
  }

  async function deriveKey(passphrase, salt) {
    const material = await globalThis.crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(passphrase),
      KDF_NAME,
      false,
      ["deriveKey"]
    );
    return globalThis.crypto.subtle.deriveKey(
      { name: KDF_NAME, salt, iterations: KDF_ITERATIONS, hash: KDF_HASH },
      material,
      { name: CIPHER_NAME, length: CIPHER_LENGTH },
      false,
      ["encrypt", "decrypt"]
    );
  }

  async function encryptPayload(key, salt, payload) {
    const iv = globalThis.crypto.getRandomValues(new Uint8Array(IV_BYTES));
    const ciphertext = await globalThis.crypto.subtle.encrypt(
      { name: CIPHER_NAME, iv, additionalData: AAD, tagLength: 128 },
      key,
      serialize(payload)
    );
    return {
      format: FORMAT,
      version: VERSION,
      kdf: { name: KDF_NAME, hash: KDF_HASH, iterations: KDF_ITERATIONS },
      cipher: { name: CIPHER_NAME, length: CIPHER_LENGTH },
      salt: encodeBase64Url(salt),
      iv: encodeBase64Url(iv),
      ciphertext: encodeBase64Url(new Uint8Array(ciphertext))
    };
  }

  async function create(passphrase, payload) {
    requireCrypto();
    validatePassphrase(passphrase);
    const salt = globalThis.crypto.getRandomValues(new Uint8Array(SALT_BYTES));
    const key = await deriveKey(passphrase, salt);
    return encryptPayload(key, salt, payload);
  }

  async function unlock(passphrase, envelope, options = {}) {
    requireCrypto();
    validatePassphrase(passphrase);
    const idleTimeoutMs = resolveIdleTimeout(options);
    const parsed = validateEnvelope(envelope);
    const key = await deriveKey(passphrase, parsed.salt);
    let data;
    try {
      const plaintext = await globalThis.crypto.subtle.decrypt(
        { name: CIPHER_NAME, iv: parsed.iv, additionalData: AAD, tagLength: 128 },
        key,
        parsed.ciphertext
      );
      data = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(plaintext));
      serialize(data);
    } catch {
      throw new Error("Heslo nesouhlasí nebo je šifrovaný trezor poškozený.");
    }

    let activeKey = key;
    let activeSalt = parsed.salt;
    let activeData = data;
    let locked = false;
    let idleTimer = null;
    const lockListeners = new Set();

    const lock = () => {
      if (locked) return;
      if (idleTimer !== null) {
        globalThis.clearTimeout(idleTimer);
        idleTimer = null;
      }
      activeData = null;
      activeKey = null;
      activeSalt = null;
      locked = true;
      const listeners = Array.from(lockListeners);
      lockListeners.clear();
      for (const listener of listeners) {
        try { listener(); } catch {}
      }
    };
    const scheduleLock = () => {
      if (idleTimer !== null) globalThis.clearTimeout(idleTimer);
      idleTimer = globalThis.setTimeout(lock, idleTimeoutMs);
    };
    const assertUnlocked = () => {
      if (locked || !activeKey) throw new Error("Offline trezor je uzamčený.");
      scheduleLock();
    };

    scheduleLock();
    return Object.freeze({
      isLocked: () => locked,
      onLock: callback => {
        if (typeof callback !== "function") throw new TypeError("Posluchač uzamčení musí být funkce.");
        if (locked) {
          try { callback(); } catch {}
          return () => {};
        }
        lockListeners.add(callback);
        return () => lockListeners.delete(callback);
      },
      read: () => {
        assertUnlocked();
        return cloneJson(activeData);
      },
      write: nextValue => {
        assertUnlocked();
        activeData = cloneJson(nextValue);
      },
      seal: async () => {
        assertUnlocked();
        const keyAtStart = activeKey;
        const saltAtStart = activeSalt;
        const dataAtStart = cloneJson(activeData);
        const envelope = await encryptPayload(keyAtStart, saltAtStart, dataAtStart);
        if (locked || activeKey !== keyAtStart) throw new Error("Offline trezor je uzamčený.");
        return envelope;
      },
      lock
    });
  }

  globalThis.MicroHelperOfflineVault = Object.freeze({
    create,
    unlock,
    format: FORMAT,
    version: VERSION,
    kdfIterations: KDF_ITERATIONS,
    maxPlaintextBytes: MAX_PLAINTEXT_BYTES,
    defaultIdleTimeoutMs: DEFAULT_IDLE_TIMEOUT_MS
  });
})();
