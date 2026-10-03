import { readFavorites } from './favorites.js';
import { navigate } from 'astro:transitions/client';

function initArchive() {
  const root = document.querySelector('[data-archive]');
  if (!root || root.dataset.bound) return;
  root.dataset.bound = 'true';
  const search = root.querySelector('#search-input');
  const artist = root.querySelector('#filter-artist');
  const month = root.querySelector('#filter-month');
  const favoriteFilter = root.querySelector('[data-favorites-filter]');
  const cards = [...root.querySelectorAll('.dedication-card')];
  const empty = root.querySelector('#no-result');
  const count = root.querySelector('[data-results-count]');
  const random = root.querySelector('[data-surprise]');
  const normalize = value => value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim();
  const indexed = cards.map(card => ({ card, text: normalize(card.dataset.search || ''), artist: normalize(card.dataset.artist || '') }));
  const params = new URLSearchParams(location.search);
  search.value = params.get('q') || '';
  artist.value = params.get('artista') || '';
  month.value = params.get('mese') || '';
  favoriteFilter.setAttribute('aria-pressed', String(params.get('preferiti') === '1'));

  function applyFilters(updateUrl = false) {
    const q = normalize(search.value);
    const selectedArtist = normalize(artist.value);
    const favoritesOnly = favoriteFilter.getAttribute('aria-pressed') === 'true';
    const favorites = readFavorites();
    let visible = 0;
    for (const entry of indexed) {
      const show = (!q || entry.text.includes(q)) && (!selectedArtist || entry.artist === selectedArtist)
        && (!month.value || entry.card.dataset.month === month.value)
        && (!favoritesOnly || favorites.has(entry.card.dataset.dedicationId));
      entry.card.hidden = !show;
      if (show) visible++;
    }
    empty.hidden = visible !== 0;
    count.textContent = `${visible} ${visible === 1 ? 'dedica' : 'dediche'}${favoritesOnly ? ' nei preferiti' : ''}`;
    random.disabled = visible === 0;
    if (updateUrl) {
      const url = new URL(location.href);
      for (const [key, value] of [['q', search.value], ['artista', artist.value], ['mese', month.value], ['preferiti', favoritesOnly ? '1' : '']]) {
        value ? url.searchParams.set(key, value) : url.searchParams.delete(key);
      }
      history.replaceState(history.state, '', url);
    }
  }
  search.addEventListener('input', () => applyFilters(true));
  artist.addEventListener('change', () => applyFilters(true));
  month.addEventListener('change', () => applyFilters(true));
  favoriteFilter.addEventListener('click', () => {
    favoriteFilter.setAttribute('aria-pressed', String(favoriteFilter.getAttribute('aria-pressed') !== 'true'));
    applyFilters(true);
  });
  root.querySelectorAll('[data-reset-filters]').forEach(button => button.addEventListener('click', () => {
    search.value = artist.value = month.value = '';
    favoriteFilter.setAttribute('aria-pressed', 'false');
    applyFilters(true);
    search.focus();
  }));
  random.addEventListener('click', () => {
    const visible = cards.filter(card => !card.hidden);
    if (visible.length) navigate(visible[Math.floor(Math.random() * visible.length)].href);
  });
  const onFavorites = () => applyFilters();
  window.addEventListener('ddgpilli:favorites-changed', onFavorites);
  document.addEventListener('astro:before-swap', () => window.removeEventListener('ddgpilli:favorites-changed', onFavorites), { once: true });
  applyFilters();
}
document.addEventListener('astro:page-load', initArchive);
initArchive();
