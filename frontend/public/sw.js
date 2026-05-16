const CACHE = 'shiftwise-v1'
const OFFLINE_URL = '/offline'

// Assets to cache on install
const PRECACHE = [
  '/',
  '/dashboard',
  '/attendance',
  '/manifest.json',
  '/icon-192.png',
]

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  // API calls — network only, no cache
  if (e.request.url.includes('/api/')) {
    e.respondWith(fetch(e.request))
    return
  }

  // Pages — network first, fallback to cache
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone()
        caches.open(CACHE).then(c => c.put(e.request, clone))
        return res
      })
      .catch(() => caches.match(e.request))
  )
})

// Push notifications
self.addEventListener('push', (e) => {
  let data = {}
  try {
    data = e.data?.json() ?? {}
  } catch {
    data = { title: 'ShiftWise', body: e.data?.text() || '' }
  }
  e.waitUntil(
    self.registration.showNotification(data.title || 'ShiftWise', {
      body: data.body || '',
      icon: '/icon.svg',
      badge: '/icon.svg',
      dir: 'rtl',
      lang: 'he',
      vibrate: [200, 100, 200],
      tag: data.tag || 'shiftwise',
      renotify: true,
      data: { url: data.url || '/' },
    })
  )
})

self.addEventListener('notificationclick', (e) => {
  e.notification.close()
  e.waitUntil(clients.openWindow(e.notification.data?.url || '/'))
})
