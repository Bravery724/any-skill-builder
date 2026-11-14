import test from 'node:test';
import assert from 'node:assert/strict';
import { setup, makeBoot, copy, delay } from './form_harness.mjs';

const delegateIds = ['delegate-unanswered-top'];
function assertDelegationDisabled(env, expected) {
  for (const id of delegateIds) assert.equal(env.ids.get(id).disabled, expected, id);
}

function actionBoot(transport = 'live', language = 'en') {
  const boot = makeBoot(transport, language);
  boot.view.answers.answers.other = { status: 'deferred', actor: 'user', question_version: 1, rationale: 'Review later' };
  delete boot.view.answers.answers.last;
  return boot;
}

function createEnv(t, boot = actionBoot(), storage) {
  const env = setup(boot, storage);
  t.after(() => env.dispose());
  return env;
}

function type(node, value, composing = false) {
  node.value = value;
  node.dispatch('input', { isComposing: composing, inputType: composing ? 'insertCompositionText' : 'insertText' });
}

function delegateAndFinish(env) {
  if (env.ids.get('delegate-unanswered-top').getAttribute('aria-pressed') !== 'true') env.ids.get('delegate-unanswered-top').click();
  return env.api.finish();
}

for (const [language, label] of [['en', 'Skill to build'], ['ko', '만들 스킬']]) {
  test(`The ${language} goal summary shows the saved request as text without changing answers`, t => {
    const boot = makeBoot('live', language);
    boot.view.questionnaire.goal = 'Build a skill: <img src=x onerror="alert(1)"> 한글 요청';
    const env = createEnv(t, boot);
    assert.equal(env.ids.get('goal-summary').hidden, false);
    assert.equal(env.ids.get('goal-label').textContent, label);
    assert.equal(env.ids.get('goal-text').textContent, boot.view.questionnaire.goal);
    assert.equal(env.ids.get('goal-text').children.length, 0);
    assert.equal(env.ids.get('goal-toggle').hidden, true);
    assert.deepEqual(copy(env.api.answers), boot.view.answers);
    assert.equal(env.requests.length, 0);
  });
}

test('An overflowing goal can expand and collapse without losing answers or page position', t => {
  const boot = makeBoot('offline');
  boot.view.questionnaire.goal = 'Explain research clearly. '.repeat(30);
  const env = createEnv(t, boot);
  const summary = env.ids.get('goal-summary'), text = env.ids.get('goal-text'), toggle = env.ids.get('goal-toggle');
  text.scrollHeight = 180;
  Object.defineProperty(text, 'clientHeight', { get: () => summary.dataset.expanded === 'true' ? 180 : 48 });
  env.api.render();
  assert.equal(toggle.hidden, false);
  assert.equal(toggle.getAttribute('aria-expanded'), 'false');
  toggle.click();
  assert.equal(toggle.getAttribute('aria-expanded'), 'true');
  assert.equal(toggle.textContent, 'Show less');
  env.api.goPage(1);
  assert.equal(toggle.getAttribute('aria-expanded'), 'true');
  const page = env.ids.get('range').textContent;
  toggle.click();
  assert.equal(toggle.getAttribute('aria-expanded'), 'false');
  assert.equal(toggle.textContent, 'Show full request');
  assert.equal(env.ids.get('range').textContent, page);
  assert.equal(text.textContent, boot.view.questionnaire.goal);
  assert.deepEqual(copy(env.api.answers), boot.view.answers);
  assert.equal(env.requests.length, 0);
});

test('Loading the latest live record refreshes the goal summary with the saved goal', async t => {
  const boot = makeBoot();
  const env = createEnv(t, boot);
  env.ids.get('refresh-state').click();
  const request = env.pending.shift();
  assert.match(request.request.url, /^\/api\/state/);
  const fresh = copy(env.server);
  fresh.questionnaire.goal = 'Create a skill for accessible interface reviews.';
  request.resolve({ ok: true, json: async () => fresh });
  await delay(0);
  assert.equal(env.ids.get('goal-text').textContent, fresh.questionnaire.goal);
  assert.deepEqual(copy(env.api.answers), boot.view.answers);
});

for (const questionType of ['single', 'image']) {
  test(`Clearing a ${questionType} selection saves an unanswered question before handing it to AI`, async t => {
    const boot = makeBoot();
    const question = boot.view.questionnaire.questions.find(q => q.id === 'other');
    question.type = questionType;
    if (questionType === 'image') {
      for (const option of question.options) option.image = `assets/${option.id}.svg`;
    }
    const env = createEnv(t, boot);
    if (questionType === 'image') env.api.goPage(1);
    const card = () => env.ids.get('questions').querySelectorAll('.question').find(node => node.dataset.question === 'other');
    assert.equal(card().querySelector('.question-status').textContent, 'Answered');
    card().querySelector('.clear-selection').click();
    assert.equal(card().querySelector('.question-status').textContent, 'Unanswered');
    assert.equal(card().querySelector('.clear-selection'), null);
    assert.equal(env.requests[0].body.changes.other, null);
    const handoff = delegateAndFinish(env);
    env.ack(); await delay(65);
    assert.equal(env.server.answers.answers.other, undefined);
    assert.match(env.requests.at(-1).url, /^\/api\/delegate/);
    env.ack(); await handoff;
  });
}

test('Erasing a text answer updates its status without replacing the editor and exports it as unanswered', async t => {
  const env = createEnv(t, makeBoot('offline', 'ko'));
  const editor = env.textarea('text');
  const card = editor.closest('.question');
  assert.equal(editor.placeholder, '답변을 입력하세요');
  assert.equal(card.querySelector('.question-status').textContent, '답변 완료');
  editor.focus(); type(editor, '');
  assert.equal(card.querySelector('.question-status').textContent, '미응답');
  assert.equal(env.textarea('text'), editor);
  assert.equal(env.api.view.counts.unanswered, 1);
  type(editor, '  ');
  await delegateAndFinish(env);
  const exported = JSON.parse(await env.downloads.at(-1).text());
  assert.equal(exported.answers.answers.text, undefined);
});

