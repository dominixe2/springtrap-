/* IndexedDB adapter for encrypted envelopes only; plaintext and keys never enter this module. */
(() => {
  "use strict";

  const DB_NAME = "micro-helper-offline-vault";
  const DB_VERSION = 1;
  const STORE_NAME = "vaults";
  const RECORD_ID = "primary";
  const FORMAT = "micro-helper-offline-vault";
  const VERSION = 1;
  const MAX_PLAINTEXT_BYTES = 8 * 1024 * 1024;
  const MAX_CIPHERTEXT_CHARS = Math.ceil((MAX_PLAINTEXT_BYTES + 16) * 4 / 3);

  function exactKeys(value, expected) {
    return value !== null && typeof value === "object" && !Array.isArray(value) &&
      Object.keys(value).sort().join("|") === expected.slice().sort().join("|");
  }

  function requireBase64Url(value, minLength, maxLength, field) {
    if (typeof value !== "string" || value.length < minLength || value.length > maxLength ||
        value.length % 4 === 1 || !/^[A-Za-z0-9_-]+$/.test(value)) {
      throw new TypeError("Neplatné šifrované úložiště (pole " + field + ").");
    }
  }

  function validateEnvelope(value) {
    if (!exactKeys(value, ["format", "version", "kdf", "cipher", "salt", "iv", "ciphertext"]) ||
        value.format !== FORMAT || value.version !== VERSION) {
      throw new TypeError("Neplatný nebo nepodporovaný obal offline trezoru.");
    }
    if (!exactKeys(value.kdf, ["name", "hash", "iterations"]) ||
        value.kdf.name !== "PBKDF2" || value.kdf.hash !== "SHA-256" || value.kdf.iterations !== 600000) {
      throw new TypeError("Nepodporované parametry odvození klíče offline trezoru.");
    }
    if (!exactKeys(value.cipher, ["name", "length"]) ||
        value.cipher.name !== "AES-GCM" || value.cipher.length !== 256) {
      throw new TypeError("Nepodporované šifrování offline trezoru.");
    }
    requireBase64Url(value.salt, 22, 22, "salt");
    requireBase64Url(value.iv, 16, 16, "iv");
    requireBase64Url(value.ciphertext, 22, MAX_CIPHERTEXT_CHARS, "ciphertext");
    return {
      format: FORMAT,
      version: VERSION,
      kdf: { name: "PBKDF2", hash: "SHA-256", iterations: 600000 },
      cipher: { name: "AES-GCM", length: 256 },
      salt: value.salt,
      iv: value.iv,
      ciphertext: value.ciphertext
    };
  }

  function cloneAndValidateEnvelope(value) {
    let serialized;
    try {
      serialized = JSON.stringify(value);
    } catch {
      throw new TypeError("Obal offline trezoru nelze bezpečně uložit.");
    }
    if (typeof serialized !== "string" || serialized.length > MAX_CIPHERTEXT_CHARS + 512) {
      throw new RangeError("Šifrovaný offline trezor je příliš velký.");
    }
    let parsed;
    try {
      parsed = JSON.parse(serialized);
    } catch {
      throw new TypeError("Obal offline trezoru není platný JSON.");
    }
    return validateEnvelope(parsed);
  }

  function openDatabase(factory) {
    if (!factory || typeof factory.open !== "function") {
      return Promise.reject(new Error("Tento prohlížeč nepodporuje IndexedDB."));
    }
    return new Promise((resolve, reject) => {
      let blocked = false;
      let request;
      try {
        request = factory.open(DB_NAME, DB_VERSION);
      } catch {
        reject(new Error("Šifrované offline úložiště nelze otevřít."));
        return;
      }
      request.onupgradeneeded = () => {
        try {
          const database = request.result;
          if (!database.objectStoreNames.contains(STORE_NAME)) {
            database.createObjectStore(STORE_NAME, { keyPath: "id" });
          }
        } catch {
          reject(new Error("Strukturu šifrovaného offline úložiště nelze vytvořit."));
        }
      };
      request.onblocked = () => {
        blocked = true;
        reject(new Error("Offline úložiště je blokované jinou otevřenou kartou. Zavři starší kartu a zkus to znovu."));
      };
      request.onerror = () => {
        if (!blocked) reject(new Error("Šifrované offline úložiště nelze otevřít."));
      };
      request.onsuccess = () => {
        const database = request.result;
        if (blocked) {
          database.close();
          return;
        }
        resolve(database);
      };
    });
  }

  function createStore(options = {}) {
    if (!options || typeof options !== "object" || Array.isArray(options) ||
        Object.keys(options).some(key => key !== "indexedDB")) {
      throw new TypeError("Neplatná konfigurace offline úložiště.");
    }
    const factory = options.indexedDB === undefined ? globalThis.indexedDB : options.indexedDB;
    let databasePromise = null;

    function getDatabase() {
      if (!databasePromise) {
        const pending = openDatabase(factory).then(database => {
          database.onversionchange = () => {
            database.close();
            if (databasePromise === pending) databasePromise = null;
          };
          return database;
        }).catch(error => {
          if (databasePromise === pending) databasePromise = null;
          throw error;
        });
        databasePromise = pending;
      }
      return databasePromise;
    }

    async function load() {
      const database = await getDatabase();
      return new Promise((resolve, reject) => {
        let record = null;
        let settled = false;
        const fail = () => {
          if (settled) return;
          settled = true;
          reject(new Error("Šifrovaná data offline trezoru se nepodařilo načíst."));
        };
        let transaction;
        try {
          transaction = database.transaction(STORE_NAME, "readonly");
          transaction.oncomplete = () => {
            if (settled) return;
            settled = true;
            try {
              if (record === null || record === undefined) {
                resolve(null);
                return;
              }
              if (!exactKeys(record, ["id", "envelope"]) || record.id !== RECORD_ID) {
                throw new TypeError("Neplatný záznam offline trezoru.");
              }
              resolve(cloneAndValidateEnvelope(record.envelope));
            } catch {
              reject(new Error("Uložený offline trezor je poškozený nebo nepodporovaný; původní data nebyla změněna."));
            }
          };
          transaction.onerror = fail;
          transaction.onabort = fail;
          const request = transaction.objectStore(STORE_NAME).get(RECORD_ID);
          request.onsuccess = () => { record = request.result; };
          request.onerror = fail;
        } catch {
          fail();
        }
      });
    }

    async function save(envelope) {
      const safeEnvelope = cloneAndValidateEnvelope(envelope);
      const database = await getDatabase();
      return new Promise((resolve, reject) => {
        let settled = false;
        const fail = () => {
          if (settled) return;
          settled = true;
          reject(new Error("Šifrovaný offline trezor se nepodařilo bezpečně uložit."));
        };
        try {
          const transaction = database.transaction(STORE_NAME, "readwrite");
          transaction.oncomplete = () => {
            if (settled) return;
            settled = true;
            resolve();
          };
          transaction.onerror = fail;
          transaction.onabort = fail;
          const request = transaction.objectStore(STORE_NAME).put({
            id: RECORD_ID,
            envelope: safeEnvelope
          });
          request.onerror = fail;
        } catch {
          fail();
        }
      });
    }

    function close() {
      const current = databasePromise;
      databasePromise = null;
      if (current) current.then(database => database.close()).catch(() => {});
    }

    return Object.freeze({ load, save, close });
  }

  globalThis.MicroHelperOfflineVaultStorage = Object.freeze({
    createStore,
    format: FORMAT,
    version: VERSION
  });
})();
