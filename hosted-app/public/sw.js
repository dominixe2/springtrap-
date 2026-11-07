/* Micro Helper offline shell. API responses and personal data are never cached here. */
const CACHE_NAME = 'micro-helper-pwa-v3';
const APP_SHELL = ['/', '/manifest.webmanifest', '/icon.svg'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches
      .keys()
      .then(keys =>
        Promise.all(
          keys
            .filter(
              key => key.startsWith('micro-helper-pwa-') && key !== CACHE_NAME
            )
            .map(key => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  // Never cache API/auth responses or private account data.
  if (
    request.method !== 'GET' ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/v1/') ||
    url.pathname.startsWith('/docs') ||
    url.pathname.startsWith('/openapi')
  )
    return;
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok)
            caches
              .open(CACHE_NAME)
              .then(cache => cache.put('/', response.clone()));
          return response;
        })
        .catch(
          async () => (await caches.match(request)) || (await caches.match('/'))
        )
    );
    return;
  }
  const isAppAsset =
    ['script', 'style', 'image', 'font'].includes(request.destination) ||
    url.pathname.startsWith('/assets/') ||
    url.pathname === '/manifest.webmanifest' ||
    url.pathname === '/icon.svg' ||
    url.pathname.startsWith('/static/');

  if (isAppAsset) {
    event.respondWith(
      caches.match(request).then(async cached => {
        const network = fetch(request)
          .then(response => {
            if (response.ok && response.type === 'basic') {
              const copy = response.clone();
              void caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
            }
            return response;
          })
          .catch(() => cached || Response.error());

        return cached || network;
      })
    );
  }
});
