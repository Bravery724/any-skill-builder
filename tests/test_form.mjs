import test from 'node:test';
import assert from 'node:assert/strict';
import { setup, makeBoot, delay } from './form_harness.mjs';

function createEnv(t, boot = makeBoot(), storage) {
  const env = setup(boot, storage);
  t.after(() => env.dispose());
  return env;
}

function inputValue(node, value, composing = false, caret = value.length) {
  node.value = value;
  node.setSelectionRange(caret, caret);
  node.dispatch('input', { inputType: composing ? 'insertCompositionText' : 'insertText', isComposing: composing });
}
const start = node => node.dispatch('compositionstart');
const end = (node, value = node.value) => node.dispatch('compositionend', { data: value });

function assertEditor(env, node, value, caret = value.length) {
  assert.equal(env.textarea('text'), node, 'The focused editor must not be replaced');
  assert.equal(node.isConnected, true);
  assert.equal(node.value, value);
  assert.equal(node.selectionStart, caret);
  assert.equal(node.selectionEnd, caret);
}

async function blurAndAck(env, value) {
  env.ids.get('next').focus();
  await delay(5);
  const writes = env.requests.filter(request => request.body?.changes?.text);
  assert.equal(writes.length, 1, 'Only the completed answer should be sent');
  assert.equal(writes[0].body.changes.text.value, value);
  env.ack(); await delay(0);
  assert.equal(env.server.answers.answers.text.value, value);
  assert.equal(env.server.answers.history.filter(entry => entry.question_id === 'text').length, 1);
}

test('The form uses the supplied English interface messages', t => {
  const env = createEnv(t);
  assert.equal(env.document.documentElement.lang, 'en');
  assert.equal(env.ids.get('next').textContent, makeBoot().locale.messages.next);
  assert.equal(env.textarea('text').value, 'Initial answer');
});

test('Explicit Korean interface messages remain supported', t => {
  const boot = makeBoot('offline', 'ko');
  const env = createEnv(t, boot);
  assert.equal(env.document.documentElement.lang, 'ko');
  assert.equal(env.ids.get('next').textContent, boot.locale.messages.next);
});

for (const sample of [
  { language: 'Korean', cycles: [['ㅎ', '하', '한'], ['한ㄱ', '한국'], ['한국ㅇ', '한국어']], final: '한국어 입력 확인' },
  { language: 'Japanese', cycles: [['に', 'にほ', 'にほん', '日本'], ['日本ご', '日本語']], final: '日本語の入力確認' },
  { language: 'Chinese', cycles: [['z', 'zh', 'zhong', '中'], ['中文']], final: '中文输入测试' },
]) {
  test(`${sample.language} composition survives a background acknowledgement and saves once`, async t => {
    const env = createEnv(t);
    env.api.change('other', { status: 'answered', value: 'b' });
    const node = env.textarea('text'); node.focus();
    for (let index = 0; index < sample.cycles.length; index++) {
      start(node);
      for (const value of sample.cycles[index]) inputValue(node, value, true);
      if (index === 0) { env.ack(); await delay(0); }
      assertEditor(env, node, sample.cycles[index].at(-1));
      end(node);
      assertEditor(env, node, sample.cycles[index].at(-1));
      inputValue(node, node.value);
    }
    inputValue(node, sample.final);
    assertEditor(env, node, sample.final);
    assert.equal(env.requests.filter(request => request.body?.changes?.text).length, 0);
    await blurAndAck(env, sample.final);
    const resumedBoot = makeBoot(); resumedBoot.view = env.server;
    const resumed = createEnv(t, resumedBoot, new Map(env.storage));
    assert.equal(resumed.textarea('text').value, sample.final);
  });
}

for (const order of ['input-before-end', 'input-after-end']) {
  test(`Japanese conversion preserves its last character with ${order}`, async t => {
    const env = createEnv(t, makeBoot('offline'));
    const node = env.textarea('text'); node.focus();
    start(node); inputValue(node, 'にほんご', true);
    if (order === 'input-before-end') { inputValue(node, '日本語', true); end(node); }
    else { end(node); inputValue(node, '日本語'); }
    assertEditor(env, node, '日本語');
    env.api.download();
    const exported = JSON.parse(await env.downloads.at(-1).text());
    assert.equal(exported.answers.text.value, '日本語');
    assert.equal(exported.history.filter(entry => entry.question_id === 'text').length, 1);
  });
}

test('Cancelled composition restores the original text without persisting a candidate', t => {
  const env = createEnv(t, makeBoot('offline'));
  const node = env.textarea('text'); node.focus();
  inputValue(node, '中文 '); start(node); inputValue(node, '中文 shi', true);
  inputValue(node, '中文 ', true); end(node, '');
  assertEditor(env, node, '中文 ');
  env.api.persistCurrentText();
  const resumed = createEnv(t, makeBoot('offline'), new Map(env.storage));
  assert.equal(resumed.textarea('text').value, '中文 ');
});

test('An English middle insertion preserves its caret through a background acknowledgement', async t => {
  const env = createEnv(t);
  env.api.change('other', { status: 'answered', value: 'b' });
  const node = env.textarea('text'); node.focus();
  inputValue(node, 'ac', false, 1); inputValue(node, 'abc', false, 2);
  env.ack(); await delay(0);
  assertEditor(env, node, 'abc', 2);
  inputValue(node, 'abXc', false, 3); assertEditor(env, node, 'abXc', 3);
  await blurAndAck(env, 'abXc');
});

