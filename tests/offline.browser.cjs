// Run against the production preview (not Astro dev).
const { chromium, webkit, devices, expect } = require('playwright/test');
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve('dist');
(async () => {
  for (const [name, engine, device, options] of [
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
  ]) {
  let originStopped = false;
  const server = http.createServer((request, response) => {
    if (originStopped) { request.socket.destroy(); return; }
    const relative = decodeURIComponent(new URL(request.url, 'http://localhost').pathname).replace(/^\/dediche-musicali\//, '');
    let filename = path.resolve(root, relative || '.');
    if (filename !== root && !filename.startsWith(root + path.sep)) { response.writeHead(403).end(); return; }
    try {
      if (fs.statSync(filename).isDirectory()) filename = path.join(filename, 'index.html');
      const type = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.webp': 'image/webp', '.png': 'image/png' }[path.extname(filename)] || 'application/octet-stream';
      response.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store', Vary: 'Origin' });
      fs.createReadStream(filename).pipe(response);
    } catch { response.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}/dediche-musicali/`;
  const browser = await engine.launch({ ...options, headless: true });
  try {
    const context = await browser.newContext(device);
    await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
    await context.addInitScript(() => {
      if (window.top !== window) return;
      localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
      localStorage.setItem('ddgpilli-pwa-installed', 'true');
    });
    const page = await context.newPage();
    page.on('pageerror', error => console.error('PAGE ERROR', error.message));
    page.on('requestfailed', request => {
      if (request.url().includes('/_astro/')) console.error('ASSET FAILED', request.url());
    });
    async function warmed() {
      await page.waitForFunction(async () => {
        const urls = [location.href, ...performance.getEntriesByType('resource').map(entry => entry.name).filter(url => url.includes('/_astro/'))];
        return (await Promise.all(urls.map(url => caches.match(url)))).every(Boolean);
      });
    }
    await page.goto(base);
    await page.evaluate(() => navigator.serviceWorker.ready);
    await page.waitForFunction(async () => {
      const names = await caches.keys();
      const cache = await caches.open(names.find(name => name.endsWith('v2')));
      const keys = await cache.keys();
      return Boolean(await cache.match(location.href)) && keys.some(key => key.url.endsWith('.css')) && keys.some(key => key.url.includes('/_astro/') && key.url.endsWith('.js'));
    });
    const title = await page.title();
    await warmed();
    await page.goto(base + 'archive/');
    await page.waitForFunction(async () => !!await caches.match(location.href));
    await warmed();
    // WebKit's offline emulator rejects even literal SW responses (#42775).
    // Dropping origin connections exercises real cache fallback on that engine.
    if (name === 'iPhone') originStopped = true;
    else await context.setOffline(true);
    await page.goto(base);
    await expect(page).toHaveTitle(title);
    if (name === 'Android') await expect(page.locator('[data-offline-notice]')).toBeVisible();
    await expect(page.locator('.music-title')).toBeVisible();
    await page.goto(base + 'archive/');
    await expect(page.locator('#search-input')).toBeVisible();
    await page.locator('#search-input').fill('zzzznessunrisultato');
    await expect(page.locator('#no-result')).toBeVisible();
    await page.goto(base + 'dediche/2026-09-01-pillirosso-massituo/');
    await expect(page).toHaveTitle('Sei offline · DDGPilli');
    originStopped = false;
    if (name === 'Android') await context.setOffline(false);
    await page.evaluate(async home => {
      const cache = await caches.open('dediche-musicali-pwa-v2');
      await cache.put(home, new Response('<title>STALE CACHE</title>', { headers: { 'Content-Type': 'text/html' } }));
    }, base);
    await page.goto(base);
    await expect(page).toHaveTitle(title);
    const keys = await page.evaluate(async () => (await (await caches.open('dediche-musicali-pwa-v2')).keys()).map(key => key.url));
    assert.ok(keys.every(url => new URL(url).origin === new URL(base).origin));
    assert.ok(keys.every(url => !/feedback|site-settings|pwa-config|\.mp3/.test(url)));
    console.log(`${name}: PASS — visited pages offline, functional offline search, unvisited fallback, network freshness, no feedback/config/audio cached`);
  } finally { await browser.close(); await new Promise(resolve => server.close(resolve)); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
