const { chromium, webkit, devices, expect } = require('playwright/test');
const fs = require('node:fs');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4334/dediche-musicali/';
const detail = base + 'dediche/2026-10-05-fotografia-geolier/';
const fixture = fs.readFileSync('public/images/og-default.png');

(async () => {
  for (const [name, engine, device, options] of [
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
  ]) {
    const browser = await engine.launch({ headless: true, ...options });
    try {
      const context = await browser.newContext({ ...device, serviceWorkers: 'block', reducedMotion: 'reduce' });
      let mode = 'success';
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.origin === new URL(base).origin) return route.continue();
        if (url.hostname === 'i.ytimg.com') {
          if (mode === 'missing' || (mode === 'fallback' && url.pathname.endsWith('maxresdefault.jpg'))) return route.fulfill({ status: 404, body: '' });
          if (mode === 'tiny' && url.pathname.endsWith('maxresdefault.jpg')) return route.fulfill({ contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="90"/>' });
          return route.fulfill({ contentType: 'image/png', body: fixture });
        }
        return route.abort();
      });
      await context.addInitScript(() => {
        const original = window.fetch.bind(window);
        window.fetch = (input, options) => new URL(input instanceof Request ? input.url : input, location.href).origin === location.origin
          ? original(input, options) : Promise.resolve(new Response('{}'));
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
        localStorage.setItem('ddgpilli-pwa-installed', 'true');
      });
      const page = await context.newPage();
      for (const scenario of ['success', 'fallback', 'tiny', 'missing']) {
        mode = scenario;
        await page.goto(detail);
        const poster = page.locator('[data-video-poster]').first();
        await poster.scrollIntoViewIfNeeded();
        const expected = scenario === 'success' ? /qrwqvaX6iRw\/maxresdefault.jpg$/
          : scenario === 'missing' ? /images\/og-default.png/ : /qrwqvaX6iRw\/hqdefault.jpg$/;
        await expect(poster).toHaveAttribute('src', expected);
        await expect.poll(() => poster.evaluate(img => img.complete && img.naturalWidth > 120)).toBe(true);
        await page.locator('[data-video-loader]').first().click();
        await expect(page.locator('iframe.video-player')).toHaveAttribute('src', /youtube.com\/embed\/qrwqvaX6iRw/);
      }
      mode = 'fallback';
      await page.goto(base + 'archive/');
      await page.locator('a[href="/dediche-musicali/dediche/2026-10-05-fotografia-geolier/"]').first().click();
      const restoredPoster = page.locator('[data-video-poster]').first();
      await restoredPoster.scrollIntoViewIfNeeded();
      await expect(restoredPoster).toHaveAttribute('src', /qrwqvaX6iRw\/hqdefault.jpg$/);
      await expect.poll(() => restoredPoster.evaluate(img => img.complete && img.naturalWidth > 120)).toBe(true);
      await page.locator('[data-video-loader]').first().click();
      await expect(page.locator('iframe.video-player')).toHaveAttribute('src', /youtube.com\/embed\/qrwqvaX6iRw/);
      console.log(`${name}: thumbnail, 404, tiny placeholder, local fallback, Play and archive navigation passed`);
      await context.close();
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
