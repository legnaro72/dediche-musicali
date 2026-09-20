// Run against `npm run dev -- --host 127.0.0.1 --port 4331`.
// Requires Playwright (or NODE_PATH pointing to the bundled runtime).
const { chromium, webkit, devices } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4331/dediche-musicali/';

(async () => {
  for (const file of ['public/manifest.json']) {
    assert.equal(JSON.parse(fs.readFileSync(file)).orientation, 'any');
  }
  for (const [name, engine, device, launch] of [
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
  ]) {
    if (process.env.NAV_TEST_DEVICE && process.env.NAV_TEST_DEVICE !== name) continue;
    console.log(`${name}: starting browser`);
    const browser = await engine.launch({ headless: true, timeout: 30000, ...launch });
    try {
      const context = await browser.newContext({ ...device,
        ...(process.env.NAV_TEST_REDUCED_MOTION ? { reducedMotion: 'reduce' } : {}),
      });
      // Keep the test local: no analytics, external media or production writes.
      await context.route('**/*', route => {
        if (new URL(route.request().url()).origin === new URL(base).origin) return route.continue();
        return route.abort();
      });
      await context.addInitScript(() => {
        if (window.top !== window) return;
        // Mock external fetch before network/CORS handling, consistently across
        // Chromium and WebKit. Local page, script and config requests stay real.
        const fetchLocal = window.fetch.bind(window);
        window.fetch = (input, options) => {
          const url = new URL(input instanceof Request ? input.url : input, location.href);
          return url.origin === location.origin ? fetchLocal(input, options)
            : Promise.resolve(new Response('{}', { headers: { 'Content-Type': 'application/json' } }));
        };
        window.__pageLoadCount = 0;
        document.addEventListener('astro:page-load', () => { window.__pageLoadCount++; });
        localStorage.setItem('ddgpilli-user-nome', 'Test');
        localStorage.setItem('ddgpilli-user-cognome', 'Navigazione');
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
      });
      const page = await context.newPage();
      page.setDefaultTimeout(30000);
      console.log(`${name}: checking navigation`);
      const errors = [];
      page.on('pageerror', error => {
        // Chromium can cancel the visual snapshot when a mobile viewport changes.
        // The navigation itself must still complete and pass every interaction.
        if (error.message === 'Transition was aborted because of invalid state. Viewport size changed') return;
        errors.push(error.message);
      });
      const toggle = page.locator('[data-nav-toggle]');
      const menu = page.locator('#primary-navigation');
      async function state(open) {
        await page.waitForFunction(() => !document.documentElement.hasAttribute('data-astro-transition'));
        await page.waitForFunction(expected => {
          const button = document.querySelector('[data-nav-toggle]');
          const list = document.getElementById('primary-navigation');
          return button?.getAttribute('aria-expanded') === String(expected)
            && list?.classList.contains('is-open') === expected
            && (list.getBoundingClientRect().height > 0 && getComputedStyle(list).visibility !== 'hidden') === expected;
        }, open);
        assert.equal(await menu.isVisible(), open);
      }
      async function exercise() {
        console.log(`${name}: ${new URL(page.url()).pathname}`);
        await toggle.tap(); await state(true);
        await toggle.tap(); await state(false);
        await toggle.tap(); await state(true);
        await page.keyboard.press('Escape'); await state(false);
        await toggle.focus(); await page.keyboard.press('Enter'); await state(true);
        await page.keyboard.press('Space'); await state(false);
        await toggle.tap(); await state(true);
        await page.touchscreen.tap(5, page.viewportSize().height - 25);
        await state(false);
      }
      async function navigate(action) {
        const previous = await page.evaluate(() => window.__pageLoadCount);
        await action();
        await page.waitForFunction(count => window.__pageLoadCount > count, previous);
        await state(false);
      }
      await page.goto(base);
      await page.waitForFunction(() => window.__pageLoadCount > 0);
      await exercise();
      await page.evaluate(() => { window.__navigationTestMarker = true; });
      for (let round = 0; round < 2; round++) {
        for (const [label, path] of [['Archivio', 'archive/'], ['Statistiche', 'statistiche/'], ['Link utili', 'link-utili/'], ['Home', '']]) {
          await toggle.tap(); await state(true);
          await navigate(() => menu.getByRole('link', { name: label, exact: true }).tap());
          await page.waitForURL(base + path);
          await state(false);
          assert.equal(await page.evaluate(() => window.__navigationTestMarker), true, 'Must exercise Astro navigation, not reload');
          await exercise();
        }
      }
      await navigate(() => page.goBack()); await exercise();
      await navigate(() => page.goForward()); await exercise();
      await page.evaluate(() => window.scrollTo(0, 500));
      await page.waitForFunction(() => document.getElementById('navbar').classList.contains('scrolled'));
      await toggle.tap(); await state(true);
      await page.setViewportSize({ width: 844, height: 390 });
      await state(false);
      await toggle.tap(); await state(true);
      await navigate(() => menu.getByRole('link', { name: 'Link utili', exact: true }).tap());
      await page.waitForURL(base + 'link-utili/'); await state(false);
      await toggle.tap(); await state(true);
      await page.setViewportSize({ width: 320, height: 568 }); await state(false);
      await exercise();
      for (const path of ['archive/', 'statistiche/', 'link-utili/']) {
        await page.goto(base + path);
        await page.waitForFunction(() => window.__pageLoadCount > 0);
        await exercise();
      }
      await page.goto(base + 'archive/');
      const detail = page.locator('main a[href*="/dediche/"]').first();
      if (await detail.count()) {
        await navigate(() => detail.tap());
        await page.waitForURL('**/dediche/**');
        await exercise();
      } else {
        throw new Error('No dedication link found: detail-page coverage missing');
      }
      assert.deepEqual(errors, [], `${name}: uncaught browser errors`);
      console.log(`${name}: PASS — repeated navigation, history, direct entry, detail, touch, keyboard, scroll, landscape, 320px`);
    } finally {
      await browser.close();
    }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