test('Unchecking the last multi-choice option returns the question to unanswered', t => {
  const env = createEnv(t, makeBoot('offline'));
  const gate = () => env.ids.get('questions').querySelectorAll('.question').find(node => node.dataset.question === 'gate');
  for (const value of ['b', 'a']) {
    const option = gate().querySelectorAll('input').find(input => input.value === value);
    option.checked = false;
    option.dispatch('change');
  }
  assert.equal(gate().querySelector('.question-status').textContent, 'Unanswered');
  assert.equal(env.api.answers.answers.gate, undefined);
});

test('The top AI control only selects delegation; Finish sends one request from the first page', async t => {
  const env = createEnv(t);
  assert.equal(env.textarea('last'), undefined);
  assertDelegationDisabled(env, false);
  const initial = env.server.answers.answers;
  env.ids.get('delegate-unanswered-top').click();
  assert.equal(env.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), 'true');
  assert.equal(env.requests.length, 0);
  assert.equal(env.downloads.length, 0);
  assert.deepEqual(copy(env.api.answers.answers), initial);
  env.ids.get('finish').click();
  env.ids.get('finish').click();
  await delay(0);
  assert.equal(env.requests.length, 1);
  assertDelegationDisabled(env, true);
  for (const id of delegateIds) {
    assert.equal(env.ids.get(id).textContent, actionBoot().locale.messages.delegate_selected);
    assert.notEqual(env.ids.get(id).getAttribute('aria-busy'), 'true');
  }
  assert.equal(env.ids.get('finish').textContent, actionBoot().locale.messages.submitting);
  assert.equal(env.ids.get('finish').getAttribute('aria-busy'), 'true');
  assert.equal(env.ids.get('next').textContent, actionBoot().locale.messages.next);
  assert.notEqual(env.ids.get('next').getAttribute('aria-busy'), 'true');
  assert.equal(env.requests.at(-1).url.startsWith('/api/delegate'), true);
  assert.deepEqual(env.requests.at(-1).body, {
    run_id: 'form-regression', project_id: 'form-regression', revision: 1, base_answer_revision: 1,
  });
  env.ack(); await delay(0);
  assert.deepEqual(env.server.answers.answers, initial);
  assert.equal(env.server.answers.answers.other.status, 'deferred');
  assert.match(env.ids.get('completion').textContent, /AI request accepted/);
  assert.equal(env.ids.get('reset-all').disabled, true);
  assertDelegationDisabled(env, true);
  for (const id of delegateIds) assert.notEqual(env.ids.get(id).getAttribute('aria-busy'), 'true');
});

test('AI delegation can be cancelled without answering, submitting, or downloading', t => {
  const boot = actionBoot('offline');
  delete boot.view.answers.answers.text;
  const env = createEnv(t, boot);
  const original = copy(env.api.answers);
  const status = () => env.textarea('text').closest('.question').querySelector('.question-status').textContent;
  const toggle = env.ids.get('delegate-unanswered-top');
  toggle.click();
  assert.equal(toggle.getAttribute('aria-pressed'), 'true');
  assert.equal(status(), boot.locale.messages.ai_pending);
  assert.equal(env.api.view.counts.unanswered, 2);
  assert.equal(env.ids.get('delegation-note').hidden, false);
  toggle.click();
  assert.equal(toggle.getAttribute('aria-pressed'), 'false');
  assert.equal(status(), boot.locale.messages.question_status_unanswered);
  assert.deepEqual(copy(env.api.answers), original);
  assert.equal(env.requests.length, 0);
  assert.equal(env.downloads.length, 0);
});

test('Next permits unanswered questions and remains navigation on the last page', async t => {
  const boot = actionBoot('offline');
  delete boot.view.answers.answers.text;
  const env = createEnv(t, boot);
  await env.api.next();
  assert.ok(env.textarea('last'));
  assert.equal(env.ids.get('next').disabled, true);
  await env.api.next();
  assert.equal(env.ids.get('finish').disabled, false);
  assert.equal(env.downloads.length, 0);
  assert.equal(env.requests.length, 0);
});

test('Finish without delegation shows all missing answers and Continue finds the first missing question', async t => {
  const boot = actionBoot('offline');
  delete boot.view.answers.answers.text;
  const env = createEnv(t, boot);
  env.api.goPage(1);
  await env.api.finish();
  assert.equal(env.ids.get('finish-confirmation').hidden, false);
  assert.match(env.ids.get('finish-message').textContent, /2/);
  assert.equal(env.document.activeElement, env.ids.get('finish-message'));
  assert.equal(env.downloads.length, 0);
  assert.equal(env.requests.length, 0);
  env.ids.get('continue-answering').click();
  assert.equal(env.ids.get('finish-confirmation').hidden, true);
  assert.equal(env.document.activeElement, env.textarea('text'));
  assert.equal(env.api.answers.answers.other.status, 'deferred');
});

test('The missing-answer prompt can delegate and finish immediately without visiting the last page', async t => {
  const env = createEnv(t, actionBoot('offline', 'ko'));
  const original = copy(env.api.answers.answers);
  await env.api.finish();
  assert.equal(env.ids.get('finish-confirmation').hidden, false);
  env.ids.get('confirm-delegate').click(); await delay(0);
  assert.equal(env.downloads.length, 1);
  const exported = JSON.parse(await env.downloads[0].text());
  assert.equal(exported.action, 'delegate_unanswered');
  assert.deepEqual(exported.answers.answers, original);
  assert.equal(env.ids.get('finish-confirmation').hidden, true);
  assert.equal(env.textarea('last'), undefined);
});

test('AI selection survives a matching draft resume and reset clears that selection', async t => {
  const boot = actionBoot('offline');
  const env = createEnv(t, boot);
  env.ids.get('delegate-unanswered-top').click();
  const resumed = createEnv(t, boot, new Map(env.storage));
  assert.equal(resumed.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), 'true');
  assert.equal(resumed.downloads.length, 0);
  resumed.api.openReset(); await resumed.api.resetAllAnswers();
  assert.equal(resumed.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), 'false');
  await resumed.api.finish();
  assert.equal(resumed.ids.get('finish-confirmation').hidden, false);
  assert.equal(resumed.downloads.length, 0);
});

