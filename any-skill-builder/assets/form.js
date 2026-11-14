(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const copy = value => JSON.parse(JSON.stringify(value));
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  };
  let locale = { messages: { load_failed: $('form-main').dataset.loadError, regenerate: $('form-main').dataset.regenerate } };
  let numberFormat;
  let graphemes;
  const textLength = value => Array.from(value).length;
  function limitText(value, limit) {
    if (value.length <= limit || textLength(value) <= limit) return value;
    if (!graphemes) return Array.from(value).slice(0, limit).join('');
    let result = '', length = 0;
    for (const { segment } of graphemes.segment(value)) {
      const size = textLength(segment);
      if (length + size > limit) break;
      result += segment; length += size;
    }
    return result;
  }
  function t(key, values = {}) {
    const template = Object.hasOwn(locale.messages, key) ? locale.messages[key] : key;
    return String(template).replace(/\{([A-Za-z][A-Za-z0-9_]*)\}/g, (match, name) => {
      if (!Object.hasOwn(values, name)) return match;
      return typeof values[name] === 'number' && numberFormat ? numberFormat.format(values[name]) : String(values[name]);
    });
  }
  let boot;
  try {
    boot = JSON.parse($('skill-builder-data').textContent);
    if (!boot.view?.questionnaire || !boot.view?.answers || !boot.locale?.messages) throw new Error('Missing view or locale');
    locale = boot.locale;
    document.documentElement.lang = locale.language;
    document.documentElement.dir = locale.direction === 'rtl' ? 'rtl' : 'ltr';
    document.title = t('page_title');
    try { numberFormat = new Intl.NumberFormat(locale.language); } catch { numberFormat = new Intl.NumberFormat(); }
    try { graphemes = new Intl.Segmenter(locale.language, { granularity: 'grapheme' }); } catch { /* Code-point limits remain available in older browsers. */ }
  } catch {
    $('counts').textContent = t('load_failed');
    $('notice').textContent = t('regenerate');
    return;
  }

  const live = boot.transport === 'live';
  let authoritative = copy(boot.view);
  let questionnaire = authoritative.questionnaire;
  let answers = copy(authoritative.answers);
  let queue = [];
  let inFlight = null;
  let saving = false;
  let paused = false;
  let conflict = false;
  let submitted = false;
  let submittedAction = null;
  let submitting = false;
  let submittingAction = null;
  let resetPending = false;
  let aiDelegation = false;
  let pageIndex = 0;
  let pages = [];
  let view;
  let pageAnchor = null;
  let lastActiveCount = null;
  let partialMulti = {};
  let composition = null;
  let textDrafts = {};
  let textSessions = {};
  let deferDrafts = {};
  let deferSessions = {};
  let draftSaveTimer = null;
  let displayAnswers = answers;
  let rendering = false;
  const draftKey = () => `skill-builder:${questionnaire.run_id}:${questionnaire.revision}`;
  const api = path => `${path}?token=${encodeURIComponent(boot.token || '')}`;
  const question = id => questionnaire.questions.find(q => q.id === id);
  const record = id => displayAnswers.answers[id];
  const semantic = a => JSON.stringify(a ? [a.status, a.value ?? null, a.actor || 'user', a.rationale || '', a.question_version, a.assumptions || []] : null);
  const editorDrafts = kind => kind === 'defer' ? deferDrafts : textDrafts;
  const editorSessions = kind => kind === 'defer' ? deferSessions : textSessions;
  const editorLimit = (q, kind) => kind === 'defer' ? 20000 : q.max_length || 20000;

  function multiSelectionValid(q, value) {
    const ids = (q.options || []).map(o => o.id);
    return Array.isArray(value) && value.length > 0 && value.length <= (q.max_choices || ids.length) && new Set(value).size === value.length && value.every(v => ids.includes(v)) && !(value.length > 1 && q.options.some(o => o.exclusive && value.includes(o.id)));
  }

  function valueValid(q, value) {
    if (q.type === 'text') return typeof value === 'string' && value.trim().length > 0 && textLength(value) <= (q.max_length || 20000);
    if (q.type === 'multi') return multiSelectionValid(q, value) && value.length >= (q.min_choices || 1);
    const ids = (q.options || []).map(o => o.id);
    return typeof value === 'string' && ids.includes(value);
  }

  function validateEnvelope(envelope, ignoreBase = false) {
    if (!envelope || envelope.schema_version !== 1 || envelope.run_id !== questionnaire.run_id || envelope.project_id !== questionnaire.project_id || envelope.revision !== questionnaire.revision) throw new Error(t('wrong_envelope'));
    if (!ignoreBase && envelope.answer_revision !== authoritative.answers.answer_revision) throw new Error(t('wrong_answer_revision'));
    if (!Number.isInteger(envelope.answer_revision) || envelope.answer_revision < 0) throw new Error(t('invalid_answers'));
    if (!envelope.answers || typeof envelope.answers !== 'object' || Array.isArray(envelope.answers)) throw new Error(t('invalid_answers'));
    if (Object.hasOwn(envelope, 'history') && (!Array.isArray(envelope.history) || envelope.history.some(item => !item || typeof item !== 'object' || Array.isArray(item)))) throw new Error(t('invalid_answers'));
    for (const [id, a] of Object.entries(envelope.answers)) {
      const q = question(id);
      if (!q || !a || typeof a !== 'object' || Array.isArray(a) || a.question_version !== q.version || !['answered', 'deferred'].includes(a.status)) throw new Error(t('wrong_question_version'));
      if (Object.hasOwn(a, 'actor') && !['user', 'ai'].includes(a.actor)
        || Object.hasOwn(a, 'rationale') && typeof a.rationale !== 'string'
        || Object.hasOwn(a, 'assumptions') && (!Array.isArray(a.assumptions) || a.assumptions.some(value => typeof value !== 'string'))
        || a.actor === 'ai' && a.status === 'answered' && !a.rationale?.trim()) throw new Error(t('invalid_answers'));
      if (a.status === 'answered' && !valueValid(q, a.value)) throw new Error(t('invalid_answer', { title: q.title }));
    }
  }

  function derive(envelope) {
    const states = {};
    const visiting = new Set();
    function resolve(id) {
      if (states[id]) return states[id];
      if (visiting.has(id)) throw new Error(t('cyclic_condition'));
      const q = question(id);
      if (!q) throw new Error(t('missing_condition'));
      visiting.add(id);
      let waiting = false, inactive = false;
      for (const condition of q.when || []) {
        const parentState = resolve(condition.question_id);
        const a = envelope.answers[condition.question_id];
        if (parentState === 'inactive') inactive = true;
        else if (parentState === 'waiting' || !a || a.status !== 'answered') waiting = true;
        else if ('equals' in condition ? a.value !== condition.equals : !Array.isArray(a.value) || !a.value.includes(condition.includes)) inactive = true;
      }
      visiting.delete(id);
      return states[id] = inactive ? 'inactive' : waiting ? 'waiting' : 'active';
    }
    questionnaire.questions.forEach(q => resolve(q.id));
    const counts = { total: questionnaire.questions.length, active: 0, answered: 0, deferred: 0, unanswered: 0, waiting: 0, inactive: 0 };
    for (const q of questionnaire.questions) {
      const state = states[q.id];
      if (state !== 'active') { counts[state]++; continue; }
      counts.active++;
      const a = envelope.answers[q.id];
      if (!a) counts.unanswered++;
      else if (a.status === 'deferred') counts.deferred++;
      else if (a.status === 'answered' && valueValid(q, a.value)) counts.answered++;
      else counts.unanswered++;
    }
    return { questionnaire, answers: envelope, states, counts, traversal_complete: counts.active > 0 && counts.unanswered === 0, ready_to_build: counts.active > 0 && counts.unanswered === 0 && counts.deferred === 0 && counts.waiting === 0 };
  }

  function validatedPartialDrafts(raw, envelope, strict = false) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
      if (strict) throw new Error(t('invalid_draft'));
      return {};
    }
    const states = derive(envelope).states, result = {};
    for (const [id, values] of Object.entries(raw)) {
      const q = question(id);
      if (q?.type !== 'multi' || states[id] !== 'active' || Object.hasOwn(envelope.answers, id)
        || !multiSelectionValid(q, values) || values.length >= (q.min_choices || 1)) {
        if (strict) throw new Error(t('invalid_draft'));
        continue;
      }
      result[id] = copy(values);
    }
    return result;
  }

  function archive(envelope, id, reason, editSession) {
    if (editSession && (envelope.history || []).some(h => h.question_id === id && h.edit_session === editSession && h.reason === reason)) return;
    if (envelope.answers[id]) (envelope.history ||= []).push({ question_id: id, answer: copy(envelope.answers[id]), reason, at: new Date().toISOString(), ...(editSession ? { edit_session: editSession } : {}) });
  }

  function apply(envelope, operation, keepHistory = true) {
    const q = question(operation.id);
    if (!q) return;
    const previous = envelope.answers[q.id];
    if (semantic(previous) === semantic(operation.record)) return;
    if (keepHistory) archive(envelope, q.id, 'browser_answer_changed', operation.edit_session);
    if (operation.record) envelope.answers[q.id] = copy(operation.record);
    else delete envelope.answers[q.id];
    const affected = new Set([q.id]);
    let expanded = true;
    while (expanded) {
      expanded = false;
      for (const child of questionnaire.questions) {
        if (!affected.has(child.id) && (child.when || []).some(c => affected.has(c.question_id))) {
          affected.add(child.id); expanded = true;
          if (keepHistory) archive(envelope, child.id, 'parent_answer_changed', operation.edit_session);
          delete envelope.answers[child.id];
        }
      }
    }
  }

  function project() {
    if (live && !conflict) {
      answers = copy(authoritative.answers);
      queue.forEach(op => apply(answers, op));
    }
    displayAnswers = copy(answers);
    for (const [id, value] of Object.entries(textDrafts)) {
      const q = question(id);
      if (q?.type === 'text') apply(displayAnswers, { id, record: value.trim() ? { status: 'answered', value, actor: 'user', question_version: q.version, rationale: '' } : null }, false);
    }
    for (const [id, value] of Object.entries(deferDrafts)) {
      const q = question(id), current = displayAnswers.answers[id];
      if (q && current?.status === 'deferred') apply(displayAnswers, { id, record: { status: 'deferred', actor: 'user', question_version: q.version, rationale: value } }, false);
    }
    view = derive(displayAnswers);
  }

  function saveLocal() {
    try {
      localStorage.setItem(draftKey(), JSON.stringify({ run_id: questionnaire.run_id, project_id: questionnaire.project_id, revision: questionnaire.revision, base_answer_revision: authoritative.answers.answer_revision, answers, queue, partial_multi: partialMulti, text_drafts: textDrafts, text_sessions: textSessions, defer_drafts: deferDrafts, defer_sessions: deferSessions, reset_pending: resetPending, ai_delegation: aiDelegation, page_anchor: pageAnchor }));
      if (!live) $('save-status').textContent = t('saved_browser');
    } catch {
      if (!live) $('save-status').textContent = t('browser_save_failed');
    }
  }

  function scheduleDraftSave() {
    clearTimeout(draftSaveTimer);
    draftSaveTimer = setTimeout(saveLocal, 120);
  }

  function textSession(id, kind = 'answer') {
    return editorSessions(kind)[id] ||= globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function commitTextDraft(id, endSession = false, kind = 'answer') {
    const drafts = editorDrafts(kind);
    if (Object.hasOwn(drafts, id)) {
      const value = drafts[id], q = question(id);
      const editSession = textSession(id, kind);
      delete drafts[id];
      if (!q || (kind === 'defer' ? answers.answers[id]?.status !== 'deferred' : q.type !== 'text')) {
        if (endSession) delete editorSessions(kind)[id];
        return;
      }
      const nextRecord = kind === 'defer' ? { status: 'deferred', actor: 'user', question_version: q.version, rationale: value }
        : value.trim() ? { status: 'answered', value, actor: 'user', question_version: q.version, rationale: '' } : null;
      if (conflict) {
        apply(answers, { id, record: nextRecord, edit_session: editSession });
        project(); saveLocal(); render();
      } else if (semantic(answers.answers[id]) !== semantic(nextRecord)) change(id, nextRecord, editSession);
      else { project(); saveLocal(); render(); }
    }
    if (endSession) { delete editorSessions(kind)[id]; saveLocal(); render(); }
  }

  function retainComposition() {
    if (!composition?.input.isConnected) return;
    const kind = composition.kind || 'answer', q = question(composition.id);
    if (q) editorDrafts(kind)[q.id] = limitText(composition.input.value, editorLimit(q, kind));
  }

  function flushTextDrafts(endSessions = false) {
    retainComposition();
    for (const id of Object.keys(textDrafts)) commitTextDraft(id, endSessions);
    for (const id of Object.keys(deferDrafts)) commitTextDraft(id, endSessions, 'defer');
    if (endSessions) { textSessions = {}; deferSessions = {}; }
    clearTimeout(draftSaveTimer); saveLocal();
  }

  function showRecovery(message, isConflict) {
    paused = true; conflict = isConflict;
    $('recovery').hidden = false;
    $('recovery-message').textContent = message;
    $('retry-save').hidden = isConflict || !live;
    $('refresh-state').hidden = false;
    $('save-status').textContent = t('unsaved_changes');
    saveLocal();
    if (view) render();
  }

  async function responseJson(response) {
    let data;
    try { data = await response.json(); } catch { throw new Error(t('invalid_response')); }
    if (!response.ok) {
      const error = new Error(t('request_failed'));
      error.status = response.status;
      error.code = data.error;
      throw error;
    }
    return data;
  }

  async function pump() {
    if (!live || saving || paused || submitted || !queue.length) return;
    saving = true;
    $('save-status').textContent = t('saving');
    try {
      while (queue.length && !paused) {
        inFlight = queue[0];
        const data = await responseJson(await fetch(api('/api/answers'), {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ run_id: questionnaire.run_id, project_id: questionnaire.project_id, revision: questionnaire.revision, base_answer_revision: authoritative.answers.answer_revision, changes: { [inFlight.id]: inFlight.record } })
        }));
        authoritative = data.view || data;
        questionnaire = authoritative.questionnaire;
        queue.shift(); inFlight = null;
        project(); saveLocal(); render();
      }
      if (!paused) $('save-status').textContent = t('saved');
    } catch (error) {
      inFlight = null;
      showRecovery(error.status === 409 ? t('conflict') : t('retry_when_connected', { message: error.status ? error.message : t('connection_failed') }), error.status === 409);
    } finally {
      saving = false;
      updateActions();
    }
  }

  function change(id, nextRecord, editSession) {
    if (submitted || submitting || conflict) return;
    const q = question(id);
    if (!q || view.states[id] !== 'active') return;
    const operation = { id, record: nextRecord ? { ...nextRecord, actor: 'user', question_version: q.version, rationale: nextRecord.rationale || '' } : null, ...(editSession ? { edit_session: editSession } : {}) };
    if (!editSession) { delete textDrafts[id]; delete textSessions[id]; }
    if (!editSession || nextRecord?.status !== 'deferred') { delete deferDrafts[id]; delete deferSessions[id]; }
    if (nextRecord) delete partialMulti[id];
    const descendants = new Set([id]);
    let found = true;
    while (found) {
      found = false;
      for (const child of questionnaire.questions) if (!descendants.has(child.id) && (child.when || []).some(c => descendants.has(c.question_id))) { descendants.add(child.id); delete partialMulti[child.id]; delete textDrafts[child.id]; delete textSessions[child.id]; delete deferDrafts[child.id]; delete deferSessions[child.id]; found = true; }
    }
    if (live) {
      const last = queue.at(-1);
      if (last && last.id === id && last !== inFlight) queue[queue.length - 1] = operation;
      else queue.push(operation);
    } else apply(answers, operation);
    project();
    $('completion').hidden = true;
    $('notice').textContent = '';
    saveLocal(); render();
    void pump();
  }

  function orderedQuestions() {
    const ids = new Set(); const ordered = [];
    for (const group of questionnaire.groups) for (const q of questionnaire.questions) if (q.group_id === group.id) { ordered.push(q); ids.add(q.id); }
    for (const q of questionnaire.questions) if (!ids.has(q.id)) ordered.push(q);
    return ordered;
  }

  function makePages() {
    const result = [];
    for (const group of questionnaire.groups) {
      const active = questionnaire.questions.filter(q => q.group_id === group.id && view.states[q.id] === 'active');
      let batch = [], weight = 0;
      for (const q of active) {
        const cost = ['image', 'text'].includes(q.type) ? 2 : 1;
        if (batch.length && weight + cost > 4) { result.push({ group, questions: batch }); batch = []; weight = 0; }
        batch.push(q); weight += cost;
      }
      if (batch.length) result.push({ group, questions: batch });
    }
    return result;
  }

  function safeSourceUrl(raw) {
    try { const url = new URL(raw); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; } catch { return null; }
  }

  function assetUrl(raw) {
    if (typeof raw !== 'string' || !raw.startsWith('assets/') || /[\\:#?%]/.test(raw)) return null;
    const parts = raw.split('/');
    if (parts.some(p => !p || p === '.' || p === '..')) return null;
    const path = parts.map(encodeURIComponent).join('/');
    return live ? `/${path}?token=${encodeURIComponent(boot.token || '')}` : path;
  }

  function valueLabel(q, value) {
    if (q.type === 'text') return String(value ?? '');
    const values = Array.isArray(value) ? value : [value];
    return values.map(id => q.options.find(o => o.id === id)?.label || id).join(t('list_separator'));
  }

  function recommendationDetails(q) {
    const details = element('details'); details.dataset.question = q.id;
    details.append(element('summary', '', t('recommendation_details')));
    if (q.recommendation) {
      details.append(element('p', '', t('recommendation', { value: valueLabel(q, q.recommendation.value) })));
      details.append(element('p', '', q.recommendation.rationale || ''));
      const assumptions = q.recommendation.assumptions || [];
      if (assumptions.length) details.append(element('p', '', t('assumptions', { values: assumptions.join(t('list_separator')) })));
      if (valueValid(q, q.recommendation.value)) {
        const use = element('button', 'text-button', t('use_recommendation')); use.type = 'button'; use.disabled = submitted || submitting || conflict;
        use.addEventListener('click', () => change(q.id, { status: 'answered', value: copy(q.recommendation.value), rationale: t('recommendation_selected') }));
        details.append(use);
      }
    }
    if (q.decision) details.append(element('p', '', t('decision', { decision: q.decision })));
    const origins = { source: t('origin_source'), inference: t('origin_inference'), proposal: t('origin_proposal'), user: t('origin_user') };
    details.append(element('p', '', origins[q.origin] || q.origin || ''));
    const sources = (q.source_ids || []).map(id => questionnaire.sources.find(s => s.id === id)).filter(Boolean);
    if (sources.length) {
      const list = element('ul');
      for (const source of sources) {
        const item = element('li'); const url = safeSourceUrl(source.url);
        if (url) { const a = element('a', '', source.title); a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; item.append(a); }
        else item.append(element('span', '', source.title));
        const statuses = { read: t('source_read'), partial: t('source_partial'), unavailable: t('source_unavailable') };
        const status = statuses[source.status] || source.status;
        item.append(document.createTextNode(t('list_separator') + (source.accessed_at ? t('source_meta', { status, date: source.accessed_at }) : status)));
        if (source.notes) item.append(element('div', '', source.notes));
        list.append(item);
      }
      details.append(list);
    }
    return details;
  }

  function optionInput(q, option, type) {
    const input = element('input'); input.type = type; input.name = `answer-${q.id}`; input.value = option.id; input.dir = 'auto';
    input.dataset.focus = `${q.id}:${option.id}`;
    const answer = record(q.id);
    input.checked = Object.hasOwn(partialMulti, q.id) ? partialMulti[q.id].includes(option.id) : answer?.status === 'answered' && (Array.isArray(answer.value) ? answer.value.includes(option.id) : answer.value === option.id);
    input.disabled = submitted || submitting || conflict;
    input.addEventListener('change', () => {
      let value = option.id;
      if (q.type === 'multi') {
        const existing = partialMulti[q.id] || (record(q.id)?.status === 'answered' && Array.isArray(record(q.id).value) ? record(q.id).value : []);
        let selected = input.checked ? [...new Set([...existing, option.id])] : existing.filter(id => id !== option.id);
        if (input.checked && option.exclusive) selected = [option.id];
        else if (input.checked) selected = selected.filter(id => !q.options.find(o => o.id === id)?.exclusive);
        value = q.options.map(o => o.id).filter(id => selected.includes(id));
        if (value.length > (q.max_choices || q.options.length)) { input.checked = false; $('notice').textContent = t('max_choices', { count: q.max_choices }); return; }
        if (!value.length) { delete partialMulti[q.id]; change(q.id, null); return; }
        if (!valueValid(q, value)) {
          partialMulti[q.id] = value;
          if (record(q.id)) change(q.id, null);
          else { saveLocal(); render(); }
          $('notice').textContent = t('min_choices', { count: q.min_choices || 1 });
          return;
        }
      }
      change(q.id, { status: 'answered', value });
    });
    return input;
  }

  function showImage(option, url, opener) {
    $('image-caption').textContent = option.label;
    $('enlarged-image').alt = option.description || option.label;
    $('enlarged-image').src = url;
    $('image-dialog').showModal();
    $('close-image').focus();
    $('image-dialog').addEventListener('close', () => {
      const current = opener.isConnected ? opener : [...$('questions').querySelectorAll('[data-focus]')].find(node => node.dataset.focus === opener.dataset.focus);
      if (current && !current.hidden) current.focus();
      else focusQuestion(pageAnchor);
    }, { once: true });
  }

  function imageOptions(q) {
    const grid = element('div', 'visual-options');
    for (const option of q.options) {
      const card = element('div', 'image-option');
      const preview = element('button', 'image-preview'); preview.type = 'button'; preview.setAttribute('aria-label', t('enlarge_image', { label: option.label }));
      preview.dataset.focus = `image:${q.id}:${option.id}`;
      const img = element('img'); img.alt = option.description || option.label; img.loading = 'lazy';
      const url = assetUrl(option.image);
      const failure = element('p', 'image-failure', t('image_failed')); failure.hidden = true;
      const label = element('label', 'image-label'); const input = optionInput(q, option, 'radio');
      label.append(input, element('span', '', option.label));
      const fail = () => { img.hidden = true; preview.hidden = true; failure.hidden = false; if (!input.checked) input.disabled = true; };
      img.addEventListener('error', fail);
      if (url) { img.src = url; preview.addEventListener('click', () => showImage(option, url, preview)); }
      else fail();
      preview.append(img); card.append(preview, failure, label);
      if (option.description) card.append(element('p', 'image-description', option.description));
      grid.append(card);
    }
    return grid;
  }

  function textEditor(q, kind = 'answer') {
      const isNote = kind === 'defer', a = record(q.id);
      const input = element('textarea', isNote ? 'text-answer defer-reason' : 'text-answer');
      input.name = `${isNote ? 'defer-reason' : 'answer'}-${q.id}`;
      input.setAttribute('aria-labelledby', isNote ? `title-${q.id} defer-label-${q.id}` : `title-${q.id}`);
      input.dataset.focus = `${q.id}:${isNote ? 'defer-reason' : 'text'}`; input.dataset.questionVersion = String(q.version); input.dataset.editorKind = kind;
      input.placeholder = isNote ? '' : q.placeholder || t('answer_placeholder'); input.dir = 'auto'; input.disabled = submitted || submitting || conflict;
      input.value = isNote ? a?.rationale || '' : a?.status === 'answered' ? a.value : '';
      const retainText = () => {
        if (!input.isConnected || view.states[q.id] !== 'active' || question(q.id)?.version !== q.version || isNote && record(q.id)?.status !== 'deferred') return;
        const value = limitText(input.value, editorLimit(q, kind));
        if (composition?.input !== input && value !== input.value) input.value = value;
        textSession(q.id, kind);
        editorDrafts(kind)[q.id] = value;
        project(); updateCounts(); updateQuestionStatuses(); updateActions(); scheduleDraftSave();
      };
      input.addEventListener('focus', () => textSession(q.id, kind));
      input.addEventListener('compositionstart', () => {
        if (!input.isConnected || view.states[q.id] !== 'active') return;
        textSession(q.id, kind);
        composition = { id: q.id, input, kind };
        input.dataset.composing = 'true';
        updateActions();
      });
      input.addEventListener('input', event => {
        if (event.isComposing || composition?.input === input) {
          if (!composition) composition = { id: q.id, input, kind };
          input.dataset.composing = 'true';
          retainText();
          return;
        }
        retainText();
      });
      input.addEventListener('compositionend', () => {
        if (composition?.input === input) composition = null;
        delete input.dataset.composing;
        retainText();
      });
      input.addEventListener('blur', () => {
        if (rendering) return;
        setTimeout(() => {
          if (document.activeElement?.dataset?.focus !== input.dataset.focus && composition?.input !== input) commitTextDraft(q.id, true, kind);
        }, 0);
      });
      return input;
  }

  function updateQuestionStatus(card, badge, q) {
    const answer = record(q.id);
    const status = answer?.status === 'deferred' ? 'deferred'
      : answer?.status === 'answered' && valueValid(q, answer.value) ? 'answered' : 'unanswered';
    card.dataset.status = status;
    const label = t(status === 'unanswered' && aiDelegation ? 'ai_pending' : `question_status_${status}`);
    if (badge.textContent !== label) badge.textContent = label;
  }

  function updateQuestionStatuses() {
    for (const card of $('questions').querySelectorAll('.question')) {
      const q = question(card.dataset.question);
      if (q) updateQuestionStatus(card, card.querySelector('.question-status'), q);
    }
  }

  function renderQuestion(q, number) {
    const a = record(q.id);
    const card = element('section', 'question'); card.dataset.question = q.id;
    const field = element('fieldset');
    const legend = element('legend');
    const heading = element('span', 'question-heading');
    const title = element('span', 'question-title'); title.id = `title-${q.id}`;
    const badge = element('span', 'question-status'); badge.setAttribute('aria-live', 'polite');
    title.append(element('span', 'number', t('question_number', { number })), document.createTextNode(q.title));
    updateQuestionStatus(card, badge, q);
    heading.append(title, badge); legend.append(heading); field.append(legend);
    if (q.help) field.append(element('p', 'help', q.help));
    if (q.type === 'image') field.append(imageOptions(q));
    else if (q.type === 'text') field.append(textEditor(q));
    else {
      const options = element('div', 'options');
      for (const option of q.options) {
        const label = element('label', 'option');
        const text = element('span', 'option-copy'); text.append(element('span', '', option.label));
        if (option.description) text.append(element('div', 'option-description', option.description));
        label.append(optionInput(q, option, q.type === 'multi' ? 'checkbox' : 'radio'), text); options.append(label);
      }
      field.append(options);
    }
    card.append(field);
    const footer = element('div', 'question-footer');
    footer.append(recommendationDetails(q));
    if ((q.type === 'single' || q.type === 'image') && a?.status === 'answered') {
      const clear = element('button', 'hold clear-selection', t('clear_selection')); clear.type = 'button';
      clear.disabled = submitted || submitting || conflict;
      clear.addEventListener('click', () => {
        change(q.id, null);
        focusQuestion(q.id);
      });
      footer.append(clear);
    }
    const hold = element('button', 'hold', a?.status === 'deferred' ? t('undo_defer') : t('defer')); hold.type = 'button'; hold.dataset.focus = `${q.id}:hold`;
    hold.setAttribute('aria-pressed', String(a?.status === 'deferred')); hold.setAttribute('aria-label', t(a?.status === 'deferred' ? 'undo_defer_question' : 'defer_question', { number })); hold.disabled = submitted || submitting || conflict;
    hold.addEventListener('click', () => change(q.id, a?.status === 'deferred' ? null : { status: 'deferred' }));
    footer.append(hold); card.append(footer);
    if (a?.status === 'deferred') {
      const note = element('div', 'defer-note');
      const label = element('label', 'defer-label', t('defer_reason_label')); label.id = `defer-label-${q.id}`;
      const input = textEditor(q, 'defer'); input.id = `defer-reason-${q.id}`; label.htmlFor = input.id;
      note.append(label, input); card.append(note);
    }
    if (a?.actor === 'ai') card.append(element('span', 'answer-actor', t('ai_answer')));
    return card;
  }

  function updateActions() {
    $('previous').hidden = false;
    const navigatingBlocked = submitted || submitting || Boolean(composition);
    $('previous').disabled = navigatingBlocked || pageIndex === 0 || !pages.length;
    $('page-select').disabled = navigatingBlocked;
    $('next').disabled = navigatingBlocked || !pages.length || pageIndex >= pages.length - 1;
    $('next').textContent = t('next');
    const blocked = submitted || submitting || Boolean(composition) || conflict || live && paused;
    const confirming = !$('reset-confirmation').hidden;
    const hasInput = aiDelegation || Object.keys(displayAnswers.answers).length || Object.keys(partialMulti).length || Object.keys(textDrafts).length || Object.keys(deferDrafts).length;
    const delegate = $('delegate-unanswered-top');
    delegate.disabled = blocked || confirming || !view.counts.unanswered && !aiDelegation;
    delegate.textContent = t(aiDelegation ? 'delegate_selected' : 'delegate_unanswered');
    delegate.setAttribute('aria-pressed', String(aiDelegation));
    $('delegation-note').hidden = !aiDelegation;
    $('delegation-note').textContent = t('delegation_note', { count: view.counts.unanswered });
    const finishing = submitting && submittingAction !== 'reset';
    $('finish').disabled = blocked || confirming || !pages.length;
    $('finish').textContent = submitted ? t(submittedAction === 'ai_requested' ? 'ai_request_sent' : 'submitted') : t(finishing ? 'submitting' : 'finish');
    $('finish').setAttribute('aria-busy', String(finishing));
    $('finish-note').textContent = t(live ? 'finish_live' : 'finish_offline');
    $('confirm-delegate').disabled = blocked || confirming || !view.counts.unanswered;
    $('continue-answering').disabled = submitting || Boolean(composition);
    if (!$('finish-confirmation').hidden) {
      $('finish-message').textContent = t('finish_missing', { count: view.counts.unanswered });
      if (!view.counts.unanswered) {
        const wasInside = document.activeElement === $('finish-message') || document.activeElement === $('confirm-delegate') || document.activeElement === $('continue-answering');
        $('finish-confirmation').hidden = true;
        if (wasInside) $('finish').focus();
      }
    }
    $('reset-all').disabled = blocked || confirming || !hasInput;
    $('confirm-reset').disabled = blocked || !hasInput;
    $('confirm-reset').textContent = t(submittingAction === 'reset' ? 'submitting' : 'reset_confirm');
    $('confirm-reset').setAttribute('aria-busy', String(submittingAction === 'reset'));
    $('cancel-reset').disabled = submitting;
  }

  function updateCounts() {
    const c = view.counts;
    $('counts').textContent = t(aiDelegation && c.unanswered ? 'counts_delegated' : 'counts', c);
    const conditional = [];
    if (c.waiting) conditional.push(t('waiting_count', { count: c.waiting }));
    if (c.inactive) conditional.push(t('inactive_count', { count: c.inactive }));
    $('conditional-status').hidden = !conditional.length;
    $('conditional-status').textContent = t('conditional_counts', { total: c.total, conditions: conditional.join(t('list_separator')) });
    return c;
  }

  function render(force = false) {
    const c = updateCounts();
    const focus = document.activeElement;
    const focusedQuestion = focus?.closest?.('.question')?.dataset.question;
    const editorKind = focus?.dataset?.editorKind || 'answer';
    const canKeepEditor = focus instanceof HTMLTextAreaElement && focus.isConnected
      && view.states[focusedQuestion] === 'active' && question(focusedQuestion)?.version === Number(focus.dataset.questionVersion)
      && Object.hasOwn(editorSessions(editorKind), focusedQuestion)
      && (editorKind === 'defer' ? record(focusedQuestion)?.status === 'deferred' : record(focusedQuestion)?.status !== 'deferred')
      && !conflict && !submitted && !submitting;
    if (!force && canKeepEditor) {
      updateQuestionStatuses();
      updateActions();
      return;
    }
    if (composition && (!canKeepEditor || force)) composition = null;
    rendering = true;
    try {
    const focusKey = focus?.dataset?.focus;
    const selection = focus instanceof HTMLTextAreaElement ? [focus.selectionStart, focus.selectionEnd] : null;
    const oldTop = focusedQuestion ? focus.closest('.question').getBoundingClientRect().top : null;
    const expanded = new Set([...$('questions').querySelectorAll('details[open]')].map(d => d.dataset.question));
    pages = makePages();
    const anchorPage = pageAnchor ? pages.findIndex(p => p.questions.some(q => q.id === pageAnchor)) : -1;
    pageIndex = anchorPage >= 0 ? anchorPage : Math.min(pageIndex, Math.max(0, pages.length - 1));
    pageAnchor = pages[pageIndex]?.questions[0]?.id || null;
    const active = orderedQuestions().filter(q => view.states[q.id] === 'active');
    const visible = pages[pageIndex]?.questions || [];
    $('core-guidance').hidden = !visible.some(q => q.importance === 'core');
    $('core-guidance').textContent = t('core_guidance');
    $('range').textContent = visible.length ? t('question_range', { start: active.indexOf(visible[0]) + 1, end: active.indexOf(visible.at(-1)) + 1 }) : '';
    $('questions').replaceChildren(...visible.map(q => renderQuestion(q, active.indexOf(q) + 1)));
    if (!visible.length) $('questions').append(element('p', 'empty', t('empty_questions')));
    for (const details of $('questions').querySelectorAll('details')) if (expanded.has(details.dataset.question)) details.open = true;
    $('page-select').replaceChildren(...pages.map((p, i) => {
      const option = element('option', '', t('page_option', { page: i + 1, pages: pages.length, group: p.group.label })); option.value = String(i); option.selected = i === pageIndex; return option;
    }));
    $('page-select').hidden = pages.length < 2;
    updateActions();
    if (focusKey) {
      const replacement = [...$('questions').querySelectorAll('[data-focus]')].find(node => node.dataset.focus === focusKey);
      if (replacement) {
        replacement.focus({ preventScroll: true });
        if (selection && replacement instanceof HTMLTextAreaElement) replacement.setSelectionRange(...selection);
        if (oldTop !== null) window.scrollBy(0, replacement.closest('.question').getBoundingClientRect().top - oldTop);
      }
    }
    if (lastActiveCount !== null && c.active > lastActiveCount && !paused) $('notice').textContent = t('questions_added', { added: c.active - lastActiveCount, active: c.active });
    lastActiveCount = c.active;
    } finally { rendering = false; }
  }

  function focusQuestion(id) {
    const target = [...$('questions').querySelectorAll('.question')].find(q => q.dataset.question === id);
    const control = [...(target?.querySelectorAll('input,textarea,button') || [])].find(node => {
      const details = node.closest('details');
      return !node.disabled && !node.hidden && (!details || details.open);
    });
    control?.focus({ preventScroll: true });
  }

  function goPage(index, targetId) {
    if (composition || submitted || submitting) return;
    if (index < 0 || index >= pages.length) return;
    const targetAnchor = targetId || pages[index].questions[0].id;
    flushTextDrafts(true);
    $('finish-confirmation').hidden = true;
    pageIndex = index; pageAnchor = targetAnchor;
    $('notice').textContent = ''; render(true); saveLocal();
    focusQuestion(targetId || pageAnchor);
    window.scrollTo(0, 0);
  }

  function unansweredOn(questions) { return questions.find(q => view.states[q.id] === 'active' && (!record(q.id) || record(q.id).status === 'answered' && !valueValid(q, record(q.id).value))); }
  function revealUnanswered(q) {
    const index = pages.findIndex(p => p.questions.some(v => v.id === q.id));
    if (index >= 0) goPage(index, q.id);
    $('notice').textContent = t('answer_or_defer', { title: q.title });
    const card = [...$('questions').querySelectorAll('.question')].find(node => node.dataset.question === q.id);
    card?.scrollIntoView({ block: 'center' });
  }

  function download(envelope = null, suffix = 'answers') {
    flushTextDrafts(true);
    const partial = validatedPartialDrafts(partialMulti, answers);
    const recovery = !envelope && Object.keys(partial).length > 0;
    const exported = envelope || (recovery ? { action: 'restore_draft', answers, partial_multi: partial, reset_pending: !live && resetPending }
      : !live && resetPending ? { action: 'reset_answers', answers } : answers);
    const blob = new Blob([JSON.stringify(exported, null, 2) + '\n'], { type: 'application/json' });
    const url = URL.createObjectURL(blob); const a = element('a'); a.href = url;
    a.download = `${questionnaire.project_id.replace(/[^a-zA-Z0-9_-]/g, '_')}-${recovery ? 'recovery' : suffix}.json`;
    a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    if (recovery) $('notice').textContent = t('draft_exported');
  }

  function resumeMessage() {
    const resume = boot.resume;
    if (!resume || resume.run_id !== questionnaire.run_id || resume.project_id !== questionnaire.project_id
      || typeof resume.workspace !== 'string' || !/^(?:[A-Za-z]:[\\/]|\/)/.test(resume.workspace)
      || /[\r\n\x00]/.test(resume.workspace) || (boot.token && resume.workspace.includes(boot.token))) return null;
    const message = t('resume_message', { project: resume.project_id, run: resume.run_id, workspace: resume.workspace });
    return live ? message : message + '\n\n' + t('resume_offline_note');
  }

  function addResumeTools(section) {
    const message = resumeMessage();
    if (!message) return;
    const tools = element('div', 'resume-tools');
    const button = element('button', 'text-button', t('resume_copy')); button.type = 'button';
    const field = element('textarea', 'resume-text');
    field.value = message; field.readOnly = true; field.hidden = true; field.dir = 'auto';
    field.setAttribute('aria-label', t('resume_label'));
    const feedback = element('p', 'resume-status'); feedback.setAttribute('role', 'status');
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        if (!globalThis.navigator?.clipboard?.writeText) throw new Error('Clipboard unavailable');
        await globalThis.navigator.clipboard.writeText(message);
        feedback.textContent = t('resume_copied');
      } catch {
        field.hidden = false;
        field.focus(); field.select();
        feedback.textContent = t('resume_manual');
      } finally { button.disabled = false; }
    });
    tools.append(button, field, feedback); section.append(tools);
  }

  function complete(event) {
    const section = $('completion'); section.replaceChildren(); section.hidden = false;
    const held = questionnaire.questions.filter(q => view.states[q.id] === 'active' && record(q.id)?.status === 'deferred');
    const title = element('h2', '', event === 'ai_requested' ? t(live ? 'ai_request_title' : 'ai_request_offline_title')
      : live ? t('answers_delivered') : t('answers_downloaded'));
    title.tabIndex = -1; section.append(title);
    if (held.length) { section.append(element('p', '', t('deferred_complete', { count: held.length }))); const ul = element('ul'); held.forEach(q => ul.append(element('li', '', q.title))); section.append(ul); }
    section.append(element('p', '', event === 'ai_requested' ? t(live ? 'ai_request_live' : 'ai_request_offline') : live ? t('complete_live') : t('complete_offline')));
    addResumeTools(section);
    title.focus(); section.scrollIntoView({ block: 'center' });
  }

  function versionPayload() {
    return { run_id: questionnaire.run_id, project_id: questionnaire.project_id, revision: questionnaire.revision, base_answer_revision: authoritative.answers.answer_revision };
  }

  async function waitForSaves() {
    while (queue.length || saving) {
      if (paused) throw new Error(t('save_incomplete'));
      if (!saving) await pump();
      else await new Promise(resolve => setTimeout(resolve, 50));
    }
    if (paused) throw new Error(t('save_incomplete'));
  }

  async function delegateUnanswered() {
    if (!live) {
      download({ action: 'delegate_unanswered', answers: copy(answers), ...(resetPending ? { reset_all: true } : {}) }, 'ai-request');
      complete('ai_requested');
      return;
    }
    const result = await responseJson(await fetch(api('/api/delegate'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(versionPayload()) }));
    if (result.view) { authoritative = result.view; questionnaire = authoritative.questionnaire; project(); }
    submitted = true; submittedAction = 'ai_requested'; saveLocal(); render();
    $('save-status').textContent = t('ai_request_sent'); complete('ai_requested');
  }

  function toggleDelegation() {
    if (submitted || submitting || composition || conflict || live && paused || !$('reset-confirmation').hidden) return;
    flushTextDrafts(true);
    if (!aiDelegation && !view.counts.unanswered) return;
    aiDelegation = !aiDelegation;
    $('finish-confirmation').hidden = true;
    $('completion').hidden = true;
    saveLocal(); render();
  }

  async function confirmDelegate() {
    if ($('finish-confirmation').hidden || submitted || submitting || composition || conflict || live && paused) return;
    aiDelegation = true;
    saveLocal(); render();
    await finish();
  }

  function continueAnswering() {
    if (submitting || composition) return;
    $('finish-confirmation').hidden = true;
    const missing = unansweredOn(orderedQuestions());
    if (missing) revealUnanswered(missing);
    else { updateActions(); $('finish').focus(); }
  }

  function openReset() {
    if (submitted || submitting || composition || conflict || live && paused) return;
    $('finish-confirmation').hidden = true;
    $('reset-confirmation').hidden = false;
    updateActions(); $('cancel-reset').focus();
  }

  function cancelReset() {
    if (submitting) return;
    $('reset-confirmation').hidden = true;
    updateActions(); $('reset-all').focus();
  }

  async function resetAllAnswers() {
    if ($('reset-confirmation').hidden || submitted || submitting || composition || conflict || live && paused) return;
    flushTextDrafts(true);
    submitting = true; submittingAction = 'reset'; render();
    let resetSucceeded = false;
    try {
      if (live) {
        await waitForSaves();
        const result = await responseJson(await fetch(api('/api/reset'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(versionPayload()) }));
        authoritative = result.view || result; questionnaire = authoritative.questionnaire; answers = copy(authoritative.answers); queue = [];
      } else {
        for (const id of Object.keys(answers.answers)) archive(answers, id, 'browser_reset_all');
        answers.answers = {}; resetPending = true;
      }
      partialMulti = {}; clearTextDrafts(); pageIndex = 0; pageAnchor = null; aiDelegation = false;
      $('reset-confirmation').hidden = true; $('completion').hidden = true; $('finish-confirmation').hidden = true;
      project(); saveLocal(); render(true);
      $('notice').textContent = t('reset_complete');
      resetSucceeded = true;
    } catch (error) {
      if (!paused) showRecovery(error.status ? error.message : t('save_incomplete'), error.status === 409);
    } finally {
      submitting = false; submittingAction = null; render();
      if (resetSucceeded) { focusQuestion(pageAnchor); window.scrollTo(0, 0); }
    }
  }

  async function next() {
    if (submitted || submitting || composition) return;
    if (pageIndex < pages.length - 1) goPage(pageIndex + 1);
  }

  async function finish() {
    if (submitted || submitting || composition || conflict || live && paused || !$('reset-confirmation').hidden) return;
    flushTextDrafts(true);
    submitting = true; submittingAction = 'finish'; render();
    let needsDecision = false;
    try {
      if (live) await waitForSaves();
      project();
      if (!view.counts.active) { $('notice').textContent = t('empty_questions'); return; }
      if (view.counts.unanswered && !aiDelegation) {
        needsDecision = true;
        $('finish-confirmation').hidden = false;
        return;
      }
      $('finish-confirmation').hidden = true;
      if (view.counts.unanswered) {
        submittingAction = 'delegate'; render();
        await delegateUnanswered();
        return;
      }
      if (!view.traversal_complete) { $('notice').textContent = t('check_unanswered'); return; }
      submittingAction = 'submit'; render();
      if (!live) { download(resetPending ? { action: 'reset_answers', answers } : answers); complete(view.ready_to_build ? 'submitted' : 'deferred_review'); return; }
      const result = await responseJson(await fetch(api('/api/submit'), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(versionPayload()) }));
      if (result.view) { authoritative = result.view; questionnaire = authoritative.questionnaire; project(); }
      submitted = true; submittedAction = 'submitted'; saveLocal(); render();
      $('save-status').textContent = t('delivery_complete'); complete(result.event);
    } catch (error) {
      if (!paused) showRecovery(error.status ? error.message : t('save_incomplete'), error.status === 409);
    } finally {
      submitting = false; submittingAction = null; render();
      if (needsDecision) {
        $('finish-message').focus();
        $('finish-confirmation').scrollIntoView({ block: 'center' });
      }
    }
  }

  function restoreLocal() {
    let saved;
    try {
      const raw = localStorage.getItem(draftKey());
      if (!raw) return;
      saved = JSON.parse(raw);
      validateEnvelope(saved.answers);
      resetPending = !live && saved.reset_pending === true;
      pageAnchor = typeof saved.page_anchor === 'string' ? saved.page_anchor : null;
      if (saved.base_answer_revision !== authoritative.answers.answer_revision) throw new Error(t('base_changed'));
      aiDelegation = saved.ai_delegation === true;
      restoreTextDrafts(saved);
      partialMulti = validatedPartialDrafts(saved.partial_multi, saved.answers);
      if (live) {
        if (!Array.isArray(saved.queue)) return;
        queue = saved.queue.filter(op => question(op.id) && (op.record === null || ['answered', 'deferred'].includes(op.record?.status) && op.record.question_version === question(op.id).version && (op.record.status === 'deferred' || valueValid(question(op.id), op.record.value))));
      } else answers = copy(saved.answers);
      $('save-status').textContent = t('draft_restored');
    } catch {
      aiDelegation = false;
      try {
        validateEnvelope(saved?.answers, true);
        answers = copy(saved.answers); queue = []; paused = true; conflict = true;
        resetPending = !live && saved.reset_pending === true;
        restoreTextDrafts(saved);
        partialMulti = validatedPartialDrafts(saved.partial_multi, saved.answers);
        pageAnchor = typeof saved.page_anchor === 'string' ? saved.page_anchor : null;
        $('recovery').hidden = false;
        $('recovery-message').textContent = t('old_draft_conflict');
        $('retry-save').hidden = true; $('refresh-state').hidden = false;
        $('save-status').textContent = t('old_draft_status');
      } catch {
        $('notice').textContent = t('draft_restore_failed');
        try { const old = localStorage.getItem(draftKey()); if (old) localStorage.setItem(`${draftKey()}:recovery`, old); } catch { /* Recovery remains optional when storage is blocked. */ }
      }
    }
  }

  function restoreTextDrafts(saved) {
    for (const [id, value] of Object.entries(saved.text_drafts || {})) {
      const q = question(id);
      if (q?.type === 'text' && typeof value === 'string' && textLength(value) <= (q.max_length || 20000)) {
        textDrafts[id] = value;
        const session = saved.text_sessions?.[id];
        if (typeof session === 'string' && session.length <= 100) textSessions[id] = session;
      }
    }
    for (const [id, value] of Object.entries(saved.defer_drafts || {})) {
      const q = question(id);
      if (q && saved.answers?.answers?.[id]?.status === 'deferred' && typeof value === 'string' && textLength(value) <= 20000) {
        deferDrafts[id] = value;
        const session = saved.defer_sessions?.[id];
        if (typeof session === 'string' && session.length <= 100) deferSessions[id] = session;
      }
    }
  }

  function clearTextDrafts() {
    clearTimeout(draftSaveTimer);
    textDrafts = {}; textSessions = {}; deferDrafts = {}; deferSessions = {}; composition = null;
  }

  function persistCurrentText() {
    retainComposition();
    clearTimeout(draftSaveTimer); saveLocal();
  }

  $('questionnaire').addEventListener('submit', event => event.preventDefault());
  $('previous').addEventListener('click', () => goPage(pageIndex - 1));
  $('page-select').addEventListener('change', event => goPage(Number(event.target.value)));
  $('next').addEventListener('click', () => void next());
  $('delegate-unanswered-top').addEventListener('click', toggleDelegation);
  $('finish').addEventListener('click', () => void finish());
  $('confirm-delegate').addEventListener('click', () => void confirmDelegate());
  $('continue-answering').addEventListener('click', continueAnswering);
  $('reset-all').addEventListener('click', openReset);
  $('confirm-reset').addEventListener('click', () => void resetAllAnswers());
  $('cancel-reset').addEventListener('click', cancelReset);
  $('close-image').addEventListener('click', () => $('image-dialog').close());
  $('image-dialog').addEventListener('click', event => { if (event.target === $('image-dialog')) { const r = $('image-dialog').getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) $('image-dialog').close(); } });
  $('export-draft').addEventListener('click', () => download());
  $('export-recovery').addEventListener('click', () => download(null, 'recovery'));
  $('retry-save').addEventListener('click', () => { paused = false; conflict = false; $('recovery').hidden = true; updateActions(); void pump(); });
  $('refresh-state').addEventListener('click', async () => {
    download(null, 'recovery');
    try { localStorage.setItem(`${draftKey()}:recovery`, JSON.stringify({ answers, queue, partial_multi: partialMulti, reset_pending: resetPending, page_anchor: pageAnchor })); } catch { /* Download still provides a recovery copy. */ }
    try {
      const fresh = live ? await responseJson(await fetch(api('/api/state'))) : authoritative;
      authoritative = fresh.view || fresh; questionnaire = authoritative.questionnaire; answers = copy(authoritative.answers); queue = []; partialMulti = {}; paused = false; conflict = false; inFlight = null; submitted = false; submittedAction = null; resetPending = false; aiDelegation = false;
      clearTextDrafts();
      $('finish-confirmation').hidden = true;
      $('recovery').hidden = true; project(); render(true); saveLocal();
      $('save-status').textContent = t('state_refreshed');
    } catch (error) { $('recovery-message').textContent = t('input_retained', { message: error.status ? error.message : t('connection_failed') }); }
  });
  $('import-draft').hidden = live;
  if (!live) $('refresh-state').textContent = t('refresh_offline');
  $('import-draft').addEventListener('click', () => $('import-file').click());
  $('import-file').addEventListener('change', async event => {
    const file = event.target.files?.[0]; if (!file) return;
    try {
      if (file.size > 10 * 1024 * 1024) throw new Error(t('file_too_large'));
      let imported;
      try { imported = JSON.parse(await file.text()); } catch { throw new Error(t('invalid_json')); }
      if (imported?.action === 'delegate_unanswered') {
        validateEnvelope(imported.answers);
        if (Object.hasOwn(imported, 'reset_all') && typeof imported.reset_all !== 'boolean') throw new Error(t('invalid_answers'));
        $('notice').textContent = t('ai_request_import_notice');
        event.target.value = '';
        return;
      }
      const isDraft = imported?.action === 'restore_draft';
      const isReset = imported?.action === 'reset_answers';
      const envelope = isReset || isDraft ? imported.answers : imported;
      validateEnvelope(envelope);
      let partial = {};
      if (isDraft) {
        if (typeof imported.reset_pending !== 'boolean' || Object.keys(imported).some(key => !['action', 'answers', 'partial_multi', 'reset_pending'].includes(key))) throw new Error(t('invalid_draft'));
        partial = validatedPartialDrafts(imported.partial_multi, envelope, true);
      }
      answers = copy(envelope); resetPending = isReset || isDraft && imported.reset_pending; partialMulti = partial; paused = false; conflict = false; aiDelegation = false; clearTextDrafts(); $('recovery').hidden = true; $('finish-confirmation').hidden = true; project(); render(true); saveLocal(); $('notice').textContent = t(isDraft ? 'draft_imported' : 'file_imported');
    } catch (error) { $('notice').textContent = t('import_failed', { message: error.message }); }
    event.target.value = '';
  });
  $('transport-note').textContent = live ? t('transport_live') : t('transport_offline');
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') persistCurrentText(); });
  window.addEventListener('beforeunload', event => { persistCurrentText(); if (live && (queue.length || saving || paused || Object.keys(textDrafts).length || Object.keys(deferDrafts).length)) { event.preventDefault(); event.returnValue = ''; } });
  try {
    restoreLocal(); project(); render();
    if (live && queue.length) void pump();
  } catch (error) {
    $('counts').textContent = t('check_configuration'); $('notice').textContent = error.message; $('next').disabled = true; $('finish').disabled = true;
  }
})();
