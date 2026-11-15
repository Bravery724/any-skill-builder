import test from 'node:test';
import assert from 'node:assert/strict';
import { setup, makeBoot, copy, select, inputValue, catalog } from './form_harness.mjs';

function envFor(t, boot = makeBoot()) { const env = setup(boot); t.after(() => env.dispose()); assert.ok(env.api, env.ids.get('notice').textContent); return env; }
function goto(env, id) { env.api.goPage(env.api.pages.findIndex(page => page.questions.some(q => q.id === id))); }

test('An offline questionnaire loads with answer counts, original request, and saving available on page one', t => {
  const env = envFor(t);
  assert.equal(env.ids.get('goal-text').textContent, makeBoot().view.questionnaire.goal);
  assert.equal(env.api.view.counts.answered, 4);
  assert.equal(env.ids.get('save-answers').disabled, false);
  assert.equal(env.api.pageIndex, 0);
  assert.equal(env.requests.length, 0);
});

test('Each choice question has Other, while a text question has one ordinary textarea', t => {
  const env = envFor(t);
  assert.ok(env.other('gate'));
  assert.equal(env.card('text').querySelectorAll('textarea').length, 1);
  assert.equal(env.other('text'), undefined);
  goto(env, 'other'); assert.ok(env.other('other'));
});

test('Clearing a selection empties its answer and invalidates dependent answers with history', t => {
  const env = envFor(t);
  env.api.clearAnswer('gate');
  assert.equal(env.api.answers.answers.gate, undefined);
  assert.equal(env.api.answers.answers.text, undefined);
  assert.equal(env.api.view.states.text, 'waiting');
  assert.ok(env.api.answers.history.some(record => record.question_id === 'text' && record.reason === 'parent_answer_changed'));
  select(env.input('gate', 'a'));
  assert.equal(env.api.view.states.text, 'active');
  assert.equal(env.api.answers.answers.text, undefined);
});

test('Selecting then clearing Other returns a single choice question to unanswered', t => {
  const env = envFor(t); goto(env, 'other');
  select(env.other('other'));
  assert.equal(env.api.answers.answers.other, undefined);
  assert.equal(env.textarea('other').hidden, false);
  inputValue(env.textarea('other'), 'Use an illustrated one-page report.');
  assert.deepEqual(copy(env.api.answers.answers.other.value), { other: 'Use an illustrated one-page report.', selected: [] });
  inputValue(env.textarea('other'), '   ');
  assert.equal(env.api.answers.answers.other, undefined);
  assert.equal(env.card('other').dataset.status, 'unanswered');
});

test('Multi-choice Other preserves ordinary selections together with the custom direction', t => {
  const env = envFor(t);
  select(env.other('gate'));
  inputValue(env.textarea('gate'), 'Also support paired reviews.');
  assert.deepEqual(copy(env.api.answers.answers.gate.value), { other: 'Also support paired reviews.', selected: ['a', 'b'] });
  inputValue(env.textarea('gate'), '');
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['a', 'b']);
  assert.equal(env.api.ui.gate.other_enabled, true);
});

test('Exclusive options cannot be combined with ordinary choices or Other', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].options[2].exclusive = true;
  const env = envFor(t, boot);
  select(env.input('gate', 'c'));
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['c']);
  select(env.other('gate'));
  assert.deepEqual(copy(env.api.ui.gate.selected), []);
  inputValue(env.textarea('gate'), 'Custom workflow');
  select(env.input('gate', 'c'));
  assert.equal(env.api.ui.gate.other_enabled, false);
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['c']);
});

test('A sole exclusive choice completes a minimum-two question and switching back restores its minimum', t => {
  const boot = makeBoot(), q = boot.view.questionnaire.questions[0];
  q.min_choices = 2; q.options[2].exclusive = true;
  const env = envFor(t, boot);
  select(env.input('gate', 'c'));
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['c']);
  assert.equal(env.card('gate').dataset.status, 'answered');
  assert.equal(env.api.answers.pending_inputs, undefined);
  assert.equal(env.api.pendingDrafts().gate, undefined);
  assert.equal(env.api.view.ready_to_build, true);
  assert.equal(env.api.valueValid(q, ['a', 'c']), false);
  assert.equal(env.api.valueValid(q, { other: 'Additional instructions', selected: ['c'] }), false);
  select(env.input('gate', 'a'));
  assert.deepEqual(copy(env.api.ui.gate.selected), ['a']);
  assert.equal(env.api.answers.answers.gate, undefined);
  assert.equal(env.api.view.ready_to_build, false);
  assert.deepEqual(copy(env.api.answers.pending_inputs.gate.selected), ['a']);
});

