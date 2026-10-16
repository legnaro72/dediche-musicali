import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mergeFeedback, feedbackUserKey } from '../src/scripts/feedback-data.js';

const first = { userKey: 'anna-rossi', userName: 'Anna Rossi', value: 9, updatedAt: '2026-10-14T10:00:00Z' };
const second = { userKey: 'luca-verdi', userName: 'Luca Verdi', value: 10, updatedAt: '2026-10-14T11:00:00Z' };
const saved = { votes: [first, second], thoughts: [{ ...first, text: 'Primo pensiero' }, { ...second, text: 'Secondo pensiero' }] };

test('a cache containing only the last user preserves every vote and comment', () => {
  const merged = mergeFeedback(saved, { votes: [second], thoughts: [saved.thoughts[1]] });
  assert.equal(merged.votes.length, 2);
  assert.equal(merged.thoughts.length, 2);
  assert.equal(merged.voteAverage, 9.5);
});
test('a user updating their vote on another device counts once, using the newer value', () => {
  const newer = { ...first, userId: 'other-device', value: 7, updatedAt: '2026-10-15T10:00:00Z' };
  assert.equal(mergeFeedback(saved, { votes: [newer] }).voteAverage, 8.5);
  assert.equal(mergeFeedback({ votes: [newer, second] }, { votes: [first] }).voteAverage, 8.5);
  assert.equal(feedbackUserKey({ userName: 'Ánna Rossi' }), first.userKey);
});
test('fresh API lists preserve intentional deletions instead of resurrecting cached entries', () => {
  const merged = mergeFeedback(saved, saved, { votes: [], thoughts: [] });
  assert.deepEqual(merged.votes, []);
  assert.deepEqual(merged.thoughts, []);
  assert.equal(merged.voteAverage, null);
});
test('comments without votes and missing API records retain their independent entries', () => {
  const merged = mergeFeedback(saved, { thoughts: [{ userKey: 'terzo', text: 'Solo commento' }] }, {});
  assert.equal(merged.thoughts.length, 3);
  assert.equal(merged.votes.length, 2);
});
