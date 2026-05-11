'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { startOfWeek, subWeeks, format } from 'date-fns'
import { he } from 'date-fns/locale'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar, Legend,
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

  const { data: fairness = [], isLoading: fairnessLoading } = useQuery({
    queryKey: ['analytics', 'fairness', currentWeek],
    queryFn: () => analyticsApi.getFairness(currentWeek),
  })

  const totalHours = hoursData.reduce((sum: number, e: any) => sum + e.total_hours, 0)
  const avgHoursPerEmployee = hoursData.length
    ? Math.round(totalHours / hoursData.length)
    : 0

  const maxHours = Math.max(...hoursData.map((e: any) => e.total_hours), 1)
  const minHours = Math.min(...hoursData.map((e: any) => e.total_hours), 0)
  const fairnessGap = maxHours - minHours

  const radarData = fairness.slice(0, 6).map((e: any) => ({
    name: e.employee_name.split(' ')[0],
    'שעות': Math.round(e.total_hours),
    'סוף שבוע': e.weekend_shifts * 8,
    'ערב': e.evening_shifts * 7,
    'בוקר': e.morning_shifts * 8,
  }))

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden" dir="rtl">
      <ManagerNav />

      <main className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900">אנליטיקס</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                נתונים של {weeksBack} שבועות אחרונים
              </p>
            </div>

            <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
              {WEEKS_OPTIONS.map((w) => (
                <button
                  key={w}
                  onClick={() => setWeeksBack(w)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    weeksBack === w
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {w} שבועות
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* KPI cards */}
          <div className="grid grid-cols-4 gap-4">
            <KpiCard
              title="סה״כ שעות"
              value={totalHours.toLocaleString()}
              sub={`${weeksBack} שבועות`}
              color="blue"
              icon="⏱"
            />
            <KpiCard
              title="ממוצע לעובד"
              value={`${avgHoursPerEmployee}`}
              sub="שעות סה״כ"
              color="indigo"
              icon="👤"
            />
            <KpiCard
              title="פער הוגנות"
              value={`${Math.round(fairnessGap)}`}
              sub="שעות בין עובדים"
              color={fairnessGap > 30 ? 'amber' : 'green'}
              icon={fairnessGap > 30 ? '⚠️' : '✅'}
            />
            <KpiCard
              title="עובדים פעילים"
              value={`${hoursData.length}`}
              sub="קיבלו משמרות"
              color="purple"
              icon="👥"
            />
          </div>

          {/* Hours distribution chart */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-1">
              חלוקת שעות בין עובדים
            </h2>
            <p className="text-sm text-gray-400 mb-5">
              סה״כ שעות שכל עובד עבד ב-{weeksBack} שבועות האחרונים
            </p>

            {hoursLoading ? (
              <div className="h-64 flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={hoursData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis
                    dataKey="employee_name"
                    tick={{ fontSize: 12, fill: '#94A3B8' }}
                    tickFormatter={(v) => v.split(' ')[0]}
                  />
                  <YAxis tick={{ fontSize: 12, fill: '#94A3B8' }} />
                  <Tooltip
                    formatter={(value: any) => [`${value} שעות`, '']}
                    labelStyle={{ fontFamily: 'inherit', textAlign: 'right' }}
                    contentStyle={{ borderRadius: 12, border: '1px solid #E2E8F0' }}
                  />
                  <Bar
                    dataKey="total_hours"
                    name="שעות עבודה"
                    fill="#3B82F6"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Weekend shifts */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-1">
                משמרות סופי שבוע
              </h2>
              <p className="text-sm text-gray-400 mb-5">פיזור סופי שבוע בין עובדים</p>

              {hoursLoading ? (
                <div className="h-48 flex items-center justify-center">
                  <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : (
                <div className="space-y-3">
                  {hoursData
                    .sort((a: any, b: any) => b.weekend_shifts - a.weekend_shifts)
                    .map((emp: any) => {
                      const maxWeekend = Math.max(...hoursData.map((e: any) => e.weekend_shifts), 1)
                      const pct = (emp.weekend_shifts / maxWeekend) * 100
                      const isHigh = emp.weekend_shifts === maxWeekend
                      return (
                        <div key={emp.employee_id}>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-sm font-medium text-gray-700">
                              {emp.employee_name.split(' ')[0]}
                            </span>
                            <span className={`text-sm font-semibold ${isHigh ? 'text-amber-600' : 'text-gray-500'}`}>
                              {emp.weekend_shifts} משמרות
                            </span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all ${isHigh ? 'bg-amber-400' : 'bg-blue-400'}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                </div>
              )}
            </div>

            {/* Radar chart */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-1">
                פרופיל עומס — השבוע
              </h2>
              <p className="text-sm text-gray-400 mb-3">
                השוואת סוגי משמרות לפי עובד
              </p>

              {fairnessLoading ? (
                <div className="h-48 flex items-center justify-center">
                  <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : radarData.length === 0 ? (
                <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
                  אין נתונים לשבוע הנוכחי
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke="#E2E8F0" />
                    <PolarAngleAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748B' }} />
                    <Radar dataKey="שעות" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.15} />
                    <Radar dataKey="סוף שבוע" stroke="#F59E0B" fill="#F59E0B" fillOpacity={0.1} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                  </RadarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Fairness table */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-1">
              טבלת הוגנות — השבוע הנוכחי
            </h2>
            <p className="text-sm text-gray-400 mb-5">
              פירוט סוגי משמרות לכל עובד
            </p>

            {fairnessLoading ? (
              <div className="h-32 flex items-center justify-center">
                <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : fairness.length === 0 ? (
              <p className="text-gray-400 text-sm text-center py-8">
                הרץ אופטימייזר לשבוע הנוכחי כדי לראות נתונים
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-100">
                      {['עובד', 'שעות', 'בוקר', 'ערב', 'סוף שבוע'].map((h) => (
                        <th key={h} className="text-right text-xs font-semibold text-gray-400 uppercase px-4 py-2.5">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {fairness
                      .sort((a: any, b: any) => b.total_hours - a.total_hours)
                      .map((emp: any, i: number) => (
                        <tr key={emp.employee_id} className={i < fairness.length - 1 ? 'border-b border-gray-50' : ''}>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-white text-xs font-bold flex-none">
                                {emp.employee_name[0]}
                              </div>
                              <span className="text-sm font-medium text-gray-900">{emp.employee_name}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm font-semibold text-gray-900">
                              {emp.total_hours.toFixed(1)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <ShiftBadge count={emp.morning_shifts} color="yellow" />
                          </td>
                          <td className="px-4 py-3">
                            <ShiftBadge count={emp.evening_shifts} color="purple" />
                          </td>
                          <td className="px-4 py-3">
                            <ShiftBadge count={emp.weekend_shifts} color="amber" />
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

function KpiCard({
  title, value, sub, color, icon,
}: { title: string; value: string; sub: string; color: string; icon: string }) {
  const colorMap: Record<string, string> = {
    blue: 'from-blue-50 to-blue-100 text-blue-700',
    indigo: 'from-indigo-50 to-indigo-100 text-indigo-700',
    amber: 'from-amber-50 to-amber-100 text-amber-700',
    green: 'from-green-50 to-green-100 text-green-700',
    purple: 'from-purple-50 to-purple-100 text-purple-700',
  }
  return (
    <div className={`bg-gradient-to-br rounded-2xl p-5 border border-transparent shadow-sm ${colorMap[color] ?? colorMap.blue}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium opacity-70 mb-2">{title}</p>
          <p className="text-3xl font-bold">{value}</p>
          <p className="text-xs opacity-60 mt-1">{sub}</p>
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  )
}

function ShiftBadge({ count, color }: { count: number; color: string }) {
  if (count === 0) return <span className="text-gray-300 text-sm">—</span>
  const colorMap: Record<string, string> = {
    yellow: 'bg-yellow-100 text-yellow-700',
    purple: 'bg-purple-100 text-purple-700',
    amber: 'bg-amber-100 text-amber-700',
    blue: 'bg-blue-100 text-blue-700',
  }
  return (
    <span className={`inline-flex items-center justify-center w-7 h-7 rounded-lg text-xs font-bold ${colorMap[color]}`}>
      {count}
    </span>
  )
}
