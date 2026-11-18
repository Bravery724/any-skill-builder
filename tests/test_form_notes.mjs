import test from 'node:test';
import assert from 'node:assert/strict';
import { setup, makeBoot, copy, select, inputValue, downloadedBoot, catalog } from './form_harness.mjs';

function envFor(t, boot = makeBoot()) { const env = setup(boot); t.after(() => env.dispose()); assert.ok(env.api, env.ids.get('notice').textContent); return env; }

for (const [language, partial, final] of [
  ['Korean', '논문 분ㅅ', '논문 분석을 쉽게 설명해주세요.'],
  ['Japanese', 'ぶんせき', '分析をわかりやすく説明してください。'],
  ['Chinese', 'fen xi', '请清楚地解释分析结果。'],
]) {
  test(`${language} composition keeps the editor node, focus, and partial input`, t => {
    const env = envFor(t); const input = env.textarea('text'); input.focus();
    input.dispatch('compositionstart'); inputValue(input, partial, true);
    assert.equal(env.textarea('text'), input);
    assert.equal(env.document.activeElement, input);
    assert.equal(input.value, partial);
    assert.equal(env.api.composition.input, input);
    inputValue(input, final, true); input.dispatch('compositionend');
    assert.equal(env.api.composition, null);
    assert.equal(env.api.answers.answers.text.value, final);
    assert.equal(env.textarea('text'), input);
  });
}

test('Editing in the middle of text preserves the selection and does not replace the textarea', t => {
  const env = envFor(t); const input = env.textarea('text'); input.focus();
  inputValue(input, 'alpha BETA omega', false, 6, 10);
  assert.equal(env.textarea('text'), input);
  assert.equal(input.selectionStart, 6); assert.equal(input.selectionEnd, 10);
  inputValue(input, 'alpha 다른 omega', false, 8);
  assert.equal(input.selectionStart, 8); assert.equal(input.selectionEnd, 8);
});

test('Other text uses the same composition-safe editing path and preserves ordinary selections', t => {
  const env = envFor(t); select(env.other('gate'));
  const input = env.textarea('gate'); input.focus(); input.dispatch('compositionstart');
  inputValue(input, '직접 입ㄹ', true, 3);
  assert.equal(env.textarea('gate'), input);
  assert.equal(input.selectionStart, 3);
  inputValue(input, '직접 입력한 다른 방식', true); input.dispatch('compositionend');
  assert.equal(env.api.answers.answers.gate.value.other, '직접 입력한 다른 방식');
  assert.deepEqual(copy(env.api.answers.answers.gate.value.selected), ['a', 'b']);
});

test('Saving during composition includes the current DOM text even before the final input event', async t => {
  const env = envFor(t); const input = env.textarea('text'); input.focus(); input.dispatch('compositionstart');
  input.value = '마지막 조합 내용';
  env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.equal(saved.boot.view.answers.answers.text.value, '마지막 조합 내용');
  assert.equal(env.textarea('text'), input);
});

test('Unicode limits count code points and retain over-limit input until the user corrects it', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[1].max_length = 4;
  boot.view.answers.answers.text.value = 'abcd';
  const env = envFor(t, boot); const input = env.textarea('text');
  inputValue(input, '😀한日文'); assert.equal(env.api.answers.answers.text.value, '😀한日文');
  inputValue(input, '😀한日文a'); env.api.saveAnswers();
  assert.equal(env.downloads.length, 0);
  assert.equal(input.value, '😀한日文a');
  assert.equal(input.getAttribute('aria-invalid'), 'true');
  assert.match(env.ids.get('notice').textContent, /4/);
  inputValue(input, '😀한日文'); assert.equal(input.getAttribute('aria-invalid'), 'false');
  env.api.saveAnswers(); assert.equal(env.downloads.length, 1);
});

test('Over-limit text in an initially blank answer still warns before closing', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[1].max_length = 4;
  delete boot.view.answers.answers.text;
  const env = envFor(t, boot);
  inputValue(env.textarea('text'), 'Long unsaved text');
  assert.equal(env.api.answers.answers.text, undefined);
  assert.equal(env.api.dirty, true);
  assert.equal(env.unload().prevented, true);
  env.api.saveAnswers();
  assert.equal(env.downloads.length, 0);
  assert.equal(env.api.dirty, true);
  env.card('text').querySelector('.clear-answer').click();
  assert.equal(env.card('text').querySelector('.field-error').hidden, true);
  assert.equal(env.textarea('text').getAttribute('aria-invalid'), 'false');
  env.api.saveAnswers();
  assert.equal(env.downloads.length, 1);
});

test('Clearing all text is unanswered and exports no invented replacement', async t => {
  const env = envFor(t); inputValue(env.textarea('text'), '');
  assert.equal(env.card('text').dataset.status, 'unanswered');
  env.api.saveAnswers(); const saved = await downloadedBoot(env.downloads[0]);
  assert.equal(saved.boot.view.answers.answers.text, undefined);
  assert.equal(saved.boot.view.counts.unanswered, 1);
});

test('Navigation restores text exactly without replacing it with an older canonical record', t => {
  const env = envFor(t); const input = env.textarea('text');
  inputValue(input, '最新の変更 · 최신 수정 · newest edit');
  env.api.goPage(env.api.pages.length - 1); env.api.goPage(0);
  assert.equal(env.textarea('text').value, '最新の変更 · 최신 수정 · newest edit');
  assert.equal(env.textarea('text'), input);
});

