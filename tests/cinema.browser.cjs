const { chromium, webkit, devices, expect } = require('playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4332/dediche-musicali/';

(async () => {
  fs.mkdirSync('.cache/cinema', { recursive: true });
  for (const [name, engine, device, options] of [
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
  ]) {
    const browser = await engine.launch({ headless: true, ...options });
    try {
      const context = await browser.newContext({ ...device, viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
      await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
      await context.addInitScript(() => {
        if (window.top !== window) return;
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
        localStorage.setItem('ddgpilli-pwa-installed', 'true');
        const nativeFetch = window.fetch.bind(window);
        window.fetch = (input, options) => {
          const url = new URL(input instanceof Request ? input.url : input, location.href);
          return url.origin === location.origin ? nativeFetch(input, options) : Promise.resolve(new Response('{}'));
        };
        window.__cinemaLoads = 0;
        document.addEventListener('astro:page-load', () => window.__cinemaLoads++);
      });
      const page = await context.newPage();
      const errors = [];
      page.on('pageerror', e => {
        if (!/Viewport size changed|skipTransition\(\) called/.test(e.message)) errors.push(e.message);
      });
      await page.goto(base);
      await expect(page.locator('.story-heading')).toHaveClass(/cinema-arrived/);
      await expect(page.locator('.music-hero')).toHaveAttribute('data-cinema-active', '');
      await page.waitForTimeout(1100);
      const metrics = await page.evaluate(() => {
        const box = selector => document.querySelector(selector).getBoundingClientRect();
        const dock = box('.listening-dock');
        return {
          titleBeforePhoto: box('.music-title').bottom < box('.hero-image-frame').top,
          dockHit: !!document.elementFromPoint(dock.x + dock.width / 2, dock.y + dock.height / 2)?.closest('.listening-dock'),
          lights: [...document.querySelectorAll('.cinematic-light')].map(el => {
            const b = el.getBoundingClientRect();
            return Math.max(0, Math.min(innerWidth, b.right) - Math.max(0, b.left)) * Math.max(0, Math.min(innerHeight, b.bottom) - Math.max(0, b.top));
          }),
        };
      });
      assert.ok(metrics.titleBeforePhoto, 'Title readable before photo on mobile');
      assert.ok(metrics.dockHit, 'Dock is really clickable in the viewport');
      assert.ok(metrics.lights.every(area => area > 50000), 'Both lights overlap the mobile viewport');
      const sample = () => page.locator('.hero-image').evaluate(el => getComputedStyle(el).transform);
      const photoBefore = await sample();
      await page.waitForTimeout(700);
      assert.notEqual(await sample(), photoBefore, 'Photograph moves over time');
      await page.screenshot({ path: `.cache/cinema/${name}-home.png` });
      await page.locator('[data-letter] summary').click();
      await expect(page.locator('[data-letter]')).toHaveAttribute('open', '');
      await expect(page.locator('.letter-content')).toBeVisible();
      assert.equal(await page.locator('.letter-content').evaluate(el => getComputedStyle(el).animationName), 'letter-open');
      await page.locator('[data-letter] summary').press('Enter');
      await expect(page.locator('[data-letter]')).not.toHaveAttribute('open');
      await page.locator('[data-letter] summary').press('Enter');
      await expect(page.locator('.letter-content')).toBeVisible();
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.waitForTimeout(150);
      assert.equal(await page.evaluate(() => document.getAnimations().filter(a => a.playState === 'running').length), 0, 'Runtime reduced motion stops all animations');
      await expect(page.locator('.letter-content')).toHaveCSS('opacity', '1');
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      // Native shared element transition must have matching names on the destination.
      await page.locator('.stage-extras a.text-link').click();
      await page.waitForURL('**/dediche/**');
      await page.waitForFunction(() => !document.documentElement.hasAttribute('data-astro-transition'));
      await expect(page.locator('[data-letter] summary')).toBeVisible();
      await page.locator('[data-letter] summary').click();
      await expect(page.locator('.letter-content')).toBeVisible();
      await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.waitForTimeout(150);
      assert.equal(await page.evaluate(() => document.getAnimations().filter(a => a.playState === 'running').length), 0);
      // Exercise the real Astro animation fallback without native View Transitions.
      await page.emulateMedia({ reducedMotion: 'no-preference' });
      await context.addInitScript(() => { document.startViewTransition = undefined; });
      await page.goto(base);
      await page.waitForFunction(() => window.__cinemaLoads > 0);
      const count = await page.evaluate(() => window.__cinemaLoads);
      await page.locator('[data-nav-toggle]').click();
      await page.locator('#primary-navigation').getByRole('link', { name: 'Archivio', exact: true }).click();
      await page.waitForFunction(previous => window.__cinemaLoads > previous, count);
      await page.waitForFunction(() => !document.documentElement.hasAttribute('data-astro-transition'));
      await page.locator('#search-input').fill('zzzz-no-match');
      await expect(page.locator('.dedication-card:not([hidden])')).toHaveCount(0);
      await page.locator('[data-nav-toggle]').click();
      await page.locator('#primary-navigation').getByRole('link', { name: 'Home', exact: true }).click();
      await page.waitForURL(base);
      await expect(page.locator('.story-heading')).toHaveClass(/cinema-arrived/);
      // The entrance must happen after the intro closes, not only behind it.
      const introPage = await context.newPage();
      await introPage.addInitScript(() => {
        localStorage.setItem('ddgpilli-background-audio-enabled', 'true');
        sessionStorage.removeItem('ddgpilli-audio-intro-seen');
      });
      await introPage.goto(base);
      await expect(introPage.locator('[data-audio-intro]')).toBeVisible();
      await introPage.waitForTimeout(1200);
      await introPage.locator('[data-audio-intro-skip]').click();
      await expect(introPage.locator('[data-audio-intro]')).toBeHidden();
      await expect(introPage.locator('.story-heading')).toHaveClass(/cinema-arrived/);
      assert.ok(await introPage.locator('.story-heading').evaluate(el => el.getAnimations().some(a => a.animationName === 'story-arrival' && a.playState === 'running')), 'Entrance restarts after intro');
      await introPage.emulateMedia({ reducedMotion: 'reduce' });
      await introPage.reload();
      await introPage.locator('[data-audio-intro-skip]').click();
      await introPage.waitForTimeout(150);
      assert.equal(await introPage.evaluate(() => document.getAnimations().filter(a => a.playState === 'running').length), 0, 'Cold reduced-motion load has no animations');
      await introPage.close();
      assert.deepEqual(errors, []);
      console.log(`${name}: PASS — visible light, moving photo, tappable dock, letter/keyboard, live reduced motion, detail and non-native navigation`);
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
