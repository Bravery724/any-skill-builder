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
  const initialHTML = '<!doctype html>\n' + document.documentElement.outerHTML;
  let boot, questionnaire, answers, locale, numberFormat;
  function t(key, values = {}) {
    return String(locale.messages[key] ?? key).replace(/\{([A-Za-z][A-Za-z0-9_]*)\}/g, (match, name) => {
      if (!Object.hasOwn(values, name)) return match;
      return typeof values[name] === 'number' ? numberFormat.format(values[name]) : String(values[name]);
    });
  }
  try {
    boot = JSON.parse($('skill-builder-data').textContent);
    if (boot.format !== 'any-skill-builder-questionnaire' || boot.format_version !== 1
      || !boot.view?.questionnaire || !boot.view?.answers || !boot.locale?.messages) throw new Error('Unsupported questionnaire');
    questionnaire = copy(boot.view.questionnaire);
    answers = copy(boot.view.answers);
    locale = boot.locale;
    document.documentElement.lang = locale.language;
    document.documentElement.dir = locale.direction === 'rtl' ? 'rtl' : 'ltr';
    document.title = t('page_title');
    try { numberFormat = new Intl.NumberFormat(locale.language); } catch { numberFormat = new Intl.NumberFormat(); }
  } catch {
    $('counts').textContent = $('form-main').dataset.loadError;
    $('notice').textContent = $('form-main').dataset.regenerate;
    return;
  }

  const byId = new Map(questionnaire.questions.map(q => [q.id, q]));
  const cards = new Map();
  const editors = new Map();
  const choiceInputs = new Map();
  const ui = {};
  const archived = new Set();
  let pageIndex = 0, pages = [], view, composition = null, dirty = false;
  let lastExportState = '';
  const textLength = value => Array.from(value).length;
  const selectedIds = value => value && typeof value === 'object' && !Array.isArray(value)
    ? value.selected || [] : Array.isArray(value) ? value : typeof value === 'string' ? [value] : [];
  const customValue = value => value && typeof value === 'object' && !Array.isArray(value);

  function validSelected(q, selected, minimum = true) {
    const ids = q.options.map(o => o.id);
    return Array.isArray(selected) && selected.every(id => ids.includes(id))
      && new Set(selected).size === selected.length && selected.length <= (q.max_choices || ids.length)
      && (!minimum || selected.length >= (q.min_choices || 1))
      && !(selected.length > 1 && q.options.some(o => o.exclusive && selected.includes(o.id)));
  }

  function valueValid(q, value) {
    if (q.type === 'text') return typeof value === 'string' && !!value.trim() && textLength(value) <= (q.max_length || 20000);
    if (customValue(value)) {
      return Object.keys(value).every(key => ['other', 'selected'].includes(key))
        && typeof value.other === 'string' && !!value.other.trim() && textLength(value.other) <= (q.max_length || 20000)
        && Array.isArray(value.selected) && (q.type === 'multi' ? validSelected(q, value.selected, false)
          && !q.options.some(o => o.exclusive && value.selected.includes(o.id)) : value.selected.length === 0);
    }
    if (q.type === 'multi') return validSelected(q, value);
    return typeof value === 'string' && q.options.some(o => o.id === value);
  }

  function derive(envelope) {
    const states = {}, visiting = new Set();
    function resolve(id) {
      if (states[id]) return states[id];
      if (visiting.has(id)) throw new Error(t('cyclic_condition'));
      const q = byId.get(id);
      if (!q) throw new Error(t('missing_condition'));
      visiting.add(id);
      let waiting = false, inactive = false;
      for (const condition of q.when || []) {
        const parentState = resolve(condition.question_id);
        const parent = byId.get(condition.question_id), answer = envelope.answers[condition.question_id];
        if (parentState === 'inactive') inactive = true;
        else if (parentState === 'waiting') waiting = true;
        else if (!answer || !valueValid(parent, answer.value)) {
          const selected = envelope.pending_inputs?.[condition.question_id]?.selected || [];
          if (!('includes' in condition && selected.includes(condition.includes))) waiting = true;
        }
        else {
          let value = answer.value;
          if (customValue(value)) {
            if ('includes' in condition && value.selected.includes(condition.includes)) continue;
            if (!Object.hasOwn(answer, 'branch_value')) { waiting = true; continue; }
            value = answer.branch_value;
          }
          if ('equals' in condition ? value !== condition.equals : !selectedIds(value).includes(condition.includes)) inactive = true;
        }
      }
      visiting.delete(id);
      return states[id] = inactive ? 'inactive' : waiting ? 'waiting' : 'active';
    }
    questionnaire.questions.forEach(q => resolve(q.id));
    const counts = { total: questionnaire.questions.length, active: 0, answered: 0, unanswered: 0, waiting: 0, inactive: 0 };
    for (const q of questionnaire.questions) {
      if (states[q.id] !== 'active') { counts[states[q.id]]++; continue; }
      counts.active++;
      if (envelope.answers[q.id]?.status === 'answered' && valueValid(q, envelope.answers[q.id].value)) counts.answered++;
      else counts.unanswered++;
    }
    return { questionnaire, answers: envelope, states, counts, ready_to_build: !!counts.total && !counts.unanswered && !counts.waiting };
  }

  function stateFor(q, answer) {
    const value = answer?.value;
    if (q.type === 'text') return { text: typeof value === 'string' ? value : '' };
    return { selected: selectedIds(value), other_enabled: !!customValue(value), other_text: customValue(value) ? value.other : '' };
  }

  function answerFromState(q) {
    const state = ui[q.id];
    let value;
    if (q.type === 'text') value = state.text;
    else if (state.other_enabled && state.other_text.trim()) value = { other: state.other_text, selected: state.selected };
    else value = q.type === 'multi' ? state.selected : state.selected[0];
    if (!valueValid(q, value)) return null;
    return { status: 'answered', actor: 'user', question_version: q.version, rationale: '', value: copy(value) };
  }

  function archive(id, reason) {
    if (!answers.answers[id] || archived.has(id)) return;
    answers.history ||= [];
    answers.history.push({ question_id: id, answer: copy(answers.answers[id]), reason, at: new Date().toISOString() });
    archived.add(id);
  }

  function syncPendingInputs() {
    const pending = {};
    for (const q of questionnaire.questions) {
      const state = ui[q.id];
      if (q.type !== 'multi' || !state || answers.answers[q.id] || !state.selected.length
        || state.selected.length >= (q.min_choices || 1) || !validSelected(q, state.selected, false)) continue;
      pending[q.id] = { selected: copy(state.selected), other_enabled: state.other_enabled, other_text: '', question_version: q.version };
    }
    if (Object.keys(pending).length) answers.pending_inputs = pending;
    else delete answers.pending_inputs;
  }

  function project() {
    syncPendingInputs();
    view = derive(answers);
  }

  function invalidateHiddenAnswers() {
    for (const q of questionnaire.questions) {
      if (view.states[q.id] === 'active') continue;
      archive(q.id, 'parent_answer_changed');
      delete answers.answers[q.id];
      ui[q.id] = stateFor(q);
    }
    project();
  }

  function change(id, nextRecord, updateStructure = true) {
    const q = byId.get(id);
    if (!q || view.states[id] !== 'active') return;
    const before = answers.answers[id];
    const beforeValue = before ? JSON.stringify(before.value) : null;
    const nextValue = nextRecord ? JSON.stringify(nextRecord.value) : null;
    if (beforeValue !== nextValue || before?.actor === 'ai') {
      archive(id, 'browser_answer_changed');
      if (nextRecord) answers.answers[id] = copy(nextRecord);
      else delete answers.answers[id];
    }
    project();
    invalidateHiddenAnswers();
    updateSummary();
    if (updateStructure) render();
    dirty = currentState() !== lastExportState;
    updateSaveState();
  }

  function pendingDrafts() {
    const result = {};
    for (const q of questionnaire.questions) {
      if (q.type === 'text' || view.states[q.id] !== 'active') continue;
      const state = ui[q.id], answer = answers.answers[q.id];
      if ((!answer && state.selected.length) || (state.other_enabled && !state.other_text.trim())) result[q.id] = copy(state);
    }
    return result;
  }

  function currentState() { return JSON.stringify({ answers: answers.answers, inputs: ui }); }

  function updateSaveState() {
    $('save-state').textContent = t(dirty ? 'unsaved_changes' : boot.saved_at ? 'saved_snapshot' : 'save_guidance');
  }

  function makePages() {
    const result = [];
    for (const group of questionnaire.groups) {
      const active = questionnaire.questions.filter(q => q.group_id === group.id && view.states[q.id] === 'active');
      let batch = [], weight = 0;
      for (const q of active) {
        const cost = q.type === 'image' ? 2 : 1;
        if (batch.length && weight + cost > 2) { result.push({ group, questions: batch }); batch = []; weight = 0; }
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
    const value = boot.assets?.[raw];
    return typeof value === 'string' && /^data:image\/(?:png|jpeg|webp|gif|svg\+xml|avif);base64,[A-Za-z0-9+/=]+$/.test(value) ? value : null;
  }

  function valueLabel(q, value) {
    if (q.type === 'text') return String(value ?? '');
    const labels = selectedIds(value).map(id => q.options.find(o => o.id === id)?.label || id);
    if (customValue(value)) labels.push(value.other);
    return labels.join(t('list_separator'));
  }

  function recommendationDetails(q) {
    const details = element('details', 'evidence');
    details.append(element('summary', '', t('recommendation_details')));
    if (q.recommendation) {
      details.append(element('p', '', t('recommendation', { value: valueLabel(q, q.recommendation.value) })));
      details.append(element('p', '', q.recommendation.rationale));
      const assumptions = q.recommendation.assumptions || [];
      if (assumptions.length) details.append(element('p', '', t('assumptions', { values: assumptions.join(t('list_separator')) })));
      if (valueValid(q, q.recommendation.value)) {
        const use = element('button', 'text-button', t('use_recommendation')); use.type = 'button';
        use.addEventListener('click', () => {
          ui[q.id] = stateFor(q, { value: q.recommendation.value });
          change(q.id, answerFromState(q));
        });
        details.append(use);
      }
    }
    if (q.decision) details.append(element('p', '', t('decision', { decision: q.decision })));
    if (q.origin) details.append(element('p', '', t('origin_' + q.origin)));
    const sources = (q.source_ids || []).map(id => questionnaire.sources.find(s => s.id === id)).filter(Boolean);
    if (sources.length) {
      const list = element('ul');
      for (const source of sources) {
        const item = element('li'); const url = safeSourceUrl(source.url);
        if (url) { const a = element('a', '', source.title); a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer'; item.append(a); }
        else item.append(element('span', '', source.title));
        const status = t('source_' + source.status);
        item.append(document.createTextNode(t('list_separator') + (source.accessed_at ? t('source_meta', { status, date: source.accessed_at }) : status)));
        if (source.notes) item.append(element('div', '', source.notes));
        list.append(item);
      }
      details.append(list);
    }
    return details;
  }

  function choose(q, option, checked) {
    const state = ui[q.id];
    if (q.type === 'multi') {
      let selected = checked ? [...new Set([...state.selected, option.id])] : state.selected.filter(id => id !== option.id);
      if (checked && option.exclusive) { selected = [option.id]; state.other_enabled = false; state.other_text = ''; }
      else if (checked) selected = selected.filter(id => !q.options.find(o => o.id === id)?.exclusive);
      if (selected.length > (q.max_choices || q.options.length)) { $('notice').textContent = t('max_choices', { count: q.max_choices }); syncCard(q); return; }
      state.selected = q.options.map(o => o.id).filter(id => selected.includes(id));
    } else {
      state.selected = checked ? [option.id] : [];
      state.other_enabled = false; state.other_text = '';
    }
    $('notice').textContent = '';
    change(q.id, answerFromState(q));
  }

  function chooseOther(q, checked) {
    const state = ui[q.id];
    state.other_enabled = checked;
    if (checked) state.selected = q.type === 'multi' ? state.selected.filter(id => !q.options.find(o => o.id === id)?.exclusive) : [];
    else state.other_text = '';
    change(q.id, answerFromState(q));
    if (checked) editors.get(q.id)?.focus();
  }

  function optionInput(q, option, other = false) {
    const input = element('input');
    input.type = q.type === 'multi' ? 'checkbox' : 'radio';
    input.name = `answer-${q.id}`; input.value = other ? '' : option.id;
    input.dataset.focus = `${q.id}:${other ? 'custom' : option.id}`;
    if (other) input.dataset.other = 'true';
    (choiceInputs.get(q.id) || choiceInputs.set(q.id, []).get(q.id)).push({ input, option, other });
    input.addEventListener('change', () => other ? chooseOther(q, input.checked) : choose(q, option, input.checked));
    return input;
  }

  function textEditor(q, other = false) {
    const input = element('textarea', 'text-answer');
    input.id = `input-${q.id}`; input.name = `${other ? 'other' : 'answer'}-${q.id}`;
    input.setAttribute('aria-labelledby', other ? `title-${q.id} label-${q.id}` : `title-${q.id}`);
    input.dataset.focus = `${q.id}:text`; input.dir = 'auto';
    input.placeholder = q.placeholder || t('answer_placeholder');
    input.value = other ? ui[q.id].other_text : ui[q.id].text;
    const retain = () => {
      if (!input.isConnected || view.states[q.id] !== 'active') return;
      if (other) ui[q.id].other_text = input.value; else ui[q.id].text = input.value;
      change(q.id, answerFromState(q), false);
      const error = cards.get(q.id)?.querySelector('.field-error');
      if (error) {
        const tooLong = textLength(input.value) > (q.max_length || 20000);
        error.textContent = tooLong ? t('text_too_long', { count: q.max_length || 20000 }) : '';
        error.hidden = !tooLong;
        input.setAttribute('aria-invalid', String(tooLong));
      }
    };
    input.addEventListener('compositionstart', () => { composition = { id: q.id, input }; });
    input.addEventListener('input', retain);
    input.addEventListener('compositionend', () => { if (composition?.input === input) composition = null; retain(); });
    input.addEventListener('blur', () => { retain(); if (!composition) render(); });
    editors.set(q.id, input);
    return input;
  }

  function showImage(option, url, opener) {
    $('image-caption').textContent = option.label;
    $('enlarged-image').alt = option.description || option.label;
    $('enlarged-image').src = url;
    $('image-dialog').showModal(); $('close-image').focus();
    $('image-dialog').addEventListener('close', () => { if (opener.isConnected) opener.focus(); }, { once: true });
  }

  function imageOptions(q) {
    const grid = element('div', 'visual-options');
    for (const option of q.options) {
      const card = element('div', 'image-option');
      const preview = element('button', 'image-preview'); preview.type = 'button';
      preview.setAttribute('aria-label', t('enlarge_image', { label: option.label }));
      const img = element('img'); img.alt = option.description || option.label; img.loading = 'lazy';
      const input = optionInput(q, option), url = assetUrl(option.image);
      const failure = element('p', 'image-failure', t('image_failed')); failure.hidden = true;
      const fail = () => { img.hidden = true; preview.hidden = true; failure.hidden = false; };
      img.addEventListener('error', fail);
      if (url) { img.src = url; preview.addEventListener('click', () => showImage(option, url, preview)); } else fail();
      preview.append(img);
      const label = element('label', 'image-label'); label.append(input, element('span', '', option.label));
      card.append(preview, failure, label);
      if (option.description) card.append(element('p', 'image-description', option.description));
      grid.append(card);
    }
    return grid;
  }

  function questionCard(q) {
    const card = element('section', 'question'); card.dataset.question = q.id; card.setAttribute('aria-labelledby', `title-${q.id}`);
    const top = element('div', 'question-top'); top.append(element('span', 'number'));
    if (q.importance === 'core') { const label = element('span', 'core-label', t('core_label')); label.title = t('core_guidance'); top.append(label); }
    top.append(element('span', 'question-status'));
    const title = element('h2', '', q.title); title.id = `title-${q.id}`; title.tabIndex = -1;
    card.append(top, title);
    if (q.help) card.append(element('p', 'help', q.help));
    const actor = element('p', 'answer-actor', t('ai_answer')); card.append(actor);
    if (q.type === 'text') card.append(textEditor(q));
    else {
      const options = element('div', 'options'); options.setAttribute('role', q.type === 'multi' ? 'group' : 'radiogroup'); options.setAttribute('aria-labelledby', title.id);
      if (q.type === 'image') options.append(imageOptions(q));
      else for (const option of q.options) {
        const label = element('label', 'option'), labelCopy = element('span', 'option-copy');
        labelCopy.append(element('span', '', option.label));
        if (option.description) labelCopy.append(element('span', 'option-description', option.description));
        label.append(optionInput(q, option), labelCopy); options.append(label);
      }
      const otherLabel = element('label', 'option'); otherLabel.append(optionInput(q, null, true), element('span', 'option-copy', t('other_choice'))); options.append(otherLabel);
      const field = element('div', 'other-field');
      const label = element('label', 'other-label', t('other_label')); label.id = `label-${q.id}`; label.htmlFor = `input-${q.id}`;
      field.append(label, textEditor(q, true)); card.append(options, field);
    }
    const error = element('p', 'notice field-error'); error.id = `error-${q.id}`; error.hidden = true; error.setAttribute('role', 'status'); card.append(error);
    editors.get(q.id).setAttribute('aria-describedby', error.id);
    const partial = element('p', 'help partial-hint'); partial.hidden = true; card.append(partial);
    const footer = element('div', 'question-footer'); footer.append(recommendationDetails(q));
    const clear = element('button', 'clear-answer', t('clear_selection')); clear.type = 'button';
    clear.addEventListener('click', () => clearAnswer(q.id)); footer.append(clear); card.append(footer);
    cards.set(q.id, card); return card;
  }

  function syncCard(q) {
    const card = cards.get(q.id); if (!card) return;
    const record = answers.answers[q.id], state = ui[q.id];
    card.dataset.status = record ? 'answered' : 'unanswered';
    card.querySelector('.question-status').textContent = t(record ? 'question_status_answered' : 'question_status_unanswered');
    card.querySelector('.answer-actor').hidden = record?.actor !== 'ai';
    card.querySelector('.clear-answer').hidden = q.type === 'text' ? !state.text : !state.selected.length && !state.other_enabled && !state.other_text;
    for (const { input, option, other } of choiceInputs.get(q.id) || []) input.checked = other ? state.other_enabled : state.selected.includes(option.id);
    const field = card.querySelector('.other-field'); if (field) field.hidden = !state.other_enabled;
    const editor = editors.get(q.id), value = q.type === 'text' ? state.text : state.other_text;
    if (editor && document.activeElement !== editor && composition?.input !== editor && editor.value !== value) editor.value = value;
    const partial = card.querySelector('.partial-hint');
    partial.hidden = !(q.type === 'multi' && state.selected.length && !record);
    if (!partial.hidden) partial.textContent = t('partial_choices', { count: q.min_choices || 1 });
  }

  function updateSummary() {
    const countsText = t('counts', view.counts);
    if ($('counts').textContent !== countsText) $('counts').textContent = countsText;
    const parts = [];
    if (view.counts.waiting) parts.push(t('waiting_count', { count: view.counts.waiting }));
    if (view.counts.inactive) parts.push(t('inactive_count', { count: view.counts.inactive }));
    $('conditional-status').hidden = !parts.length;
    $('conditional-status').textContent = parts.length ? t('conditional_counts', { total: view.counts.total, conditions: parts.join(t('list_separator')) }) : '';
    for (const q of questionnaire.questions) syncCard(q);
  }

  function updateGoal() {
    const expanded = $('goal-summary').dataset.expanded === 'true';
    $('goal-toggle').hidden = !expanded && $('goal-text').scrollHeight <= $('goal-text').clientHeight + 1;
    $('goal-toggle').setAttribute('aria-expanded', String(expanded));
    $('goal-toggle').textContent = t(expanded ? 'goal_collapse' : 'goal_expand');
  }

  function render() {
    const previousAnchor = pages[pageIndex]?.questions[0]?.id;
    pages = makePages();
    const anchored = pages.findIndex(page => page.questions.some(q => q.id === previousAnchor));
    pageIndex = Math.max(0, Math.min(anchored < 0 ? pageIndex : anchored, pages.length - 1));
    const current = pages[pageIndex];
    const nodes = current ? current.questions.map(q => cards.get(q.id) || questionCard(q)) : [element('p', 'empty', t('empty_questions'))];
    const existing = Array.from($('questions').children);
    if (existing.length !== nodes.length || nodes.some((node, i) => existing[i] !== node)) $('questions').replaceChildren(...nodes);
    const options = pages.map((page, index) => { const option = element('option', '', t('page_option', { page: index + 1, pages: pages.length, group: page.group.label })); option.value = String(index); return option; });
    $('page-select').replaceChildren(...options); $('page-select').value = String(pageIndex); $('page-select').disabled = pages.length < 2;
    $('section-label').textContent = current?.group.label || '';
    $('previous').disabled = pageIndex === 0; $('next').disabled = pageIndex >= pages.length - 1;
    $('save-answers').disabled = !questionnaire.questions.length;
    const active = questionnaire.questions.filter(q => view.states[q.id] === 'active');
    for (const q of current?.questions || []) cards.get(q.id).querySelector('.number').textContent = t('question_number', { number: active.indexOf(q) + 1 });
    updateSummary(); updateGoal();
  }

  function flushEditors() {
    for (const [id, input] of editors) {
      if (!input.isConnected || view.states[id] !== 'active') continue;
      const q = byId.get(id), state = ui[id];
      const previous = q.type === 'text' ? state.text : state.other_text;
      if (previous === input.value || q.type !== 'text' && !state.other_enabled) continue;
      if (q.type === 'text') state.text = input.value;
      else state.other_text = input.value;
      change(id, answerFromState(q), false);
    }
  }

  function goPage(index) {
    flushEditors();
    pageIndex = Math.max(0, Math.min(index, pages.length - 1));
    render(); window.scrollTo({ top: 0, behavior: 'instant' });
    $('questions').querySelector('h2')?.focus();
  }

  function clearAnswer(id) {
    const q = byId.get(id); ui[id] = stateFor(q);
    const editor = editors.get(id); if (editor) editor.value = '';
    if (composition?.id === id) composition = null;
    change(id, null);
    (choiceInputs.get(id)?.[0]?.input || editor)?.focus();
  }

  function resetAllAnswers() {
    for (const q of questionnaire.questions) { archive(q.id, 'reset_all'); ui[q.id] = stateFor(q); }
    answers.answers = {}; composition = null;
    for (const input of editors.values()) input.value = '';
    project(); pageIndex = 0; render();
    dirty = currentState() !== lastExportState; updateSaveState();
    $('reset-dialog').close(); $('notice').textContent = t('reset_complete');
  }

  function exportIdentity() {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    const bytes = new Uint8Array(16);
    if (globalThis.crypto?.getRandomValues) globalThis.crypto.getRandomValues(bytes);
    else for (let index = 0; index < bytes.length; index++) bytes[index] = Math.floor(Math.random() * 256);
    bytes[6] = (bytes[6] & 15) | 64;
    bytes[8] = (bytes[8] & 63) | 128;
    const hex = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }

  function snapshot() {
    flushEditors();
    for (const q of questionnaire.questions) {
      if (view.states[q.id] !== 'active') continue;
      const raw = q.type === 'text' ? ui[q.id].text : ui[q.id].other_enabled ? ui[q.id].other_text : '';
      if (textLength(raw) > (q.max_length || 20000)) {
        const targetPage = pages.findIndex(page => page.questions.some(item => item.id === q.id));
        if (targetPage >= 0) goPage(targetPage);
        editors.get(q.id)?.focus();
        throw new Error(t('text_too_long', { count: q.max_length || 20000 }));
      }
    }
    const exported = copy(boot);
    exported.saved_at = new Date().toISOString();
    exported.export_id = exportIdentity();
    exported.view = copy(view);
    exported.view.answers.answer_revision = boot.base_answer_revision;
    delete exported.view.answers.pending_inputs;
    exported.drafts = pendingDrafts();
    exported.page_anchor = pages[pageIndex]?.questions[0]?.id || null;
    return exported;
  }

  function serialize(exported = snapshot()) {
    const escaped = JSON.stringify(exported).replace(/&/g, '\\u0026').replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
    const pattern = /(<script\b[^>]*\bid="skill-builder-data"[^>]*>)[\s\S]*?(<\/script\s*>)/gi;
    let matches = 0;
    const result = initialHTML.replace(pattern, (_, start, end) => { matches++; return start + escaped + end; });
    if (matches !== 1) throw new Error(t('save_failed'));
    return result;
  }

  function saveAnswers() {
    let url;
    try {
      const exported = snapshot();
      url = URL.createObjectURL(new Blob([serialize(exported)], { type: 'text/html;charset=utf-8' }));
      const link = element('a'); link.href = url; link.download = 'questionnaire.html'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      lastExportState = currentState(); dirty = false;
      $('save-state').textContent = t('download_started');
      $('save-message').textContent = t('download_started');
      $('save-summary').textContent = t('save_summary', { answered: view.counts.answered, unanswered: view.counts.unanswered + view.counts.waiting });
      $('save-dialog').showModal(); $('close-save').focus();
    } catch (error) {
      if (url) URL.revokeObjectURL(url);
      $('notice').textContent = error.message || t('save_failed');
    }
  }

  try {
    for (const q of questionnaire.questions) {
      const record = answers.answers[q.id];
      if (record && (record.status !== 'answered' || record.question_version !== q.version || !valueValid(q, record.value))) throw new Error(t('invalid_answers'));
      ui[q.id] = stateFor(q, record);
      const draft = boot.drafts?.[q.id];
      if (draft && q.type !== 'text' && validSelected(q, draft.selected || [], false)
        && typeof draft.other_enabled === 'boolean' && typeof draft.other_text === 'string') ui[q.id] = copy(draft);
    }
    project();
    pages = makePages();
    if (boot.page_anchor) pageIndex = Math.max(0, pages.findIndex(page => page.questions.some(q => q.id === boot.page_anchor)));
    $('goal-text').textContent = questionnaire.goal;
    render(); lastExportState = currentState(); updateSaveState();
  } catch (error) {
    $('counts').textContent = t('load_failed'); $('notice').textContent = error.message;
    $('save-answers').disabled = true; return;
  }
  $('questionnaire').addEventListener('submit', event => event.preventDefault());
  $('previous').addEventListener('click', () => goPage(pageIndex - 1));
  $('next').addEventListener('click', () => goPage(pageIndex + 1));
  $('page-select').addEventListener('change', event => goPage(Number(event.target.value)));
  $('save-answers').addEventListener('click', saveAnswers);
  $('close-save').addEventListener('click', () => $('save-dialog').close());
  $('reset-all').addEventListener('click', () => $('reset-dialog').showModal());
  $('cancel-reset').addEventListener('click', () => $('reset-dialog').close());
  $('confirm-reset').addEventListener('click', resetAllAnswers);
  $('close-image').addEventListener('click', () => $('image-dialog').close());
  $('goal-toggle').addEventListener('click', () => { $('goal-summary').dataset.expanded = String($('goal-summary').dataset.expanded !== 'true'); updateGoal(); });
  window.addEventListener('resize', updateGoal);
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  if (typeof ResizeObserver === 'function') {
    new ResizeObserver(updateGoal).observe($('goal-text'));
    const bar = document.querySelector('.savebar');
    new ResizeObserver(() => document.documentElement.style.setProperty('--footer-space', `${Math.ceil(bar.getBoundingClientRect().height) + 55}px`)).observe(bar);
  }
})();