test('A stale draft cannot restore AI delegation authorization', t => {
  const boot = actionBoot('offline');
  const env = createEnv(t, boot);
  env.ids.get('delegate-unanswered-top').click();
  const current = copy(boot); current.view.answers.answer_revision++;
  const resumed = createEnv(t, current, new Map(env.storage));
  assert.equal(resumed.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), 'false');
  assert.equal(resumed.ids.get('recovery').hidden, false);
  assert.equal(resumed.downloads.length, 0);
});

test('Importing another answer record clears the previously selected AI delegation', async t => {
  const env = createEnv(t, actionBoot('offline'));
  env.ids.get('delegate-unanswered-top').click();
  const incoming = copy(env.api.answers);
  env.ids.get('import-file').files = [{ size: 100, text: async () => JSON.stringify(incoming) }];
  env.ids.get('import-file').dispatch('change'); await delay(0);
  assert.equal(env.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), 'false');
  await env.api.finish();
  assert.equal(env.ids.get('finish-confirmation').hidden, false);
  assert.equal(env.downloads.length, 0);
});

test('Completing the last missing answer after choosing AI uses ordinary submission', async t => {
  const env = createEnv(t);
  env.ids.get('delegate-unanswered-top').click();
  env.api.change('last', { status: 'answered', value: 'User decided this too' });
  const finishing = env.api.finish();
  env.ack(); await delay(65);
  assert.match(env.requests.at(-1).url, /^\/api\/submit/);
  assert.equal(env.requests.some(item => item.url.startsWith('/api/delegate')), false);
  env.ack(); await finishing;
  assert.equal(env.server.answers.answers.other.status, 'deferred');
});

test('A newly activated unanswered branch is included in the final AI handoff', async t => {
  const boot = actionBoot('offline');
  boot.view.answers.answers.gate.value = ['b'];
  delete boot.view.answers.answers.text;
  const env = createEnv(t, boot);
  env.ids.get('delegate-unanswered-top').click();
  assert.equal(env.api.view.states.text, 'inactive');
  env.api.change('gate', { status: 'answered', value: ['a'] });
  assert.equal(env.api.view.states.text, 'active');
  assert.equal(env.api.view.counts.unanswered, 2);
  await env.api.finish();
  const exported = JSON.parse(await env.downloads[0].text());
  assert.deepEqual(exported.answers.answers.gate.value, ['a']);
  assert.equal(Object.hasOwn(exported.answers.answers, 'text'), false);
  assert.equal(Object.hasOwn(exported.answers.answers, 'last'), false);
  assert.equal(exported.answers.answers.other.status, 'deferred');
});

test('A failed draft save prevents Finish from sending a submission or delegation', async t => {
  const env = createEnv(t);
  env.ids.get('delegate-unanswered-top').click();
  const editor = env.textarea('text'); editor.focus(); type(editor, 'Unsaved draft to retain');
  const finishing = env.api.finish();
  const pending = env.pending.shift();
  assert.match(pending.request.url, /^\/api\/answers/);
  pending.resolve({ ok: false, status: 503, json: async () => ({ error: 'unavailable' }) });
  await finishing;
  assert.equal(env.ids.get('recovery').hidden, false);
  assert.equal(env.ids.get('retry-save').hidden, false);
  assert.equal(env.ids.get('finish').disabled, true);
  assert.equal(env.api.answers.answers.text.value, 'Unsaved draft to retain');
  assert.equal(env.requests.some(item => /^\/api\/(submit|delegate)/.test(item.url)), false);
});

test('Finish preserves an in-flight save conflict and protects the retained draft', async t => {
  const boot = actionBoot();
  const env = createEnv(t, boot);
  env.ids.get('delegate-unanswered-top').click();
  const editor = env.textarea('text'); editor.focus(); type(editor, 'Retain this conflicting draft');
  const finishing = env.api.finish();
  const pending = env.pending.shift();
  assert.match(pending.request.url, /^\/api\/answers/);
  pending.resolve({ ok: false, status: 409, json: async () => ({ error: 'stale_answers' }) });
  await finishing;
  assert.equal(env.ids.get('recovery').hidden, false);
  assert.equal(env.ids.get('recovery-message').textContent, boot.locale.messages.conflict);
  assert.equal(env.ids.get('retry-save').hidden, true);
  assert.equal(env.ids.get('refresh-state').hidden, false);
  assert.equal(env.ids.get('finish').disabled, true);
  assert.equal(env.ids.get('delegate-unanswered-top').disabled, true);
  assert.equal(env.textarea('text').disabled, true);
  assert.equal(env.textarea('text').value, 'Retain this conflicting draft');
  const retained = copy(env.api.answers);
  env.api.change('other', { status: 'answered', value: 'a' });
  await env.api.finish();
  assert.deepEqual(copy(env.api.answers), retained);
  assert.equal(env.requests.length, 1);
  assert.equal(env.requests.some(item => /^\/api\/(submit|delegate)/.test(item.url)), false);
});

test('AI delegation waits for current text and reason saves before using the latest revision', async t => {
  const env = createEnv(t);
  const node = env.textarea('text'); node.focus(); type(node, 'Current 한글 answer');
  const note = env.ids.get('questions').querySelectorAll('textarea').find(field => field.name === 'defer-reason-other');
  note.focus(); type(note, 'Need different 日本語 examples');
  const request = delegateAndFinish(env);
  assert.equal(env.requests.at(-1).body.changes.text.value, 'Current 한글 answer');
  assert.equal(env.requests.some(item => item.url.startsWith('/api/delegate')), false);
  env.ack(); await delay(0);
  assert.equal(env.requests.at(-1).body.changes.other.status, 'deferred');
  assert.equal(env.requests.at(-1).body.changes.other.rationale, 'Need different 日本語 examples');
  env.ack(); await delay(65);
  assert.equal(env.requests.at(-1).url.startsWith('/api/delegate'), true);
  assert.equal(env.requests.at(-1).body.base_answer_revision, env.server.answers.answer_revision);
  env.ack(); await request;
  assert.equal(env.server.answers.answers.text.value, 'Current 한글 answer');
  assert.equal(env.server.answers.answers.other.status, 'deferred');
});

