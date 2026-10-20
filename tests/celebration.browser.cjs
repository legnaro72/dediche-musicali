const { chromium, webkit, devices, expect } = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4336/dediche-musicali/';
const out = '.cache/playwright/celebration';
const active = (text = 'Pìlli, sei magia!', duration = 10) => ({ enabled: true, text, duration });

(async () => {
  fs.mkdirSync(out, { recursive: true });
  for (const [name, engine, device, launch] of [
    ['Desktop', chromium, { viewport: { width: 1440, height: 1100 } }, { channel: 'chrome' }],
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
  ]) {
    if (process.env.NAV_TEST_DEVICE && process.env.NAV_TEST_DEVICE !== name) continue;
    const browser = await engine.launch({ headless: true, ...launch });
    let config = active();
    const context = await browser.newContext({ ...device, serviceWorkers: 'block', recordVideo: { dir: out, size: { width: 960, height: 900 } } });
    const errors = [];
    try {
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.pathname.endsWith('/config/site-settings.json')) return route.fulfill({ contentType: 'application/json', body: JSON.stringify({ siteEffect: 'none', celebration: config }) });
        return url.origin === new URL(base).origin ? route.continue() : route.abort();
      });
      await context.addInitScript(() => {
        if (window.top !== window) return;
        const original = window.fetch.bind(window);
        window.fetch = (input, options) => new URL(input instanceof Request ? input.url : input, location.href).origin === location.origin
          ? original(input, options) : Promise.resolve(new Response('{}'));
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
        localStorage.setItem('ddgpilli-pwa-installed', 'true');
        window.__phases = [];
        new MutationObserver(records => records.forEach(record => {
          if (record.attributeName === 'data-phase') window.__phases.push({ phase: record.target.dataset.phase, time: performance.now() });
        })).observe(document, { subtree: true, attributes: true, attributeFilter: ['data-phase'] });
      });
      const page = await context.newPage();
      page.on('pageerror', error => { if (!/Viewport size changed|skipTransition/.test(error.message)) errors.push(error.message); });
      page.on('crash', () => errors.push('Tab crashed'));
      const root = page.locator('[data-photo-celebration]');
      const canvas = root.locator('canvas');
      const open = async () => {
        await page.goto(base);
        await page.locator('.photo-celebration-stage').evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
      };
      await open();
      await expect(root).toHaveAttribute('data-state', 'running', { timeout: 15000 });
      await expect(canvas).toHaveCount(1);
      const before = await page.locator('.full-photo-frame').evaluate(el => getComputedStyle(el).transform);
      const spotifyBefore = await page.locator('iframe[src*="spotify"]').getAttribute('src');
      assert.ok(spotifyBefore, 'Spotify embed is present');
      for (const phase of ['entrance', 'growth', 'tension', 'explosion', 'dissolve']) {
        await expect(root).toHaveAttribute('data-phase', phase, { timeout: 15000 });
        if (name === 'Desktop') await page.screenshot({ path: `${out}/${name}-${phase}.png` });
      }
      await expect(root).toHaveAttribute('data-state', 'finished', { timeout: 10000 });
      await expect(canvas).toHaveCount(0);
      await expect(root).toBeHidden();
      const phases = await page.evaluate(() => window.__phases);
      const elapsed = phases.find(p => p.phase === 'finished').time - phases.find(p => p.phase === 'entrance').time;
      assert.ok(elapsed > 9500 && elapsed < 12500, `Default duration is 10s including fade: ${elapsed}`);
      assert.notEqual(await page.locator('.full-photo-frame').evaluate(el => getComputedStyle(el).transform), before, 'Existing frame motion is preserved');
      assert.equal(await page.locator('iframe[src*="spotify"]').getAttribute('src'), spotifyBefore, 'Spotify has not been recreated or altered');
      assert.ok(await page.locator('.photo-celebration-stage').evaluate(el => {
        const photo = el.querySelector('img'), overlay = el.querySelector('[data-photo-celebration]');
        return getComputedStyle(overlay).pointerEvents === 'none' && Math.abs(el.offsetHeight - photo.offsetHeight) < 1;
      }), 'Overlay does not change layout or intercept taps');
      await page.evaluate(c => { window.dispatchEvent(new CustomEvent('ddgpilli:site-settings-updated', { detail: { celebration: c } })); document.dispatchEvent(new Event('astro:page-load')); }, active());
      await page.waitForTimeout(200);
      await expect(canvas).toHaveCount(0); // Polling and repeated page-load events cannot replay.
      console.log(`${name}: real-time default animation, five phases, cleanup, frame and Spotify passed`);

      for (const value of [undefined, { enabled: false, text: 'Off', duration: 10 }, active(''), active('   ')]) {
        config = value;
        await open();
        await page.waitForTimeout(200);
        await expect(canvas).toHaveCount(0);
      }

      config = active("L’amore è Pìlli 🌺 <img src=x onerror=alert('x')> ".repeat(4), 3);
      await open();
      await expect(root).toHaveAttribute('data-state', 'running');
      await page.setViewportSize({ width: 844, height: 390 });
      await expect(root).toHaveAttribute('data-state', 'finished', { timeout: 6000 });
      assert.equal(await page.locator('.photo-celebration-stage img').count(), 1, 'Special text cannot insert HTML');
      await expect(canvas).toHaveCount(0);
      await page.setViewportSize(device.viewport);

      await page.emulateMedia({ reducedMotion: 'reduce' });
      config = active('Pìlli, l’amore è qui! 🌺', 3);
      await open();
      await expect(root).toHaveAttribute('data-variant', 'reduced');
      await expect(root).toHaveAttribute('data-particles', '0');
      await expect(root).toHaveAttribute('data-state', 'finished', { timeout: 6000 });
      await page.emulateMedia({ reducedMotion: 'no-preference' });

      config = active('Una pausa, poi magia', 3);
      await open();
      await expect(root).toHaveAttribute('data-state', 'running');
      await page.evaluate(() => {
        Object.defineProperty(document, 'hidden', { configurable: true, value: true });
        document.dispatchEvent(new Event('visibilitychange'));
      });
      const pausedPhase = await root.getAttribute('data-phase');
      await page.waitForTimeout(400);
      assert.equal(await root.getAttribute('data-phase'), pausedPhase, 'Hidden-tab timeline is paused');
      await page.evaluate(() => { delete document.hidden; document.dispatchEvent(new Event('visibilitychange')); });
      await expect(root).toHaveAttribute('data-state', 'finished', { timeout: 6000 });

      // Leave during the effect; return through Astro client navigation twice.
      config = active('Un nuovo ingresso', 3);
      await open();
      await expect(root).toHaveAttribute('data-state', 'running');
      const detail = await page.locator('.stage-extras a.text-link').getAttribute('href');
      for (let i = 0; i < 2; i++) {
        await page.evaluate(async href => {
          const link = document.createElement('a'); link.href = href; link.textContent = 'Test navigation';
          link.id = 'celebration-test-nav'; document.body.prepend(link); link.click();
        }, detail);
        await page.waitForURL('**/dediche/**');
        await expect(page.locator('[data-photo-celebration]')).toHaveCount(0);
        await page.evaluate(home => {
          const link = document.createElement('a'); link.href = home; link.textContent = 'Test home'; document.body.prepend(link); link.click();
        }, base);
        await page.waitForURL(base);
        await page.locator('.photo-celebration-stage').evaluate(el => el.scrollIntoView({ block: 'center', behavior: 'instant' }));
        await expect(root).toHaveAttribute('data-state', 'running');
        await expect(canvas).toHaveCount(1);
      }
      await page.evaluate(() => window.dispatchEvent(new CustomEvent('ddgpilli:site-settings-updated', { detail: { celebration: { enabled: false } } })));
      await expect(canvas).toHaveCount(0); // Disabling also cancels a running effect.

      if (name === 'Desktop') {
        config = active('Trenta secondi di magia', 30);
        await open();
        await expect(root).toHaveAttribute('data-state', 'running');
        await expect(root).toHaveAttribute('data-duration', '30');
        for (const phase of ['tension', 'explosion', 'dissolve']) await expect(root).toHaveAttribute('data-phase', phase, { timeout: 21000 });
        await expect(root).toHaveAttribute('data-state', 'finished', { timeout: 12000 });
        await page.addInitScript(() => { HTMLCanvasElement.prototype.getContext = () => null; });
        config = active('Fallback', 3);
        await open();
        await expect(root).toHaveAttribute('data-state', 'error');
        await expect(canvas).toHaveCount(0);
        await expect(page.locator('.hero-image')).toBeVisible();
        await expect(page.locator('iframe[src*="spotify"]')).toHaveCount(1);
      }
      assert.deepEqual(errors, []);
      console.log(`${name}: disabled/legacy/empty, long Unicode text, 3s/10s${name === 'Desktop' ? '/30s' : ''}, resize, reduced motion and repeated Astro navigation passed`);
      const recording = page.video();
      await page.close();
      await recording.saveAs(`${out}/${name}-session.webm`);
    } finally { await context.close(); await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
