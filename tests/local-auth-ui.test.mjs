import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import test from "node:test";

function makeElement(tagName) {
  return {
    tagName: tagName.toUpperCase(),
    children: [],
    attributes: {},
    listeners: {},
    style: {},
    textContent: "",
    id: "",
    append(...nodes) {
      this.children.push(...nodes);
    },
    insertBefore(node, reference) {
      const index = this.children.indexOf(reference);
      if (index < 0) this.children.push(node);
      else this.children.splice(index, 0, node);
    },
    setAttribute(name, value) {
      this.attributes[name] = value;
    },
    removeAttribute(name) {
      delete this.attributes[name];
    },
    addEventListener(name, callback) {
      this.listeners[name] = callback;
    },
    focus() {
      this.focused = true;
    },
  };
}

function findById(root, id) {
  if (root.id === id) return root;
  for (const child of root.children || []) {
    const match = findById(child, id);
    if (match) return match;
  }
  return null;
}

test("offline auth failure leaves only the encrypted vault accessible", async () => {
  const main = makeElement("main");
  const header = makeElement("header");
  const chat = makeElement("section");
  const offlineAccess = makeElement("section");
  offlineAccess.id = "offlineVaultAccess";
  main.append(header, chat, offlineAccess);
  const body = makeElement("body");
  body.append(main);
  const head = makeElement("head");

  const document = {
    readyState: "complete",
    body,
    head,
    createElement: makeElement,
    querySelector(selector) {
      if (selector === "main") return main;
      if (selector === "header") return header;
      return null;
    },
    getElementById(id) {
      return findById(body, id);
    },
    addEventListener() {},
  };
  const window = {
    async fetch() {
      throw new Error("simulated offline network");
    },
    location: { reload() {} },
  };

  const source = await readFile(
    new URL("../src/micro_helper/static/local-auth.js", import.meta.url),
    "utf8",
  );
  vm.runInNewContext(source, { document, window, URL });
  await new Promise(resolve => setImmediate(resolve));

  const gate = findById(body, "mh-local-auth-gate");
  const card = findById(body, "mh-local-auth-card");
  const retry = card?.children.find(child => child.tagName === "BUTTON");

  assert.ok(gate, "offline status banner should be visible");
  assert.equal(gate.attributes.role, "status");
  assert.equal(gate.attributes["aria-live"], "polite");
  assert.equal(card.attributes.role, undefined, "the offline notice is not a login dialog");
  assert.equal(card.attributes["aria-modal"], undefined);
  assert.equal(header.attributes.inert, "");
  assert.equal(header.attributes["aria-hidden"], "true");
  assert.equal(chat.attributes.inert, "");
  assert.equal(chat.attributes["aria-hidden"], "true");
  assert.equal(main.attributes.inert, undefined);
  assert.equal(offlineAccess.attributes.inert, undefined);
  assert.equal(offlineAccess.attributes["aria-hidden"], undefined);
  assert.equal(retry?.focused, true);
  assert.equal(body.style.overflow, "");
});


test("setup and login gates expose an accessible modal and isolate the private page", async () => {
  for (const configured of [false, true]) {
    const header = makeElement("header");
    const main = makeElement("main");
    const body = makeElement("body");
    body.append(header, main);
    const head = makeElement("head");
    const document = {
      readyState: "complete",
      body,
      head,
      createElement: makeElement,
      querySelector(selector) {
        return selector === "header" ? header : null;
      },
      getElementById(id) {
        return findById(body, id);
      },
      addEventListener() {},
    };
    const window = { location: { reload() {} } };
    const fetch = async () => ({
      ok: true,
      async json() {
        return { configured, authenticated: false };
      },
    });
    const source = await readFile(
      new URL("../src/micro_helper/static/local-auth.js", import.meta.url),
      "utf8",
    );

    vm.runInNewContext(source, { document, window, URL, fetch });
    await new Promise(resolve => setImmediate(resolve));

    const gate = findById(body, "mh-local-auth-gate");
    const dialog = findById(body, "mh-local-auth-card");
    const title = findById(body, "mh-local-auth-title");
    const description = findById(body, "mh-local-auth-description");
    const form = dialog?.children.find(child => child.tagName === "FORM");
    const password = form?.children[0];

    assert.ok(gate, "authentication gate should be visible");
    assert.equal(dialog?.attributes.role, "dialog");
    assert.equal(dialog?.attributes["aria-modal"], "true");
    assert.equal(dialog?.attributes["aria-labelledby"], "mh-local-auth-title");
    assert.equal(dialog?.attributes["aria-describedby"], "mh-local-auth-description");
    assert.equal(title?.textContent, configured ? "Přihlášení do Micro Helperu" : "Zabezpečení Micro Helperu");
    assert.ok(description?.textContent);
    assert.equal(header.attributes.inert, "");
    assert.equal(header.attributes["aria-hidden"], "true");
    assert.equal(main.attributes.inert, "");
    assert.equal(main.attributes["aria-hidden"], "true");
    assert.equal(password?.focused, true, "keyboard focus should move to the password field");
    assert.equal(body.style.overflow, "hidden");
  }
});
