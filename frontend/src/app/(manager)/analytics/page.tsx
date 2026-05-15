'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { startOfWeek } from 'date-fns'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, LineChart, Line, Legend,
} from 'recharts'
import { analyticsApi } from '@/lib/api/analytics'
import { ManagerNav } from '@/components/layout/ManagerNav'

const WEEKS_OPTIONS = [4, 8, 12]

export default function AnalyticsPage() {
  const [weeksBack, setWeeksBack] = useState(8)
  const currentWeek = startOfWeek(new Date(), { weekStartsOn: 0 })

  const { data: hoursData = [], isLoading: hoursLoading } = useQuery({
    queryKey: ['analytics', 'hours', weeksBack],
    queryFn: () => analyticsApi.getHoursDistribution(weeksBack),
  })

  const { data: payrollTrend = [], isLoading: trendLoading } = useQuery({
    queryKey: ['analytics', 'payroll-trend'],
    queryFn: () => analyticsApi.getPayrollTrend(6),
  })

  const { data: attendanceStats = [], isLoading: attendanceLoading } = useQuery({
    queryKey: ['analytics', 'attendance-stats'],
    queryFn: () => analyticsApi.getAttendanceStats(),
  })

  const { data: fairness = [] } = useQuery({
    queryKey: ['analytics', 'fairness', currentWeek],
    queryFn: () => analyticsApi.getFairness(currentWeek),
  })

  const totalHours = hoursData.reduce((sum: number, e: any) => sum + e.total_hours, 0)
  const avgHoursPerEmployee = hoursData.length ? Math.round(totalHours / hoursData.length) : 0
  const maxHours = Math.max(...hoursData.map((e: any) => e.total_hours), 1)
  const minHours = Math.min(...hoursData.map((e: any) => e.total_hours), 0)
  const fairnessGap = maxHours - minHours

  const thisMonthPayroll = payrollTrend.length > 0 ? payrollTrend[payrollTrend.length - 1]?.total_payroll ?? 0 : 0
  const thisMonthHours = payrollTrend.length > 0 ? payrollTrend[payrollTrend.length - 1]?.total_hours ?? 0 : 0

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden" dir="rtl">
      <ManagerNav />

      <main className="flex-1 overflow-auto pt-14 md:pt-0 pb-20 md:pb-0">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-4 md:px-6 py-4 sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900">אנליטיקס</h1>
              <p className="text-sm text-slate-500 mt-0.5">נתונים עסקיים בזמן אמת</p>
            </div>
            <div className="flex gap-1 bg-slate-100 p-1 rounded-xl">
              {WEEKS_OPTIONS.map((w) => (
                <button
                  key={w}
                  onClick={() => setWeeksBack(w)}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    weeksBack === w ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  {w}שב׳
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 md:p-6 space-y-5">

          {/* KPI cards — 2 cols mobile, 4 cols desktop */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <KpiCard title="שכר החודש" value={`₪${thisMonthPayroll.toLocaleString()}`} sub="חודש נוכחי" color="indigo" icon="💰" />
            <KpiCard title="שעות החודש" value={`${thisMonthHours}`} sub="סה״כ שעות" color="blue" icon="⏱" />
            <KpiCard
              title="פער הוגנות"
              value={`${Math.round(fairnessGap)}`}
              sub="שעות בין עובדים"
              color={fairnessGap > 30 ? 'amber' : 'green'}
              icon={fairnessGap > 30 ? '⚠️' : '✅'}
            />
            <KpiCard title="עובדים פעילים" value={`${hoursData.length}`} sub="קיבלו משמרות" color="purple" icon="👥" />
          </div>

          {/* Payroll trend — line chart */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 md:p-6">
            <h2 className="text-base font-semibold text-slate-900 mb-0.5">עלות שכר חודשית</h2>
            <p className="text-sm text-slate-400 mb-4">6 חודשים אחרונים — שכר ושעות</p>
            {trendLoading ? (
              <Spinner />
            ) : payrollTrend.length === 0 ? (
              <Empty text="אין נתוני נוכחות עדיין" />
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={payrollTrend} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94A3B8' }} />
                  <YAxis yAxisId="payroll" orientation="right" tick={{ fontSize: 11, fill: '#6366F1' }}
                    tickFormatter={(v) => `₪${(v / 1000).toFixed(0)}K`} />
                  <YAxis yAxisId="hours" orientation="left" tick={{ fontSize: 11, fill: '#3B82F6' }} />
                  <Tooltip
                    formatter={(value: any, name: string) =>
                      name === 'שכר' ? [`₪${value.toLocaleString()}`, name] : [`${value} שעות`, name]
                    }
                    contentStyle={{ borderRadius: 12, border: '1px solid #E2E8F0', fontSize: 13 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line yAxisId="hours" type="monotone" dataKey="total_hours" name="שעות"
                    stroke="#3B82F6" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                  <Line yAxisId="payroll" type="monotone" dataKey="total_payroll" name="שכר"
                    stroke="#6366F1" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Attendance stats per employee */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 md:p-6">
            <h2 className="text-base font-semibold text-slate-900 mb-0.5">נוכחות לפי עובד — החודש</h2>
            <p className="text-sm text-slate-400 mb-4">ימי עבודה, שעות וממוצע יומי</p>
            {attendanceLoading ? (
              <Spinner />
            ) : attendanceStats.length === 0 ? (
              <Empty text="אין נתוני נוכחות לחודש הנוכחי" />
            ) : (
              <div className="space-y-3">
                {(attendanceStats as any[]).map((emp: any) => {
                  const maxH = Math.max(...(attendanceStats as any[]).map((e: any) => e.total_hours), 1)
                  const pct = (emp.total_hours / maxH) * 100
                  return (
                    <div key={emp.employee_id}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-xs font-bold text-indigo-600 flex-none">
                            {emp.employee_name[0]}
                          </div>
                          <span className="text-sm font-medium text-slate-800">{emp.employee_name}</span>
                          {emp.invalid_location > 0 && (
                            <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">
                              ⚠️ {emp.invalid_location} ללא GPS
                            </span>
                          )}
                        </div>
                        <div className="text-left text-xs text-slate-500 flex gap-3">
                          <span>{emp.days} ימים</span>
                          <span className="font-semibold text-slate-800">{emp.total_hours} שע׳</span>
                          <span className="hidden md:block">{emp.avg_hours_per_day} ממוצע/יום</span>
                        </div>
                      </div>
                      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-400 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Hours distribution bar chart */}
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 md:p-6">
            <h2 className="text-base font-semibold text-slate-900 mb-0.5">חלוקת שעות — {weeksBack} שבועות</h2>
            <p className="text-sm text-slate-400 mb-4">סה״כ שעות שכל עובד עבד</p>
            {hoursLoading ? (
              <Spinner />
            ) : hoursData.length === 0 ? (
              <Empty text="אין נתוני שעות — הרץ אופטימייזר" />
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={hoursData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis dataKey="employee_name" tick={{ fontSize: 11, fill: '#94A3B8' }}
                    tickFormatter={(v) => v.split(' ')[0]} />
                  <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} />
                  <Tooltip
                    formatter={(v: any) => [`${v} שעות`, '']}
                    contentStyle={{ borderRadius: 12, border: '1px solid #E2E8F0', fontSize: 13 }}
                  />
                  <Bar dataKey="total_hours" name="שעות" fill="#6366F1" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Fairness table */}
          {fairness.length > 0 && (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 md:p-6">
              <h2 className="text-base font-semibold text-slate-900 mb-0.5">טבלת הוגנות — השבוע</h2>
              <p className="text-sm text-slate-400 mb-4">פירוט סוגי משמרות לכל עובד</p>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-100">
                      {['עובד', 'שעות', 'בוקר', 'ערב', 'סוף שבוע'].map((h) => (
                        <th key={h} className="text-right text-xs font-semibold text-slate-400 uppercase px-3 py-2">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(fairness as any[]).sort((a: any, b: any) => b.total_hours - a.total_hours).map((emp: any, i: number) => (
                      <tr key={emp.employee_id} className={i < fairness.length - 1 ? 'border-b border-slate-50' : ''}>
                        <td className="px-3 py-2.5">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-white text-xs font-bold flex-none" style={{ background: 'linear-gradient(135deg,#818cf8,#6366f1)' }}>
                              {emp.employee_name[0]}
                            </div>
                            <span className="text-sm font-medium text-slate-900">{emp.employee_name}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-sm font-semibold text-slate-900">{emp.total_hours.toFixed(1)}</td>
                        <td className="px-3 py-2.5"><ShiftBadge count={emp.morning_shifts} color="yellow" /></td>
                        <td className="px-3 py-2.5"><ShiftBadge count={emp.evening_shifts} color="purple" /></td>
                        <td className="px-3 py-2.5"><ShiftBadge count={emp.weekend_shifts} color="amber" /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  )
}

function KpiCard({ title, value, sub, color, icon }: { title: string; value: string; sub: string; color: string; icon: string }) {
  const colorMap: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700 border-blue-100',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    purple: 'bg-purple-50 text-purple-700 border-purple-100',
  }
  return (
    <div className={`rounded-2xl p-4 border shadow-sm ${colorMap[color] ?? colorMap.blue}`}>
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs font-medium opacity-70">{title}</p>
        <span className="text-lg">{icon}</span>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs opacity-60 mt-0.5">{sub}</p>
    </div>
  )
}

function ShiftBadge({ count, color }: { count: number; color: string }) {
  if (count === 0) return <span className="text-slate-300 text-sm">—</span>
  const colorMap: Record<string, string> = {
    yellow: 'bg-yellow-100 text-yellow-700',
    purple: 'bg-purple-100 text-purple-700',
    amber: 'bg-amber-100 text-amber-700',
  }
  return (
    <span className={`inline-flex items-center justify-center w-7 h-7 rounded-lg text-xs font-bold ${colorMap[color]}`}>
      {count}
    </span>
  )
}

function Spinner() {
  return (
    <div className="h-40 flex items-center justify-center">
      <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

function Empty({ text }: { text: string }) {
  return (
    <div className="h-40 flex flex-col items-center justify-center gap-2">
      <span className="text-3xl">📊</span>
      <p className="text-sm text-slate-400">{text}</p>
    </div>
  )
}
