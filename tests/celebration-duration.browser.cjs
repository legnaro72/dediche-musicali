const { chromium, webkit, devices, expect } = require('playwright/test');
const assert = require('node:assert/strict');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4336/dediche-musicali/';

(async () => {
  await Promise.all([
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
  ].map(async ([name, engine, device, launch]) => {
    const browser = await engine.launch({ headless: true, ...launch });
    try {
      const context = await browser.newContext({ ...device, serviceWorkers: 'block' });
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.pathname.endsWith('site-settings.json')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ siteEffect: 'none', celebration: { enabled: true, text: 'Pìlli, trenta secondi di magia!', duration: 30 } }) });
        return url.origin === new URL(base).origin ? route.continue() : route.abort();
      });
      await context.addInitScript(() => {
        if (top !== window) return;
        const original = window.fetch.bind(window);
        window.fetch = (input, options) => new URL(input instanceof Request ? input.url : input, location.href).origin === location.origin ? original(input, options) : Promise.resolve(new Response('{}'));
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
      });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('crash', () => errors.push('Tab crashed'));
      await page.goto(base);
      await page.locator('.photo-celebration-stage').evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
      const root = page.locator('[data-photo-celebration]');
      await expect(root).toHaveAttribute('data-state', 'running', { timeout: 15000 });
      const started = await page.evaluate(() => performance.now());
      await expect(root).toHaveAttribute('data-phase', 'tension', { timeout: 20000 });
      await page.setViewportSize({ width: 844, height: 390 });
      await expect(root).toHaveAttribute('data-phase', 'explosion', { timeout: 10000 });
      await expect(root).toHaveAttribute('data-state', 'finished', { timeout: 18000 });
      const elapsed = await page.evaluate(() => performance.now()) - started;
      assert.ok(elapsed >= 29000 && elapsed < 34000, `${name}: elapsed ${elapsed}`);
      await expect(root.locator('canvas')).toHaveCount(0);
      assert.deepEqual(errors, []);
      console.log(`${name}: real-time 30s, orientation during effect, final cleanup passed`);
      await context.close();
    } finally { await browser.close(); }
  }));
})().catch(error => { console.error(error); process.exitCode = 1; });
