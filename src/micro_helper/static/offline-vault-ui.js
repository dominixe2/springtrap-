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
      vault, storage, fetchImpl, confirmImpl = () => false, promptImpl = () => null,
      downloadImpl = () => {}, reloadImpl = () => {}, lifecycle = null,
      visibility = null, abortControllerFactory = () => new AbortController(),
      documentImpl = globalThis.document, elements = {}
    } = options;
    if (!vault || typeof vault.create !== "function" || typeof vault.unlock !== "function" ||
        !storage || typeof storage.load !== "function" || typeof storage.save !== "function" ||
        typeof fetchImpl !== "function" || typeof abortControllerFactory !== "function") {
      throw new TypeError("Trezor není správně inicializovaný.");
    }

    let storedEnvelope = null;
    let session = null;
    let busy = false;
    let pageHidden = visibility?.visibilityState === "hidden";
    let visibilityEpoch = 0;
    let activeCreateAbortController = null;
    let activeWorkspaceAbortController = null;
    let unsubscribeSessionLock = null;

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

    function clearWorkspace() {
      if (elements.workspace) elements.workspace.hidden = true;
      for (const key of [
        "workspaceSummary", "workspaceMemoryList", "workspacePreferenceList",
        "workspaceHistoryList", "workspaceTaskList", "workspacePlanList"
      ]) {
        if (elements[key]) elements[key].textContent = "";
      }
      for (const key of ["workspaceMemorySelect", "workspacePreferenceSelect"]) {
        if (elements[key] && typeof elements[key].replaceChildren === "function") {
          elements[key].replaceChildren();
        }
      }
      for (const key of [
        "workspaceMemoryText", "workspacePreferenceName", "workspacePreferenceValue"
      ]) {
        if (elements[key]) elements[key].value = "";
      }
    }

    function updateControls() {
      const unlocked = hasUnlockedSession();
      if (elements.create) elements.create.disabled = busy;
      if (elements.unlock) elements.unlock.disabled = busy || !storedEnvelope;
      if (elements.lock) elements.lock.disabled = busy || !unlocked;
      if (elements.restore) elements.restore.disabled = busy || !unlocked;
      if (elements.export) elements.export.disabled = busy || !storedEnvelope;
      if (elements.import) elements.import.disabled = busy;
      if (elements.workspace) elements.workspace.hidden = !unlocked;
      for (const key of [
        "workspaceMemoryText", "workspaceMemoryCategory", "workspaceMemorySave",
        "workspaceMemorySelect", "workspaceMemoryEdit", "workspaceMemoryDelete",
        "workspacePreferenceCategory", "workspacePreferenceName", "workspacePreferenceValue",
        "workspacePreferenceSave", "workspacePreferenceSelect", "workspacePreferenceEdit",
        "workspacePreferenceDelete", "workspaceClearHistory"
      ]) {
        if (elements[key]) elements[key].disabled = busy || !unlocked;
      }
    }

    function replaceSelectOptions(select, records, labelFor) {
      if (!select || typeof select.replaceChildren !== "function" || !documentImpl?.createElement) return;
      const options = [];
      for (const record of records) {
        const option = documentImpl.createElement("option");
        option.value = String(record.id);
        option.textContent = labelFor(record);
        options.push(option);
      }
      select.replaceChildren(...options);
    }

    function renderWorkspace() {
      if (!hasUnlockedSession()) {
        clearWorkspace();
        return false;
      }
      const backup = session.read();
      if (!isBackupPayload(backup)) throw new Error("Obsah offline trezoru nemá podporovaný formát.");
      if (elements.workspace) elements.workspace.hidden = false;
      if (elements.workspaceSummary) {
        const created = typeof backup.created_at === "string" ? backup.created_at : "neznámé datum";
        elements.workspaceSummary.textContent =
          "Místní kopie: " + created +
          ". Změny se ukládají pouze šifrovaně v tomto zařízení; automatická synchronizace se serverem není dostupná.";
      }
      const memories = Array.isArray(backup.memories) ? backup.memories : [];
      const preferences = Array.isArray(backup.preferences) ? backup.preferences : [];
      replaceSelectOptions(elements.workspaceMemorySelect, memories,
        item => "[" + String(item.category || "kontext") + "] " + String(item.content || ""));
      replaceSelectOptions(elements.workspacePreferenceSelect, preferences,
        item => "[" + String(item.category || "ostatní") + "] " +
          String(item.preference || "") + " — " + String(item.value || ""));
      if (elements.workspaceMemoryList) {
        elements.workspaceMemoryList.textContent = memories.length
          ? memories.length + " uložených poznámek v offline kopii."
          : "Offline kopie zatím neobsahuje žádné poznámky.";
      }
      if (elements.workspacePreferenceList) {
        elements.workspacePreferenceList.textContent = preferences.length
          ? preferences.length + " uložených pravidel přizpůsobení."
          : "Offline kopie zatím neobsahuje žádná pravidla.";
      }
      if (elements.workspaceHistoryList) {
        const messages = Array.isArray(backup.messages) ? backup.messages.slice(-50) : [];
        elements.workspaceHistoryList.textContent = messages.length
          ? messages.map(item => (item.role === "user" ? "Ty: " : "Micro Helper: ") + String(item.content || "")).join("\n\n")
          : "Offline kopie neobsahuje historii konverzace.";
      }
      if (elements.workspaceTaskList) {
        const tasks = Array.isArray(backup.tasks) ? backup.tasks : [];
        elements.workspaceTaskList.textContent = tasks.length
          ? tasks.map(item => String(item.title || "Úkol") + " — " + String(item.status || "neznámý stav")).join("\n")
          : "Žádné uložené úkoly.";
      }
      if (elements.workspacePlanList) {
        const plans = Array.isArray(backup.learning_plans) ? backup.learning_plans : [];
        elements.workspacePlanList.textContent = plans.length
          ? plans.map(item => String(item.title || "Plán") + " — " + String(item.status || "aktivní") +
              (item.goal ? "\n" + String(item.goal) : "")).join("\n\n")
          : "Žádné uložené učební plány.";
      }
      return true;
    }

    function handleSessionLock(candidate) {
      if (session !== candidate) return;
      session = null;
      try { activeWorkspaceAbortController?.abort(); } catch {}
      unsubscribeSessionLock = null;
      clearPassphrase();
      clearWorkspace();
      setSummary("Obsah offline trezoru zůstává skrytý, dokud jej znovu neodemkneš.");
      updateControls();
      setStatus("Offline trezor se automaticky uzamkl. Pro další přístup zadej heslo znovu.");
    }

    async function persistWorkspaceChange(mutator, successMessage) {
      if (busy) return false;
      if (pageHidden || !hasUnlockedSession()) {
        setStatus("Offline trezor je uzamčený. Nejdřív jej znovu odemkni.");
        return false;
      }
      const operationVisibilityEpoch = visibilityEpoch;
      const currentSession = session;
      let before = null;
      let operationAbortController = null;
      let committed = false;
      busy = true;
      updateControls();
      try {
        before = currentSession.read();
        const next = JSON.parse(JSON.stringify(before));
        mutator(next);
        next.created_at = new Date().toISOString();
        if (!isBackupPayload(next)) throw new Error("Neplatná offline data.");
        currentSession.write(next);
        operationAbortController = abortControllerFactory();
        if (!operationAbortController || !operationAbortController.signal ||
            typeof operationAbortController.abort !== "function") {
          throw new Error("Přerušení uložení není dostupné.");
        }
        activeWorkspaceAbortController = operationAbortController;
        const envelope = await currentSession.seal();
        if (pageHidden || visibilityEpoch !== operationVisibilityEpoch ||
            session !== currentSession || currentSession.isLocked()) {
          throw new Error("Offline trezor byl během ukládání uzamčen.");
        }
        await storage.save(envelope, {signal: operationAbortController.signal});
        storedEnvelope = envelope;
        committed = true;
        if (pageHidden || visibilityEpoch !== operationVisibilityEpoch ||
            session !== currentSession || currentSession.isLocked()) {
          setStatus("Změna byla uložena před uzamčením. Offline trezor zůstává uzamčený.");
          return true;
        }
        try {
          renderWorkspace();
        } catch {
          lock({silent: true});
          setStatus("Změna byla uložena. Offline trezor se z bezpečnostních důvodů uzamkl.");
          return true;
        }
        setStatus(successMessage + " Změna je pouze v zašifrované offline kopii; se serverem se nesynchronizuje.");
        return true;
      } catch {
        if (committed) {
          setStatus("Změna byla uložena. Offline trezor je uzamčený; odemkni jej znovu.");
          return true;
        }
        if (before && session === currentSession && !currentSession.isLocked()) {
          try { currentSession.write(before); } catch {}
        }
        if (pageHidden || visibilityEpoch !== operationVisibilityEpoch) {
          setStatus("Změna byla přerušena při přechodu aplikace do pozadí. Původní šifrovaná kopie zůstala zachována.");
        } else {
          setStatus("Změnu se nepodařilo uložit. Původní šifrovaná kopie zůstala zachována.");
        }
        return false;
      } finally {
        if (activeWorkspaceAbortController === operationAbortController) {
          activeWorkspaceAbortController = null;
        }
        busy = false;
        updateControls();
      }
    }

    function nextNumericId(items) {
      return items.reduce((maximum, item) =>
        Number.isSafeInteger(item?.id) && item.id > maximum ? item.id : maximum, 0) + 1;
    }

    async function addMemory(content, category = "preference") {
      const value = String(content ?? "").trim();
      const group = String(category ?? "").trim();
      if (!value || value.length > 1000 || !group || group.length > 40) {
        setStatus("Poznámka musí mít 1–1000 znaků a platnou kategorii.");
        return false;
      }
      return persistWorkspaceChange(data => {
        if (data.memories.length >= 1000) throw new Error("Limit offline poznámek byl dosažen.");
        data.memories.push({
          id: nextNumericId(data.memories),
          content: value,
          category: group,
          created_at: new Date().toISOString()
        });
      }, "Poznámka uložena");
    }

    async function editMemory(memoryId) {
      if (!hasUnlockedSession()) return false;
      const item = session.read().memories.find(record => String(record.id) === String(memoryId));
      if (!item) return false;
      const next = promptImpl("Uprav poznámku v offline kopii:", String(item.content || ""));
      if (next === null || next === undefined || !String(next).trim()) return false;
      const value = String(next).trim();
      if (value.length > 1000) {
        setStatus("Poznámka může mít nejvýše 1000 znaků.");
        return false;
      }
      return persistWorkspaceChange(data => {
        const target = data.memories.find(record => String(record.id) === String(memoryId));
        if (!target) throw new Error("Poznámka už v offline kopii neexistuje.");
        target.content = value;
      }, "Poznámka upravena");
    }

    async function deleteMemory(memoryId) {
      if (!hasUnlockedSession()) return false;
      const item = session.read().memories.find(record => String(record.id) === String(memoryId));
      if (!item || !confirmImpl("Smazat tuto poznámku pouze z offline kopie? Serverová data se nezmění.")) return false;
      return persistWorkspaceChange(data => {
        data.memories = data.memories.filter(record => String(record.id) !== String(memoryId));
      }, "Poznámka smazána z offline kopie");
    }

    async function addPreference(category, preference, value) {
      const group = String(category ?? "").trim();
      const name = String(preference ?? "").trim();
      const content = String(value ?? "").trim();
      if (!group || group.length > 40 || !name || name.length > 80 || !content || content.length > 500) {
        setStatus("Preference musí mít platnou oblast, název a hodnotu.");
        return false;
      }
      return persistWorkspaceChange(data => {
        const existing = data.preferences.find(item =>
          item.category === group && item.preference === name);
        const now = new Date().toISOString();
        if (existing) {
          existing.value = content;
          existing.source = "user";
          existing.updated_at = now;
        } else {
          if (data.preferences.length >= 1000) throw new Error("Limit offline preferencí byl dosažen.");
          data.preferences.push({
            id: nextNumericId(data.preferences),
            category: group,
            preference: name,
            value: content,
            source: "user",
            updated_at: now
          });
        }
      }, "Pravidlo přizpůsobení uloženo");
    }

    async function editPreference(preferenceId) {
      if (!hasUnlockedSession()) return false;
      const item = session.read().preferences.find(record => String(record.id) === String(preferenceId));
      if (!item) return false;
      const next = promptImpl("Uprav hodnotu pravidla v offline kopii:", String(item.value || ""));
      if (next === null || next === undefined || !String(next).trim()) return false;
      const value = String(next).trim();
      if (value.length > 500) {
        setStatus("Hodnota preference může mít nejvýše 500 znaků.");
        return false;
      }
      return persistWorkspaceChange(data => {
        const target = data.preferences.find(record => String(record.id) === String(preferenceId));
        if (!target) throw new Error("Preference už v offline kopii neexistuje.");
        target.value = value;
        target.source = "user";
        target.updated_at = new Date().toISOString();
      }, "Pravidlo upraveno");
    }

    async function deletePreference(preferenceId) {
      if (!hasUnlockedSession()) return false;
      const item = session.read().preferences.find(record => String(record.id) === String(preferenceId));
      if (!item || !confirmImpl("Smazat toto pravidlo pouze z offline kopie? Serverová data se nezmění.")) return false;
      return persistWorkspaceChange(data => {
        data.preferences = data.preferences.filter(record => String(record.id) !== String(preferenceId));
      }, "Pravidlo smazáno z offline kopie");
    }

    async function clearHistory() {
      if (!hasUnlockedSession()) return false;
      if (!session.read().messages.length ||
          !confirmImpl("Vymazat historii pouze z offline kopie? Serverová historie se nezmění.")) return false;
      return persistWorkspaceChange(data => { data.messages = []; }, "Offline historie vymazána");
    }

    function lock(options = {}) {
      const current = session;
      session = null;
      if (unsubscribeSessionLock) {
        try { unsubscribeSessionLock(); } catch {}
        unsubscribeSessionLock = null;
      }
      if (current) {
        try { current.lock(); } catch {}
      }
      clearPassphrase();
      clearWorkspace();
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
      if (pageHidden) {
        clearPassphrase();
        setStatus("Trezor lze zálohovat pouze při zobrazené aplikaci.");
        return false;
      }
      const operationVisibilityEpoch = visibilityEpoch;
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
      setStatus("Ověřuji importovaný šifrovaný soubor…");
      let operationAbortController = null;
      try {
        operationAbortController = abortControllerFactory();
        if (!operationAbortController || !operationAbortController.signal ||
            typeof operationAbortController.abort !== "function") {
          throw new Error("abort");
        }
        activeCreateAbortController = operationAbortController;
        const existing = await storage.load();
        if (existing && !confirmImpl(
          "V tomto prohlížeči už šifrovaná záloha existuje. Nahradit ji novou zálohou aktuálních dat?"
        )) {
          setStatus("Nahrazení šifrované zálohy bylo zrušeno.");
          return false;
        }
        if (session) lock({silent: true});
        setStatus("Načítám aktuální zálohu a šifruji ji…");
        const response = await fetchImpl("/v1/backup", {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          signal: operationAbortController.signal
        });
        if (!response.ok) throw new Error("backup");
        const payload = await response.json();
        if (!isBackupPayload(payload)) throw new Error("format");
        if (pageHidden || visibilityEpoch !== operationVisibilityEpoch) {
          setStatus("Šifrování bylo přerušeno přechodem aplikace do pozadí. Záloha nebyla uložena.");
          return false;
        }
        const envelope = await vault.create(passphrase, payload);
        if (pageHidden || visibilityEpoch !== operationVisibilityEpoch) {
          setStatus("Šifrování bylo přerušeno přechodem aplikace do pozadí. Záloha nebyla uložena.");
          return false;
        }
        await storage.save(envelope, {signal: operationAbortController.signal});
        storedEnvelope = envelope;
        if (elements.passphraseConfirm) elements.passphraseConfirm.hidden = true;
        lock({silent: true});
        setSummary("Záloha je zašifrovaná. V IndexedDB je uložen pouze šifrovaný obal.");
        if (pageHidden || visibilityEpoch !== operationVisibilityEpoch) {
          setStatus("Záloha byla uložena před uzamčením aplikace. Trezor zůstává uzamčený.");
          return true;
        }
        setStatus("Šifrovaná záloha byla bezpečně uložena.");
        return true;
      } catch {
        if (pageHidden || visibilityEpoch !== operationVisibilityEpoch) {
          setStatus("Zálohování bylo přerušeno přechodem aplikace do pozadí. Původní šifrovaná záloha zůstala zachována.");
        } else {
          setStatus("Zálohu se nepodařilo zašifrovat nebo uložit. Původní uložený záznam zůstává zachován.");
        }
        return false;
      } finally {
        if (activeCreateAbortController === operationAbortController) {
          activeCreateAbortController = null;
        }
        clearPassphrase();
        busy = false;
        updateControls();
      }
    }

    async function unlock() {
      if (busy) return false;
      if (pageHidden) {
        setStatus("Trezor lze odemknout pouze při zobrazené aplikaci.");
        return false;
      }
      const operationVisibilityEpoch = visibilityEpoch;
      const passphrase = String(elements.passphrase?.value ?? "");
      if (!passphrase) {
        setStatus("Zadej heslo šifrovaného trezoru.");
        return false;
      }
      busy = true;
      updateControls();
      setStatus("Ověřuji heslo šifrovaného trezoru…");
      let candidate = null;
      try {
        const envelope = storedEnvelope || await storage.load();
        if (!envelope) {
          setStatus("V tomto prohlížeči není uložená šifrovaná záloha.");
          return false;
        }
        if (session) lock({silent: true});
        candidate = await vault.unlock(passphrase, envelope);
        if (pageHidden || visibilityEpoch !== operationVisibilityEpoch) {
          candidate.lock();
          candidate = null;
          setSummary("Obsah zálohy zůstává skrytý.");
          setStatus("Trezor zůstal uzamčený, protože aplikace během odemykání přešla do pozadí.");
          return false;
        }
        const backup = candidate.read();
        if (!isBackupPayload(backup)) throw new Error("format");
        session = candidate;
        storedEnvelope = envelope;
        if (typeof candidate.onLock === "function") {
          unsubscribeSessionLock = candidate.onLock(() => handleSessionLock(candidate));
        }
        setSummary(
          "Odemčeno pouze v paměti: " +
          backup.memories.length + " poznámek, " +
          backup.messages.length + " zpráv, " +
          backup.tasks.length + " úkolů, " +
          backup.learning_plans.length + " plánů a " +
          backup.preferences.length + " preferencí."
        );
        if (!renderWorkspace() || !hasUnlockedSession()) {
          setStatus("Trezor se během odemykání uzamkl. Pro další přístup zadej heslo znovu.");
          return false;
        }
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
      setStatus("Předávám obnovu bezpečnostnímu potvrzení…");
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
        storedEnvelope = parsed;
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

    const onVisibilityChange = () => {
      pageHidden = visibility?.visibilityState === "hidden";
      if (pageHidden) {
        visibilityEpoch += 1;
        try { activeCreateAbortController?.abort(); } catch {}
        try { activeWorkspaceAbortController?.abort(); } catch {}
        lock();
      }
    };

    function dispose() {
      visibilityEpoch += 1;
      pageHidden = true;
      try { activeCreateAbortController?.abort(); } catch {}
      try { activeWorkspaceAbortController?.abort(); } catch {}
      lock({silent: true});
      try { storage.close?.(); } catch {}
      try { visibility?.removeEventListener?.("visibilitychange", onVisibilityChange); } catch {}
    }

    if (lifecycle && typeof lifecycle.addEventListener === "function") {
      lifecycle.addEventListener("pagehide", dispose, {once: true});
    }
    if (visibility && typeof visibility.addEventListener === "function") {
      visibility.addEventListener("visibilitychange", onVisibilityChange);
    }

    return Object.freeze({
      refresh,
      createBackup,
      unlock,
      lock,
      restore,
      exportEncrypted,
      importEncryptedFile,
      addMemory,
      editMemory,
      deleteMemory,
      addPreference,
      editPreference,
      deletePreference,
      clearHistory,
      dispose,
      getState: () => Object.freeze({
        hasStoredEnvelope: Boolean(storedEnvelope),
        unlocked: hasUnlockedSession(),
        workspaceVisible: Boolean(elements.workspace && !elements.workspace.hidden),
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
      file: document.getElementById("offlineVaultFile"),
      workspace: document.getElementById("offlineVaultWorkspace"),
      workspaceSummary: document.getElementById("offlineWorkspaceSummary"),
      workspaceMemoryForm: document.getElementById("offlineWorkspaceMemoryForm"),
      workspaceMemoryText: document.getElementById("offlineWorkspaceMemoryText"),
      workspaceMemoryCategory: document.getElementById("offlineWorkspaceMemoryCategory"),
      workspaceMemorySave: document.getElementById("offlineWorkspaceMemorySave"),
      workspaceMemorySelect: document.getElementById("offlineWorkspaceMemorySelect"),
      workspaceMemoryEdit: document.getElementById("offlineWorkspaceMemoryEdit"),
      workspaceMemoryDelete: document.getElementById("offlineWorkspaceMemoryDelete"),
      workspaceMemoryList: document.getElementById("offlineWorkspaceMemoryList"),
      workspacePreferenceForm: document.getElementById("offlineWorkspacePreferenceForm"),
      workspacePreferenceCategory: document.getElementById("offlineWorkspacePreferenceCategory"),
      workspacePreferenceName: document.getElementById("offlineWorkspacePreferenceName"),
      workspacePreferenceValue: document.getElementById("offlineWorkspacePreferenceValue"),
      workspacePreferenceSave: document.getElementById("offlineWorkspacePreferenceSave"),
      workspacePreferenceSelect: document.getElementById("offlineWorkspacePreferenceSelect"),
      workspacePreferenceEdit: document.getElementById("offlineWorkspacePreferenceEdit"),
      workspacePreferenceDelete: document.getElementById("offlineWorkspacePreferenceDelete"),
      workspacePreferenceList: document.getElementById("offlineWorkspacePreferenceList"),
      workspaceHistoryList: document.getElementById("offlineWorkspaceHistoryList"),
      workspaceClearHistory: document.getElementById("offlineWorkspaceClearHistory"),
      workspaceTaskList: document.getElementById("offlineWorkspaceTaskList"),
      workspacePlanList: document.getElementById("offlineWorkspacePlanList")
    };
    const storage = storageApi.createStore();
    const controller = createController({
      vault,
      storage,
      fetchImpl: globalThis.fetch.bind(globalThis),
      confirmImpl: message => globalThis.confirm(message),
      promptImpl: message => globalThis.prompt(message),
      downloadImpl: downloadEncryptedEnvelope,
      reloadImpl: () => globalThis.location.reload(),
      lifecycle: globalThis,
      visibility: globalThis.document,
      documentImpl: globalThis.document,
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
    elements.workspaceMemoryForm?.addEventListener("submit", event => {
      event.preventDefault();
      void controller.addMemory(elements.workspaceMemoryText?.value, elements.workspaceMemoryCategory?.value)
        .then(saved => { if (saved && elements.workspaceMemoryText) elements.workspaceMemoryText.value = ""; });
    });
    elements.workspaceMemoryEdit?.addEventListener("click", () => {
      void controller.editMemory(elements.workspaceMemorySelect?.value);
    });
    elements.workspaceMemoryDelete?.addEventListener("click", () => {
      void controller.deleteMemory(elements.workspaceMemorySelect?.value);
    });
    elements.workspacePreferenceForm?.addEventListener("submit", event => {
      event.preventDefault();
      void controller.addPreference(
        elements.workspacePreferenceCategory?.value,
        elements.workspacePreferenceName?.value,
        elements.workspacePreferenceValue?.value
      ).then(saved => {
        if (saved) {
          if (elements.workspacePreferenceName) elements.workspacePreferenceName.value = "";
          if (elements.workspacePreferenceValue) elements.workspacePreferenceValue.value = "";
        }
      });
    });
    elements.workspacePreferenceEdit?.addEventListener("click", () => {
      void controller.editPreference(elements.workspacePreferenceSelect?.value);
    });
    elements.workspacePreferenceDelete?.addEventListener("click", () => {
      void controller.deletePreference(elements.workspacePreferenceSelect?.value);
    });
    elements.workspaceClearHistory?.addEventListener("click", () => { void controller.clearHistory(); });
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
