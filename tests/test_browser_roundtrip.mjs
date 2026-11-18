import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { cp, mkdtemp, rm } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright-core');
const root = fileURLToPath(new URL('../', import.meta.url));
const cli = path.join(root, 'any-skill-builder', 'scripts', 'skill_builder.py');
const fixture = path.join(root, 'examples', 'weekly-update-questionnaire.json');
const parent = 'missing-information';
const child = 'clarification-trigger';
const custom = { other: 'Ask for clarification before drafting.', selected: [] };

function run(workspace, command, ...args) {
  const output = execFileSync('python', ['-B', cli, command, '--workspace', workspace, ...args], { encoding: 'utf8' });
  return JSON.parse(output);
}

test('offline Chrome download preserves the interpreted AI answer through keyboard navigation', async (t) => {
  const scratch = await mkdtemp(path.join(process.env.SKILL_BUILDER_TEST_TMPDIR || tmpdir(), 'form-roundtrip-'));
  t.after(() => rm(scratch, { recursive: true, force: true, maxRetries: 5 }));
  const workspace = path.join(scratch, 'run');
  const goal = 'Create a weekly team-update skill from supplied project notes';
  run(workspace, 'init', '--goal', goal, '--review-policy', 'legacy');
  run(workspace, 'set-questions', '--input', fixture, '--rebind-project');
  run(workspace, 'answer', '--question', parent, '--value-json', JSON.stringify(custom),
    '--actor', 'ai', '--rationale', 'The notes leave a material fact unresolved.');
  run(workspace, 'interpret-answer', '--question', parent, '--value-json', '"clarify-first"',
    '--rationale', 'This answer explicitly calls for clarification first.');
  run(workspace, 'answer', '--question', child, '--value-json', '"Ask the release owner."');
  const original = run(workspace, 'status', '--json');
  const before = original.answers.answers;
  assert.equal(before[parent].actor, 'ai');
  assert.equal(before[child].actor, 'user');

  // Use the installed browser. Keep its profile and downloads in this test's scratch folder.
  const context = await chromium.launchPersistentContext(path.join(scratch, 'chrome'), {
    channel: 'chrome', headless: true, offline: true, downloadsPath: scratch,
  });
  try {
    t.diagnostic('Chrome ' + context.browser().version());
    const page = await context.newPage();
    for (const action of ['save immediately', 'Tab without editing', 'edit then Tab']) {
      await t.test(action, async () => {
        const caseRun = path.join(scratch, action);
        await cp(workspace, caseRun, { recursive: true });
        const html = run(caseRun, 'render').path;
        await page.goto(pathToFileURL(html).href);
        await page.locator('#page-select').selectOption('1'); // Incomplete notes
        const editor = page.locator('#input-' + parent);
        assert.equal(await editor.inputValue(), custom.other);
        assert.equal(await page.locator('#input-' + child).inputValue(), before[child].value);
        if (action !== 'save immediately') {
          await editor.click();
          if (action === 'edit then Tab') await editor.fill('Ask only about urgent items.');
          await editor.press('Tab');
        }
        const [download] = await Promise.all([
          page.waitForEvent('download'),
          page.locator('#save-answers').click(),
        ]);
        const saved = path.join(scratch, 'saved.html');
        await download.saveAs(saved);
        const imported = run(caseRun, 'import-answers', '--input', saved, '--full');
        const answer = imported.answers.answers[parent];
        if (action === 'edit then Tab') {
          assert.equal(answer.actor, 'user');
          assert.equal(answer.value.other, 'Ask only about urgent items.');
          assert.ok(!Object.hasOwn(answer, 'branch_value'));
          assert.ok(!Object.hasOwn(answer, 'branch_rationale'));
          assert.deepEqual(imported.unresolved_branch_ids, [parent]);
          assert.equal(imported.states[child], 'waiting');
        } else {
          assert.deepEqual(answer, before[parent]);
          assert.deepEqual(imported.answers.answers[child], before[child]);
          assert.deepEqual(imported.unresolved_branch_ids, []);
          assert.equal(imported.states[child], 'active');
        }
      });
    }
    await t.test('one shared input and both example outcomes survive choosing, saving, and restoring', async () => {
      await page.goto(pathToFileURL(run(workspace, 'render').path).href);
      await page.locator('#page-select').selectOption('1');
      const question = original.questionnaire.questions.find(q => q.id === parent);
      assert.ok(await page.getByText(question.help, { exact: true }).isVisible());
      for (const option of question.options) {
        for (const text of [option.description, option.effect]) {
          assert.ok(await page.getByText(text, { exact: true }).isVisible());
          assert.equal(await page.getByRole('radio', { name: text }).inputValue(), option.id);
        }
      }
      const draft = question.options.find(option => option.id === 'draft-gaps');
      await page.getByRole('radio', { name: draft.description }).check();
      const [download] = await Promise.all([
        page.waitForEvent('download'), page.locator('#save-answers').click(),
      ]);
      const saved = path.join(scratch, 'compared-choices.html');
      await download.saveAs(saved);
      const restored = run(path.join(scratch, 'restored'), 'restore', '--input', saved, '--full');
      assert.deepEqual(restored.questionnaire.questions.find(q => q.id === parent), question);
      assert.equal(restored.answers.answers[parent].value, draft.id);
      assert.equal(restored.answers.answers[parent].actor, 'user');
    });
  } finally {
    await context.close();
  }
});
