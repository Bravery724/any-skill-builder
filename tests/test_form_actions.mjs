import test from 'node:test';
import assert from 'node:assert/strict';
import { setup, makeBoot, copy, select, inputValue, downloadedBoot } from './form_harness.mjs';

function envFor(t, boot = makeBoot(), storage) { const env = setup(boot, storage); t.after(() => env.dispose()); assert.ok(env.api, env.ids.get('notice').textContent); return env; }

test('Saving without randomUUID still produces a canonical UUID accepted by the import contract', async t => {
  const env = envFor(t); delete env.crypto.randomUUID;
  env.api.saveAnswers(); env.api.saveAnswers();
  const first = (await downloadedBoot(env.downloads[0])).boot;
  const second = (await downloadedBoot(env.downloads[1])).boot;
  assert.match(first.export_id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.notEqual(first.export_id, second.export_id);
});

test('The UUID fallback uses available browser random bytes', async t => {
  const env = envFor(t); delete env.crypto.randomUUID; let used = false;
  env.crypto.getRandomValues = bytes => { used = true; bytes.fill(23); return bytes; };
  env.api.saveAnswers();
  const saved = (await downloadedBoot(env.downloads[0])).boot;
  assert.equal(used, true);
  assert.match(saved.export_id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test('Saving from page one downloads self-contained HTML with the exact questionnaire and current answers', async t => {
  const boot = makeBoot(), env = envFor(t, boot);
  inputValue(env.textarea('text'), 'Preserve this saved response.');
  env.ids.get('save-answers').click();
  assert.equal(env.downloads.length, 1);
  assert.equal(env.downloads[0].type, 'text/html;charset=utf-8');
  const saved = await downloadedBoot(env.downloads[0]);
  assert.deepEqual(saved.boot.view.questionnaire, boot.view.questionnaire);
  assert.equal(saved.boot.view.answers.answers.text.value, 'Preserve this saved response.');
  assert.equal(saved.boot.base_answer_revision, boot.base_answer_revision);
  assert.equal(saved.boot.view.answers.answer_revision, boot.base_answer_revision);
  assert.equal(saved.boot.questionnaire_sha256, boot.questionnaire_sha256);
  assert.ok(saved.boot.saved_at); assert.ok(saved.boot.export_id);
  assert.ok(saved.html.includes('<style>')); assert.ok(saved.html.includes('function saveAnswers()'));
  assert.equal(env.requests.length, 0);
});

test('A saved HTML reopens with the answers embedded in that file, ignoring stale browser storage', async t => {
  const env = envFor(t); env.api.clearAnswer('text'); env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  const storage = new Map([['skill-builder:form-regression:1', JSON.stringify({ answers: makeBoot().view.answers })]]);
  const reopened = envFor(t, saved.boot, storage);
  assert.equal(reopened.api.answers.answers.text, undefined);
  assert.equal(reopened.textarea('text').value, '');
  assert.equal(reopened.api.dirty, false);
});

test('Saving a blank questionnaire is permitted and preserves emptiness on reopen', async t => {
  const env = envFor(t); env.api.resetAllAnswers(); env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.deepEqual(saved.boot.view.answers.answers, {});
  const reopened = envFor(t, saved.boot);
  assert.equal(reopened.api.view.counts.answered, 0);
  assert.equal(reopened.api.view.counts.waiting, 1);
  assert.equal(reopened.ids.get('save-answers').disabled, false);
});

test('Blank Other plus valid ordinary selections round-trips exactly without losing the selections', async t => {
  const env = envFor(t); select(env.other('gate')); env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.deepEqual(saved.boot.view.answers.answers.gate.value, ['a', 'b']);
  assert.equal(saved.boot.drafts.gate.other_enabled, true);
  const reopened = envFor(t, saved.boot);
  assert.equal(reopened.other('gate').checked, true);
  assert.equal(reopened.textarea('gate').value, '');
  assert.equal(reopened.input('gate', 'a').checked, true);
});

test('Below-minimum selections survive save and reopen as selections rather than complete answers', async t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].min_choices = 2;
  const env = envFor(t, boot); select(env.input('gate', 'b'), false); env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.equal(saved.boot.view.answers.answers.gate, undefined);
  assert.deepEqual(saved.boot.drafts.gate.selected, ['a']);
  const reopened = envFor(t, saved.boot);
  assert.equal(reopened.input('gate', 'a').checked, true);
  assert.equal(reopened.api.view.states.text, 'active');
  assert.equal(reopened.textarea('text').value, 'Initial answer');
  select(reopened.input('gate', 'c'));
  assert.deepEqual(copy(reopened.api.answers.answers.gate.value), ['a', 'c']);
  assert.equal(reopened.api.answers.answers.text.value, 'Initial answer');
});

test('Minimum-two exclusive answers save and reopen as complete answers, and clearing stays cleared', async t => {
  const boot = makeBoot(), q = boot.view.questionnaire.questions[0];
  q.min_choices = 2; q.options[2].exclusive = true;
  const env = envFor(t, boot); select(env.input('gate', 'c')); env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.deepEqual(saved.boot.view.answers.answers.gate.value, ['c']);
  assert.equal(saved.boot.drafts.gate, undefined);
  assert.equal(saved.boot.view.answers.pending_inputs, undefined);
  const reopened = envFor(t, saved.boot);
  assert.equal(reopened.input('gate', 'c').checked, true);
  assert.equal(reopened.card('gate').dataset.status, 'answered');
  assert.equal(reopened.api.view.ready_to_build, true);
  reopened.api.clearAnswer('gate'); reopened.api.saveAnswers();
  const cleared = envFor(t, (await downloadedBoot(reopened.downloads[0])).boot);
  assert.equal(cleared.api.answers.answers.gate, undefined);
  assert.equal(cleared.api.answers.pending_inputs, undefined);
  assert.equal(cleared.input('gate', 'c').checked, false);
});

test('A legacy sole-exclusive draft reopens and resaves as a user answer', async t => {
  const boot = makeBoot(), q = boot.view.questionnaire.questions[0];
  q.min_choices = 2; q.options[2].exclusive = true;
  delete boot.view.answers.answers.gate; delete boot.view.answers.answers.text;
  boot.drafts = { gate: { selected: ['c'], other_enabled: false, other_text: '' } };
  const env = envFor(t, boot);
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['c']);
  assert.equal(env.api.answers.answers.gate.actor, 'user');
  assert.equal(env.api.answers.pending_inputs, undefined);
  assert.equal(env.api.view.ready_to_build, true);
  env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.deepEqual(saved.boot.view.answers.answers.gate.value, ['c']);
  assert.equal(saved.boot.drafts.gate, undefined);
});

test('A conflicting legacy exclusive draft cannot replace an embedded answer on reopen', t => {
  const boot = makeBoot(), q = boot.view.questionnaire.questions[0];
  q.min_choices = 2; q.options[2].exclusive = true;
  boot.drafts = { gate: { selected: ['c'], other_enabled: false, other_text: '' } };
  const env = envFor(t, boot);
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['a', 'b']);
  assert.deepEqual(copy(env.api.ui.gate.selected), ['a', 'b']);
  assert.equal(env.input('gate', 'c').checked, false);
});