test('Finish submits deferrals for chat review without requesting AI answers', async t => {
  const boot = makeBoot();
  boot.view.answers.answers.other = { status: 'deferred', actor: 'user', question_version: 1, rationale: 'Keep deferred' };
  const env = createEnv(t, boot);
  assert.equal(env.api.view.counts.unanswered, 0);
  assertDelegationDisabled(env, true);
  const finishing = env.api.finish(); await delay(0);
  assert.equal(env.requests.length, 1);
  assert.match(env.requests[0].url, /^\/api\/submit/);
  env.ack(); await finishing;
  assert.equal(env.server.answers.answers.other.status, 'deferred');
});

test('Global actions remain blocked during composition and conflict recovery', async t => {
  const env = createEnv(t);
  const node = env.textarea('text'); node.focus(); node.dispatch('compositionstart'); type(node, '작성 ㅈ', true);
  assertDelegationDisabled(env, true);
  assert.equal(env.ids.get('reset-all').disabled, true);
  await env.api.finish(); env.api.openReset();
  assert.equal(env.ids.get('reset-confirmation').hidden, true);
  assert.equal(env.requests.length, 0);
  node.dispatch('compositionend');
  env.api.showRecovery('Conflict', true);
  assertDelegationDisabled(env, true);
  await env.api.finish(); env.api.openReset();
  assert.equal(env.ids.get('reset-confirmation').hidden, true);
  assert.equal(env.requests.length, 0);
});

test('Reset requires explicit confirmation and can be cancelled without changing answers', async t => {
  const env = createEnv(t);
  const before = copy(env.api.answers);
  env.ids.get('reset-all').click();
  assert.equal(env.ids.get('reset-confirmation').hidden, false);
  assert.equal(env.requests.length, 0);
  assertDelegationDisabled(env, true);
  env.ids.get('cancel-reset').click();
  assert.equal(env.ids.get('reset-confirmation').hidden, true);
  assertDelegationDisabled(env, false);
  await env.api.resetAllAnswers();
  assert.equal(env.requests.length, 0);
  assert.deepEqual(copy(env.api.answers), before);
});

test('Live reset clears all answers and deferrals but retains questions and server history', async t => {
  const env = createEnv(t);
  const questions = env.server.questionnaire;
  const original = env.server.answers.answers;
  env.api.openReset(); env.ids.get('confirm-reset').focus();
  const resetting = env.api.resetAllAnswers(); await delay(0);
  assert.equal(env.requests.at(-1).url.startsWith('/api/reset'), true);
  assert.equal(env.ids.get('confirm-reset').textContent, actionBoot().locale.messages.submitting);
  assert.equal(env.ids.get('confirm-reset').getAttribute('aria-busy'), 'true');
  assert.equal(env.ids.get('next').textContent, actionBoot().locale.messages.next);
  env.ack(); await resetting;
  assert.deepEqual(env.server.answers.answers, {});
  assert.deepEqual(env.server.questionnaire, questions);
  assert.deepEqual(env.server.answers.history.map(entry => entry.question_id).sort(), Object.keys(original).sort());
  assert.equal(env.api.view.counts.deferred, 0);
  assert.equal(env.api.view.states.text, 'waiting');
  assert.equal(env.ids.get('reset-confirmation').hidden, true);
  assertDelegationDisabled(env, false);
  assert.equal(env.requests.some(item => item.url.startsWith('/api/delegate')), false);
  assert.equal(env.document.activeElement.name, 'answer-gate');
  assert.equal(env.document.activeElement.isConnected, true);
  assert.equal(env.document.activeElement.disabled, false);
  assert.equal(env.ids.get('confirm-reset').getAttribute('aria-busy'), 'false');
});

test('Live reset saves current drafts before resetting and does not restore them afterward', async t => {
  const env = createEnv(t);
  const node = env.textarea('text'); node.focus(); type(node, 'Draft to retain in history');
  env.api.openReset(); const resetting = env.api.resetAllAnswers();
  assert.equal(env.requests.at(-1).body.changes.text.value, 'Draft to retain in history');
  env.ack(); await delay(65);
  assert.equal(env.requests.at(-1).url.startsWith('/api/reset'), true);
  assert.equal(env.requests.at(-1).body.base_answer_revision, env.server.answers.answer_revision);
  env.ack(); await resetting;
  assert.deepEqual(env.server.answers.answers, {});
  assert.ok(env.server.answers.history.some(entry => entry.answer.value === 'Draft to retain in history'));
  const resumedBoot = actionBoot(); resumedBoot.view = env.server;
  const resumed = createEnv(t, resumedBoot, new Map(env.storage));
  assert.deepEqual(copy(resumed.api.answers.answers), {});
  assert.equal(resumed.textarea('text'), undefined);
});

test('A reset conflict preserves the current answers and freezes further mutations', async t => {
  const env = createEnv(t);
  const before = copy(env.api.answers.answers);
  env.api.openReset(); const resetting = env.api.resetAllAnswers(); await delay(0);
  const pending = env.pending.shift();
  pending.resolve({ ok: false, status: 409, json: async () => ({ error: 'stale_answers' }) });
  await resetting;
  assert.deepEqual(copy(env.api.answers.answers), before);
  assert.equal(env.ids.get('recovery').hidden, false);
  assertDelegationDisabled(env, true);
  assert.equal(env.ids.get('confirm-reset').disabled, true);
  assert.equal(env.ids.get('confirm-reset').getAttribute('aria-busy'), 'false');
  assert.notEqual(env.document.activeElement.name, 'answer-gate');
});

test('Reset preserves an in-flight save conflict instead of allowing retries or clearing answers', async t => {
  const boot = actionBoot();
  const env = createEnv(t, boot);
  const editor = env.textarea('text'); editor.focus(); type(editor, 'Keep this draft before reset');
  env.api.openReset();
  const resetting = env.api.resetAllAnswers();
  const pending = env.pending.shift();
  assert.match(pending.request.url, /^\/api\/answers/);
  pending.resolve({ ok: false, status: 409, json: async () => ({ error: 'stale_answers' }) });
  await resetting;
  assert.equal(env.ids.get('recovery-message').textContent, boot.locale.messages.conflict);
  assert.equal(env.ids.get('retry-save').hidden, true);
  assert.equal(env.ids.get('confirm-reset').disabled, true);
  assert.equal(env.textarea('text').disabled, true);
  assert.equal(env.api.answers.answers.text.value, 'Keep this draft before reset');
  assert.equal(env.api.answers.answers.other.status, 'deferred');
  assert.equal(env.requests.length, 1);
  assert.equal(env.requests.some(item => item.url.startsWith('/api/reset')), false);
});

