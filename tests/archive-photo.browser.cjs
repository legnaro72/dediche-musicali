const { chromium, webkit, devices, expect } = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4336/dediche-musicali/';
const yesterday = '2026-10-18-in-viaggio-verso-il-paradiso-achille-lauro';

(async () => {
  fs.mkdirSync('.cache/playwright/archive-photo', { recursive: true });
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
      await page.goto(base + 'archive/');
      const card = page.locator(`[data-dedication-id="${yesterday}"]`);
      const frame = card.locator('.dedication-card-img-wrap');
      await card.evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
      await expect(card).toHaveAttribute('data-art-active', '');
      const sample = () => frame.evaluate(el => getComputedStyle(el).transform);
      const before = await sample();
      await expect.poll(sample, { timeout: 10000 }).not.toBe(before);
      await card.hover({ force: true });
      await expect(card.locator('.image-frame')).toHaveCSS('transform', 'none');
      await page.screenshot({ path: `.cache/playwright/archive-photo/${name}.png` });
      // Decode every image, including lazy offscreen entries, before checking geometry.
      await page.locator('.dedication-card img').evaluateAll(async images => {
        images.forEach(img => { img.loading = 'eager'; });
        await Promise.all(images.map(img => img.decode()));
      });
      for (const viewport of [device.viewport, { width: 844, height: 390 }]) {
        await page.setViewportSize(viewport);
        const failures = await page.locator('.dedication-card').evaluateAll(cards => cards.flatMap(card => {
          const img = card.querySelector('img');
          if (!img) return [];
          const frame = card.querySelector('.dedication-card-img-wrap');
          frame.getAnimations().forEach(animation => { animation.pause(); animation.currentTime = 5000; });
          const photo = img.getBoundingClientRect();
          const outer = card.getBoundingClientRect();
          const complete = Math.abs(photo.width / photo.height - img.naturalWidth / img.naturalHeight) < .01;
          const contained = photo.left >= outer.left && photo.right <= outer.right && photo.top >= outer.top && photo.bottom <= outer.bottom;
          return complete && contained && !img.parentElement.classList.contains('landscape-frame') ? [] : [{ id: card.dataset.dedicationId, complete, contained, size: [img.offsetWidth, img.offsetHeight], natural: [img.naturalWidth, img.naturalHeight], photo: photo.toJSON(), outer: outer.toJSON() }];
        }));
        assert.deepEqual(failures, [], 'Every archive photo is complete at maximum animated zoom');
      }
      await page.setViewportSize(device.viewport);
      await page.locator('#search-input').fill('In Viaggio Verso Il Paradiso');
      await expect(card).toBeVisible();
      await card.click({ force: true });
      await page.waitForURL(`**/dediche/${yesterday}/`);
      const detailPhoto = page.locator('.detail-art img');
      await expect.poll(() => detailPhoto.evaluate(img => img.complete && img.naturalWidth)).toBe(1080);
      assert.ok(await detailPhoto.evaluate(img => Math.abs(img.offsetWidth / img.offsetHeight - 1080 / 1037) < .01), 'Yesterday full original proportions preserved in detail');
      await page.goto(base + 'archive/');
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await expect(page.locator('.dedication-card-img-wrap').first()).toHaveCSS('animation-name', 'none');
      console.log(`${name}: all archive photos uncropped, visible animation, rotation, filters, detail navigation and reduced motion passed`);
      await context.close();
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
