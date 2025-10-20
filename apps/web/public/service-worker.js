const CACHE_NAME = 'prep-cache-v1';
const APP_SHELL_URL = '/';
const URLS_TO_CACHE = [APP_SHELL_URL];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(URLS_TO_CACHE))
  );
});

self.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        let networkError;
        try {
          const preload = await event.preloadResponse;
          if (preload) {
            return preload;
          }

          const networkResponse = await fetch(event.request);
          if (networkResponse && networkResponse.ok) {
            return networkResponse;
          }
        } catch (error) {
          networkError = error;
          // Ignore network failures and fall through to the cache lookup below.
        }

        const cache = await caches.open(CACHE_NAME);
        const cachedShell =
          (await cache.match(APP_SHELL_URL)) || (await cache.match('/index.html'));
        if (cachedShell) {
          return cachedShell;
        }

        // If the shell isn't cached, rethrow to surface the original error.
        if (networkError) {
          throw networkError;
        }

        return fetch(event.request);
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