for (const language of ['en', 'ko']) {
  test(`Offline delegation exports an explicit request while preserving answers and deferrals (${language})`, async t => {
    const env = createEnv(t, actionBoot('offline', language));
    const original = copy(env.api.answers.answers);
    await delegateAndFinish(env);
    const exported = JSON.parse(await env.downloads.at(-1).text());
    assert.equal(exported.action, 'delegate_unanswered');
    assert.equal(Object.hasOwn(exported, 'reset_all'), false);
    assert.deepEqual(exported.answers.answers, original);
    assert.equal(exported.answers.answer_revision, 1);
    assert.equal(env.requests.length, 0);
    assert.equal(env.ids.get('completion').hidden, false);
    assert.ok(env.ids.get('completion').textContent.includes(actionBoot('offline', language).locale.messages.ai_request_offline));
  });
}

test('Offline reset intent survives resume and regular export without changing the loaded revision', async t => {
  const env = createEnv(t, actionBoot('offline'));
  const original = copy(env.api.answers.answers);
  env.api.openReset(); env.ids.get('confirm-reset').focus(); await env.api.resetAllAnswers();
  assert.deepEqual(copy(env.api.answers.answers), {});
  assert.equal(env.document.activeElement.name, 'answer-gate');
  assert.equal(env.document.activeElement.isConnected, true);
  assert.equal(env.document.activeElement.disabled, false);
  assert.equal(env.api.answers.answer_revision, 1);
  assert.deepEqual(copy(env.api.answers.history.map(entry => entry.question_id)).sort(), Object.keys(original).sort());
  const resumed = createEnv(t, actionBoot('offline'), new Map(env.storage));
  resumed.api.download();
  const exported = JSON.parse(await resumed.downloads.at(-1).text());
  assert.equal(exported.action, 'reset_answers');
  assert.deepEqual(exported.answers.answers, {});
  assert.equal(exported.answers.answer_revision, 1);
  assert.equal(resumed.requests.length, 0);
});

test('Reset followed by offline AI delegation preserves newly entered answers and carries reset intent', async t => {
  const env = createEnv(t, actionBoot('offline'));
  env.api.openReset(); await env.api.resetAllAnswers();
  env.api.change('gate', { status: 'answered', value: ['a'] });
  env.api.change('other', { status: 'deferred', rationale: 'Keep this new deferral' });
  await delegateAndFinish(env);
  const exported = JSON.parse(await env.downloads.at(-1).text());
  assert.equal(exported.action, 'delegate_unanswered');
  assert.equal(exported.reset_all, true);
  assert.equal(exported.answers.answer_revision, 1);
  assert.deepEqual(exported.answers.answers.gate.value, ['a']);
  assert.equal(exported.answers.answers.other.status, 'deferred');
  assert.equal(Object.hasOwn(exported.answers.answers, 'text'), false);
  assert.equal(Object.hasOwn(exported.answers.answers, 'last'), false);
});

test('Importing an offline reset draft keeps its reset intent when exported again', async t => {
  const env = createEnv(t, actionBoot('offline'));
  const incoming = copy(env.api.answers); incoming.answers = {};
  const wrapped = { action: 'reset_answers', answers: incoming };
  env.ids.get('import-file').files = [{ size: 100, text: async () => JSON.stringify(wrapped) }];
  env.ids.get('import-file').dispatch('change'); await delay(0);
  env.api.download();
  assert.equal(JSON.parse(await env.downloads.at(-1).text()).action, 'reset_answers');
});

test('Reset pending alone does not request AI during ordinary offline submission', async t => {
  const env = createEnv(t, actionBoot('offline'));
  env.api.openReset(); await env.api.resetAllAnswers();
  env.api.change('gate', { status: 'deferred' });
  env.api.change('other', { status: 'deferred' });
  env.api.change('last', { status: 'deferred' });
  await env.api.finish();
  const exported = JSON.parse(await env.downloads.at(-1).text());
  assert.equal(exported.action, 'reset_answers');
  assert.equal(Object.hasOwn(exported, 'reset_all'), false);
  assert.equal(env.requests.length, 0);
});

test('Finish submits complete answers from the first page and owns the progress indicator', async t => {
  const boot = makeBoot();
  const env = createEnv(t, boot);
  const submitting = env.api.finish(); await delay(0);
  assert.equal(env.requests.at(-1).url.startsWith('/api/submit'), true);
  assert.equal(env.ids.get('finish').textContent, boot.locale.messages.submitting);
  assert.equal(env.ids.get('finish').getAttribute('aria-busy'), 'true');
  assert.equal(env.ids.get('next').textContent, boot.locale.messages.next);
  assert.notEqual(env.ids.get('next').getAttribute('aria-busy'), 'true');
  for (const id of delegateIds) {
    assert.equal(env.ids.get(id).textContent, boot.locale.messages.delegate_unanswered);
    assert.notEqual(env.ids.get(id).getAttribute('aria-busy'), 'true');
  }
  env.ack(); await submitting;
  assert.equal(env.ids.get('finish').getAttribute('aria-busy'), 'false');
});

test('Closing an image preview restores focus after a background save replaces its opener', async t => {
  const boot = makeBoot();
  const imageQuestion = boot.view.questionnaire.questions.find(q => q.id === 'other');
  imageQuestion.type = 'image';
  for (const option of imageQuestion.options) option.image = `assets/${option.id}.svg`;
  const env = createEnv(t, boot);
  env.api.goPage(1);
  env.api.change('last', { status: 'answered', value: 'Background save' });
  const opener = env.ids.get('questions').querySelector('.image-preview');
  opener.focus(); opener.click();
  assert.equal(env.document.activeElement, env.ids.get('close-image'));
  env.ack(); await delay(0);
  assert.equal(opener.isConnected, false);
  const current = env.ids.get('questions').querySelector('.image-preview');
  assert.notEqual(current, opener);
  env.ids.get('close-image').click();
  assert.equal(env.document.activeElement, current);
  assert.equal(env.document.activeElement.isConnected, true);
});