test('A child answered under a pending parent is saved alongside its incomplete selections', async t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].min_choices = 2;
  boot.view.answers.answers = {};
  const env = envFor(t, boot);
  select(env.input('gate', 'a'));
  inputValue(env.textarea('text'), 'My decision under option a.');
  env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.equal(saved.boot.view.answers.answers.gate, undefined);
  assert.equal(saved.boot.view.answers.pending_inputs, undefined);
  assert.deepEqual(saved.boot.drafts.gate.selected, ['a']);
  assert.equal(saved.boot.view.answers.answers.text.value, 'My decision under option a.');
  const reopened = envFor(t, saved.boot);
  assert.equal(reopened.api.view.states.text, 'active');
  assert.equal(reopened.textarea('text').value, 'My decision under option a.');
});

test('Saving keeps the current page anchor and reopening restores that page', async t => {
  const env = envFor(t); env.api.goPage(env.api.pages.length - 1); env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.equal(saved.boot.page_anchor, 'last');
  const reopened = envFor(t, saved.boot);
  assert.ok(reopened.textarea('last'));
});

test('Each saved snapshot has a new identity while its canonical answer baseline remains fixed', async t => {
  const env = envFor(t); env.api.saveAnswers(); env.ids.get('close-save').click();
  inputValue(env.textarea('text'), 'A later edit.'); env.api.saveAnswers();
  const first = await downloadedBoot(env.downloads[0]), second = await downloadedBoot(env.downloads[1]);
  assert.notEqual(first.boot.export_id, second.boot.export_id);
  assert.equal(first.boot.base_answer_revision, second.boot.base_answer_revision);
  assert.equal(second.boot.view.answers.answer_revision, first.boot.view.answers.answer_revision);
  assert.equal(first.boot.view.answers.answers.text.value, 'Initial answer');
  assert.equal(second.boot.view.answers.answers.text.value, 'A later edit.');
});

