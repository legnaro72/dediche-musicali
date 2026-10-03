export const favoritesKey = 'ddgpilli-favorites-v1';
let memory = [];
let sessionOnly = false;

export function readFavorites() {
  if (sessionOnly) return new Set(memory);
  try {
    const value = JSON.parse(localStorage.getItem(favoritesKey) || '[]');
    memory = Array.isArray(value) ? [...new Set(value.filter(id => typeof id === 'string'))] : [];
  } catch { /* Private browsing or unavailable storage: keep this session usable. */ }
  return new Set(memory);
}

export function toggleFavorite(id) {
  const values = readFavorites();
  const saved = !values.has(id);
  saved ? values.add(id) : values.delete(id);
  memory = [...values];
  let persistent = true;
  try { localStorage.setItem(favoritesKey, JSON.stringify(memory)); }
  catch { persistent = false; sessionOnly = true; }
  window.dispatchEvent(new Event('ddgpilli:favorites-changed'));
  return { saved, persistent };
}
