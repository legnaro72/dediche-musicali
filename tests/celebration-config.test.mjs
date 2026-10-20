import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { normalizeCelebration, fitCelebrationText } from '../src/scripts/celebration-config.js';

test('shared Python/frontend configuration fixtures', () => {
  for (const { input, expected } of JSON.parse(fs.readFileSync('tests/fixtures/celebration-config.json'))) assert.deepEqual(normalizeCelebration(input), expected);
  assert.equal(normalizeCelebration({ duration: Infinity }).duration, 10);
  assert.equal(Array.from(normalizeCelebration({ text: '🌺'.repeat(140) }).text).length, 120);
});
test('short, long, Unicode and unbroken text fit the photo without HTML interpretation', () => {
  const ctx = { font: '', measureText(value) { return { width: Array.from(value).length * Number(this.font.match(/(\d+)px/)[1]) * .59 }; } };
  for (const text of ['Pìlli!', "L’amore è magia 🌺 ".repeat(6), 'a'.repeat(120), "<img onerror=alert('x')>"]) {
    for (const [width, height] of [[260, 420], [540, 900], [740, 290]]) {
      const layout = fitCelebrationText(ctx, text, width, height, 'sans-serif');
      ctx.font = `800 ${layout.size}px sans-serif`;
      assert.ok(layout.lines.every(line => ctx.measureText(line).width <= width * .88 + .01));
      assert.ok(layout.lines.length * layout.lineHeight <= height * .7);
    }
  }
});
