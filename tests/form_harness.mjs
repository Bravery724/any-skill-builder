/**
 * Exercise the shipped offline form in a deterministic DOM/event environment.
 * Models field identity, caret position, composition events, and download payloads.
 * Real browser layout, file dialogs, and native OS input methods need separate checks.
 */
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source = await fs.readFile(new URL('../any-skill-builder/assets/form.js', import.meta.url), 'utf8');
const template = await fs.readFile(new URL('../any-skill-builder/assets/form.html', import.meta.url), 'utf8');
const css = await fs.readFile(new URL('../any-skill-builder/assets/form.css', import.meta.url), 'utf8');
export const catalog = JSON.parse(await fs.readFile(new URL('../any-skill-builder/assets/locales.json', import.meta.url), 'utf8'));
export const copy = value => JSON.parse(JSON.stringify(value));
export const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

export function makeBoot(language = 'en') {
  const questionnaire = {
    schema_version: 1, run_id: 'form-regression', project_id: 'form-regression', revision: 1, mode: 'questionnaire',
    goal: 'Create a reusable project update skill.',
    groups: [{ id: 'first', label: 'Scope' }, { id: 'second', label: 'Details' }], sources: [],
    questions: [
      { id: 'gate', version: 1, group_id: 'first', type: 'multi', title: 'Choose a workflow', importance: 'core', when: [],
        options: ['a', 'b', 'c'].map(id => ({ id, label: id, effect: id })) },
      { id: 'text', version: 1, group_id: 'first', type: 'text', title: 'Describe the topic', max_length: 20000,
        when: [{ question_id: 'gate', includes: 'a' }] },
      { id: 'other', version: 1, group_id: 'first', type: 'single', title: 'Choose an output', when: [],
        options: ['a', 'b'].map(id => ({ id, label: id, effect: id })) },
      { id: 'last', version: 1, group_id: 'second', type: 'text', title: 'Additional details', when: [] },
    ],
  };
  const answer = value => ({ status: 'answered', actor: 'user', question_version: 1, rationale: '', value });
  return {
    format: 'any-skill-builder-questionnaire', format_version: 1, saved_at: null, export_id: null,
    base_answer_revision: 1, questionnaire_sha256: 'a'.repeat(64), assets: {}, drafts: {},
    resume: { workspace: '/example/run', html_path: '/example/run/questionnaire.html', run_id: questionnaire.run_id, project_id: questionnaire.project_id },
    locale: { language, direction: 'ltr', messages: catalog[language] || catalog.en },
    view: { questionnaire, answers: {
      schema_version: 1, run_id: questionnaire.run_id, project_id: questionnaire.project_id, revision: 1, answer_revision: 1,
      answers: { gate: answer(['a', 'b']), text: answer('Initial answer'), other: answer('a'), last: answer('Initial details') }, history: [],
    } },
  };
}

export function renderFixture(boot) {
  const escaped = JSON.stringify(boot).replace(/&/g, '\\u0026').replace(/</g, '\\u003c').replace(/>/g, '\\u003e');
  return template.replace(/\{\{(t:[A-Za-z_]+|locale\.(?:language|direction))\}\}/g, (_, marker) => marker.startsWith('t:') ? boot.locale.messages[marker.slice(2)] : boot.locale[marker.slice(7)])
    .replace('<!--INLINE_CSS-->', `<style>${css}</style>`)
    .replace('<!--BOOT_JSON-->', `<script id="skill-builder-data" type="application/json">${escaped}</script>`)
    .replace('<!--INLINE_JS-->', `<script>${source}</script>`);
}

export async function downloadedBoot(blob) {
  const html = await blob.text();
  const match = html.match(/<script id="skill-builder-data" type="application\/json">([\s\S]*?)<\/script>/);
  assert.ok(match, 'Saved HTML must contain its data script');
  return { html, boot: JSON.parse(match[1]) };
}