function interpretedBoot() {
  const boot = makeBoot();
  Object.assign(boot.view.answers.answers.gate, {
    actor: 'ai', rationale: 'Keep the requested review step.', assumptions: ['The reviewers share a workspace.'],
    value: { selected: ['b'], other: 'Paired review' }, user_selected: ['b'],
    branch_value: ['a', 'b'], branch_rationale: 'Paired review needs a topic description.',
  });
  return boot;
}

test('Moving focus through an interpreted AI Other answer preserves its active human answer through save and reopen', async t => {
  const boot = interpretedBoot(), env = envFor(t, boot);
  env.textarea('gate').focus();
  env.textarea('text').focus();
  assert.equal(env.api.dirty, false);
  assert.equal(env.api.view.states.text, 'active');
  env.ids.get('save-answers').click();
  const { boot: saved } = await downloadedBoot(env.downloads[0]);
  assert.deepEqual(saved.view.answers, boot.view.answers);
  assert.deepEqual(copy(envFor(t, saved).api.answers), boot.view.answers);
});

test('Saving a focused AI text answer preserves its original line endings, authorship and history on successive saves', async t => {
  const boot = makeBoot(); const answer = boot.view.answers.answers.text;
  Object.assign(answer, { actor: 'ai', rationale: 'Fits the request.', assumptions: ['Use two lines.'], value: 'First\r\nSecond' });
  const env = envFor(t, boot);
  const editor = env.textarea('text');
  editor.focus();
  assert.equal(editor.value, 'First\nSecond');
  editor.dispatch('compositionstart'); editor.dispatch('compositionend');
  env.ids.get('save-answers').click();
  env.ids.get('close-save').click();
  env.api.goPage(1); env.api.goPage(0);
  env.ids.get('save-answers').click();
  for (const download of env.downloads) assert.deepEqual((await downloadedBoot(download)).boot.view.answers, boot.view.answers);
  assert.equal(env.downloads.length, 2);
  assert.equal(env.api.dirty, false);
});

test('Editing an interpreted AI Other while focused updates its author and branch on save even without an input event', async t => {
  const boot = interpretedBoot(), env = envFor(t, boot);
  const editor = env.textarea('gate');
  editor.focus(); editor.dispatch('compositionstart'); editor.value = 'Individual reflection';
  env.ids.get('save-answers').click();
  const { boot: saved } = await downloadedBoot(env.downloads[0]);
  assert.equal(saved.view.answers.answers.gate.actor, 'user');
  assert.equal(saved.view.answers.answers.gate.value.other, 'Individual reflection');
  assert.equal(saved.view.answers.answers.gate.branch_value, undefined);
  assert.equal(saved.view.states.text, 'waiting');
  assert.equal(saved.view.answers.answers.text, undefined);
  assert.deepEqual(saved.view.answers.history.find(entry => entry.question_id === 'text').answer, boot.view.answers.answers.text);
});

test('Cancelling an IME candidate in an AI Other answer keeps the interpretation and its human child', t => {
  const boot = interpretedBoot(), env = envFor(t, boot), editor = env.textarea('gate');
  editor.focus(); editor.dispatch('compositionstart');
  inputValue(editor, 'Paired review 검', true);
  assert.equal(env.unload().prevented, true);
  editor.value = 'Paired review'; editor.dispatch('compositionend'); editor.dispatch('input');
  assert.deepEqual(copy(env.api.snapshot().view.answers), boot.view.answers);
  assert.equal(env.api.dirty, false);
});

test('Editing an AI-authored answer makes only the changed answer user-owned', t => {
  const boot = makeBoot(); boot.view.answers.answers.text.actor = 'ai'; boot.view.answers.answers.text.rationale = 'Initial recommendation.';
  const env = envFor(t, boot); inputValue(env.textarea('text'), 'My explicit revision.');
  assert.equal(env.api.answers.answers.text.actor, 'user');
  assert.equal(env.api.answers.answers.text.value, 'My explicit revision.');
  assert.equal(env.api.answers.answers.gate.actor, 'user');
});

test('Korean UI uses translated labels without changing user text', t => {
  const env = envFor(t, makeBoot('ko'));
  assert.equal(env.document.documentElement.lang, 'ko');
  assert.equal(env.textarea('text').placeholder, catalog.ko.answer_placeholder);
  assert.equal(env.card('gate').querySelector('.question-status').textContent, catalog.ko.question_status_answered);
  assert.equal(env.api.answers.answers.text.value, 'Initial answer');
});

test('Custom languages and RTL keep the supplied messages and text direction', t => {
  const boot = makeBoot(); boot.locale = { language: 'ar', direction: 'rtl', messages: { ...catalog.en, answer_placeholder: 'اكتب إجابتك', question_status_answered: 'تمت الإجابة' } };
  const env = envFor(t, boot);
  assert.equal(env.document.documentElement.lang, 'ar');
  assert.equal(env.document.documentElement.dir, 'rtl');
  assert.equal(env.textarea('text').placeholder, 'اكتب إجابتك');
  assert.equal(env.textarea('text').dir, 'auto');
  inputValue(env.textarea('text'), 'تحليل واضح مع أمثلة');
  assert.equal(env.api.answers.answers.text.value, 'تحليل واضح مع أمثلة');
});

test('An initially long request can be expanded without disturbing answers or editor identity', t => {
  const env = envFor(t); const input = env.textarea('text');
  env.ids.get('goal-text').scrollHeight = 300; env.api.updateGoal();
  assert.equal(env.ids.get('goal-toggle').hidden, false);
  env.ids.get('goal-toggle').click();
  assert.equal(env.ids.get('goal-toggle').getAttribute('aria-expanded'), 'true');
  assert.equal(env.textarea('text'), input);
  assert.equal(env.api.answers.answers.text.value, 'Initial answer');
});
