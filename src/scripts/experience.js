import { readFavorites, toggleFavorite, favoritesKey } from './favorites.js';
import './cinema.js';

let toastTimer;
export function notify(message) {
  const toast = document.querySelector('[data-experience-toast]');
  if (!toast) return;
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.hidden = false;
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4500);
}

function syncFavorites() {
  const favorites = readFavorites();
  document.querySelectorAll('[data-favorite]').forEach(button => {
    const saved = favorites.has(button.dataset.favorite);
    button.setAttribute('aria-pressed', String(saved));
    button.setAttribute('aria-label', saved ? 'Rimuovi dai preferiti' : 'Salva nei preferiti');
    const label = button.querySelector('[data-favorite-label]');
    if (label) label.textContent = saved ? 'Salvata' : 'Salva';
  });
}

function showShareFallback(url, trigger) {
  const dialog = document.querySelector('[data-share-dialog]');
  const input = dialog?.querySelector('input');
  if (!(dialog instanceof HTMLDialogElement) || !input) return;
  input.value = url;
  dialog.showModal();
  input.focus();
  input.select();
  dialog.addEventListener('close', () => trigger?.focus(), { once: true });
}

document.addEventListener('click', async event => {
  if (!(event.target instanceof Element)) return;
  const favorite = event.target.closest('[data-favorite]');
  if (favorite) {
    const { saved, persistent } = toggleFavorite(favorite.dataset.favorite);
    notify(!persistent ? 'Memoria non disponibile: preferiti conservati solo per questa sessione.' : saved ? 'Salvata nei preferiti su questo dispositivo ♥' : 'Dedica rimossa dai preferiti.');
  }
  const share = event.target.closest('[data-share-url]');
  if (share) {
    const url = share.dataset.shareUrl;
    if (navigator.share) {
      try { await navigator.share({ title: share.dataset.shareTitle, url }); return; }
      catch (error) { if (error.name === 'AbortError') return; }
    }
    showShareFallback(url, share);
  }
  if (event.target.closest('[data-copy-link]')) {
    const input = document.querySelector('[data-share-dialog] input');
    try {
      await navigator.clipboard.writeText(input.value);
      notify('Link copiato. Pronto da condividere.');
      document.querySelector('[data-share-dialog]')?.close();
    } catch {
      input?.focus();
      input?.select();
      notify('Tieni premuto sul link selezionato e scegli Copia.');
    }
  }
  if (event.target.closest('[data-share-close]')) document.querySelector('[data-share-dialog]')?.close();
  const reaction = event.target.closest('[data-reaction]');
  if (reaction && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    reaction.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.16)' }, { transform: 'scale(1)' }], { duration: 350 });
  }
});

let revealObserver;
function initExperience() {
  syncFavorites();
  syncConnection();
  const current = location.pathname.replace(/\/$/, '');
  document.querySelectorAll('#primary-navigation a').forEach(link => {
    if (new URL(link.href).pathname.replace(/\/$/, '') === current) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  revealObserver?.disconnect();
  const reveals = document.querySelectorAll('.reveal');
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) {
    reveals.forEach(node => node.classList.add('visible'));
    return;
  }
  revealObserver = new IntersectionObserver(entries => entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    entry.target.classList.add('visible');
    entry.target.classList.remove('reveal-pending');
    revealObserver.unobserve(entry.target);
  }), { threshold: 0.05 });
  reveals.forEach(node => { node.classList.add('reveal-pending'); revealObserver.observe(node); });
}

function syncConnection() {
  const notice = document.querySelector('[data-offline-notice]');
  if (notice) notice.hidden = navigator.onLine;
}
window.addEventListener('online', syncConnection);
window.addEventListener('offline', syncConnection);
window.addEventListener('ddgpilli:favorites-changed', syncFavorites);
window.addEventListener('storage', event => {
  if (event.key === favoritesKey || event.key === null) window.dispatchEvent(new Event('ddgpilli:favorites-changed'));
});
document.addEventListener('astro:page-load', initExperience);
matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', initExperience);
document.addEventListener('astro:before-swap', () => {
  revealObserver?.disconnect();
  document.querySelector('[data-share-dialog]')?.close();
  clearTimeout(toastTimer);
});
initExperience();

document.addEventListener('visibilitychange', () => { document.body.toggleAttribute('data-page-hidden', document.hidden); });
window.addEventListener('blur', () => {
  setTimeout(() => {
    if (document.activeElement?.matches('.audio-embed iframe, .video-player')) document.dispatchEvent(new Event('ddgpilli:foreground-audio'));
  }, 0);
});