test('A selection survives a background save and replacement preserves the edited text', async t => {
  const env = createEnv(t);
  env.api.change('other', { status: 'answered', value: 'b' });
  const node = env.textarea('text'); node.focus(); inputValue(node, 'alpha BETA omega');
  node.setSelectionRange(6, 10); env.ack(); await delay(0);
  assert.equal(env.textarea('text'), node);
  assert.equal(node.selectionStart, 6); assert.equal(node.selectionEnd, 10);
  inputValue(node, 'alpha β omega', false, 7);
  assertEditor(env, node, 'alpha β omega', 7);
  await blurAndAck(env, 'alpha β omega');
});

for (const sample of [
  { language: 'French accents and decomposed Latin', text: 'café, déjà vu, e\u0301, A\u030A' },
  { language: 'Arabic with mixed LTR text', text: 'العربية اختبار 123 — API و2026' },
  { language: 'Hindi conjuncts and combining marks', text: 'हिन्दी परीक्षण क्षि और भारत' },
  { language: 'Emoji and supplementary characters', text: '😀 👩🏽‍💻 👨‍👩‍👧‍👦 🇰🇷 𐐷' },
  { language: 'Mixed Unicode', text: '한국어 日本語 中文 العربية हिन्दी café e\u0301 😀 𐐷' },
]) {
  test(`${sample.language} survives draft resume, blur, and JSON export exactly`, async t => {
    const env = createEnv(t, makeBoot('offline'));
    const node = env.textarea('text'); node.focus(); inputValue(node, sample.text);
    env.api.persistCurrentText();
    const resumed = createEnv(t, makeBoot('offline'), new Map(env.storage));
    assert.equal(resumed.textarea('text').value, sample.text);
    const resumedNode = resumed.textarea('text'); resumedNode.focus();
    resumed.ids.get('next').focus(); await delay(5); resumed.api.download();
    const exported = JSON.parse(await resumed.downloads.at(-1).text());
    assert.equal(exported.answers.text.value, sample.text);
    assert.equal(exported.history.filter(entry => entry.question_id === 'text').length, 1);
    assert.equal(resumedNode.dir, 'auto');
  });
}

test('A grapheme crossing the code-point limit is not split when composition ends', async t => {
  const boot = makeBoot('offline');
  boot.view.questionnaire.questions.find(question => question.id === 'text').max_length = 3;
  const env = createEnv(t, boot), node = env.textarea('text'); node.focus();
  start(node); inputValue(node, 'ab👩🏽‍💻', true); assert.equal(node.value, 'ab👩🏽‍💻');
  end(node); assert.equal(node.value, 'ab');
  env.api.download();
  assert.equal(JSON.parse(await env.downloads.at(-1).text()).answers.text.value, 'ab');
});

test('Explicit page navigation commits the draft before replacing the editor', async t => {
  const env = createEnv(t), node = env.textarea('text'); node.focus();
  inputValue(node, 'A draft with 한글 and 日本語');
  env.api.goPage(1);
  assert.equal(node.isConnected, false);
  assert.ok(env.textarea('last'));
  assert.equal(env.requests.at(-1).body.changes.text.value, 'A draft with 한글 and 日本語');
  env.ack(); await delay(0);
});

test('A parent change discards an obsolete draft even if its dependent condition stays true', t => {
  const env = createEnv(t, makeBoot('offline')), node = env.textarea('text'); node.focus();
  inputValue(node, 'Obsolete draft');
  env.api.change('gate', { status: 'answered', value: ['a', 'c'] });
  assert.equal(node.isConnected, false);
  assert.equal(env.textarea('text').value, '');
  assert.equal(env.api.drafts.text, undefined);
  env.api.change('gate', { status: 'answered', value: ['b'] });
  assert.equal(env.textarea('text'), undefined);
});

test('Conflict recovery freezes editing while retaining the composition draft', t => {
  const env = createEnv(t), node = env.textarea('text'); node.focus();
  start(node); inputValue(node, '작성 중', true);
  env.api.showRecovery('Conflict', true);
  assert.equal(node.isConnected, false);
  assert.equal(env.textarea('text').disabled, true);
  assert.equal(env.textarea('text').value, '작성 중');
  assert.equal(env.api.composition, null);
});

test('Submission saves final text before sending the current answer revision', async t => {
  const env = createEnv(t); env.api.goPage(1);
  const node = env.textarea('last'); node.focus(); inputValue(node, 'Final input');
  const finishing = env.api.finish();
  assert.equal(env.requests.at(-1).body.changes.last.value, 'Final input');
  env.ack(); await delay(65); assert.ok(env.pending.length); env.ack(); await finishing;
  assert.equal(env.requests.at(-1).url.startsWith('/api/submit'), true);
  assert.equal(env.server.answers.answers.last.value, 'Final input');
  assert.equal(env.requests.at(-1).body.base_answer_revision, env.server.answers.answer_revision);
});

test('Hiding the page retains a composition draft for a later resume', t => {
  const env = createEnv(t, makeBoot('offline')), node = env.textarea('text'); node.focus();
  start(node); inputValue(node, '작성 중인 초안', true);
  env.document.visibilityState = 'hidden';
  for (const listener of env.document.listeners.visibilitychange) listener();
  const resumed = createEnv(t, makeBoot('offline'), new Map(env.storage));
  assert.equal(resumed.textarea('text').value, '작성 중인 초안');
});
