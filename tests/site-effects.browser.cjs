const { chromium } = require('playwright');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ reducedMotion: 'no-preference' });
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      return url.hostname === '127.0.0.1' && route.request().method() === 'GET'
        ? route.continue() : route.abort();
    });
    await page.goto('http://127.0.0.1:4331/dediche-musicali/', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(() => document.querySelector('#global-site-effect canvas')?.width > 0);
    assert.equal(await page.locator('[data-plus-vote]').getAttribute('hidden'), null);
    for (let i = 0; i < 3; i++) {
      await page.evaluate(() => window.dispatchEvent(new CustomEvent('ddgpilli:site-settings-updated', { detail: window.__DDGPILLI_SITE_SETTINGS })));
    }
    await page.waitForTimeout(1000);
    assert.equal(await page.locator('#global-site-effect canvas').count(), 1);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.waitForFunction(() => !document.querySelector('#global-site-effect canvas'));
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.waitForFunction(() => document.querySelector('#global-site-effect canvas')?.width > 0);
    console.log('PASS: Plus visible; particles survive refresh and reduced-motion changes.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
