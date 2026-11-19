/* User-facing encrypted backup vault. It stores only authenticated ciphertext in IndexedDB. */
(() => {
  "use strict";

  const BACKUP_KEYS = [
    "format", "version", "created_at", "profile", "memories",
    "messages", "tasks", "learning_plans", "preferences"
  ];
  const MAX_IMPORT_BYTES = 12 * 1024 * 1024;

  function isBackupPayload(value) {
    return Boolean(
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      Object.keys(value).sort().join("|") === BACKUP_KEYS.slice().sort().join("|") &&
      value.format === "micro-helper-backup" &&
      value.version === 1 &&
      typeof value.created_at === "string" &&
      value.profile &&
      typeof value.profile === "object" &&
      !Array.isArray(value.profile) &&
      ["memories", "messages", "tasks", "learning_plans", "preferences"]
        .every(key => Array.isArray(value[key]))
    );
  }

  function createController(options) {
    if (!options || typeof options !== "object") throw new TypeError("Chybí konfigurace trezoru.");
    const {
      vault, storage, fetchImpl, confirmImpl = () => false,
      downloadImpl = () => {}, reloadImpl = () => {}, lifecycle = null,
      elements = {}
    } = options;
    if (!vault || typeof vault.create !== "function" || typeof vault.unlock !== "function" ||
        !storage || typeof storage.load !== "function" || typeof storage.save !== "function" ||
        typeof fetchImpl !== "function") {
      throw new TypeError("Trezor není správně inicializovaný.");
    }

    let storedEnvelope = null;
    let session = null;
    let busy = false;

    const setStatus = value => {
      if (elements.status) elements.status.textContent = value;
    };
    const setSummary = value => {
      if (elements.summary) elements.summary.textContent = value;
    };
    const clearPassphrase = () => {
      if (elements.passphrase) elements.passphrase.value = "";
      if (elements.passphraseConfirm) elements.passphraseConfirm.value = "";
    };
    const hasUnlockedSession = () => Boolean(session && !session.isLocked());

    function updateControls() {
      if (elements.create) elements.create.disabled = busy;
      if (elements.unlock) elements.unlock.disabled = busy || !storedEnvelope;
      if (elements.lock) elements.lock.disabled = busy || !hasUnlockedSession();
      if (elements.restore) elements.restore.disabled = busy || !hasUnlockedSession();
      if (elements.export) elements.export.disabled = busy || !storedEnvelope;
      if (elements.import) elements.import.disabled = busy;
    }

    function lock(options = {}) {
      if (session) {
        try { session.lock(); } catch {}
      }
      session = null;
      clearPassphrase();
      if (elements.summary && options.keepSummary !== true) {
        setSummary("Obsah zálohy zůstává skrytý, dokud trezor znovu neodemkneš.");
      }
      updateControls();
      if (options.silent !== true) setStatus("Šifrovaný trezor je uzamčený.");
    }

    async function refresh() {
      try {
        storedEnvelope = await storage.load();
        if (elements.passphraseConfirm) elements.passphraseConfirm.hidden = Boolean(storedEnvelope);
        if (storedEnvelope) {
          setStatus("Šifrovaná záloha je uložená v tomto prohlížeči.");
          setSummary("Odemkni trezor heslem. Soukromý obsah se zatím nenačítá.");
        } else {
          setStatus("Šifrovaný trezor zatím není vytvořen.");
          setSummary("Vytvoř šifrovanou kopii aktuální zálohy Micro Helperu.");
        }
      } catch {
        storedEnvelope = null;
        setStatus("Šifrované úložiště není dostupné. Původní záznam nebyl změněn.");
        setSummary("Zkontroluj podporu IndexedDB a zda není úložiště blokované jinou kartou.");
      }
      updateControls();
      return Boolean(storedEnvelope);
    }

    async function createBackup() {
      if (busy) return false;
      const passphrase = String(elements.passphrase?.value ?? "");
      if (passphrase.length < 12) {
        clearPassphrase();
        setStatus("Heslo trezoru musí mít alespoň 12 znaků.");
        return false;
      }
      if (elements.passphraseConfirm) {
        if (elements.passphraseConfirm.hidden) {
          elements.passphraseConfirm.hidden = false;
          elements.passphraseConfirm.focus?.();
          setStatus("Pro vytvoření nové zálohy zadej stejné heslo ještě jednou.");
          return false;
        }
        if (String(elements.passphraseConfirm.value ?? "") !== passphrase) {
          clearPassphrase();
          setStatus("Hesla se neshodují. Zadej je znovu.");
          return false;
        }
      }
      busy = true;
      updateControls();
      try {
        const existing = await storage.load();
        if (existing && !confirmImpl(
          "V tomto prohlížeči už šifrovaná záloha existuje. Nahradit ji novou zálohou aktuálních dat?"
        )) {
          setStatus("Nahrazení šifrované zálohy bylo zrušeno.");
          return false;
        }
        const response = await fetchImpl("/v1/backup", {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store"
        });
        if (!response.ok) throw new Error("backup");
        const payload = await response.json();
        if (!isBackupPayload(payload)) throw new Error("format");
        const envelope = await vault.create(passphrase, payload);
        await storage.save(envelope);
        storedEnvelope = envelope;
        if (elements.passphraseConfirm) elements.passphraseConfirm.hidden = true;
        lock({silent: true});
        setSummary("Záloha je zašifrovaná. V IndexedDB je uložen pouze šifrovaný obal.");
        setStatus("Šifrovaná záloha byla bezpečně uložena.");
        return true;
      } catch {
        setStatus("Zálohu se nepodařilo zašifrovat nebo uložit. Původní uložený záznam zůstává zachován.");
        return false;
      } finally {
        clearPassphrase();
        busy = false;
        updateControls();
      }
    }

    async function unlock() {
      if (busy) return false;
      const passphrase = String(elements.passphrase?.value ?? "");
      if (!passphrase) {
        setStatus("Zadej heslo šifrovaného trezoru.");
        return false;
      }
      busy = true;
      updateControls();
      let candidate = null;
      try {
        const envelope = storedEnvelope || await storage.load();
        if (!envelope) {
          setStatus("V tomto prohlížeči není uložená šifrovaná záloha.");
          return false;
        }
        candidate = await vault.unlock(passphrase, envelope);
        const backup = candidate.read();
        if (!isBackupPayload(backup)) throw new Error("format");
        session = candidate;
        storedEnvelope = envelope;
        setSummary(
          "Odemčeno pouze v paměti: " +
          backup.memories.length + " poznámek, " +
          backup.messages.length + " zpráv, " +
          backup.tasks.length + " úkolů, " +
          backup.learning_plans.length + " plánů a " +
          backup.preferences.length + " preferencí. Obsah není zobrazen."
        );
        setStatus("Trezor odemčen. Po 5 minutách nečinnosti se automaticky uzamkne.");
        return true;
      } catch {
        if (candidate) {
          try { candidate.lock(); } catch {}
        }
        session = null;
        setSummary("Obsah zálohy zůstává skrytý.");
        setStatus("Heslo nesouhlasí nebo je šifrovaná záloha poškozená.");
        return false;
      } finally {
        clearPassphrase();
        busy = false;
        updateControls();
      }
    }

    async function restore() {
      if (busy) return false;
      if (!hasUnlockedSession()) {
        lock({silent: true});
        setStatus("Trezor je uzamčený. Nejdřív jej znovu odemkni.");
        return false;
      }
      busy = true;
      updateControls();
      try {
        const backup = session.read();
        if (!isBackupPayload(backup)) throw new Error("format");
        // The page's shared fetch policy wrapper displays the exact restore action,
        // obtains the one-time body-bound confirmation, and only then sends this request.
        const response = await fetchImpl("/v1/backup/restore", {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ backup, confirm_replace: true })
        });
        if (!response.ok) throw new Error("restore");
        lock({silent: true});
        setStatus("Záloha obnovena. Obnovuji aplikaci…");
        reloadImpl();
        return true;
      } catch {
        setStatus("Obnova se nepodařila. Stávající data nebyla potvrzeně nahrazena.");
        return false;
      } finally {
        busy = false;
        updateControls();
      }
    }

    async function exportEncrypted() {
      if (busy) return false;
      try {
        const envelope = await storage.load();
        if (!envelope) {
          setStatus("Nejdřív vytvoř nebo importuj šifrovanou zálohu.");
          return false;
        }
        downloadImpl(envelope, "micro-helper-encrypted-backup.json");
        setStatus("Exportován byl pouze šifrovaný soubor, nikoli otevřená data.");
        return true;
      } catch {
        setStatus("Šifrovanou zálohu se nepodařilo exportovat.");
        return false;
      }
    }

    async function importEncryptedFile(file) {
      if (busy || !file) return false;
      if (!Number.isSafeInteger(file.size) || file.size <= 0 || file.size > MAX_IMPORT_BYTES) {
        setStatus("Šifrovaný soubor je prázdný nebo přesahuje limit 12 MiB.");
        return false;
      }
      busy = true;
      updateControls();
      try {
        const existing = await storage.load();
        if (existing && !confirmImpl(
          "Import nahradí šifrovanou zálohu uloženou v tomto prohlížeči. Pokračovat?"
        )) {
          setStatus("Import šifrované zálohy byl zrušen.");
          return false;
        }
        const parsed = JSON.parse(await file.text());
        if (session) lock({silent: true});
        await storage.save(parsed);
        storedEnvelope = await storage.load();
        if (elements.passphraseConfirm) elements.passphraseConfirm.hidden = true;
        setSummary("Šifrovaný soubor byl uložen. Pro zobrazení souhrnu jej odemkni heslem.");
        setStatus("Šifrovaná záloha byla importována.");
        return true;
      } catch {
        setStatus("Soubor není platná podporovaná šifrovaná záloha. Původní záznam nebyl změněn.");
        return false;
      } finally {
        busy = false;
        updateControls();
      }
    }

    function dispose() {
      lock({silent: true});
      try { storage.close?.(); } catch {}
    }

    if (lifecycle && typeof lifecycle.addEventListener === "function") {
      lifecycle.addEventListener("pagehide", dispose, {once: true});
    }

    return Object.freeze({
      refresh,
      createBackup,
      unlock,
      lock,
      restore,
      exportEncrypted,
      importEncryptedFile,
      dispose,
      getState: () => Object.freeze({
        hasStoredEnvelope: Boolean(storedEnvelope),
        unlocked: hasUnlockedSession(),
        busy
      })
    });
  }

  function downloadEncryptedEnvelope(envelope, filename) {
    const blob = new Blob([JSON.stringify(envelope)], {type: "application/json"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function initializePage() {
    const panel = document.getElementById("offlineVaultPanel");
    if (!panel) return;
    const vault = globalThis.MicroHelperOfflineVault;
    const storageApi = globalThis.MicroHelperOfflineVaultStorage;
    if (!vault || !storageApi) {
      const status = document.getElementById("offlineVaultStatus");
      if (status) status.textContent = "Šifrovaný trezor není načten. Obnov stránku online.";
      return;
    }
    const elements = {
      passphrase: document.getElementById("offlineVaultPassphrase"),
      passphraseConfirm: document.getElementById("offlineVaultPassphraseConfirm"),
      status: document.getElementById("offlineVaultStatus"),
      summary: document.getElementById("offlineVaultSummary"),
      create: document.getElementById("offlineVaultCreate"),
      unlock: document.getElementById("offlineVaultUnlock"),
      lock: document.getElementById("offlineVaultLock"),
      restore: document.getElementById("offlineVaultRestore"),
      export: document.getElementById("offlineVaultExport"),
      import: document.getElementById("offlineVaultImport"),
      file: document.getElementById("offlineVaultFile")
    };
    const storage = storageApi.createStore();
    const controller = createController({
      vault,
      storage,
      fetchImpl: globalThis.fetch.bind(globalThis),
      confirmImpl: message => globalThis.confirm(message),
      downloadImpl: downloadEncryptedEnvelope,
      reloadImpl: () => globalThis.location.reload(),
      lifecycle: globalThis,
      elements
    });
    elements.create?.addEventListener("click", () => { void controller.createBackup(); });
    elements.unlock?.addEventListener("click", () => { void controller.unlock(); });
    elements.lock?.addEventListener("click", () => controller.lock());
    elements.restore?.addEventListener("click", () => { void controller.restore(); });
    elements.export?.addEventListener("click", () => { void controller.exportEncrypted(); });
    elements.import?.addEventListener("click", () => elements.file?.click());
    elements.file?.addEventListener("change", event => {
      const input = event.currentTarget;
      const file = input?.files?.[0];
      void controller.importEncryptedFile(file).finally(() => {
        if (input) input.value = "";
      });
    });
    void controller.refresh();
  }

  globalThis.MicroHelperOfflineVaultUI = Object.freeze({
    createController,
    isBackupPayload
  });

  if (globalThis.document) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initializePage, {once: true});
    } else {
      initializePage();
    }
  }
})();