test('Closing a failed image preview focuses a visible enabled fallback', t => {
  const boot = makeBoot('offline');
  const imageQuestion = boot.view.questionnaire.questions.find(q => q.id === 'other');
  imageQuestion.type = 'image';
  imageQuestion.recommendation = { value: 'a', rationale: 'Test recommendation' };
  for (const option of imageQuestion.options) option.image = `assets/${option.id}.svg`;
  delete boot.view.answers.answers.other;
  const env = createEnv(t, boot);
  env.api.goPage(1);
  const card = env.ids.get('questions').querySelector('.question');
  card.querySelector('.image-preview').click();
  for (const img of card.querySelectorAll('img')) img.dispatch('error');
  env.ids.get('close-image').click();
  assert.equal(env.document.activeElement, card.querySelector('.hold'));
  assert.equal(env.document.activeElement.disabled, false);
});

for (const entry of ['toggle', 'confirmation']) {
  test(`Core questions remain AI-delegatable through ${entry} and the guidance follows visible pages`, async t => {
    const boot = actionBoot('offline', 'ko');
    boot.view.questionnaire.questions.find(q => q.id === 'other').importance = 'core';
    delete boot.view.answers.answers.other;
    const env = createEnv(t, boot);
    assert.equal(env.ids.get('core-guidance').hidden, false);
    assert.equal(env.ids.get('core-guidance').textContent, boot.locale.messages.core_guidance);
    env.api.goPage(1);
    assert.equal(env.ids.get('core-guidance').hidden, true);
    env.api.goPage(0);
    if (entry === 'toggle') {
      env.ids.get('delegate-unanswered-top').click();
      await env.api.finish();
    } else {
      await env.api.finish();
      assert.equal(env.ids.get('finish-confirmation').hidden, false);
      env.ids.get('confirm-delegate').click(); await delay(0);
    }
    assert.equal(env.downloads.length, 1);
    const exported = JSON.parse(await env.downloads[0].text());
    assert.equal(exported.action, 'delegate_unanswered');
    assert.equal(Object.hasOwn(exported.answers.answers, 'other'), false);
    assert.equal(exported.answers.answers.text.value, 'Initial answer');
  });
}

test('Questionnaires without core metadata retain their existing display and AI behavior', t => {
  const env = createEnv(t, actionBoot('offline'));
  assert.equal(env.ids.get('core-guidance').hidden, true);
  env.ids.get('delegate-unanswered-top').click();
  assert.equal(env.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), 'true');
});

function resumeBoot(transport = 'offline', language = 'en') {
  const boot = makeBoot(transport, language);
  boot.resume = { workspace: 'D:\\projects\\example-run', run_id: boot.view.questionnaire.run_id, project_id: boot.view.questionnaire.project_id };
  return boot;
}

for (const language of ['en', 'ko']) {
  test(`Offline resume copy preserves task identity and explains the required file handoff (${language})`, async t => {
    const boot = resumeBoot('offline', language);
    const env = createEnv(t, boot);
    let copied;
    env.navigator.clipboard = { writeText: async value => { copied = value; } };
    await env.api.finish();
    const panel = env.ids.get('completion');
    assert.equal(panel.querySelector('h2').textContent, boot.locale.messages.answers_downloaded);
    panel.querySelector('.resume-tools').querySelector('button').click(); await delay(0);
    assert.ok(copied.includes(boot.resume.workspace));
    assert.ok(copied.includes(boot.resume.run_id));
    assert.ok(copied.includes(boot.locale.messages.resume_offline_note));
    assert.equal(copied.includes(boot.token), false);
    assert.equal(copied.includes('127.0.0.1'), false);
    assert.equal(panel.querySelector('.resume-status').textContent, boot.locale.messages.resume_copied);
    assert.equal(panel.querySelector('.resume-text').hidden, true);
    assert.equal(env.requests.length, 0);
  });
}

for (const availability of ['missing', 'rejected']) {
  test(`Resume copy offers a selected read-only fallback when clipboard is ${availability}`, async t => {
    const boot = resumeBoot();
    const env = createEnv(t, boot);
    if (availability === 'rejected') env.navigator.clipboard = { writeText: async () => { throw new Error('Denied'); } };
    await env.api.finish();
    const panel = env.ids.get('completion');
    const button = panel.querySelector('.resume-tools').querySelector('button');
    button.click(); await delay(0);
    const field = panel.querySelector('.resume-text');
    assert.equal(field.hidden, false);
    assert.equal(field.readOnly, true);
    assert.equal(env.document.activeElement, field);
    assert.deepEqual([field.selectionStart, field.selectionEnd], [0, field.value.length]);
    assert.equal(panel.querySelector('.resume-status').textContent, boot.locale.messages.resume_manual);
    assert.equal(button.disabled, false);
  });
}

test('Live completion reports acceptance and defers host-read confirmation to chat', async t => {
  const boot = resumeBoot('live');
  const env = createEnv(t, boot);
  let copied;
  env.navigator.clipboard = { writeText: async value => { copied = value; } };
  const finishing = env.api.finish(); await delay(0); env.ack(); await finishing;
  const panel = env.ids.get('completion');
  assert.equal(panel.querySelector('h2').textContent, boot.locale.messages.answers_delivered);
  assert.match(panel.textContent, /will confirm.*after reading/);
  assert.equal(env.ids.get('save-status').textContent, boot.locale.messages.delivery_complete);
  panel.querySelector('.resume-tools').querySelector('button').click(); await delay(0);
  assert.equal(copied.includes(boot.locale.messages.resume_offline_note), false);
  assert.equal(copied.includes(boot.token), false);
  assert.equal(env.requests.length, 1);
});

for (const corrupt of ['foreign', 'url', 'token', 'newline']) {
  test(`Resume controls omit ${corrupt} task metadata instead of copying an unsafe or wrong locator`, async t => {
    const boot = resumeBoot();
    if (corrupt === 'foreign') boot.resume.run_id = 'another-run';
    if (corrupt === 'url') boot.resume.workspace = 'http://127.0.0.1:123/?token=' + boot.token;
    if (corrupt === 'token') boot.resume.workspace += '\\' + boot.token;
    if (corrupt === 'newline') boot.resume.workspace += '\nOther instructions';
    const env = createEnv(t, boot);
    await env.api.finish();
    assert.equal(env.ids.get('completion').querySelector('.resume-tools'), null);
  });
}

