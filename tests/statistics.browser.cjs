const { chromium, webkit, devices, expect } = require('playwright/test');
const fs = require('node:fs');
const base = process.env.NAV_TEST_URL || 'http://127.0.0.1:4335/dediche-musicali/';
const dedication = JSON.parse(fs.readFileSync('data/dedications/2026-10-14-dimmi-le-vibrazioni.json'));

(async () => {
  for (const [name, engine, device, launch] of [
    ['Android', chromium, devices['Pixel 7'], { channel: 'chrome' }],
    ['iPhone', webkit, devices['iPhone 13'], {}],
  ]) {
    const browser = await engine.launch({ headless: true, ...launch });
    try {
      const context = await browser.newContext({ ...device, serviceWorkers: 'block', reducedMotion: 'reduce' });
      await context.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : route.abort());
      await context.addInitScript(({ dedication }) => {
        const original = window.fetch.bind(window);
        window.fetch = (input, options) => new URL(input instanceof Request ? input.url : input, location.href).origin === location.origin
          ? original(input, options) : Promise.resolve(new Response(JSON.stringify({ ok: true, feedback: {} })));
        localStorage.setItem('ddgpilli-plus-votes', JSON.stringify({ [dedication.id]: {
          votes: [dedication.votes[1]],
          thoughts: [dedication.thoughts[1], { userKey: 'solo-commento', userName: 'Solo Commento', text: 'Pensiero senza voto' }],
        } }));
        localStorage.setItem('ddgpilli-background-audio-enabled', 'false');
        localStorage.setItem('ddgpilli-pwa-installed', 'true');
      }, { dedication });
      const page = await context.newPage();
      await page.goto(base + 'statistiche/');
      const rows = page.locator('[data-voted-table] tr').filter({ has: page.locator('td', { hasText: /^Dimmi$/ }) });
      await expect(rows).toHaveCount(3);
      for (const vote of dedication.votes) await expect(rows.filter({ hasText: vote.userName })).toContainText(`${vote.value}/10`);
      for (const thought of dedication.thoughts) await expect(rows.filter({ hasText: thought.userName })).toContainText(thought.text);
      await expect(rows.filter({ hasText: 'Solo Commento' })).toContainText('Pensiero senza voto');
      const expected = await page.evaluate(() => {
        const data = JSON.parse(document.getElementById('stats-dedications').textContent);
        const values = data.flatMap(d => d.votes?.length ? d.votes.map(v => Number(v.value)) : Number(d.voteAverage) >= 1 ? [Number(d.voteAverage)] : []);
        return { count: values.length, average: (values.reduce((a, b) => a + b, 0) / values.length).toFixed(1), thoughts: data.reduce((sum, d) => sum + d.thoughts.length, 0) + 1 };
      });
      await expect(page.locator('[data-stat="totalVotes"]')).toHaveText(String(expected.count));
      await expect(page.locator('[data-stat="averageVote"]')).toHaveText(expected.average);
      await expect(page.locator('[data-stat="totalThoughts"]')).toHaveText(String(expected.thoughts));
      // A fresh complete server response, including removals, wins over the cache.
      await page.evaluate(({ dedication }) => window.dispatchEvent(new CustomEvent('ddgpilli:stats-updated', { detail: {
        id: dedication.id, feedback: { votes: dedication.votes, thoughts: dedication.thoughts },
      } })), { dedication });
      await expect(rows).toHaveCount(2);
      for (const thought of dedication.thoughts) await expect(rows.filter({ hasText: thought.userName })).toContainText(thought.text);
      console.log(`${name}: all users, comments without votes, totals, average and live refresh passed`);
      await context.close();
    } finally { await browser.close(); }
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
