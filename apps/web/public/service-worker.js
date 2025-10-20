const CACHE_NAME = 'prep-cache-v1';
const URLS_TO_CACHE = ['/'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(URLS_TO_CACHE))
  );
});

self.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        try {
          return await fetch(event.request);
        } catch (error) {
          const cache = await caches.open(CACHE_NAME);
          const cachedShell = await cache.match('/');
          if (cachedShell) {
            return cachedShell;
          }

          throw error;
        }
      })()
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then(response => response || fetch(event.request))
  );
});

self.addEventListener('push', event => {
  const data = event.data?.text() || 'Notification';
  event.waitUntil(
    self.registration.showNotification('Prep', {
      body: data,
    })
  );
});
