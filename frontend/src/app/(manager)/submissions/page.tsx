'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ManagerNav } from '@/components/layout/ManagerNav'
import { apiClient } from '@/lib/api/client'

const DAY_NAMES = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']

const PREF_LABELS: Record<string, { label: string; cls: string }> = {
  בוקר:       { label: 'בוקר',      cls: 'bg-amber-100 text-amber-700' },
  ערב:        { label: 'ערב',       cls: 'bg-indigo-100 text-indigo-700' },
  'כל משמרת': { label: 'כל משמרת', cls: 'bg-emerald-100 text-emerald-700' },
  כלום:       { label: 'כלום',      cls: 'bg-red-100 text-red-500' },
}

function getLabel(pref: any): { label: string; cls: string } {
  if (!pref) return { label: 'כל משמרת', cls: 'bg-slate-100 text-slate-400' }
  if (!pref.available) return PREF_LABELS['כלום']
  const types: string[] = pref.preferred_types || []
  if (types.some((t: string) => t === 'morning' || t === 'afternoon'))
    return PREF_LABELS['בוקר']
  if (types.some((t: string) => t === 'evening' || t === 'night'))
    return PREF_LABELS['ערב']
  return PREF_LABELS['כל משמרת']
}

function nextSunday(from: Date): Date {
  const d = new Date(from)
  const dow = d.getDay()
  d.setDate(d.getDate() + ((7 - dow) % 7 || 7))
  return d
}

function formatDate(d: Date) {
  return d.toISOString().slice(0, 10)
}

function addWeeks(d: Date, n: number) {
  const r = new Date(d)
  r.setDate(r.getDate() + n * 7)
  return r
}

export default function AvailabilityManagerPage() {
  const [weekStart, setWeekStart] = useState<Date>(() => {
    const today = new Date()
    return nextSunday(today)
  })

  const weekStartStr = formatDate(weekStart)
  const weekEnd = addWeeks(weekStart, 1)
  weekEnd.setDate(weekEnd.getDate() - 1)

  const { data, isLoading } = useQuery({
    queryKey: ['availability-manager', weekStartStr],
    queryFn: () => apiClient.get(`/api/v1/availability/manager-view?week_start=${weekStartStr}`).then(r => r.data),
  })

  const employees: any[] = data?.employees ?? []
  const submitted = employees.filter(e => e.submitted).length

  // Determine which days appear in any submission
  const activeDays = Array.from(
    new Set(
      employees.flatMap(e => Object.keys(e.day_preferences || {}).map(Number))
    )
  ).sort((a, b) => a - b)
  const displayDays = activeDays.length > 0 ? activeDays : [0, 1, 2, 3, 4, 5]

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden" dir="rtl">
      <ManagerNav />

      <main className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900">זמינות עובדים</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                שבוע {weekStart.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit' })}–
                {weekEnd.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit' })}
              </p>
            </div>
            {/* Week nav */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setWeekStart(w => addWeeks(w, -1))}
                className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-500 transition"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
              <button
                onClick={() => setWeekStart(() => nextSunday(new Date()))}
                className="px-3 py-2 rounded-xl border border-slate-200 text-sm text-slate-600 hover:bg-slate-50 transition"
              >
                השבוע הבא
              </button>
              <button
                onClick={() => setWeekStart(w => addWeeks(w, 1))}
                className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-500 transition"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div className="p-6">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
              <p className="text-sm text-slate-500 mb-1">הגישו זמינות</p>
              <p className="text-3xl font-bold text-indigo-600">{submitted}<span className="text-lg text-slate-400">/{employees.length}</span></p>
            </div>
            <div className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
              <p className="text-sm text-slate-500 mb-1">טרם הגישו</p>
              <p className="text-3xl font-bold text-amber-500">{employees.length - submitted}</p>
            </div>
            <div className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
              <p className="text-sm text-slate-500 mb-1">אחוז הגשה</p>
              <p className="text-3xl font-bold text-emerald-600">
                {employees.length > 0 ? Math.round(submitted / employees.length * 100) : 0}%
              </p>
            </div>
          </div>

          {/* Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-x-auto">
            {isLoading ? (
              <div className="p-12 text-center text-slate-400">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                טוען זמינות...
              </div>
            ) : employees.length === 0 ? (
              <div className="p-12 text-center text-slate-400">אין עובדים פעילים</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    <th className="text-right text-xs font-semibold text-slate-400 uppercase px-5 py-3 sticky right-0 bg-slate-50/50">
                      עובד
                    </th>
                    {displayDays.map(d => (
                      <th key={d} className="text-center text-xs font-semibold text-slate-400 uppercase px-3 py-3 min-w-[90px]">
                        <div>{DAY_NAMES[d]}</div>
                        <div className="text-slate-300 font-normal normal-case">
                          {new Date(new Date(weekStart).setDate(weekStart.getDate() + d))
                            .toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit' })}
                        </div>
                      </th>
                    ))}
                    <th className="text-center text-xs font-semibold text-slate-400 uppercase px-3 py-3">סטטוס</th>
                  </tr>
                </thead>
                <tbody>
                  {employees.map((emp, i) => (
                    <tr
                      key={emp.employee_id}
                      className={`border-b border-slate-50 hover:bg-slate-50/70 transition-colors ${
                        i === employees.length - 1 ? 'border-0' : ''
                      }`}
                    >
                      <td className="px-5 py-3 sticky right-0 bg-white">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-bold text-sm flex-none">
                            {emp.employee_name[0]}
                          </div>
                          <span className="font-medium text-slate-800 text-sm whitespace-nowrap">{emp.employee_name}</span>
                        </div>
                      </td>
                      {displayDays.map(d => {
                        const pref = emp.day_preferences?.[String(d)]
                        const { label, cls } = getLabel(pref)
                        return (
                          <td key={d} className="px-3 py-3 text-center">
                            {emp.submitted ? (
                              <span className={`inline-block px-2 py-1 rounded-lg text-xs font-semibold ${cls}`}>
                                {label}
                              </span>
                            ) : (
                              <span className="text-slate-200 text-xs">—</span>
                            )}
                          </td>
                        )
                      })}
                      <td className="px-3 py-3 text-center">
                        {emp.submitted ? (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-emerald-50 text-emerald-600 text-xs font-semibold rounded-lg">
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                            הוגש
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-1 bg-amber-50 text-amber-600 text-xs font-semibold rounded-lg">
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            ממתין
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
