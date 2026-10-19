const { chromium, webkit, devices, expect } = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4336/dediche-musicali/';

(async () => {
  fs.mkdirSync('.cache/playwright/home-photo', { recursive: true });
  for (const [name, engine, device, launch] of [
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
    ['Desktop', chromium, { viewport: { width: 1440, height: 1000 } }, { channel: 'chrome' }],
  ]) {
    const browser = await engine.launch({ headless: true, ...launch });
    try {
      const context = await browser.newContext({ ...device, serviceWorkers: 'block' });
      await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
      await context.addInitScript(() => {
        const original = window.fetch.bind(window);
        window.fetch = (input, options) => new URL(input instanceof Request ? input.url : input, location.href).origin === location.origin
          ? original(input, options) : Promise.resolve(new Response('{}'));
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
        localStorage.setItem('ddgpilli-pwa-installed', 'true');
      });
      const page = await context.newPage();
      await page.goto(base);
      const photo = page.locator('.hero-image');
      const frame = page.locator('.full-photo-frame');
      await photo.evaluate(img => img.scrollIntoView({ block: 'center', behavior: 'instant' }));
      await expect.poll(() => photo.evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true);
      await expect(page.locator('.music-hero')).toHaveAttribute('data-cinema-active', '', { timeout: 15000 });
      await page.waitForTimeout(1100);
      const sample = () => frame.evaluate(el => getComputedStyle(el).transform);
      const before = await sample();
      await expect.poll(sample, { timeout: 10000, message: 'Zoom and motion remain active' }).not.toBe(before);
      await page.screenshot({ path: `.cache/playwright/home-photo/${name}.png` });
      for (const viewport of [device.viewport, { width: 844, height: 390 }]) {
        await page.setViewportSize(viewport);
        for (const [width, height] of [[600, 900], [1200, 600], [700, 700]]) {
          await photo.evaluate((img, { width, height }) => {
            img.src = 'data:image/svg+xml,' + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><rect width="100%" height="100%" fill="pink"/></svg>`);
          }, { width, height });
          await expect.poll(() => photo.evaluate(img => img.complete && img.naturalWidth)).toBe(width);
          await frame.evaluate(el => {
            el.getAnimations().forEach(animation => { animation.pause(); animation.currentTime = 9000; });
          });
          const geometry = await photo.evaluate(img => {
            const box = img.getBoundingClientRect();
            const caption = document.querySelector('.art-caption').getBoundingClientRect();
            return { ratio: box.width / box.height, captionBelow: caption.top >= box.bottom - 1,
              fits: box.left >= 0 && box.right <= innerWidth, transform: getComputedStyle(img).transform,
              noPan: !img.parentElement.classList.contains('landscape-frame') };
          });
          assert.ok(Math.abs(geometry.ratio - width / height) < .01, 'Natural image proportions retained');
          assert.ok(geometry.captionBelow && geometry.fits && geometry.noPan, 'Every edge visible at maximum zoom, caption outside photo');
          assert.equal(geometry.transform, 'none', 'No separate crop-inducing zoom');
        }
      }
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await expect(frame).toHaveCSS('animation-name', 'none');
      console.log(`${name}: full portrait, landscape and square photos; rotation; animated zoom; reduced motion passed`);
      await context.close();
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
