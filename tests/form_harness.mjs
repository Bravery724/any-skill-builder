/**
 * Execute the shipped form in a small deterministic DOM/event environment.
 * This models editor identity, caret movement, storage, and HTTP acknowledgements.
 * It does not model layout, browser input methods, or native OS composition.
 */
import fs from 'node:fs/promises';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const source = await fs.readFile(new URL('../any-skill-builder/assets/form.js', import.meta.url), 'utf8');
const catalog = JSON.parse(await fs.readFile(new URL('../any-skill-builder/assets/locales.json', import.meta.url), 'utf8'));
export const copy = value => JSON.parse(JSON.stringify(value));
export const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

export function makeBoot(transport = 'live', language = 'en') {
  const questionnaire = {
    schema_version: 1, run_id: 'form-regression', project_id: 'form-regression', revision: 1,
    groups: [{ id: 'first', label: 'Scope' }, { id: 'second', label: 'Details' }],
    sources: [],
    questions: [
      { id: 'gate', version: 1, group_id: 'first', type: 'multi', title: 'Choose a workflow', when: [],
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
    transport, token: 'synthetic-test-token',
    locale: { language, direction: 'ltr', messages: catalog[language] },
    view: {
      questionnaire,
      answers: {
        schema_version: 1, run_id: questionnaire.run_id, project_id: questionnaire.project_id,
        revision: 1, answer_revision: 1,
        answers: { gate: answer(['a', 'b']), text: answer('Initial answer'), other: answer('a'), last: answer('Initial details') },
        history: [],
      },
    },
  };
}

export function setup(boot = makeBoot(), storage = new Map()) {
  let document;
  const requests = [], pending = [], downloads = [], blobs = new Map(), timers = new Set();

  class Element {
    constructor(tag) {
      this.tagName = tag.toUpperCase();
      this.children = []; this.parentNode = null; this.dataset = {}; this.listeners = {}; this.attributes = {};
      this.value = ''; this.disabled = false; this.hidden = false; this.checked = false; this.open = false;
      this.className = ''; this.selectionStart = 0; this.selectionEnd = 0; this._text = '';
    }
    get isConnected() { return this === document?.body || !!this.parentNode?.isConnected; }
    append(...nodes) {
      for (let node of nodes) {
        if (typeof node === 'string') node = new TextNode(node);
        if (node.parentNode) node.parentNode.children = node.parentNode.children.filter(child => child !== node);
        node.parentNode = this; this.children.push(node);
      }
    }
    replaceChildren(...nodes) {
      for (const child of this.children) child.parentNode = null;
      this.children = []; this.append(...nodes);
    }
    set textContent(value) { this._text = String(value); this.replaceChildren(); }
    get textContent() { return this._text + this.children.map(child => child.textContent).join(''); }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    getAttribute(key) { return this.attributes[key] ?? null; }
    addEventListener(type, listener) { (this.listeners[type] ??= []).push(listener); }
    dispatch(type, properties = {}) {
      const event = { type, target: this, preventDefault() {}, ...properties };
      for (const listener of this.listeners[type] || []) listener(event);
    }
    focus() {
      if (this.disabled) return;
      const previous = document.activeElement;
      document.activeElement = this;
      if (previous !== this) { previous?.dispatch('blur'); this.dispatch('focus'); }
    }
    setSelectionRange(start, end) { this.selectionStart = start; this.selectionEnd = end; }
    matches(selector) {
      if (selector === '[data-focus]') return this.dataset.focus !== undefined;
      if (selector === 'details[open]') return this.tagName === 'DETAILS' && this.open;
      if (selector.startsWith('.')) return this.className.split(' ').includes(selector.slice(1));
      return this.tagName === selector.toUpperCase();
    }
    querySelectorAll(selector) {
      const selectors = selector.split(',');
      const result = [];
      for (const child of this.children) {
        if (selectors.some(item => child.matches(item))) result.push(child);
        result.push(...child.querySelectorAll(selector));
      }
      return result;
    }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    closest(selector) {
      for (let node = this; node; node = node.parentNode) if (node.matches(selector)) return node;
      return null;
    }
    getBoundingClientRect() { return { top: 0, left: 0, right: 100, bottom: 100 }; }
    scrollIntoView() {}
    showModal() { this.open = true; }
    close() { this.open = false; this.dispatch('close'); }
    click() { this.dispatch('click'); if (this.tagName === 'A') downloads.push(blobs.get(this.href)); }
  }
  class TextNode extends Element { constructor(text) { super('#text'); this._text = text; } }
  class TextArea extends Element {
    constructor() { super('textarea'); }
    select() { this.setSelectionRange(0, this.value.length); }
    get value() { return this._value || ''; }
    // Assigning a different textarea value moves the caret, as in a browser.
    set value(value) {
      if (value !== this._value) {
        this._value = String(value);
        this.selectionStart = this.selectionEnd = this._value.length;
      }
    }
  }

  const ids = new Map();
  document = {
    body: new Element('body'), documentElement: new Element('html'), activeElement: null,
    title: '', visibilityState: 'visible', listeners: {},
    getElementById: id => ids.get(id),
    createElement: tag => tag === 'textarea' ? new TextArea() : new Element(tag),
    createTextNode: text => new TextNode(text),
    addEventListener(type, listener) { (this.listeners[type] ??= []).push(listener); },
  };
  document.activeElement = document.body;
  for (const id of [
    'form-main', 'skill-builder-data', 'counts', 'notice', 'range', 'conditional-status',
    'questionnaire', 'questions', 'previous', 'next', 'page-select', 'save-status', 'completion',
    'recovery', 'retry-save', 'export-recovery', 'refresh-state', 'recovery-message', 'image-caption',
    'enlarged-image', 'image-dialog', 'close-image', 'export-draft', 'import-draft', 'import-file', 'transport-note',
    'delegate-unanswered-top', 'delegation-note', 'core-guidance', 'finish', 'finish-note', 'finish-confirmation', 'finish-message',
    'confirm-delegate', 'continue-answering', 'reset-all', 'reset-confirmation', 'confirm-reset', 'cancel-reset',
  ]) {
    const node = new Element(id === 'page-select' ? 'select' : 'div');
    node.id = id; ids.set(id, node); document.body.append(node);
  }
  ids.get('skill-builder-data').textContent = JSON.stringify(boot);
  ids.get('reset-confirmation').hidden = true;
  ids.get('finish-confirmation').hidden = true;
  ids.get('form-main').dataset = { loadError: 'Unable to load', regenerate: 'Regenerate the questionnaire' };
  const server = copy(boot.view);
  class FakeURL extends URL {
    static createObjectURL(blob) { const id = `blob:${blobs.size}`; blobs.set(id, blob); return id; }
    static revokeObjectURL() {}
  }
  const context = {
    document, HTMLTextAreaElement: TextArea, URL: FakeURL, Blob, Intl, Date, JSON, Set, Map,
    navigator: {},
    Object, Array, String, Number, Boolean, Math, Promise, crypto: { randomUUID: () => String(Math.random()) },
    setTimeout(callback, milliseconds) {
      const timer = setTimeout(() => { timers.delete(timer); callback(); }, milliseconds);
      timers.add(timer); return timer;
    },
    clearTimeout(timer) { timers.delete(timer); clearTimeout(timer); },
    localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
    window: { scrollTo() {}, scrollBy() {}, listeners: {}, addEventListener(type, listener) { (this.listeners[type] ??= []).push(listener); } },
    fetch: (url, options = {}) => {
      const request = { url, body: options.body ? JSON.parse(options.body) : null };
      requests.push(request);
      return new Promise(resolve => pending.push({ request, resolve }));
    },
  };
  vm.createContext(context);
  // Only expose existing functions/state for driving and observing the real form.
  // No production branch or editor behavior is replaced by this test hook.
  assert.match(source, /\}\)\(\);\s*$/, 'The form entry point must be available for the test hook');
  const instrumented = source.replace(/\}\)\(\);\s*$/, `
    globalThis.testAPI = {
      get view() { return view; }, get answers() { return answers; },
      get drafts() { return textDrafts; }, get composition() { return composition; },
      render, goPage, download, next, showRecovery, change, derive, persistCurrentText,
      finish, delegateUnanswered, openReset, cancelReset, resetAllAnswers
    };
  })();`);
  vm.runInContext(instrumented, context, { filename: 'form.js' });
  const api = context.testAPI;

  function ack() {
    const item = pending.shift();
    assert.ok(item, 'A request must be pending before it is acknowledged');
    if (item.request.url.startsWith('/api/answers')) {
      for (const [id, record] of Object.entries(item.request.body.changes)) {
        const before = server.answers.answers[id];
        if (before) server.answers.history.push({ question_id: id, answer: before });
        if (record) server.answers.answers[id] = copy(record);
        else delete server.answers.answers[id];
      }
      server.answers.answer_revision++;
    }
    if (item.request.url.startsWith('/api/reset')) {
      for (const [id, answer] of Object.entries(server.answers.answers)) server.answers.history.push({ question_id: id, answer, reason: 'reset_all' });
      server.answers.answers = {};
      server.answers.answer_revision++;
    }
    const view = { ...copy(server), ...copy(api.derive(server.answers)) };
    item.resolve({ ok: true, json: async () => item.request.url.startsWith('/api/submit') ? { event: view.ready_to_build ? 'submitted' : 'deferred_review', view }
      : item.request.url.startsWith('/api/delegate') ? { event: 'ai_requested', scope: 'unanswered', view } : view });
    return item.request;
  }
  return {
    api, document, ids, storage, requests, pending, downloads, ack, navigator: context.navigator,
    textarea: id => ids.get('questions').querySelectorAll('textarea').find(node => node.name === `answer-${id}`),
    get server() { return copy(server); },
    dispose() { for (const timer of timers) clearTimeout(timer); timers.clear(); },
  };
}
