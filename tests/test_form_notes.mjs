import test from 'node:test';
import assert from 'node:assert/strict';
import { setup, makeBoot, delay } from './form_harness.mjs';

function deferredBoot(transport = 'live', language = 'en', id = 'other') {
  const boot = makeBoot(transport, language);
  boot.view.answers.answers[id] = { status: 'deferred', actor: 'user', question_version: 1, rationale: 'Need more examples' };
  return boot;
}

function createEnv(t, boot = deferredBoot(), storage) {
  const env = setup(boot, storage);
  t.after(() => env.dispose());
  return env;
}

const reason = (env, id = 'other') => env.ids.get('questions').querySelectorAll('textarea').find(node => node.name === `defer-reason-${id}`);
function inputValue(node, value, composing = false, start = value.length, end = start) {
  node.value = value;
  node.setSelectionRange(start, end);
  node.dispatch('input', { isComposing: composing, inputType: composing ? 'insertCompositionText' : 'insertText' });
}

for (const [language, label] of [['en', 'Reason for deferring (optional)'], ['ko', '보류한 이유 (선택)']]) {
  test(`The optional deferral note is localized in ${language} and appears only for deferred questions`, t => {
    const env = createEnv(t, deferredBoot('offline', language));
    assert.equal(env.ids.get('questions').querySelectorAll('.defer-label')[0].textContent, label);
    assert.equal(reason(env).value, 'Need more examples');
    assert.equal(reason(env, 'text'), undefined);
    assert.equal(env.api.view.counts.deferred, 1);
    assert.equal(env.api.view.ready_to_build, false);
  });
}

for (const [language, partial, final] of [
  ['Korean', '다른 그림ㅊ', '다른 그림체도 보고 싶어요'],
  ['Japanese', 'ほかのれい', 'ほかの例も見たいです'],
  ['Chinese', 'geng duo', '需要更多例子'],
]) {
  test(`${language} deferral-note composition survives a background acknowledgement`, async t => {
    const env = createEnv(t);
    env.api.change('text', { status: 'answered', value: 'Updated unrelated answer' });
    const node = reason(env); node.focus();
    node.dispatch('compositionstart'); inputValue(node, partial, true);
    env.ack(); await delay(0);
    assert.equal(reason(env), node);
    assert.equal(node.value, partial);
    assert.equal(node.isConnected, true);
    assert.equal(env.api.view.counts.deferred, 1);
    inputValue(node, final, true); node.dispatch('compositionend'); inputValue(node, final);
    assert.equal(env.requests.filter(request => request.body?.changes?.other).length, 0);
    env.ids.get('next').focus(); await delay(5);
    assert.equal(env.requests.at(-1).body.changes.other.status, 'deferred');
    assert.equal(env.requests.at(-1).body.changes.other.rationale, final);
    assert.equal(Object.hasOwn(env.requests.at(-1).body.changes.other, 'value'), false);
    env.ack(); await delay(0);
    assert.equal(env.server.answers.answers.other.rationale, final);
    assert.equal(env.server.answers.answers.other.status, 'deferred');
    const resumed = deferredBoot(); resumed.view = env.server;
    assert.equal(reason(createEnv(t, resumed, new Map(env.storage))).value, final);
  });
}

test('A deferral-note selection and middle edit survive an acknowledgement', async t => {
  const env = createEnv(t);
  env.api.change('text', { status: 'answered', value: 'Unrelated answer' });
  const node = reason(env); node.focus(); inputValue(node, 'alpha BETA omega', false, 6, 10);
  env.ack(); await delay(0);
  assert.equal(reason(env), node);
  assert.equal(node.selectionStart, 6); assert.equal(node.selectionEnd, 10);
  inputValue(node, 'alpha 다른 omega', false, 8);
  env.api.goPage(1);
  assert.equal(env.requests.at(-1).body.changes.other.rationale, 'alpha 다른 omega');
  env.ack(); await delay(0); env.api.goPage(0);
  assert.equal(reason(env).value, 'alpha 다른 omega');
});

test('Clearing a reason keeps the question deferred rather than unanswered', async t => {
  const env = createEnv(t, deferredBoot('offline'));
  const node = reason(env); node.focus(); inputValue(node, '');
  env.api.download();
  const exported = JSON.parse(await env.downloads.at(-1).text());
  assert.equal(exported.answers.other.status, 'deferred');
  assert.equal(exported.answers.other.rationale, '');
  assert.equal(env.api.view.counts.deferred, 1);
  assert.equal(env.api.view.counts.unanswered, 0);
});

