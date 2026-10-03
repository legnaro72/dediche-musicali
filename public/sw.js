// Cache only public pages/assets. Online pages always use the network first.
const CACHE_PREFIX = 'dediche-musicali-pwa-';
const CACHE = `${CACHE_PREFIX}v2`;
const ROOT = new URL(self.registration.scope);
const OFFLINE = new URL('offline.html', ROOT).href;
const LIMIT = 120;
function cacheable(url) {
  if (url.origin !== ROOT.origin || !url.pathname.startsWith(ROOT.pathname)) return false;
  const path = url.pathname.slice(ROOT.pathname.length);
  return path === '' || /^(archive|dediche|statistiche|link-utili)(\/|$)/.test(path)
    || /^(?:_astro\/|icons\/|fonts\/|images\/dedications\/)/.test(path)
    || path === 'manifest.json' || path === 'offline.html';
}
async function store(request, response) {
  if (!response.ok || response.type === 'opaque') return;
  const copy = response.clone();
  const cache = await caches.open(CACHE);
  await cache.put(request, copy);
  const keys = await cache.keys();
  const removable = keys.filter(key => key.url !== OFFLINE);
  for (const key of removable.slice(0, Math.max(0, keys.length - LIMIT))) await cache.delete(key);
}
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.add(OFFLINE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith(CACHE_PREFIX) && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET' || request.headers.has('range') || !cacheable(new URL(request.url))) return;
  event.respondWith((async () => {
    if (new URL(request.url).pathname.includes('/_astro/')) {
      // These allowlisted assets are public and invariant across Origin headers.
      // Prewarming uses same-origin fetch; module requests may include Origin.
      const cached = await caches.match(request, { cacheName: CACHE, ignoreVary: true });
      if (cached) return cached;
    }
    try {
      const response = await fetch(request);
      if (response.ok) event.waitUntil(store(request, response).catch(() => {}));
      return response;
    } catch {
      const cached = await caches.match(request, { cacheName: CACHE, ignoreVary: true });
      if (cached) return cached;
      if (request.mode === 'navigate' || request.headers.get('accept')?.includes('text/html')) {
        return (await caches.match(OFFLINE, { cacheName: CACHE })) || Response.error();
      }
      return Response.error();
    }
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type !== 'CACHE_VISITED_PAGE' || !event.source?.url) return;
  if (new URL(event.source.url).origin !== ROOT.origin) return;
  const urls = Array.isArray(event.data.urls) ? event.data.urls.slice(0, 70) : [];
  event.waitUntil(Promise.all(urls.map(async value => {
    try {
      const url = new URL(value, ROOT);
      if (!cacheable(url)) return;
      await store(url.href, await fetch(url.href, { credentials: 'same-origin' }));
    } catch { /* Cache restrictions must never block the site. */ }
  })));
});
