// Match the identity used by the feedback API, including across devices.
export function feedbackUserKey(entry) {
  return String(entry?.userKey || entry?.user_key || entry?.userName || entry?.user_name || entry?.userId || entry?.user_id || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 160);
}

function mergeEntries(saved = [], cached = []) {
  const entries = new Map();
  for (const entry of [...(Array.isArray(saved) ? saved : []), ...(Array.isArray(cached) ? cached : [])]) {
    const key = feedbackUserKey(entry);
    if (!key) continue;
    const previous = entries.get(key);
    const timestamp = value => Date.parse(value?.updatedAt || value?.updated_at || value?.createdAt || '') || 0;
    if (!previous || timestamp(entry) >= timestamp(previous)) entries.set(key, entry);
  }
  return [...entries.values()];
}

export function mergeFeedback(saved = {}, cached = {}, remote = {}) {
  const result = { ...saved, ...cached, ...remote };
  for (const field of ['votes', 'thoughts']) {
    // A fresh server list is authoritative, including explicit removals.
    result[field] = Array.isArray(remote[field])
      ? mergeEntries(remote[field]) : mergeEntries(saved[field], cached[field]);
  }
  result.votes = result.votes.filter(entry => Number.isInteger(Number(entry.value)) && Number(entry.value) >= 1 && Number(entry.value) <= 10);
  if (result.votes.length) result.voteAverage = result.votes.reduce((sum, entry) => sum + Number(entry.value), 0) / result.votes.length;
  else if (Array.isArray(remote.votes)) result.voteAverage = null;
  return result;
}
