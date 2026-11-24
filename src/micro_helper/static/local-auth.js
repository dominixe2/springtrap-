/* Local single-user session gate. JavaScript never reads or writes the HttpOnly session cookie. */
(() => {
  const endpoint = "/v1/auth";

  function addStyles() {
    const style = document.createElement("style");
    style.textContent = [
      "#mh-local-auth-gate{position:fixed;inset:0;z-index:99999;display:grid;place-items:center;padding:18px;background:rgba(3,8,18,.96);backdrop-filter:blur(12px)}",
      "#mh-local-auth-card{width:min(440px,100%);padding:24px;border:1px solid #2d4964;border-radius:20px;background:#121b2e;box-shadow:0 20px 80px #0009}",
      "#mh-local-auth-card h2{margin:0 0 8px;font-size:22px;color:#edf4ff}",
      "#mh-local-auth-card p,#mh-local-auth-card small{color:#a9bad1;line-height:1.5}",
      "#mh-local-auth-card form{display:grid;gap:10px;margin-top:18px}",
      "#mh-local-auth-card input{width:100%;min-width:0;padding:12px;border:1px solid #344866;border-radius:10px;background:#0b1425;color:#fff;font:inherit}",
      "#mh-local-auth-card button{padding:12px;border:1px solid #328e80;border-radius:10px;background:#23695f;color:#fff;font:inherit;font-weight:650;cursor:pointer}",
      "#mh-local-auth-error{min-height:1.4em;color:#ffb4a8;font-size:13px}",
      "#mh-local-auth-logout{margin-left:8px;padding:6px 10px;border:1px solid #344866;border-radius:9px;background:#18263b;color:#edf4ff;font:inherit;font-size:12px;cursor:pointer}",
      "#mh-local-auth-offline{margin:8px 0;padding:10px 12px;border:1px solid #6a5734;border-radius:10px;color:#f0d9a6;background:#302719;font-size:13px}",
      "#mh-local-auth-gate.mh-offline-banner{position:sticky;inset:auto;z-index:99999;display:block;padding:10px 12px;background:#302719;border-bottom:1px solid #6a5734;color:#f0d9a6;backdrop-filter:none}",
      "#mh-local-auth-gate.mh-offline-banner #mh-local-auth-card{width:min(900px,100%);margin:0 auto;padding:10px 14px;box-shadow:none;display:flex;flex-wrap:wrap;align-items:center;gap:8px}",
      "#mh-local-auth-gate.mh-offline-banner h2{font-size:15px;margin:0}",
      "#mh-local-auth-gate.mh-offline-banner p{margin:0;flex:1}",
      "#mh-local-auth-gate.mh-offline-banner small{display:block;width:100%}"
    ].join("");
    document.head.append(style);
  }

  function isolateBackground(gate) {
    for (const child of document.body.children) {
      if (child !== gate) {
        child.setAttribute("inert", "");
        child.setAttribute("aria-hidden", "true");
      }
    }
    document.body.style.overflow = "hidden";
  }

  function isolateOfflinePage(gate) {
    const main = document.querySelector("main");
    const offlineAccess = document.getElementById("offlineVaultAccess");
    if (!main || !offlineAccess || !Array.from(main.children).includes(offlineAccess)) return false;
    for (const child of document.body.children) {
      if (child !== gate && child !== main) {
        child.setAttribute("inert", "");
        child.setAttribute("aria-hidden", "true");
      }
    }
    for (const child of main.children) {
      if (child === offlineAccess) {
        child.removeAttribute("inert");
        child.removeAttribute("aria-hidden");
      } else {
        child.setAttribute("inert", "");
        child.setAttribute("aria-hidden", "true");
      }
    }
    document.body.style.overflow = "";
    return true;
  }

  function showGate(configured) {
    if (document.getElementById("mh-local-auth-gate")) return;
    const gate = document.createElement("div");
    gate.id = "mh-local-auth-gate";
    const card = document.createElement("section");
    card.id = "mh-local-auth-card";
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "true");
    const title = document.createElement("h2");
    title.id = "mh-local-auth-title";
    title.textContent = configured ? "Přihlášení do Micro Helperu" : "Zabezpečení Micro Helperu";
    const description = document.createElement("p");
    description.id = "mh-local-auth-description";
    card.setAttribute("aria-labelledby", "mh-local-auth-title");
    card.setAttribute("aria-describedby", "mh-local-auth-description");
    description.textContent = configured
      ? "Tato místní instance je chráněná heslem. Relace se drží v HttpOnly cookie a po 12 hodinách vyprší."
      : "Při prvním spuštění si nastav místní heslo. Musí mít alespoň 12 znaků. Ukládá se pouze jeho odvozený hash.";
    const form = document.createElement("form");
    const password = document.createElement("input");
    password.type = "password";
    password.name = "password";
    password.autocomplete = configured ? "current-password" : "new-password";
    password.minLength = configured ? 1 : 12;
    password.maxLength = 128;
    password.required = true;
    password.placeholder = configured ? "Místní heslo" : "Nové heslo (min. 12 znaků)";
    form.append(password);
    let confirmation = null;
    if (!configured) {
      confirmation = document.createElement("input");
      confirmation.type = "password";
      confirmation.name = "password-confirm";
      confirmation.autocomplete = "new-password";
      confirmation.minLength = 12;
      confirmation.maxLength = 128;
      confirmation.required = true;
      confirmation.placeholder = "Zopakuj heslo";
      form.append(confirmation);
    }
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.textContent = configured ? "Přihlásit" : "Nastavit heslo";
    const error = document.createElement("div");
    error.id = "mh-local-auth-error";
    error.setAttribute("role", "alert");
    const note = document.createElement("small");
    note.textContent = (configured ? "Obnovení místního hesla zatím není dostupné. " : "Po nastavení hesla zatím není dostupné jeho obnovení. ") + "Heslo ani relace se neukládají do localStorage nebo sessionStorage. Místní API musí zůstat dostupné pouze přes loopback.";
    form.append(submit, error);
    card.append(title, description, form, note);
    gate.append(card);
    document.body.append(gate);
    isolateBackground(gate);

    form.addEventListener("submit", async event => {
      event.preventDefault();
      error.textContent = "";
      if (confirmation && password.value !== confirmation.value) {
        error.textContent = "Hesla se neshodují.";
        return;
      }
      submit.disabled = true;
      try {
        const response = await fetch(endpoint + (configured ? "/login" : "/setup"), {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({password: password.value})
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || "Přihlášení se nepodařilo.");
        password.value = "";
        if (confirmation) confirmation.value = "";
        window.location.reload();
      } catch (failure) {
        error.textContent = failure instanceof Error ? failure.message : "Přihlášení se nepodařilo.";
      } finally {
        submit.disabled = false;
      }
    });
    password.focus();
  }

  function showOfflineLock() {
    if (document.getElementById("mh-local-auth-gate")) return;
    const gate = document.createElement("div");
    gate.id = "mh-local-auth-gate";
    const card = document.createElement("section");
    card.id = "mh-local-auth-card";
    card.setAttribute("aria-labelledby", "mh-local-auth-offline-title");
    card.setAttribute("aria-describedby", "mh-local-auth-offline-description");
    const title = document.createElement("h2");
    title.id = "mh-local-auth-offline-title";
    title.textContent = "Offline režim — serverová data jsou uzamčená";
    const description = document.createElement("p");
    description.id = "mh-local-auth-offline-description";
    description.textContent = "Místní API není dostupné, proto nelze ověřit přihlášení. Běžný chat a serverová soukromá data zůstávají uzamčené. Samostatně můžeš otevřít pouze šifrovanou offline kopii.";
    const note = document.createElement("small");
    note.textContent = "Offline kopie vyžaduje vlastní heslo. Změny se ukládají jen do tohoto prohlížeče a automaticky se nesynchronizují.";
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Znovu ověřit přihlášení";
    retry.addEventListener("click", () => window.location.reload());
    card.append(title, description, note, retry);
    gate.className = "mh-offline-banner";
    gate.setAttribute("role", "status");
    gate.setAttribute("aria-live", "polite");
    gate.append(card);
    const main = document.querySelector("main");
    if (main && typeof document.body.insertBefore === "function") {
      document.body.insertBefore(gate, main);
    } else {
      document.body.append(gate);
    }
    if (!isolateOfflinePage(gate)) {
      gate.className = "";
      card.setAttribute("role", "dialog");
      card.setAttribute("aria-modal", "true");
      isolateBackground(gate);
    }
    retry.focus();
  }

  function addLogout() {
    const header = document.querySelector("header");
    if (!header || document.getElementById("mh-local-auth-logout")) return;
    const button = document.createElement("button");
    button.id = "mh-local-auth-logout";
    button.type = "button";
    button.textContent = "Odhlásit";
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        await fetch(endpoint + "/logout", {
          method: "POST",
          credentials: "same-origin",
          cache: "no-store",
          headers: {"Content-Type": "application/json"},
          body: "{}"
        });
      } finally {
        window.location.reload();
      }
    });
    header.append(button);
  }

  async function init() {
    addStyles();
    try {
      const response = await fetch(endpoint + "/status", {
        credentials: "same-origin",
        cache: "no-store"
      });
      if (!response.ok) throw new Error("auth status unavailable");
      const state = await response.json();
      if (state.authenticated) {
        addLogout();
        return;
      }
      showGate(Boolean(state.configured));
    } catch {
      showOfflineLock();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, {once: true});
  } else {
    void init();
  }
})();