test('Answer and reason drafts retain separate Unicode values across resume and export', async t => {
  const env = createEnv(t, deferredBoot('offline'));
  const answer = env.textarea('text'); answer.focus(); inputValue(answer, 'Answer: 한글 日本語');
  const note = reason(env); note.focus(); inputValue(note, 'Reason: العربية हिन्दी');
  env.api.persistCurrentText();
  const resumed = createEnv(t, deferredBoot('offline'), new Map(env.storage));
  assert.equal(resumed.textarea('text').value, 'Answer: 한글 日本語');
  assert.equal(reason(resumed).value, 'Reason: العربية हिन्दी');
  resumed.api.download();
  const exported = JSON.parse(await resumed.downloads.at(-1).text());
  assert.equal(exported.answers.text.value, 'Answer: 한글 日本語');
  assert.equal(exported.answers.other.rationale, 'Reason: العربية हिन्दी');
  assert.equal(exported.answers.other.status, 'deferred');
});

test('A deferred text question stores its reason without becoming an answer', async t => {
  const env = createEnv(t, deferredBoot('offline', 'en', 'text'));
  const node = reason(env, 'text'); node.focus(); inputValue(node, 'Need a clearer question');
  env.api.download();
  const exported = JSON.parse(await env.downloads.at(-1).text());
  assert.equal(exported.answers.text.status, 'deferred');
  assert.equal(exported.answers.text.rationale, 'Need a clearer question');
  assert.equal(Object.hasOwn(exported.answers.text, 'value'), false);
  assert.equal(env.textarea('text').value, '');
  const answer = env.textarea('text'); answer.focus(); inputValue(answer, 'A deliberate answer');
  env.api.download();
  const answered = JSON.parse(await env.downloads.at(-1).text());
  assert.equal(answered.answers.text.status, 'answered');
  assert.equal(answered.answers.text.value, 'A deliberate answer');
  assert.equal(reason(env, 'text'), undefined);
});

test('Undoing a deferral clears its draft and does not reuse it on a new deferral', async t => {
  const env = createEnv(t, deferredBoot('offline'));
  const node = reason(env); node.focus(); inputValue(node, 'Uncommitted old reason');
  env.api.change('other', null);
  assert.equal(reason(env), undefined);
  env.api.change('other', { status: 'deferred' });
  assert.equal(reason(env).value, '');
  env.api.download();
  assert.equal(JSON.parse(await env.downloads.at(-1).text()).answers.other.rationale, '');
});

test('Visibility persistence retains a deferral composition draft', t => {
  const env = createEnv(t, deferredBoot('offline'));
  const node = reason(env); node.focus(); node.dispatch('compositionstart'); inputValue(node, '검토 중인 이유', true);
  env.document.visibilityState = 'hidden';
  for (const listener of env.document.listeners.visibilitychange) listener();
  const resumed = createEnv(t, deferredBoot('offline'), new Map(env.storage));
  assert.equal(reason(resumed).value, '검토 중인 이유');
  assert.equal(resumed.api.view.counts.deferred, 1);
});

test('Conflict recovery preserves the reason draft while freezing its editor', t => {
  const env = createEnv(t);
  const node = reason(env); node.focus(); node.dispatch('compositionstart'); inputValue(node, '작성 중인 보류 이유', true);
  env.api.showRecovery('Conflict', true);
  assert.equal(node.isConnected, false);
  assert.equal(reason(env).disabled, true);
  assert.equal(reason(env).value, '작성 중인 보류 이유');
  assert.equal(env.api.composition, null);
});

test('Submission saves a final deferral reason before sending the latest revision', async t => {
  const env = createEnv(t, deferredBoot('live', 'en', 'last')); env.api.goPage(1);
  const node = reason(env, 'last'); node.focus(); inputValue(node, 'Discuss this after the questionnaire');
  const finishing = env.api.finish();
  assert.equal(env.requests.at(-1).body.changes.last.status, 'deferred');
  assert.equal(env.requests.at(-1).body.changes.last.rationale, 'Discuss this after the questionnaire');
  env.ack(); await delay(65); env.ack(); await finishing;
  assert.equal(env.requests.at(-1).url.startsWith('/api/submit'), true);
  assert.equal(env.requests.at(-1).body.base_answer_revision, env.server.answers.answer_revision);
  assert.equal(env.server.answers.answers.last.status, 'deferred');
  assert.equal(env.server.answers.answers.last.rationale, 'Discuss this after the questionnaire');
  assert.equal(env.api.view.ready_to_build, false);
});
