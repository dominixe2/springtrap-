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
    setAttribute(name, value) {
      this.attributes[name] = value;
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

test("offline auth failure creates an accessible modal and inerts private page", async () => {
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
  const dialog = findById(body, "mh-local-auth-card");
  const retry = dialog?.children.find(child => child.tagName === "BUTTON");

  assert.ok(gate, "offline gate should be visible");
  assert.ok(dialog, "offline dialog should exist");
  assert.equal(dialog.attributes.role, "dialog");
  assert.equal(dialog.attributes["aria-modal"], "true");
  assert.equal(dialog.attributes["aria-labelledby"], "mh-local-auth-offline-title");
  assert.equal(dialog.attributes["aria-describedby"], "mh-local-auth-offline-description");
  assert.equal(header.attributes.inert, "");
  assert.equal(header.attributes["aria-hidden"], "true");
  assert.equal(main.attributes.inert, "");
  assert.equal(main.attributes["aria-hidden"], "true");
  assert.equal(retry?.focused, true, "keyboard focus should move into the lock dialog");
  assert.equal(body.style.overflow, "hidden");
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