function partialBoot(language = 'en') {
  const boot = makeBoot('offline', language);
  boot.view.questionnaire.questions.find(q => q.id === 'gate').min_choices = 2;
  delete boot.view.answers.answers.gate;
  delete boot.view.answers.answers.text;
  boot.view.answers.answers.other = { status: 'deferred', actor: 'user', question_version: 1, rationale: 'Keep this choice for later' };
  return boot;
}

function selectMulti(env, value, selected = true) {
  const card = env.ids.get('questions').querySelectorAll('.question').find(node => node.dataset.question === 'gate');
  const control = card.querySelectorAll('input').find(node => node.value === value);
  control.checked = selected; control.dispatch('change');
}

function selectedMulti(env) {
  const card = env.ids.get('questions').querySelectorAll('.question').find(node => node.dataset.question === 'gate');
  return card.querySelectorAll('input').filter(node => node.checked).map(node => node.value);
}

async function importFile(env, data) {
  const text = JSON.stringify(data);
  env.ids.get('import-file').files = [{ size: Buffer.byteLength(text), text: async () => text }];
  env.ids.get('import-file').dispatch('change');
  await delay(0);
}

for (const language of ['en', 'ko']) {
  for (const control of ['export-draft', 'export-recovery']) {
    test(`Partial selections survive ${control} and an offline import without becoming answers (${language})`, async t => {
      const boot = partialBoot(language), original = createEnv(t, boot);
      selectMulti(original, 'a');
      original.ids.get(control).click();
      const exported = JSON.parse(await original.downloads.at(-1).text());
      assert.equal(exported.action, 'restore_draft');
      assert.deepEqual(exported.partial_multi, { gate: ['a'] });
      assert.equal(exported.reset_pending, false);
      assert.equal(exported.answers.answers.gate, undefined);
      assert.equal(exported.answers.answers.other.status, 'deferred');
      assert.equal(original.ids.get('notice').textContent, boot.locale.messages.draft_exported);

      const restored = createEnv(t, boot);
      await importFile(restored, exported);
      assert.deepEqual(selectedMulti(restored), ['a']);
      assert.equal(restored.api.answers.answers.gate, undefined);
      assert.equal(restored.api.view.counts.unanswered, 1);
      assert.equal(restored.api.view.states.text, 'waiting');
      assert.equal(restored.api.answers.answers.other.rationale, 'Keep this choice for later');
      assert.equal(restored.ids.get('notice').textContent, boot.locale.messages.draft_imported);
      assert.equal(restored.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), 'false');
      assert.equal(restored.requests.length, 0);
      const resumed = createEnv(t, boot, new Map(restored.storage));
      assert.deepEqual(selectedMulti(resumed), ['a']);
      selectMulti(resumed, 'b');
      resumed.api.change('text', { status: 'answered', value: 'Completed after draft recovery' });
      await resumed.api.finish();
      const finished = JSON.parse(await resumed.downloads.at(-1).text());
      assert.equal(Object.hasOwn(finished, 'action'), false);
      assert.equal(Object.hasOwn(finished, 'partial_multi'), false);
      assert.deepEqual(finished.answers.gate.value, ['a', 'b']);
      assert.equal(finished.answers.other.status, 'deferred');
    });
  }
}

test('Recovery after an explicit offline reset retains its reset intent through AI handoff', async t => {
  const boot = partialBoot(), original = createEnv(t, boot);
  original.api.openReset(); await original.api.resetAllAnswers();
  selectMulti(original, 'a');
  original.api.download();
  const exported = JSON.parse(await original.downloads.at(-1).text());
  assert.equal(exported.reset_pending, true);
  assert.deepEqual(exported.answers.answers, {});
  const restored = createEnv(t, boot);
  await importFile(restored, exported);
  assert.deepEqual(selectedMulti(restored), ['a']);
  await delegateAndFinish(restored);
  const request = JSON.parse(await restored.downloads.at(-1).text());
  assert.equal(request.action, 'delegate_unanswered');
  assert.equal(request.reset_all, true);
  assert.equal(Object.hasOwn(request, 'partial_multi'), false);
  assert.equal(request.answers.answer_revision, boot.view.answers.answer_revision);
  assert.deepEqual(request.answers.answers, {});
  assert.equal(request.answers.history.length, 2);
});

test('A stale browser draft keeps partial selections available in the recovery file', async t => {
  const boot = partialBoot(), original = createEnv(t, boot);
  selectMulti(original, 'a');
  const newerBoot = copy(boot); newerBoot.view.answers.answer_revision++;
  const conflicted = createEnv(t, newerBoot, new Map(original.storage));
  assert.deepEqual(selectedMulti(conflicted), ['a']);
  assert.equal(conflicted.ids.get('recovery').hidden, false);
  conflicted.ids.get('export-recovery').click();
  const exported = JSON.parse(await conflicted.downloads.at(-1).text());
  assert.equal(exported.action, 'restore_draft');
  assert.equal(exported.answers.answer_revision, boot.view.answers.answer_revision);
  assert.deepEqual(exported.partial_multi, { gate: ['a'] });
  const target = createEnv(t, newerBoot);
  const before = copy(target.api.answers);
  await importFile(target, exported);
  assert.deepEqual(copy(target.api.answers), before);
  assert.equal(target.ids.get('notice').textContent, 'Could not import: ' + boot.locale.messages.wrong_answer_revision);
});