test('New saves derive pending inputs from current fields instead of exporting stale canonical pending inputs', t => {
  const boot = makeBoot();
  boot.view.answers.pending_inputs = { gate: { selected: ['a'], other_enabled: false, other_text: '', question_version: 1 } };
  const env = envFor(t, boot);
  const saved = env.api.snapshot();
  assert.equal(saved.view.answers.pending_inputs, undefined);
  assert.deepEqual(copy(saved.drafts), {});
});

test('JSON text cannot close the data script or introduce new executable HTML', async t => {
  const env = envFor(t);
  const attack = '</script><script>globalThis.bad=true</script>& <img src=x onerror=alert(1)>\u2028\u2029';
  inputValue(env.textarea('text'), attack); env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]);
  assert.equal(saved.boot.view.answers.answers.text.value, attack);
  assert.equal(saved.html.includes(attack), false);
  assert.equal((saved.html.match(/<script id="skill-builder-data"/g) || []).length, 1);
  const reopened = envFor(t, saved.boot);
  assert.equal(reopened.textarea('text').value, attack);
});

test('Image candidates stay embedded in saved HTML with no external image fetch', async t => {
  const boot = makeBoot(); const q = boot.view.questionnaire.questions[2]; q.type = 'image';
  for (const option of q.options) option.image = `assets/${option.id}.png`;
  boot.assets = { 'assets/a.png': 'data:image/png;base64,aGVsbG8=', 'assets/b.png': 'data:image/png;base64,d29ybGQ=' };
  const env = envFor(t, boot); env.api.goPage(env.api.pages.findIndex(p => p.questions.some(item => item.id === q.id)));
  const images = env.card(q.id).querySelectorAll('img');
  assert.equal(images.length, 2); assert.equal(images[0].src, boot.assets['assets/a.png']);
  assert.ok(env.other(q.id)); env.api.saveAnswers();
  const saved = await downloadedBoot(env.downloads[0]); assert.deepEqual(saved.boot.assets, boot.assets);
  assert.equal(env.requests.length, 0);
});

test('An unsafe image URL never becomes a rendered image source', t => {
  const boot = makeBoot(); const q = boot.view.questionnaire.questions[2]; q.type = 'image';
  for (const option of q.options) option.image = `assets/${option.id}.png`;
  boot.assets = { 'assets/a.png': 'https://example.invalid/tracking.png', 'assets/b.png': 'javascript:alert(1)' };
  const env = envFor(t, boot); env.api.goPage(env.api.pages.findIndex(p => p.questions.some(item => item.id === q.id)));
  for (const img of env.card(q.id).querySelectorAll('img')) { assert.equal(img.src, undefined); assert.equal(img.hidden, true); }
});

test('Reset requires the explicit confirmation button and keeps questions available', t => {
  const env = envFor(t);
  env.ids.get('reset-all').click(); assert.equal(env.ids.get('reset-dialog').open, true);
  assert.equal(env.api.view.counts.answered, 4);
  env.ids.get('cancel-reset').click(); assert.equal(env.api.view.counts.answered, 4);
  env.ids.get('reset-all').click(); env.ids.get('confirm-reset').click();
  assert.equal(env.api.view.counts.answered, 0); assert.equal(env.api.view.counts.total, 4);
  assert.equal(env.api.answers.history.filter(item => item.reason === 'reset_all').length, 4);
});

test('The close warning appears only after edits since the latest export', t => {
  const env = envFor(t); assert.equal(env.unload().prevented, undefined);
  inputValue(env.textarea('text'), 'Unsaved edit'); assert.equal(env.unload().prevented, true);
  env.api.saveAnswers(); assert.equal(env.unload().prevented, undefined);
  inputValue(env.textarea('text'), 'New unsaved edit'); assert.equal(env.unload().prevented, true);
});

test('Save feedback distinguishes a download request from an accepted AI submission', t => {
  const env = envFor(t); env.api.saveAnswers();
  assert.equal(env.ids.get('save-dialog').open, true);
  assert.match(env.ids.get('save-message').textContent, /download has started/);
  assert.match(env.ids.get('save-message').textContent, /Finish saving/);
  assert.doesNotMatch(env.ids.get('save-message').textContent, /accepted|connected|server/i);
  env.ids.get('close-save').click(); assert.equal(env.ids.get('save-dialog').open, false);
});