test('A none label without an explicit exclusive flag still requires the ordinary minimum', t => {
  const boot = makeBoot(), q = boot.view.questionnaire.questions[0];
  q.min_choices = 2; q.options[2].label = 'None';
  const env = envFor(t, boot); env.api.clearAnswer('gate');
  select(env.input('gate', 'c'));
  assert.equal(env.api.answers.answers.gate, undefined);
  assert.equal(env.api.valueValid(q, ['c']), false);
});

test('The selection maximum refuses only the excess selection and preserves accepted choices', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].max_choices = 2;
  const env = envFor(t, boot);
  select(env.input('gate', 'c'));
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['a', 'b']);
  assert.equal(env.input('gate', 'c').checked, false);
  assert.match(env.ids.get('notice').textContent, /2/);
});

test('Below-minimum multi-choice selections remain visible as pending inputs for AI completion', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].min_choices = 2;
  const env = envFor(t, boot);
  select(env.input('gate', 'b'), false);
  assert.equal(env.api.answers.answers.gate, undefined);
  assert.equal(env.input('gate', 'a').checked, true);
  assert.deepEqual(copy(env.api.pendingDrafts().gate), { selected: ['a'], other_enabled: false, other_text: '' });
  assert.equal(env.api.view.states.text, 'active');
  assert.equal(env.api.answers.answers.text.value, 'Initial answer');
  assert.equal(env.api.view.ready_to_build, false);
});

test('A new incomplete selection opens only its known selected branch while other branches wait', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].min_choices = 2;
  boot.view.questionnaire.questions[3].when = [{ question_id: 'gate', includes: 'b' }];
  boot.view.answers.answers = {};
  const env = envFor(t, boot);
  select(env.input('gate', 'a'));
  assert.equal(env.api.answers.answers.gate, undefined);
  assert.equal(env.api.view.states.text, 'active');
  assert.equal(env.api.view.states.last, 'waiting');
  assert.ok(env.textarea('text'));
  inputValue(env.textarea('text'), 'Keep this explanation about the selected workflow.');
  assert.equal(env.api.answers.answers.text.actor, 'user');
  select(env.input('gate', 'c'));
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['a', 'c']);
  assert.equal(env.api.answers.answers.text.value, 'Keep this explanation about the selected workflow.');
  assert.equal(env.api.view.states.last, 'inactive');
});

test('Removing the selected pending parent option archives its child instead of retaining a stale answer', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].min_choices = 2;
  boot.view.answers.answers = {};
  const env = envFor(t, boot);
  select(env.input('gate', 'a'));
  inputValue(env.textarea('text'), 'Only relevant to option a.');
  select(env.input('gate', 'a'), false);
  assert.equal(env.api.view.states.text, 'waiting');
  assert.equal(env.api.answers.answers.text, undefined);
  assert.ok(env.api.answers.history.some(item => item.question_id === 'text' && item.answer.value === 'Only relevant to option a.'));
  select(env.input('gate', 'b'));
  assert.equal(env.api.view.states.text, 'waiting');
});

test('Canonical pending selections and a user-owned child restore without fabricating a complete parent', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].min_choices = 2;
  delete boot.view.answers.answers.gate;
  boot.view.answers.pending_inputs = { gate: { selected: ['a'], other_enabled: false, other_text: '', question_version: 1 } };
  boot.drafts = { gate: { selected: ['a'], other_enabled: false, other_text: '' } };
  const env = envFor(t, boot);
  assert.equal(env.api.view.states.text, 'active');
  assert.equal(env.textarea('text').value, 'Initial answer');
  assert.equal(env.api.answers.answers.gate, undefined);
  assert.equal(env.api.snapshot().view.answers.answers.text.actor, 'user');
  assert.deepEqual(copy(env.api.snapshot().drafts.gate.selected), ['a']);
});

test('derive uses its supplied pending-input envelope without reading the current UI state', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].min_choices = 2;
  const env = envFor(t, boot);
  const envelope = copy(env.api.answers);
  delete envelope.answers.gate;
  envelope.pending_inputs = { gate: { selected: ['b'], other_enabled: false, other_text: '', question_version: 1 } };
  assert.equal(env.api.derive(envelope).states.text, 'waiting');
  envelope.pending_inputs.gate.selected = ['a'];
  assert.equal(env.api.derive(envelope).states.text, 'active');
  assert.equal(env.api.derive(envelope).counts.unanswered, 1);
});

test('A meaningful custom answer can stand alone despite the regular minimum choice count', t => {
  const boot = makeBoot(); boot.view.questionnaire.questions[0].min_choices = 2;
  const env = envFor(t, boot); env.api.clearAnswer('gate'); select(env.other('gate'));
  inputValue(env.textarea('gate'), 'Use a workshop instead of the listed workflows.');
  assert.equal(env.api.answers.answers.gate.status, 'answered');
  assert.deepEqual(copy(env.api.answers.answers.gate.value.selected), []);
});

