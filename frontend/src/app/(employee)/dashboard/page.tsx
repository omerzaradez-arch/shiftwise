'use client'

import { useQuery } from '@tanstack/react-query'
import { format, startOfWeek, addDays, isToday } from 'date-fns'
import { he } from 'date-fns/locale'
import { shiftsApi } from '@/lib/api/shifts'
import { useAuthStore } from '@/stores/authStore'
import { ShiftCard } from '@/components/schedule/ShiftCard'
import { MobileNav } from '@/components/layout/MobileNav'

const GREETING = () => {
  const h = new Date().getHours()
  if (h < 12) return 'בוקר טוב'
  if (h < 17) return 'צהריים טובים'
  return 'ערב טוב'
}

export default function EmployeeDashboard() {
  const { user } = useAuthStore()
  const weekStart = startOfWeek(new Date(), { weekStartsOn: 0 })

  const { data: myShifts, isLoading } = useQuery({
    queryKey: ['my-shifts', weekStart.toISOString()],
    queryFn: () => shiftsApi.getMyShifts(weekStart),
  })

  const { data: nextShift } = useQuery({
    queryKey: ['next-shift'],
    queryFn: shiftsApi.getNextShift,
  })

  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i))
  const thisWeekHours = myShifts?.reduce((sum, s) => sum + (s.duration_hours ?? 0), 0) ?? 0

  return (
    <div className="min-h-screen bg-slate-50 pb-28" dir="rtl">
      {/* Hero header */}
      <div className="relative bg-slate-900 text-white px-5 pt-14 pb-8 overflow-hidden">
        <div className="absolute top-0 left-0 w-64 h-64 bg-indigo-600/20 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 right-0 w-48 h-48 bg-purple-600/20 rounded-full blur-3xl translate-x-1/4 translate-y-1/2" />

        <div className="relative z-10">
          <p className="text-slate-400 text-sm mb-0.5">{GREETING()},</p>
          <h1 className="text-2xl font-bold">{user?.name}</h1>

          {/* Stats row */}
          <div className="flex gap-4 mt-5">
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl px-4 py-3 flex-1">
              <p className="text-slate-400 text-xs mb-1">משמרות השבוע</p>
              <p className="text-2xl font-bold">{myShifts?.length ?? 0}</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl px-4 py-3 flex-1">
              <p className="text-slate-400 text-xs mb-1">שעות השבוע</p>
              <p className="text-2xl font-bold">{thisWeekHours}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Next shift banner */}
      {nextShift && (
        <div className="mx-4 -mt-4 relative z-10">
          <div className="bg-indigo-600 rounded-2xl p-4 shadow-lg shadow-indigo-900/20">
            <p className="text-indigo-200 text-xs font-medium mb-1">המשמרת הבאה שלך</p>
            <p className="text-white font-bold text-base">
              {format(new Date(nextShift.date), 'EEEE, d בMMMM', { locale: he })}
            </p>
            <p className="text-indigo-200 text-sm mt-0.5">
              {nextShift.start_time} — {nextShift.end_time}
              <span className="mx-2 opacity-50">·</span>
              {nextShift.shift_name}
            </p>
          </div>
        </div>
      )}

      <div className="px-4 py-6">
        {/* Week overview */}
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold text-slate-900">השבוע שלי</h2>
          <span className="text-xs text-slate-400">
            {format(weekStart, "d MMM", { locale: he })} — {format(addDays(weekStart, 6), "d MMM", { locale: he })}
          </span>
        </div>

        {/* Day chips */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-5 scrollbar-hide">
          {weekDays.map((day) => {
            const hasShift = myShifts?.some(s => s.date === format(day, 'yyyy-MM-dd'))
            const today = isToday(day)
            return (
              <div
                key={day.toISOString()}
                className={`flex-none flex flex-col items-center w-12 py-2.5 rounded-2xl text-xs font-medium transition-all ${
                  hasShift
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-200'
                    : today
                    ? 'bg-slate-800 text-white'
                    : 'bg-white text-slate-400 border border-slate-100'
                }`}
              >
                <span className="text-[10px] opacity-70">{format(day, 'EEE', { locale: he })}</span>
                <span className="text-base font-bold mt-0.5">{format(day, 'd')}</span>
                {hasShift && <div className="w-1 h-1 rounded-full bg-white/60 mt-1" />}
              </div>
            )
          })}
        </div>

        {/* Shifts list */}
        <h2 className="text-base font-bold text-slate-900 mb-3">משמרות השבוע</h2>
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-slate-200 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : myShifts && myShifts.length > 0 ? (
          <div className="space-y-3">
            {myShifts.map((shift) => (
              <ShiftCard key={shift.id} shift={shift} showSwapButton />
            ))}
          </div>
        ) : (
          <div className="text-center py-14 bg-white rounded-2xl border border-slate-100">
            <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
              <svg className="w-7 h-7 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="font-semibold text-slate-700">אין לך משמרות השבוע</p>
            <p className="text-sm text-slate-400 mt-1">הסידור יפורסם בקרוב</p>
          </div>
        )}
      </div>

      <MobileNav />
    </div>
  )
}
