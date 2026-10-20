import { normalizeCelebration, fitCelebrationText } from './celebration-config.js';

const palette = ['#fff3cd', '#ffd28b', '#ffacb9', '#c7a8ff', '#9de7f0'];
const clamp = value => Math.max(0, Math.min(1, value));
const ease = value => value < .5 ? 4 * value ** 3 : 1 - (-2 * value + 2) ** 3 / 2;

function glyphs(ctx, layout, x, y) {
  ctx.font = `800 ${layout.size}px ${layout.family}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  layout.lines.forEach((line, i) => ctx.fillText(line, x, y + (i - (layout.lines.length - 1) / 2) * layout.lineHeight));
}

function celebration(root, config, onStart, onFinish) {
  const stage = root.parentElement;
  const image = stage?.querySelector('img');
  const abort = new AbortController();
  const { signal } = abort;
  const timers = new Set();
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  let observer, resizeObserver, canvas, ctx, layout, particles = [];
  let raf = 0, finished = false, width = 0, height = 0, dirty = true;
  let origin = 0, hiddenAt = null, lastPaint = -Infinity;
  let compact = true;
  let fontFamily = 'system-ui, sans-serif';

  function finish(state = 'finished') {
    if (finished) return;
    finished = true;
    cancelAnimationFrame(raf);
    observer?.disconnect();
    resizeObserver?.disconnect();
    for (const timer of timers) clearTimeout(timer);
    timers.clear();
    abort.abort();
    if (canvas) { canvas.width = canvas.height = 1; canvas.remove(); }
    ctx = null;
    particles = [];
    root.hidden = true;
    root.dataset.state = state;
    root.dataset.phase = state;
    root.dataset.particles = '0';
    onFinish(state);
  }

  function timeout(ms, callback) {
    const timer = setTimeout(() => { timers.delete(timer); callback(); }, ms);
    timers.add(timer);
    return timer;
  }

  function waitForImage() {
    if (!image) return Promise.reject(new Error('No photo'));
    if (image.complete) return image.naturalWidth ? Promise.resolve() : Promise.reject(new Error('Photo unavailable'));
    return new Promise((resolve, reject) => {
      image.addEventListener('load', resolve, { once: true, signal });
      image.addEventListener('error', reject, { once: true, signal });
      signal.addEventListener('abort', reject, { once: true });
      timeout(6000, () => reject(new Error('Photo not ready')));
    });
  }

  function waitForVisiblePhoto() {
    return new Promise((resolve, reject) => {
      let inView = !('IntersectionObserver' in window);
      const check = () => {
        const intro = document.querySelector('[data-audio-intro]:not([hidden])');
        if (!inView || intro || document.hidden || !stage.clientWidth || !stage.clientHeight) return;
        observer?.disconnect();
        resolve();
      };
      if ('IntersectionObserver' in window) {
        observer = new IntersectionObserver(([entry]) => { inView = entry.isIntersecting; check(); });
        observer.observe(stage);
      }
      document.addEventListener('ddgpilli:intro-dismissed', check, { signal });
      document.addEventListener('visibilitychange', check, { signal });
      signal.addEventListener('abort', reject, { once: true });
      check();
    });
  }

  function seedLetters() {
    const mask = document.createElement('canvas');
    const scale = Math.min(1, 720 / width, 1000 / height);
    mask.width = Math.ceil(width * scale);
    mask.height = Math.ceil(height * scale);
    const brush = mask.getContext('2d', { willReadFrequently: true });
    if (!brush) return [];
    brush.scale(scale, scale);
    brush.fillStyle = '#fff';
    glyphs(brush, layout, width / 2, height / 2);
    const pixels = brush.getImageData(0, 0, mask.width, mask.height).data;
    const budget = compact ? 420 : 760;
    const points = [];
    let seen = 0;
    // Reservoir sampling bounds both memory and particle count even for dense text.
    for (let y = 1; y < mask.height; y += 2) {
      for (let x = 1; x < mask.width; x += 2) {
        if (pixels[(y * mask.width + x) * 4 + 3] < 120) continue;
        const point = { x: x / scale, y: y / scale };
        const slot = seen < budget ? seen : Math.floor(Math.random() * (seen + 1));
        if (slot < budget) points[slot] = point;
        seen++;
      }
    }
    mask.width = mask.height = 1;
    return points.map((point, i) => {
      const angle = Math.atan2(point.y - height / 2, point.x - width / 2) + (Math.random() - .5) * 1.2;
      const speed = Math.min(width, height) * (.35 + Math.random() * 1.05);
      return { ...point, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed,
        size: .9 + Math.random() * 2.5, spin: (Math.random() - .5) * 14,
        color: palette[i % palette.length], type: i % 7 === 0 ? 'spark' : i % 3 === 0 ? 'confetti' : 'dust' };
    });
  }

  function configure() {
    // Layout dimensions exclude the existing animated transform on the frame.
    width = stage.clientWidth;
    height = stage.clientHeight;
    if (!width || !height) return false;
    compact = width < 480 || matchMedia('(pointer: coarse)').matches;
    const density = Math.min(devicePixelRatio || 1, 1.5, Math.sqrt(900000 / (width * height)));
    canvas.width = Math.max(1, Math.ceil(width * density));
    canvas.height = Math.max(1, Math.ceil(height * density));
    ctx.setTransform(density, 0, 0, density, 0, 0);
    layout = fitCelebrationText(ctx, config.text, width, height, fontFamily);
    particles = motion.matches ? [] : seedLetters();
    root.dataset.particles = String(particles.length);
    dirty = false;
    return true;
  }

  function text(scale, alpha, tension = 0) {
    ctx.save();
    ctx.translate(width / 2, height / 2);
    ctx.scale(scale, scale);
    ctx.globalAlpha = alpha;
    ctx.font = `800 ${layout.size}px ${layout.family}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineJoin = 'round';
    ctx.lineWidth = Math.max(2, layout.size * .035);
    ctx.strokeStyle = '#291831';
    ctx.shadowColor = '#160b26';
    ctx.shadowBlur = 12;
    const gradient = ctx.createLinearGradient(-width / 2, -height * .15, width / 2, height * .15);
    gradient.addColorStop(0, '#fff5d5');
    gradient.addColorStop(.5, '#ffd392');
    gradient.addColorStop(1, '#ffb9d8');
    layout.lines.forEach((line, i) => {
      const y = (i - (layout.lines.length - 1) / 2) * layout.lineHeight;
      ctx.strokeText(line, 0, y);
      ctx.shadowColor = '#ffd6a1';
      ctx.shadowBlur = 5 + tension * 13;
      ctx.fillStyle = gradient;
      ctx.fillText(line, 0, y);
    });
    ctx.restore();
  }

  function debris(progress) {
    const travel = 1 - (1 - progress) ** 2;
    const gravity = progress * progress * height * .23;
    ctx.shadowBlur = 0;
    particles.forEach((p, i) => {
      const x = p.x + p.vx * travel;
      const y = p.y + p.vy * travel + gravity;
      ctx.globalAlpha = (1 - progress) ** 1.7;
      ctx.fillStyle = ctx.strokeStyle = p.color;
      if (p.type === 'spark' && i < (compact ? 280 : 560)) {
        const tail = .018 * (1 - progress);
        ctx.lineWidth = .8;
        ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x - p.vx * tail, y - p.vy * tail); ctx.stroke();
      }
      if (p.type === 'confetti') {
        ctx.save(); ctx.translate(x, y); ctx.rotate(p.spin * progress);
        ctx.fillRect(-p.size, -p.size / 2, p.size * 2, p.size * (.5 + Math.abs(Math.cos(p.spin * progress))));
        ctx.restore();
      } else {
        ctx.fillRect(x, y, p.size, p.size);
      }
    });
    ctx.globalAlpha = 1;
  }

  function paint(now) {
    if (finished || document.hidden) return;
    try {
      const elapsed = (now - origin) / 1000;
      const t = clamp(elapsed / config.duration);
      if (t >= 1) { finish(); return; }
      if (dirty && !configure()) { finish('cancelled'); return; }
      if (now - lastPaint >= 1000 / (compact ? 30 : 60) - 1) {
        lastPaint = now;
        ctx.clearRect(0, 0, width, height);
        let phase;
        if (motion.matches) {
          phase = 'reduced';
          text(.7, Math.min(clamp(t / .2), clamp((1 - t) / .2)) * .9);
        } else if (t < .55) {
          phase = t < .12 ? 'entrance' : t < .46 ? 'growth' : 'tension';
          const scale = t < .12 ? .16 + .12 * ease(t / .12) : .28 + .72 * ease(clamp((t - .12) / .34));
          text(scale, clamp(t / .07), clamp((t - .46) / .09));
        } else {
          const burst = (t - .55) / .45;
          phase = burst < .55 ? 'explosion' : 'dissolve';
          if (burst < .1) text(1, 1 - burst / .1, 1);
          debris(burst);
        }
        if (root.dataset.phase !== phase) root.dataset.phase = phase;
      }
      raf = requestAnimationFrame(paint);
    } catch { finish('error'); }
  }

  root.dataset.state = 'waiting';
  Promise.resolve().then(async () => {
    if (signal.aborted || finished) return;
    const family = getComputedStyle(stage).getPropertyValue('--font-sans').trim() || 'system-ui, sans-serif';
    const fonts = document.fonts ? Promise.race([
      Promise.all([document.fonts.ready, document.fonts.load(`800 64px ${family}`, config.text)]).then(() => true, () => false),
      new Promise(resolve => timeout(2000, () => resolve(false))),
    ]) : Promise.resolve(false);
    const [, fontsReady] = await Promise.all([waitForImage(), fonts, waitForVisiblePhoto()]);
    if (signal.aborted || finished) return;
    fontFamily = fontsReady ? family : 'system-ui, sans-serif';
    // No readiness timeout survives into the animation.
    for (const timer of timers) clearTimeout(timer);
    timers.clear();
    canvas = document.createElement('canvas');
    ctx = canvas.getContext('2d');
    if (!ctx) { finish('error'); return; }
    canvas.setAttribute('aria-hidden', 'true');
    root.append(canvas);
    if (!configure()) { finish('cancelled'); return; }
    if ('ResizeObserver' in window) {
      resizeObserver = new ResizeObserver(() => { dirty = true; });
      resizeObserver.observe(stage);
    } else window.addEventListener('resize', () => { dirty = true; }, { signal });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) { hiddenAt = performance.now(); cancelAnimationFrame(raf); }
      else if (hiddenAt !== null) {
        origin += performance.now() - hiddenAt;
        hiddenAt = null;
        lastPaint = -Infinity;
        raf = requestAnimationFrame(paint);
      }
    }, { signal });
    motion.addEventListener('change', () => finish('cancelled'), { signal });
    root.hidden = false;
    root.dataset.state = 'running';
    root.dataset.duration = String(config.duration);
    root.dataset.variant = motion.matches ? 'reduced' : 'full';
    origin = performance.now();
    onStart();
    raf = requestAnimationFrame(paint);
  }).catch(() => { if (!signal.aborted) finish('error'); });
  return { cancel: () => finish('cancelled') };
}

// One coordinator for Astro's module lifetime; each run owns and disposes its resources.
let entry = null;
let settings = window.__DDGPILLI_SITE_SETTINGS || {};
function consider() {
  if (!entry) return;
  const config = normalizeCelebration(settings.celebration);
  if (!config.enabled) { entry.run?.cancel(); return; }
  if (entry.started) return;
  const key = JSON.stringify(config);
  if (entry.run && entry.key === key) return;
  entry.run?.cancel();
  const current = entry;
  current.key = key;
  current.run = celebration(current.root, config, () => { current.started = true; }, state => {
    current.run = null;
    if (state === 'error') current.started = true;
  });
}
function leave() { entry?.run?.cancel(); entry = null; }
function enter() {
  const root = document.querySelector('.music-hero [data-photo-celebration]');
  if (entry?.root !== root) {
    leave();
    if (root) entry = { root, started: false, run: null, key: '' };
  }
  consider();
}
window.addEventListener('ddgpilli:site-settings-updated', event => { settings = event.detail || {}; consider(); });
document.addEventListener('astro:before-swap', leave);
document.addEventListener('astro:page-load', enter);
window.addEventListener('pageshow', event => { if (event.persisted) leave(); enter(); });
enter();