test('An uninterpreted custom parent keeps its dependent branch waiting instead of guessing false', t => {
  const boot = makeBoot();
  boot.view.answers.answers.gate.value = { other: 'A combination adapted to a small team', selected: ['b'] };
  delete boot.view.answers.answers.text;
  const env = envFor(t, boot);
  assert.equal(env.api.view.states.text, 'waiting');
  assert.equal(env.api.view.ready_to_build, false);
});

test('An explicit host interpretation controls a custom branch and survives an untouched save', t => {
  const boot = makeBoot();
  boot.view.answers.answers.gate.value = { other: 'Custom review', selected: ['b'] };
  boot.view.answers.answers.gate.branch_value = ['a', 'b'];
  const env = envFor(t, boot);
  assert.equal(env.api.view.states.text, 'active');
  assert.deepEqual(copy(env.api.snapshot().view.answers.answers.gate.branch_value), ['a', 'b']);
  select(env.other('gate'), false);
  assert.equal(env.api.answers.answers.gate.branch_value, undefined);
});

test('Parent edits clear obsolete branch interpretations', t => {
  const boot = makeBoot();
  boot.view.answers.answers.gate.value = { other: 'Custom review', selected: ['b'] };
  boot.view.answers.answers.gate.branch_value = ['a', 'b'];
  const env = envFor(t, boot);
  inputValue(env.textarea('gate'), 'A different custom review');
  assert.equal(env.api.answers.answers.gate.branch_value, undefined);
  assert.equal(env.api.view.states.text, 'waiting');
});

test('Explicit multi selections activate their branch even when an additional Other direction awaits interpretation', t => {
  const boot = makeBoot();
  boot.view.answers.answers.gate.value = { other: 'Also adapt this to my process', selected: ['a'] };
  const env = envFor(t, boot);
  assert.equal(env.api.view.states.text, 'active');
  assert.equal(env.textarea('text').value, 'Initial answer');
  assert.equal(env.api.answers.answers.gate.branch_value, undefined);
});

test('Unusual text remains user input for semantic review by the host, not browser heuristics', t => {
  const env = envFor(t);
  for (const text of ['.', '0', '없음', 'אפס', 'Do not add any scripts.']) {
    inputValue(env.textarea('text'), text);
    assert.equal(env.api.answers.answers.text.value, text);
    assert.equal(env.api.answers.answers.text.actor, 'user');
  }
});

test('A page holds up to four questions and the recommended option is marked on the card', t => {
  const boot = makeBoot();
  boot.view.questionnaire.questions[2].recommendation = { value: 'b', rationale: 'Shorter output', assumptions: [] };
  const env = envFor(t, boot);
  assert.deepEqual(copy(env.api.pages.map(page => page.questions.length)), [3, 1]);
  const badges = env.card('other').querySelectorAll('.recommended-badge');
  assert.equal(badges.length, 1);
  assert.equal(badges[0].textContent, catalog.en.recommended_badge);
  assert.equal(badges[0].closest('.option').querySelector('input').value, 'b');
  assert.equal(env.card('gate').querySelectorAll('.recommended-badge').length, 0);
});

test('Long questions can be paged through without filling all answers', t => {
  const env = envFor(t); env.api.clearAnswer('gate');
  const lastPage = env.api.pages.length - 1; env.api.goPage(lastPage);
  assert.equal(env.api.pageIndex, lastPage);
  assert.ok(env.textarea('last'));
  assert.equal(env.ids.get('save-answers').disabled, false);
});

test('A recommendation remains an explicit user choice and does not auto-fill other questions', t => {
  const boot = makeBoot();
  boot.view.questionnaire.questions[0].recommendation = { value: ['c'], rationale: 'Best for asynchronous review.', assumptions: [] };
  const env = envFor(t, boot);
  env.card('gate').querySelector('.evidence').querySelector('button').click();
  assert.deepEqual(copy(env.api.answers.answers.gate.value), ['c']);
  assert.equal(env.api.answers.answers.gate.actor, 'user');
  assert.equal(env.api.answers.answers.other.value, 'a');
});

test('Invalid embedded answer formats disable save rather than exporting a corrupt snapshot', t => {
  const boot = makeBoot(); boot.view.answers.answers.other.value = 'unknown-option';
  const env = setup(boot); t.after(() => env.dispose());
  assert.equal(env.api, undefined);
  assert.equal(env.ids.get('save-answers').disabled, true);
  assert.match(env.ids.get('notice').textContent, /saved answers/);
});
