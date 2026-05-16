import { apiClient } from './client'

export const notificationsApi = {
  getPublicKey: async (): Promise<string> => {
    const { data } = await apiClient.get('/api/v1/notifications/vapid-public-key')
    return data.key || ''
  },

  subscribe: async (sub: PushSubscription): Promise<void> => {
    const json = sub.toJSON()
    await apiClient.post('/api/v1/notifications/subscribe', {
      endpoint: json.endpoint,
      p256dh: json.keys?.p256dh,
      auth: json.keys?.auth,
    })
  },

  unsubscribe: async (endpoint: string): Promise<void> => {
    await apiClient.post('/api/v1/notifications/unsubscribe', { endpoint })
  },

  test: async (): Promise<{ sent: number }> => {
    const { data } = await apiClient.post('/api/v1/notifications/test')
    return data
  },
}

// Convert base64 to Uint8Array (required by Push API)
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(base64)
  const arr = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return arr
}

export async function enablePushNotifications(): Promise<{ ok: boolean; reason?: string }> {
  if (!('serviceWorker' in navigator)) return { ok: false, reason: 'Service Worker לא נתמך בדפדפן' }
  if (!('PushManager' in window)) return { ok: false, reason: 'Push לא נתמך בדפדפן' }

  // Request permission
  const perm = await Notification.requestPermission()
  if (perm !== 'granted') return { ok: false, reason: 'הרשאה נדחתה' }

  // Get public key from server
  const publicKey = await notificationsApi.getPublicKey()
  if (!publicKey) return { ok: false, reason: 'מפתח VAPID לא הוגדר בשרת' }

  // Wait for SW
  const reg = await navigator.serviceWorker.ready

  // Check existing subscription
  let sub = await reg.pushManager.getSubscription()
  if (!sub) {
    sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
    })
  }

  // Send to backend
  await notificationsApi.subscribe(sub)
  return { ok: true }
}

export async function disablePushNotifications(): Promise<void> {
  if (!('serviceWorker' in navigator)) return
  const reg = await navigator.serviceWorker.ready
  const sub = await reg.pushManager.getSubscription()
  if (sub) {
    await notificationsApi.unsubscribe(sub.endpoint)
    await sub.unsubscribe()
  }
}

export async function isPushEnabled(): Promise<boolean> {
  if (!('serviceWorker' in navigator)) return false
  if (Notification.permission !== 'granted') return false
  try {
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    return !!sub
  } catch {
    return false
  }
}
