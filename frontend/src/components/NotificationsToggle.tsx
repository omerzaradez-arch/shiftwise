'use client'

import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import {
  enablePushNotifications,
  disablePushNotifications,
  isPushEnabled,
  notificationsApi,
} from '@/lib/api/notifications'

export function NotificationsToggle() {
  const [enabled, setEnabled] = useState(false)
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    isPushEnabled().then(setEnabled)
  }, [])

  const toggle = async () => {
    setLoading(true)
    try {
      if (enabled) {
        await disablePushNotifications()
        setEnabled(false)
        toast.success('התראות בוטלו')
      } else {
        const res = await enablePushNotifications()
        if (res.ok) {
          setEnabled(true)
          toast.success('התראות הופעלו ✅')
        } else {
          toast.error(`שגיאה: ${res.reason}`)
        }
      }
    } catch (e: any) {
      toast.error('שגיאה: ' + (e?.message || ''))
    } finally {
      setLoading(false)
    }
  }

  const sendTest = async () => {
    setTesting(true)
    try {
      const res = await notificationsApi.test()
      if (res.sent > 0) {
        toast.success(`הודעת בדיקה נשלחה (${res.sent} מכשירים)`)
      } else {
        toast.error('לא נשלחה הודעה — וודא שההתראות מופעלות')
      }
    } catch (e) {
      toast.error('שגיאה בשליחת בדיקה')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            🔔 התראות Push
          </h3>
          <p className="text-sm text-slate-500 mt-0.5">
            קבל התראות לטלפון על בקשות החלפה, איחורים ועוד
          </p>
        </div>
        <button
          onClick={toggle}
          disabled={loading}
          className={`shrink-0 relative inline-flex h-6 w-11 items-center rounded-full transition ${
            enabled ? 'bg-indigo-600' : 'bg-slate-300'
          } ${loading ? 'opacity-50' : ''}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
              enabled ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {enabled && (
        <button
          onClick={sendTest}
          disabled={testing}
          className="mt-2 text-xs text-indigo-600 hover:text-indigo-800 font-medium disabled:opacity-50"
        >
          {testing ? 'שולח...' : 'שלח הודעת בדיקה'}
        </button>
      )}

      {typeof window !== 'undefined' && Notification.permission === 'denied' && (
        <p className="mt-3 text-xs text-amber-600 bg-amber-50 rounded-lg p-2">
          ⚠️ דחית הרשאה. כדי להפעיל — אפס את ההרשאה בהגדרות הדפדפן (האייקון 🔒 ליד ה-URL).
        </p>
      )}
    </div>
  )
}
