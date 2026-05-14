'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api/client'

interface LiveRecord {
  employee_name: string
  check_in: string
  check_out: string | null
  status: string
  running_minutes: number | null
  is_valid_location: boolean
}

interface EmpSummary {
  employee_id: string
  employee_name: string
  hourly_rate: number | null
  total_minutes: number
  total_hours_display: string
  total_pay: number | null
  days_worked: number
  records: {
    date: string
    check_in: string
    check_out: string
    hours_display: string
    total_minutes: number | null
    is_valid_location: boolean
  }[]
}

interface Report {
  month: number
  year: number
  employees: EmpSummary[]
  total_payroll: number
}

const MONTH_NAMES = ['ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר']

function formatMins(mins: number) {
  return `${Math.floor(mins / 60)}:${(mins % 60).toString().padStart(2, '0')}`
}

export default function AttendanceReportPage() {
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year] = useState(now.getFullYear())
  const [live, setLive] = useState<LiveRecord[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [tab, setTab] = useState<'live' | 'report'>('live')

  const fetchLive = async () => {
    const { data } = await apiClient.get('/api/v1/attendance/live')
    setLive(data)
  }

  const fetchReport = async () => {
    const { data } = await apiClient.get(`/api/v1/attendance/report?month=${month}&year=${year}`)
    setReport(data)
  }

  useEffect(() => { fetchLive(); fetchReport() }, [month])
  useEffect(() => {
    const t = setInterval(fetchLive, 30_000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="min-h-screen bg-slate-900 p-4 pb-24" dir="rtl">
      <div className="max-w-2xl mx-auto space-y-5">

        {/* Header */}
        <div className="pt-4">
          <h1 className="text-2xl font-black text-white">נוכחות ושכר</h1>
          <p className="text-slate-400 text-sm mt-1">מעקב כניסות/יציאות וחישוב שכר אוטומטי</p>
        </div>

        {/* Tabs */}
        <div className="flex bg-white/5 rounded-xl p-1">
          <button
            onClick={() => setTab('live')}
            className={`flex-1 py-2 rounded-lg text-sm font-semibold transition ${tab === 'live' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
          >
            🟢 עכשיו בפנים
          </button>
          <button
            onClick={() => setTab('report')}
            className={`flex-1 py-2 rounded-lg text-sm font-semibold transition ${tab === 'report' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'}`}
          >
            📊 דוח שכר
          </button>
        </div>

        {/* LIVE TAB */}
        {tab === 'live' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-slate-500">מתעדכן כל 30 שניות</p>
              <button onClick={fetchLive} className="text-xs text-indigo-400 hover:text-indigo-300">רענן</button>
            </div>

            {live.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-sm">אין נוכחות היום</div>
            ) : (
              live.map((r, i) => (
                <div key={i} className={`rounded-xl p-4 border flex items-center justify-between ${
                  r.status === 'בפנים'
                    ? 'bg-emerald-500/8 border-emerald-500/20'
                    : 'bg-white/3 border-white/8'
                }`}>
                  <div className="flex items-center gap-3">
                    <span className={`w-2.5 h-2.5 rounded-full ${r.status === 'בפנים' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
                    <div>
                      <div className="font-bold text-white text-sm">{r.employee_name}</div>
                      <div className="text-xs text-slate-500">
                        כניסה {r.check_in}{r.check_out ? ` — יציאה ${r.check_out}` : ''}
                      </div>
                    </div>
                  </div>
                  <div className="text-left">
                    <div className={`text-sm font-bold font-mono ${r.status === 'בפנים' ? 'text-emerald-400' : 'text-slate-400'}`}>
                      {r.running_minutes != null ? formatMins(r.running_minutes) : '—'}
                    </div>
                    <div className="text-xs text-slate-500">{r.status}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* REPORT TAB */}
        {tab === 'report' && report && (
          <div className="space-y-4">

            {/* Month selector */}
            <div className="flex items-center gap-2">
              <button onClick={() => setMonth(m => m > 1 ? m - 1 : 12)} className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-white flex items-center justify-center text-sm transition">›</button>
              <div className="flex-1 text-center font-bold text-white">{MONTH_NAMES[month - 1]} {year}</div>
              <button onClick={() => setMonth(m => m < 12 ? m + 1 : 1)} className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 text-white flex items-center justify-center text-sm transition">‹</button>
            </div>

            {/* Total payroll */}
            <div className="bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 rounded-2xl p-5 text-center">
              <div className="text-xs text-slate-400 mb-1">סה״כ שכר לתשלום</div>
              <div className="text-4xl font-black text-white">₪{report.total_payroll.toLocaleString()}</div>
              <div className="text-xs text-slate-500 mt-1">{report.employees.filter(e => e.total_minutes > 0).length} עובדים עבדו החודש</div>
            </div>

            {/* Per employee */}
            {report.employees.filter(e => e.total_minutes > 0 || e.days_worked > 0).map(emp => (
              <div key={emp.employee_id} className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
                <button
                  className="w-full p-4 flex items-center justify-between hover:bg-white/5 transition"
                  onClick={() => setExpanded(expanded === emp.employee_id ? null : emp.employee_id)}
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-full bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-sm font-bold text-indigo-300">
                      {emp.employee_name[0]}
                    </div>
                    <div className="text-right">
                      <div className="font-bold text-white text-sm">{emp.employee_name}</div>
                      <div className="text-xs text-slate-500">
                        {emp.days_worked} ימים · {emp.total_hours_display} שעות
                        {emp.hourly_rate ? ` · ₪${emp.hourly_rate}/שעה` : ''}
                      </div>
                    </div>
                  </div>
                  <div className="text-left">
                    <div className="font-black text-indigo-400 text-lg">
                      {emp.total_pay != null ? `₪${emp.total_pay.toLocaleString()}` : '—'}
                    </div>
                    <div className="text-xs text-slate-600 mt-0.5">{expanded === emp.employee_id ? '▲' : '▼'}</div>
                  </div>
                </button>

                {expanded === emp.employee_id && (
                  <div className="border-t border-white/8 p-4 space-y-2">
                    {emp.records.map((r, i) => (
                      <div key={i} className="flex items-center justify-between text-sm py-1.5 border-b border-white/5 last:border-0">
                        <div>
                          <span className="text-slate-300">{r.date}</span>
                          <span className="text-slate-600 mx-2">·</span>
                          <span className="text-slate-500 text-xs">{r.check_in} — {r.check_out}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          {!r.is_valid_location && <span className="text-amber-500 text-xs">⚠️</span>}
                          <span className="font-mono text-white font-semibold">{r.hours_display}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {report.employees.filter(e => e.total_minutes > 0).length === 0 && (
              <div className="text-center py-12 text-slate-500 text-sm">אין נתוני נוכחות לחודש זה</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
