const { chromium, expect } = require('playwright/test');
const assert = require('node:assert/strict');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4336/dediche-musicali/';

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    for (const javaScriptEnabled of [false, true]) {
      const context = await browser.newContext({ javaScriptEnabled, serviceWorkers: 'block' });
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.pathname.endsWith('site-settings.json')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ siteEffect: 'none', celebration: { enabled: true, text: 'Font fallback', duration: 3 } }) });
        return url.origin === new URL(base).origin ? route.continue() : route.abort();
      });
      await context.addInitScript(() => {
        if (window.top !== window) return;
        const original = window.fetch.bind(window);
        window.fetch = (input, options) => new URL(input instanceof Request ? input.url : input, location.href).origin === location.origin
          ? original(input, options) : Promise.resolve(new Response('{}'));
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
        document.fonts.load = () => new Promise(() => {});
      });
      const page = await context.newPage();
      await page.goto(base);
      await expect(page.locator('.hero-image')).toBeVisible();
      await expect(page.locator('iframe[src*="spotify"]')).toHaveCount(1);
      if (javaScriptEnabled) {
        await page.locator('.photo-celebration-stage').evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
        const root = page.locator('[data-photo-celebration]');
        await expect(root).toHaveAttribute('data-state', 'running', { timeout: 5000 });
        await expect(root).toHaveAttribute('data-state', 'finished', { timeout: 5000 });
      } else {
        await expect(page.locator('[data-photo-celebration] canvas')).toHaveCount(0);
        assert.ok(await page.locator('.hero-image').getAttribute('src'));
      }
      await context.close();
    }
    console.log('No JavaScript and unavailable font fallback: photo, Spotify markup and graceful completion passed');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
