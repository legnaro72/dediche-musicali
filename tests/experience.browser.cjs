// Regression coverage for the music experience. External services are mocked:
// no test votes, reactions or visits ever leave this browser context.
const { chromium, webkit, devices, expect } = require('playwright/test');
const assert = require('node:assert/strict');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4331/dediche-musicali/';

function wav() {
  const data = Buffer.alloc(44 + 8000 * 2 * 5);
  data.write('RIFF'); data.writeUInt32LE(data.length - 8, 4); data.write('WAVEfmt ', 8);
  data.writeUInt32LE(16, 16); data.writeUInt16LE(1, 20); data.writeUInt16LE(1, 22);
  data.writeUInt32LE(8000, 24); data.writeUInt32LE(16000, 28);
  data.writeUInt16LE(2, 32); data.writeUInt16LE(16, 34); data.write('data', 36);
  data.writeUInt32LE(data.length - 44, 40);
  return data;
}

(async () => {
  for (const [name, engine, device, launch] of [
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
  ]) {
    if (process.env.NAV_TEST_DEVICE && process.env.NAV_TEST_DEVICE !== name) continue;
    const browser = await engine.launch({ headless: true, ...launch });
    try {
      const context = await browser.newContext({ ...device, serviceWorkers: 'block' });
      await context.route('**/*', route => {
        const url = new URL(route.request().url());
        if (url.origin === new URL(base).origin) return route.continue();
        if (url.pathname.endsWith('.mp3')) return route.fulfill({ contentType: 'audio/wav', body: wav(), headers: { 'access-control-allow-origin': '*' } });
        return route.abort();
      });
      await context.addInitScript(() => {
        if (window.top !== window) return;
        localStorage.setItem('ddgpilli-user-nome', 'Test');
        localStorage.setItem('ddgpilli-user-cognome', 'Locale');
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
        localStorage.setItem('ddgpilli-pwa-installed', 'true');
        window.__pageLoads = 0;
        document.addEventListener('astro:page-load', () => window.__pageLoads++);
        window.__writes = [];
        window.__feedback = {};
        window.__DDGPILLI_FEEDBACK_API_URL = 'http://127.0.0.1:8787';
        const nativeFetch = window.fetch.bind(window);
        window.fetch = async (input, init) => {
          const url = new URL(input instanceof Request ? input.url : input, location.href);
          if (url.origin === location.origin || url.pathname.endsWith('.mp3')) return nativeFetch(input, init);
          const payload = init?.body ? JSON.parse(init.body) : {};
          const id = payload.id || url.searchParams.get('id');
          if (init?.method === 'POST') {
            window.__writes.push({ path: url.pathname, payload });
            if (window.__failFeedback) return new Response(JSON.stringify({ ok: false, error: 'Connessione non disponibile' }), { status: 503 });
            const item = window.__feedback[id] || { reactions: {}, votes: [], thoughts: [] };
            if (url.pathname === '/save_reaction') item.reactions = { [payload.reaction || 'heart']: payload.reaction ? 1 : 0 };
            if (url.pathname === '/save_vote') {
              item.votes = [{ userId: payload.userId, userName: payload.userName, value: payload.voteValue }];
              item.voteAverage = payload.voteValue;
            }
            window.__feedback[id] = item;
            return new Response(JSON.stringify({ ok: true, ...item, feedback: item }));
          }
          return new Response(JSON.stringify({ ok: true, feedback: url.pathname.endsWith('/all') ? window.__feedback : window.__feedback[id] || {} }));
        };
        Object.defineProperty(navigator, 'share', { value: undefined, configurable: true });
      });
      const page = await context.newPage();
      page.setDefaultTimeout(15000);
      const errors = [];
      page.on('pageerror', error => {
        // Cancelling a superseded visual transition rejects its ready promise in
        // Chromium. Navigation and all controls must still pass the checks below.
        if (error.message === 'Transition was skipped. skipTransition() called') return;
        if (!error.message.includes('Viewport size changed')) errors.push(error.message);
      });
      async function nav(label) {
        const count = await page.evaluate(() => window.__pageLoads);
        const toggle = page.locator('[data-nav-toggle]');
        if (await toggle.isVisible()) await toggle.click();
        await page.locator('#primary-navigation').getByRole('link', { name: label, exact: true }).click();
        await page.waitForFunction(n => window.__pageLoads > n, count);
        await page.waitForFunction(() => !document.documentElement.hasAttribute('data-astro-transition'));
      }
      const visibleCards = () => page.locator('.dedication-card:not([hidden])');
      await page.goto(base);
      await page.waitForFunction(() => window.__pageLoads > 0);
      await expect(page.locator('.listening-dock')).toBeVisible();
      const id = await page.locator('[data-favorite]').first().getAttribute('data-favorite');
      await page.locator('.listening-dock [data-favorite]').click();
      await expect(page.locator('[data-favorite]').first()).toHaveAttribute('aria-pressed', 'true');
      await page.reload();
      await expect(page.locator('.listening-dock [data-favorite]')).toHaveAttribute('aria-pressed', 'true');
      console.log(`${name}: favorite persists across reload`);

      await page.locator('.listening-dock [data-share-url]').click();
      await expect(page.locator('[data-share-dialog]')).toBeVisible();
      assert.equal(await page.locator('[data-share-dialog] input').inputValue(), `https://legnaro72.github.io/dediche-musicali/dediche/${id}/`);
      await page.locator('[data-share-close]').click();
      await page.evaluate(() => Object.defineProperty(navigator, 'share', { configurable: true, value: async data => { window.__shared = data; } }));
      await page.locator('.listening-dock [data-share-url]').click();
      assert.ok((await page.evaluate(() => window.__shared.url)).includes(id));
      await page.evaluate(() => Object.defineProperty(navigator, 'share', { configurable: true, value: async () => { throw new DOMException('Cancelled', 'AbortError'); } }));
      await page.locator('.listening-dock [data-share-url]').click();
      await expect(page.locator('[data-share-dialog]')).toBeHidden();
      console.log(`${name}: native share and manual fallback`);

      await nav('Archivio');
      await page.locator('[data-favorites-filter]').click();
      await expect(visibleCards()).toHaveCount(1);
      await expect(visibleCards()).toHaveAttribute('data-dedication-id', id);
      await page.locator('[data-reset-filters]').first().click();
      await page.locator('#search-input').fill('zzzznessunrisultato');
      await expect(visibleCards()).toHaveCount(0);
      await expect(page.locator('#no-result')).toBeVisible();
      await expect(page.locator('[data-surprise]')).toBeDisabled();
      await nav('Home');
      await nav('Archivio');
      await page.locator('#search-input').fill('zzzznessunrisultato');
      await expect(visibleCards()).toHaveCount(0);
      await page.locator('[data-reset-filters]').first().click();
      await page.locator('#filter-artist').selectOption('Vasco Rossi');
      assert.ok(await visibleCards().count() > 0);
      for (const card of await visibleCards().all()) await expect(card).toHaveAttribute('data-artist', 'Vasco Rossi');
      await visibleCards().first().click();
      await page.waitForURL('**/dediche/**');
      await page.goBack();
      await expect(page.locator('#filter-artist')).toHaveValue('Vasco Rossi');
      await page.locator('[data-surprise]').click();
      await page.waitForURL('**/dediche/**');
      console.log(`${name}: repeated search, favorites, artist, history, surprise`);

      await nav('Home');
      await page.locator('[data-plus-vote-open]').click();
      await expect(page.locator('[data-plus-vote-modal]')).toBeVisible();
      await page.locator('[data-plus-vote-score]').fill('9');
      await page.locator('[data-plus-vote-thought]').fill('Test locale, non inviato a servizi esterni.');
      await page.locator('[data-plus-vote-submit]').click();
      await expect(page.locator('[data-plus-vote-status]')).toHaveText('Voto salvato nel dataset.').catch(async error => {
        console.error(await page.evaluate(() => ({ writes: window.__writes, score: document.querySelector('[data-plus-vote-score]').value, valid: document.querySelector('[data-plus-vote-form]').checkValidity(), body: document.querySelector('[data-plus-vote-form]').outerHTML })), errors);
        throw error;
      });
      await expect(page.locator('[data-plus-vote-modal]')).toBeHidden();
      assert.equal(await page.evaluate(() => window.__writes.filter(w => w.path === '/save_vote').length), 1);
      await page.locator('[data-reaction="heart"]').click();
      await expect(page.locator('[data-count="heart"]')).toHaveText('1');
      await expect(page.locator('[data-reaction="heart"]')).toBeEnabled();
      await page.evaluate(() => { window.__failFeedback = true; });
      await page.locator('[data-reaction="heart"]').click();
      await expect(page.locator('[data-experience-toast]')).toContainText('Reazione non salvata');
      await expect(page.locator('[data-count="heart"]')).toHaveText('1');
      await page.evaluate(() => { window.__failFeedback = false; });
      await nav('Statistiche');
      await expect(page.locator('[data-stat="totalVotes"]')).not.toHaveText('-');
      await nav('Home'); await nav('Statistiche');
      await expect(page.locator('[data-stat="totalVotes"]')).not.toHaveText('-');
      console.log(`${name}: vote saves once, reaction rollback, repeated statistics`);

      await page.goto(base + 'dediche/2026-09-01-pillirosso-massituo/');
      const downloads = [];
      page.on('download', download => downloads.push(download));
      await page.locator('.listening-dock [data-audio-play]').click();
      await page.waitForFunction(() => !document.querySelector('[data-dedication-audio]').paused);
      assert.equal(downloads.length, 0, 'Listen must not download');
      const download = page.waitForEvent('download');
      await page.locator('[data-audio-download]').click();
      await download;
      assert.equal(downloads.length, 1);
      console.log(`${name}: real audio playback; download only when requested`);

      for (const width of [320, 390, 430, 844]) {
        await page.setViewportSize({ width, height: width === 844 ? 390 : 844 });
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `No horizontal overflow at ${width}`);
      }
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await nav('Home');
      const reveal = page.locator('.collection-heading');
      await reveal.scrollIntoViewIfNeeded();
      await expect(reveal).toHaveCSS('opacity', '1');
      await page.evaluate(() => {
        const original = Storage.prototype.setItem;
        Storage.prototype.setItem = function(key, value) {
          if (key === 'ddgpilli-favorites-v1') throw new DOMException('Quota exceeded', 'QuotaExceededError');
          return original.call(this, key, value);
        };
      });
      const favorite = page.locator('[data-favorite]').first();
      const wasSaved = await favorite.getAttribute('aria-pressed');
      await favorite.click();
      await expect(favorite).toHaveAttribute('aria-pressed', String(wasSaved !== 'true'));
      await expect(page.locator('[data-experience-toast]')).toContainText('solo per questa sessione');
      assert.deepEqual(errors, []);
      console.log(`${name}: PASS — layout, reduced motion, no uncaught errors`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
