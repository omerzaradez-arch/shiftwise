'use client'

import { useState, useEffect, useRef } from 'react'
import { apiClient } from '@/lib/api/client'
import { toast } from 'sonner'

interface TodayStatus {
  status: 'not_checked_in' | 'checked_in' | 'checked_out'
  check_in?: string
  check_out?: string
  total_minutes?: number
  running_minutes?: number
  is_valid_location?: boolean
}

interface HistoryRecord {
  date: string
  check_in: string
  check_out: string | null
  hours_display: string
  total_minutes: number | null
  is_valid_location: boolean
}

interface History {
  month: number
  year: number
  total_minutes: number
  total_hours_display: string
  total_pay: number | null
  hourly_rate: number | null
  records: HistoryRecord[]
}

function formatTime(isoString: string) {
  return new Date(isoString).toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })
}

function formatMinutes(mins: number) {
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return `${h}:${m.toString().padStart(2, '0')}`
}

const MONTH_NAMES = ['ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר']
const DAY_NAMES = ['א׳','ב׳','ג׳','ד׳','ה׳','ו׳','ש׳']

export default function AttendancePage() {
  const [today, setToday] = useState<TodayStatus | null>(null)
  const [history, setHistory] = useState<History | null>(null)
  const [loading, setLoading] = useState(false)
  const [runningMins, setRunningMins] = useState(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const now = new Date()

  const fetchToday = async () => {
    const { data } = await apiClient.get('/api/v1/attendance/today')
    setToday(data)
    if (data.status === 'checked_in') {
      setRunningMins(data.running_minutes || 0)
    }
  }

  const fetchHistory = async () => {
    const { data } = await apiClient.get('/api/v1/attendance/my-history')
    setHistory(data)
  }

  useEffect(() => {
    fetchToday()
    fetchHistory()
  }, [])

  // Live timer
  useEffect(() => {
    if (today?.status === 'checked_in') {
      timerRef.current = setInterval(() => setRunningMins(m => m + 1), 60_000)
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [today?.status])

  const getLocation = (): Promise<{ lat: number; lng: number } | null> => {
    return new Promise(resolve => {
      if (!navigator.geolocation) { resolve(null); return }
      navigator.geolocation.getCurrentPosition(
        pos => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => resolve(null),
        { timeout: 8000 }
      )
    })
  }

  const handleCheckIn = async () => {
    setLoading(true)
    try {
      const loc = await getLocation()
      const { data } = await apiClient.post('/api/v1/attendance/checkin', {
        lat: loc?.lat ?? null,
        lng: loc?.lng ?? null,
      })
      toast.success(data.message)
      await fetchToday()
      await fetchHistory()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'שגיאה בכניסה')
    } finally {
      setLoading(false)
    }
  }

  const handleCheckOut = async () => {
    setLoading(true)
    try {
      const loc = await getLocation()
      const { data } = await apiClient.post('/api/v1/attendance/checkout', {
        lat: loc?.lat ?? null,
        lng: loc?.lng ?? null,
      })
      toast.success(data.message)
      if (timerRef.current) clearInterval(timerRef.current)
      await fetchToday()
      await fetchHistory()
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'שגיאה ביציאה')
    } finally {
      setLoading(false)
    }
  }

  const status = today?.status ?? 'not_checked_in'

  return (
    <div className="min-h-screen bg-slate-900 p-4 pb-24" dir="rtl">
      <div className="max-w-md mx-auto space-y-5">

        {/* Header */}
        <div className="pt-4">
          <h1 className="text-2xl font-black text-white">נוכחות</h1>
          <p className="text-slate-400 text-sm mt-1">
            {now.toLocaleDateString('he-IL', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
        </div>

        {/* Main Check-in Card */}
        <div className={`rounded-2xl p-6 border text-center transition-all ${
          status === 'checked_in'
            ? 'bg-emerald-500/10 border-emerald-500/30'
            : status === 'checked_out'
            ? 'bg-slate-700/30 border-white/10'
            : 'bg-white/5 border-white/10'
        }`}>

          {/* Status indicator */}
          <div className="flex items-center justify-center gap-2 mb-4">
            <span className={`w-2.5 h-2.5 rounded-full ${
              status === 'checked_in' ? 'bg-emerald-400 animate-pulse' :
              status === 'checked_out' ? 'bg-slate-500' : 'bg-slate-600'
            }`} />
            <span className={`text-sm font-semibold ${
              status === 'checked_in' ? 'text-emerald-400' :
              status === 'checked_out' ? 'text-slate-400' : 'text-slate-500'
            }`}>
              {status === 'checked_in' ? 'בפנים' : status === 'checked_out' ? 'היום הסתיים' : 'לא נכנסת'}
            </span>
          </div>

          {/* Running timer / summary */}
          {status === 'checked_in' && (
            <div className="mb-6">
              <div className="text-5xl font-black text-white mb-1 font-mono">
                {formatMinutes(runningMins)}
              </div>
              <div className="text-slate-400 text-sm">
                כניסה בשעה {today?.check_in ? formatTime(today.check_in) : '—'}
              </div>
              {today?.is_valid_location === false && (
                <div className="mt-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-1.5 inline-block">
                  ⚠️ מיקום לא אומת
                </div>
              )}
            </div>
          )}

          {status === 'checked_out' && today && (
            <div className="mb-6 space-y-2">
              <div className="text-4xl font-black text-white font-mono">
                {formatMinutes(today.total_minutes || 0)}
              </div>
              <div className="text-slate-400 text-sm">
                {today.check_in ? formatTime(today.check_in) : '—'} — {today.check_out ? formatTime(today.check_out) : '—'}
              </div>
            </div>
          )}

          {status === 'not_checked_in' && (
            <div className="mb-6">
              <div className="text-5xl font-black text-slate-700 font-mono mb-1">00:00</div>
              <div className="text-slate-500 text-sm">לחץ כניסה להתחיל</div>
            </div>
          )}

          {/* Button */}
          {status !== 'checked_out' && (
            <button
              onClick={status === 'checked_in' ? handleCheckOut : handleCheckIn}
              disabled={loading}
              className={`w-full py-4 rounded-xl font-black text-lg transition-all disabled:opacity-60 ${
                status === 'checked_in'
                  ? 'bg-red-500 hover:bg-red-400 text-white shadow-lg shadow-red-900/30'
                  : 'bg-emerald-500 hover:bg-emerald-400 text-white shadow-lg shadow-emerald-900/30'
              }`}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  רגע...
                </span>
              ) : status === 'checked_in' ? '🔴 יציאה מהעבודה' : '🟢 כניסה לעבודה'}
            </button>
          )}

          {status === 'checked_out' && (
            <div className="text-emerald-400 font-semibold text-sm">
              ✅ יום עבודה הושלם
            </div>
          )}
        </div>

        {/* Monthly summary */}
        {history && (
          <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-white text-sm">
                {MONTH_NAMES[history.month - 1]} {history.year}
              </h2>
              <span className="text-xs text-slate-500">{history.records.length} ימים</span>
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-white/5 rounded-xl p-3 text-center">
                <div className="text-2xl font-black text-white">{history.total_hours_display}</div>
                <div className="text-xs text-slate-500 mt-1">סה״כ שעות</div>
              </div>
              <div className="bg-white/5 rounded-xl p-3 text-center">
                <div className="text-2xl font-black text-indigo-400">
                  {history.total_pay != null ? `₪${history.total_pay.toLocaleString()}` : '—'}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {history.hourly_rate ? `₪${history.hourly_rate}/שעה` : 'שכר שעתי לא הוגדר'}
                </div>
              </div>
            </div>

            {/* Records list */}
            <div className="space-y-2">
              {history.records.slice(0, 10).map((r, i) => {
                const d = new Date(r.date)
                return (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-white/5 rounded-lg flex items-center justify-center text-xs font-bold text-slate-400">
                        {DAY_NAMES[d.getDay()]}
                      </div>
                      <div>
                        <div className="text-sm text-white font-medium">
                          {d.toLocaleDateString('he-IL', { day: 'numeric', month: 'numeric' })}
                        </div>
                        <div className="text-xs text-slate-500">
                          {r.check_in} — {r.check_out || 'פתוח'}
                        </div>
                      </div>
                    </div>
                    <div className="text-left">
                      <div className="text-sm font-bold text-white font-mono">{r.hours_display}</div>
                      {!r.is_valid_location && (
                        <div className="text-xs text-amber-500">⚠️ מיקום</div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
