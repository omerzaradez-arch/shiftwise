'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'

interface Info {
  employee_name: string
  shift_date: string
  start_time: string
  end_time: string
}

interface CheckinResult {
  ok: boolean
  distance_m?: number
  check_in_time?: string
  employee_name?: string
  message?: string
}

const API = process.env.NEXT_PUBLIC_API_URL || ''

export default function CheckinPage() {
  const params = useParams<{ token: string }>()
  const token = params?.token as string
  const [info, setInfo] = useState<Info | null>(null)
  const [loadingInfo, setLoadingInfo] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<CheckinResult | null>(null)

  useEffect(() => {
    fetch(`${API}/api/v1/public/checkin/${token}`)
      .then(async (r) => {
        if (!r.ok) {
          const e = await r.json().catch(() => ({}))
          throw new Error(e.detail || 'הקישור לא תקף')
        }
        return r.json()
      })
      .then(setInfo)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingInfo(false))
  }, [token])

  const handleCheckin = useCallback(() => {
    setError(null)
    setSubmitting(true)
    if (!navigator.geolocation) {
      setError('הדפדפן לא תומך ב-GPS')
      setSubmitting(false)
      return
    }
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const r = await fetch(`${API}/api/v1/public/checkin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              token,
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
            }),
          })
          const data = await r.json()
          if (!r.ok) {
            setError(data.detail || 'שגיאה ברישום')
          } else {
            setResult(data)
          }
        } catch (e: any) {
          setError(e.message || 'שגיאה')
        } finally {
          setSubmitting(false)
        }
      },
      (err) => {
        setError(
          err.code === 1
            ? 'יש לאשר הרשאת מיקום בדפדפן'
            : 'שגיאה בקבלת המיקום — נסה שוב'
        )
        setSubmitting(false)
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    )
  }, [token])

  if (loadingInfo) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-purple-50 flex items-center justify-center p-4" dir="rtl">
      <div className="bg-white rounded-3xl shadow-xl w-full max-w-md p-6">
        {result && result.ok ? (
          <div className="text-center py-6">
            <div className="w-20 h-20 bg-emerald-100 rounded-3xl flex items-center justify-center mx-auto mb-5">
              <svg className="w-10 h-10 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mb-2">🟢 נרשמה כניסה!</h1>
            <p className="text-slate-600 mb-1">{result.employee_name}</p>
            <p className="text-3xl font-black text-indigo-600 mt-3 font-mono">{result.check_in_time}</p>
            {result.distance_m !== undefined && (
              <p className="text-xs text-slate-400 mt-2">מרחק מהעסק: {result.distance_m} מ׳</p>
            )}
            <p className="text-sm text-slate-500 mt-6">תוכל לסגור את החלון. עבודה נעימה!</p>
          </div>
        ) : result && !result.ok ? (
          <div className="text-center py-6">
            <div className="w-20 h-20 bg-amber-100 rounded-3xl flex items-center justify-center mx-auto mb-5">
              <span className="text-4xl">⚠️</span>
            </div>
            <h1 className="text-xl font-bold text-slate-900 mb-2">מיקום לא תואם</h1>
            <p className="text-slate-600 mb-1">{result.message}</p>
            <p className="text-xs text-slate-400 mt-4">פנה למנהל אם זו טעות, או נסה שוב מהמיקום הנכון.</p>
            <button
              onClick={() => { setResult(null); setError(null) }}
              className="mt-6 px-5 py-2.5 bg-indigo-600 text-white text-sm font-bold rounded-xl hover:bg-indigo-700"
            >
              נסה שוב
            </button>
          </div>
        ) : (
          <>
            <div className="text-center mb-6">
              <div className="text-4xl mb-2">📍</div>
              <h1 className="text-xl font-bold text-slate-900">אישור הגעה למשמרת</h1>
              {info && (
                <p className="text-sm text-slate-500 mt-1">
                  היי {info.employee_name}, משמרת {info.start_time}–{info.end_time}
                </p>
              )}
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-xl p-3 mb-4">
                {error}
              </div>
            )}

            <button
              onClick={handleCheckin}
              disabled={submitting}
              className="w-full py-4 bg-indigo-600 text-white font-bold rounded-2xl hover:bg-indigo-700 transition disabled:opacity-60 shadow-lg shadow-indigo-200 text-base"
            >
              {submitting ? 'בודק מיקום...' : '🟢 אשר הגעה'}
            </button>
            <p className="text-xs text-center text-slate-400 mt-4">
              נדרשת הרשאת מיקום פעם אחת. המיקום משמש רק לאימות הגעה.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
