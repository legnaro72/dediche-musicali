import { readFavorites } from './favorites.js';

function initArchive() {
  const root = document.querySelector('[data-archive]');
  if (!root || root.dataset.bound) return;
  root.dataset.bound = 'true';
  const search = root.querySelector('#search-input');
  const artist = root.querySelector('#filter-artist');
  const month = root.querySelector('#filter-month');
  const favoriteFilter = root.querySelector('[data-favorites-filter]');
  const grid = root.querySelector('#archive-grid');
  const template = root.querySelector('[data-archive-cards]');
  if (!(template instanceof HTMLTemplateElement) || !grid) return;
  const cards = [...template.content.querySelectorAll('.dedication-card')];
  const pagination = root.querySelector('[data-archive-pagination]');
  const previous = root.querySelector('[data-archive-prev]');
  const next = root.querySelector('[data-archive-next]');
  const pageLabel = root.querySelector('[data-archive-page]');
  const pageSize = 12;
  let matches = [];
  const empty = root.querySelector('#no-result');
  const count = root.querySelector('[data-results-count]');
  const random = root.querySelector('[data-surprise]');
  const normalize = value => value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim();
  const indexed = cards.map(card => ({ card, text: normalize(card.dataset.search || ''), artist: normalize(card.dataset.artist || '') }));
  const params = new URLSearchParams(location.search);
  let page = Math.max(1, Number.parseInt(params.get('pagina') || '1', 10) || 1);
  search.value = params.get('q') || '';
  artist.value = params.get('artista') || '';
  month.value = params.get('mese') || '';
  favoriteFilter.setAttribute('aria-pressed', String(params.get('preferiti') === '1'));

  function applyFilters(updateUrl = false, resetPage = true) {
    if (resetPage) page = 1;
    const q = normalize(search.value);
    const selectedArtist = normalize(artist.value);
    const favoritesOnly = favoriteFilter.getAttribute('aria-pressed') === 'true';
    const favorites = readFavorites();
    matches = indexed.filter(entry => (!q || entry.text.includes(q)) && (!selectedArtist || entry.artist === selectedArtist)
        && (!month.value || entry.card.dataset.month === month.value)
        && (!favoritesOnly || favorites.has(entry.card.dataset.dedicationId)));
    const visible = matches.length;
    const pages = Math.max(1, Math.ceil(visible / pageSize));
    page = Math.min(page, pages);
    // Template entries remain inert: only this page's photos can decode or animate.
    grid.replaceChildren(...matches.slice((page - 1) * pageSize, page * pageSize).map(entry => entry.card.cloneNode(true)));
    previous.disabled = page === 1;
    next.disabled = page === pages;
    pageLabel.textContent = `Pagina ${page} di ${pages}`;
    pagination.hidden = pages === 1;
    document.dispatchEvent(new CustomEvent('ddgpilli:archive-rendered'));
    empty.hidden = visible !== 0;
    count.textContent = `${visible} ${visible === 1 ? 'dedica' : 'dediche'}${favoritesOnly ? ' nei preferiti' : ''}`;
    random.disabled = visible === 0;
    if (updateUrl) {
      const url = new URL(location.href);
      for (const [key, value] of [['q', search.value], ['artista', artist.value], ['mese', month.value], ['preferiti', favoritesOnly ? '1' : ''], ['pagina', page > 1 ? String(page) : '']]) {
        value ? url.searchParams.set(key, value) : url.searchParams.delete(key);
      }
      history.replaceState(history.state, '', url);
    }
  }
  for (const [button, increment] of [[previous, -1], [next, 1]]) {
    button.addEventListener('click', () => {
      page += increment;
      applyFilters(true, false);
      root.querySelector('.archive-toolbar').scrollIntoView({ block: 'start', behavior: 'instant' });
    });
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
    if (matches.length) location.assign(matches[Math.floor(Math.random() * matches.length)].card.href);
  });
  const onFavorites = () => applyFilters();
  window.addEventListener('ddgpilli:favorites-changed', onFavorites);
  document.addEventListener('astro:before-swap', () => window.removeEventListener('ddgpilli:favorites-changed', onFavorites), { once: true });
  applyFilters(false, false);
}
document.addEventListener('astro:page-load', initArchive);
initArchive();
