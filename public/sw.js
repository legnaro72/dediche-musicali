const CACHE_PREFIX = 'dediche-musicali-pwa-';

self.addEventListener('install', (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith(CACHE_PREFIX)).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', () => {
  // Cache disattivata: il service worker resta registrato per la PWA,
  // ma lascia passare tutto alla rete per evitare contenuti non aggiornati.
});