export function setup(boot = makeBoot(), storage = new Map()) {
  let document;
  const downloads = [], blobs = new Map(), timers = new Set(), requests = [];
  class Element {
    constructor(tag) {
      this.tagName = tag.toUpperCase(); this.children = []; this.parentNode = null; this.dataset = {}; this.listeners = {}; this.attributes = {};
      this.value = ''; this.disabled = false; this.hidden = false; this.checked = false; this.open = false; this.className = '';
      this.selectionStart = 0; this.selectionEnd = 0; this._text = ''; this.scrollHeight = 40; this.clientHeight = 40;
    }
    get isConnected() { return this === document?.body || !!this.parentNode?.isConnected; }
    append(...nodes) {
      for (let node of nodes) {
        if (typeof node === 'string') node = new TextNode(node);
        if (node.parentNode) node.parentNode.children = node.parentNode.children.filter(child => child !== node);
        node.parentNode = this; this.children.push(node);
      }
    }
    replaceChildren(...nodes) { for (const child of this.children) child.parentNode = null; this.children = []; this.append(...nodes); }
    set textContent(value) { this._text = String(value); this.replaceChildren(); }
    get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    getAttribute(key) { return this.attributes[key] ?? null; }
    addEventListener(type, listener, options) { (this.listeners[type] ??= []).push({ listener, once: options?.once }); }
    dispatch(type, properties = {}) {
      const event = { type, target: this, preventDefault() { this.prevented = true; }, ...properties };
      for (const entry of [...this.listeners[type] || []]) { entry.listener(event); if (entry.once) this.listeners[type] = this.listeners[type].filter(item => item !== entry); }
      return event;
    }
    focus() { if (this.disabled) return; const previous = document.activeElement; document.activeElement = this; if (previous !== this) { previous?.dispatch('blur'); this.dispatch('focus'); } }
    setSelectionRange(start, end) { this.selectionStart = start; this.selectionEnd = end; }
    matches(selector) {
      if (selector.startsWith('.')) return this.className.split(' ').includes(selector.slice(1));
      if (selector.startsWith('#')) return this.id === selector.slice(1);
      return this.tagName === selector.toUpperCase();
    }
    querySelectorAll(selector) {
      const selectors = selector.split(','); const result = [];
      for (const child of this.children) { if (selectors.some(item => child.matches(item))) result.push(child); result.push(...child.querySelectorAll(selector)); }
      return result;
    }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    closest(selector) { for (let node = this; node; node = node.parentNode) if (node.matches(selector)) return node; return null; }
    getBoundingClientRect() { return { top: 0, left: 0, right: 100, bottom: 100, height: 100 }; }
    scrollIntoView() {}
    showModal() { this.open = true; }
    close() { this.open = false; this.dispatch('close'); }
    click() { if (this.disabled) return; this.dispatch('click'); if (this.tagName === 'A') { const blob = blobs.get(this.href); if (blob) blob.filename = this.download; downloads.push(blob); } }
  }
  class TextNode extends Element { constructor(text) { super('#text'); this._text = text; } }
  class TextArea extends Element {
    constructor() { super('textarea'); }
    get value() { return this._value || ''; }
    set value(value) { if (value !== this._value) { this._value = String(value); this.selectionStart = this.selectionEnd = this._value.length; } }
  }
  const ids = new Map();
  document = {
    body: new Element('body'), documentElement: new Element('html'), activeElement: null, title: '',
    getElementById: id => ids.get(id), createElement: tag => tag === 'textarea' ? new TextArea() : new Element(tag),
    createTextNode: text => new TextNode(text), querySelector: selector => document.body.querySelector(selector),
  };
  document.activeElement = document.body;
  document.documentElement.outerHTML = renderFixture(boot).replace(/^<!doctype html>\s*/i, '');
  for (const id of [...template.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]).concat(['skill-builder-data'])) {
    const node = new Element(id === 'page-select' ? 'select' : id.endsWith('-dialog') ? 'dialog' : 'div');
    node.id = id; ids.set(id, node); document.body.append(node);
  }
  ids.get('skill-builder-data').textContent = JSON.stringify(boot);
  ids.get('form-main').dataset = { loadError: 'Unable to load', regenerate: 'Regenerate the questionnaire' };
  class FakeURL extends URL {
    static createObjectURL(blob) { const id = `blob:${blobs.size}`; blobs.set(id, blob); return id; }
    static revokeObjectURL() {}
  }
  const window = { scrollTo() {}, listeners: {}, addEventListener(type, listener) { (this.listeners[type] ??= []).push(listener); } };
  const context = {
    document, URL: FakeURL, Blob, Intl, Date, JSON, Set, Map, Object, Array, String, Number, Boolean, Math, Promise,
    crypto: { randomUUID: () => '10000000-0000-4000-8000-' + String(Math.floor(Math.random() * 1e12)).padStart(12, '0') },
    setTimeout(callback, milliseconds) { const timer = setTimeout(() => { timers.delete(timer); callback(); }, milliseconds); timers.add(timer); return timer; },
    clearTimeout(timer) { timers.delete(timer); clearTimeout(timer); }, window,
    localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
    fetch: (...args) => { requests.push(args); throw Error('An offline questionnaire must not make network requests'); },
  };
  vm.createContext(context);
  assert.match(source, /\}\)\(\);\s*$/);
  const instrumented = source.replace(/\}\)\(\);\s*$/, `
    globalThis.testAPI = {
      get view() { return view; }, get answers() { return answers; }, get ui() { return ui; },
      get dirty() { return dirty; }, get composition() { return composition; }, get pageIndex() { return pageIndex; },
      get pages() { return pages; }, render, goPage, saveAnswers, snapshot, serialize, clearAnswer, resetAllAnswers,
      derive, choose, chooseOther, change, valueValid, pendingDrafts, updateGoal, flushEditors
    };
  })();`);
  vm.runInContext(instrumented, context, { filename: 'form.js' });
  return {
    api: context.testAPI, document, ids, window, storage, requests, downloads, crypto: context.crypto,
    textarea: id => ids.get('questions').querySelectorAll('textarea').find(node => node.id === `input-${id}`),
    input: (id, value) => ids.get('questions').querySelectorAll('input').find(node => node.name === `answer-${id}` && node.value === value && !node.dataset.other),
    other: id => ids.get('questions').querySelectorAll('input').find(node => node.name === `answer-${id}` && node.dataset.other),
    card: id => ids.get('questions').children.find(node => node.dataset.question === id),
    unload() { const event = { preventDefault() { this.prevented = true; } }; window.listeners.beforeunload?.forEach(fn => fn(event)); return event; },
    dispose() { for (const timer of timers) clearTimeout(timer); timers.clear(); },
  };
}

export function inputValue(node, value, composing = false, start = value.length, end = start) {
  node.value = value; node.setSelectionRange(start, end);
  node.dispatch('input', { isComposing: composing, inputType: composing ? 'insertCompositionText' : 'insertText' });
}

export function select(node, checked = true) { assert.ok(node, 'Expected a selectable form control'); node.checked = checked; node.dispatch('change'); }