for (const defect of ['run', 'questionnaire_revision', 'answer_revision', 'question_version', 'unknown_question', 'non_multi', 'unknown_option', 'duplicates', 'empty', 'already_complete', 'above_max', 'exclusive', 'inactive', 'answered', 'deferred', 'non_boolean_reset', 'missing_reset', 'array_drafts', 'extra_field', 'history_object', 'history_null', 'history_null_item', 'history_array_item', 'history_string_item', 'record_array', 'record_null', 'record_rationale', 'record_assumptions', 'record_actor', 'ai_missing_reason']) {
  test(`Malformed recovery file (${defect}) preserves the current answers, drafts, and delegation preference`, async t => {
    const boot = partialBoot();
    if (defect === 'exclusive') boot.view.questionnaire.questions.find(q => q.id === 'gate').min_choices = 3;
    if (defect === 'above_max') boot.view.questionnaire.questions.find(q => q.id === 'gate').max_choices = 2;
    if (defect === 'exclusive') boot.view.questionnaire.questions.find(q => q.id === 'gate').options[0].exclusive = true;
    if (defect === 'inactive') {
      boot.view.questionnaire.questions.find(q => q.id === 'gate').when = [{ question_id: 'other', equals: 'a' }];
      boot.view.answers.answers.other = { status: 'answered', actor: 'user', question_version: 1, value: 'b' };
    }
    const env = createEnv(t, boot);
    if (defect !== 'inactive') selectMulti(env, 'c');
    env.ids.get('delegate-unanswered-top').click();
    const before = copy(env.api.answers), stored = new Map(env.storage);
    const priorDelegation = env.ids.get('delegate-unanswered-top').getAttribute('aria-pressed');
    const incoming = { action: 'restore_draft', answers: copy(boot.view.answers), partial_multi: { gate: ['a'] }, reset_pending: false };
    if (defect === 'run') incoming.answers.run_id = 'another-run';
    if (defect === 'questionnaire_revision') incoming.answers.revision++;
    if (defect === 'answer_revision') incoming.answers.answer_revision++;
    if (defect === 'question_version') incoming.answers.answers.other.question_version++;
    if (defect === 'unknown_question') incoming.partial_multi = { missing: ['a'] };
    if (defect === 'non_multi') incoming.partial_multi = { other: ['a'] };
    if (defect === 'unknown_option') incoming.partial_multi.gate = ['missing'];
    if (defect === 'duplicates') incoming.partial_multi.gate = ['a', 'a'];
    if (defect === 'empty') incoming.partial_multi.gate = [];
    if (defect === 'already_complete' || defect === 'exclusive') incoming.partial_multi.gate = ['a', 'b'];
    if (defect === 'above_max') incoming.partial_multi.gate = ['a', 'b', 'c'];
    if (defect === 'answered') incoming.answers.answers.gate = { status: 'answered', actor: 'user', question_version: 1, value: ['a', 'b'] };
    if (defect === 'deferred') incoming.answers.answers.gate = { status: 'deferred', actor: 'user', question_version: 1, rationale: 'Keep deferred' };
    if (defect === 'non_boolean_reset') incoming.reset_pending = 'true';
    if (defect === 'missing_reset') delete incoming.reset_pending;
    if (defect === 'array_drafts') incoming.partial_multi = [];
    if (defect === 'extra_field') incoming.ai_delegation = true;
    if (defect === 'history_object') incoming.answers.history = {};
    if (defect === 'history_null') incoming.answers.history = null;
    if (defect === 'history_null_item') incoming.answers.history = [null];
    if (defect === 'history_array_item') incoming.answers.history = [[]];
    if (defect === 'history_string_item') incoming.answers.history = ['not an entry'];
    if (defect === 'record_array') incoming.answers.answers.other = [];
    if (defect === 'record_null') incoming.answers.answers.other = null;
    if (defect === 'record_rationale') incoming.answers.answers.other.rationale = {};
    if (defect === 'record_assumptions') incoming.answers.answers.other.assumptions = [null];
    if (defect === 'record_actor') incoming.answers.answers.other.actor = 'unknown';
    if (defect === 'ai_missing_reason') incoming.answers.answers.last.actor = 'ai';
    await importFile(env, incoming);
    assert.deepEqual(copy(env.api.answers), before);
    assert.deepEqual(env.storage, stored);
    assert.equal(env.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), priorDelegation);
    assert.ok(env.ids.get('notice').textContent.startsWith('Could not import:'));
    assert.equal(env.requests.length, 0);
    if (defect !== 'inactive') assert.deepEqual(selectedMulti(env), ['c']);
  });
}

test('Older answer files without history or optional record fields remain editable after import', async t => {
  const boot = makeBoot('offline'), env = createEnv(t, boot);
  const incoming = copy(boot.view.answers);
  delete incoming.history;
  for (const record of Object.values(incoming.answers)) { delete record.actor; delete record.rationale; }
  await importFile(env, incoming);
  assert.equal(env.ids.get('notice').textContent, boot.locale.messages.file_imported);
  env.api.change('other', { status: 'answered', value: 'b' });
  env.api.download();
  const exported = JSON.parse(await env.downloads.at(-1).text());
  assert.equal(exported.answers.other.value, 'b');
  assert.equal(exported.history.length, 1);
  assert.equal(exported.history[0].answer.value, 'a');
});

for (const language of ['en', 'ko']) {
  test(`An AI request file receives a chat handoff notice without applying answers or reset (${language})`, async t => {
    const boot = partialBoot(language), sender = createEnv(t, boot);
    sender.api.openReset(); await sender.api.resetAllAnswers();
    await delegateAndFinish(sender);
    const request = JSON.parse(await sender.downloads.at(-1).text());
    const target = createEnv(t, boot);
    selectMulti(target, 'c');
    if (language === 'ko') target.ids.get('delegate-unanswered-top').click();
    const priorDelegation = target.ids.get('delegate-unanswered-top').getAttribute('aria-pressed');
    const before = copy(target.api.answers), stored = new Map(target.storage);
    await importFile(target, request);
    assert.equal(target.ids.get('notice').textContent, boot.locale.messages.ai_request_import_notice);
    assert.deepEqual(copy(target.api.answers), before);
    assert.deepEqual(target.storage, stored);
    assert.deepEqual(selectedMulti(target), ['c']);
    assert.equal(target.ids.get('delegate-unanswered-top').getAttribute('aria-pressed'), priorDelegation);
    assert.equal(target.requests.length, 0);
  });
}

test('A foreign AI request file is rejected before the chat handoff notice', async t => {
  const boot = partialBoot(), env = createEnv(t, boot);
  const incoming = { action: 'delegate_unanswered', answers: copy(boot.view.answers) };
  incoming.answers.run_id = 'another-run';
  const before = copy(env.api.answers);
  await importFile(env, incoming);
  assert.equal(env.ids.get('notice').textContent, 'Could not import: ' + boot.locale.messages.wrong_envelope);
  assert.deepEqual(copy(env.api.answers), before);
  assert.equal(env.requests.length, 0);
});
