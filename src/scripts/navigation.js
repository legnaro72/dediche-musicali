// Astro runs bundled modules once. Delegate to the document so that controls
// replaced by client-side navigation (including history) keep working.
const setMenuOpen = (open) => {
  document.getElementById('primary-navigation')?.classList.toggle('is-open', open);
  document.querySelector('[data-nav-toggle]')?.setAttribute('aria-expanded', String(open));
};

document.addEventListener('click', (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  if (target.closest('[data-nav-toggle]')) {
    event.preventDefault();
    setMenuOpen(!document.getElementById('primary-navigation')?.classList.contains('is-open'));
  } else if (target.closest('#primary-navigation a') || !target.closest('#primary-navigation')) {
    setMenuOpen(false);
  }
});

// Mobile Safari need not synthesize a bubbling click on non-interactive content.
// Pointer events close on an outside touch without toggling the button twice.
document.addEventListener('pointerdown', (event) => {
  const target = event.target;
  if (target instanceof Element && !target.closest('#primary-navigation, [data-nav-toggle]')) {
    setMenuOpen(false);
  }
}, { passive: true });

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && document.getElementById('primary-navigation')?.classList.contains('is-open')) {
    setMenuOpen(false);
    document.querySelector('[data-nav-toggle]')?.focus();
  }
});

const syncNavbar = () => {
  document.getElementById('navbar')?.classList.toggle('scrolled', window.scrollY > 40);
};
const resetNavbar = () => {
  setMenuOpen(false);
  syncNavbar();
};
document.addEventListener('astro:before-swap', () => setMenuOpen(false));
document.addEventListener('astro:page-load', resetNavbar);
window.addEventListener('pageshow', resetNavbar);
window.addEventListener('resize', () => setMenuOpen(false), { passive: true });
window.addEventListener('scroll', syncNavbar, { passive: true });
resetNavbar();
