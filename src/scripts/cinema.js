// Start entrances when they can actually be seen, including after the audio intro.
const motion = matchMedia('(prefers-reduced-motion: reduce)');
let entranceObserver;
let stageObserver;
let cardObserver;
const introVisible = () => !!document.querySelector('[data-audio-intro]:not([hidden])');

function initCinema() {
  entranceObserver?.disconnect();
  stageObserver?.disconnect();
  cardObserver?.disconnect();
  if (!('IntersectionObserver' in window)) return;
  cardObserver = new IntersectionObserver(entries => {
    entries.forEach(({ target, isIntersecting }) => {
      target.toggleAttribute('data-art-active', isIntersecting && !motion.matches && !introVisible());
    });
  });
  document.querySelectorAll('.dedication-card').forEach(card => cardObserver.observe(card));
  const stage = document.querySelector('.music-hero');
  if (stage) {
    stageObserver = new IntersectionObserver(([entry]) => {
      stage.toggleAttribute('data-cinema-active', entry.isIntersecting && !motion.matches && !introVisible());
    });
    stageObserver.observe(stage);
  }
  if (motion.matches || introVisible()) return;
  entranceObserver = new IntersectionObserver(entries => {
    entries.forEach(({ target, isIntersecting }) => {
      if (!isIntersecting) return;
      target.classList.add('cinema-arrived');
      entranceObserver.unobserve(target);
    });
  }, { threshold: .12 });
  document.querySelectorAll('[data-cinema-enter]:not(.cinema-arrived)').forEach(node => entranceObserver.observe(node));
}

motion.addEventListener('change', () => {
  if (motion.matches) {
    // CSS animations are removed by the media query; also stop scripted reactions.
    document.getAnimations().forEach(animation => {
      if (!('animationName' in animation) && !('transitionProperty' in animation)) animation.cancel();
    });
  }
  initCinema();
});
document.addEventListener('ddgpilli:intro-dismissed', () => {
  document.querySelectorAll('[data-cinema-enter]').forEach(node => node.classList.remove('cinema-arrived'));
  initCinema();
});
document.addEventListener('astro:page-load', initCinema);
document.addEventListener('astro:before-swap', () => {
  entranceObserver?.disconnect();
  stageObserver?.disconnect();
  cardObserver?.disconnect();
});
initCinema();
