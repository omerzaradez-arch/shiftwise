'use client'

import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { format, startOfWeek, addWeeks, subWeeks } from 'date-fns'
import { he } from 'date-fns/locale'
import { scheduleApi } from '@/lib/api/schedule'
import { shiftTemplatesApi } from '@/lib/api/shiftTemplates'
import { WeeklyCalendar } from '@/components/schedule/WeeklyCalendar'
import { ConflictPanel } from '@/components/schedule/ConflictPanel'
import { OptimizerPanel } from '@/components/schedule/OptimizerPanel'
import { ShiftModal } from '@/components/schedule/ShiftModal'
import { ManagerNav } from '@/components/layout/ManagerNav'
import { toast } from 'sonner'
import { Schedule } from '@/types/schedule'
import Link from 'next/link'

function exportScheduleCSV(schedule: Schedule, weekStart: Date) {
  const header = 'תאריך,יום,שם עובד,תפקיד,שם משמרת,התחלה,סיום,שעות\n'
  const rows = schedule.shifts.map((s) => {
    const date = new Date(s.date)
    const dayName = format(date, 'EEEE', { locale: he })
    return `${s.date},${dayName},${s.employee_name},${s.employee_role},${s.shift_name},${s.start_time},${s.end_time},${s.duration_hours}`
  }).join('\n')

  const bom = '\uFEFF'
  const blob = new Blob([bom + header + rows], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `סידור_${format(weekStart, 'yyyy-MM-dd')}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export default function SchedulePage() {
  const qc = useQueryClient()
  const router = useRouter()
  const [currentWeek, setCurrentWeek] = useState(
    startOfWeek(new Date(), { weekStartsOn: 0 })
  )
  const [showOptimizer, setShowOptimizer] = useState(false)
  const [showConflicts, setShowConflicts] = useState(true)
  const [shiftModal, setShiftModal] = useState<
    | { mode: 'create'; defaultDate?: string }
    | { mode: 'edit'; shiftId: string }
    | null
  >(null)

  const { data: orgSettings } = useQuery({
    queryKey: ['settings'],
    queryFn: () => import('@/lib/api/client').then(m => m.apiClient.get('/api/v1/settings/').then(r => r.data)),
  })

  const { data: templates = [], isSuccess: templatesLoaded } = useQuery({
    queryKey: ['shift-templates'],
    queryFn: shiftTemplatesApi.list,
  })

  useEffect(() => {
    if (templatesLoaded && orgSettings && !orgSettings.onboarding_complete && templates.length === 0) {
      router.replace('/onboarding')
    }
  }, [templatesLoaded, orgSettings, templates.length, router])

  const { data: schedule, isLoading } = useQuery({
    queryKey: ['schedule', currentWeek.toISOString()],
    queryFn: () => scheduleApi.getWeekSchedule(currentWeek),
  })

  const { data: conflicts = [] } = useQuery({
    queryKey: ['conflicts', currentWeek.toISOString()],
    queryFn: () => scheduleApi.getConflicts(currentWeek),
    enabled: !!schedule,
  })

  const publishMutation = useMutation({
    mutationFn: () => scheduleApi.publishSchedule(schedule!.id),
    onSuccess: () => {
      toast.success('הסידור פורסם לעובדים!')
      qc.invalidateQueries({ queryKey: ['schedule'] })
    },
  })

  const handleShiftMove = useCallback(
    async (shiftId: string, newEmployeeId: string, newDate: string) => {
      try {
        await scheduleApi.moveShift(shiftId, newEmployeeId, newDate)
        qc.invalidateQueries({ queryKey: ['schedule', currentWeek.toISOString()] })
        qc.invalidateQueries({ queryKey: ['conflicts', currentWeek.toISOString()] })
        toast.success('המשמרת עודכנה')
      } catch {
        toast.error('לא ניתן לבצע שינוי זה')
      }
    },
    [currentWeek, qc]
  )

  const score = schedule?.optimizer_score ?? 0
  const coverage = schedule?.coverage_percent ?? 0
  const scoreColor = score >= 80 ? 'text-good' : score >= 60 ? 'text-warn' : 'text-bad'
  const coverageColor = coverage >= 90 ? 'text-good' : coverage >= 70 ? 'text-warn' : 'text-bad'

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden" dir="rtl">
      <ManagerNav />

      <main className="flex-1 flex flex-col overflow-hidden pt-14 md:pt-0 pb-20 md:pb-0">
        {/* Top bar */}
        <div className="bg-white border-b border-slate-200 px-5 py-3 flex items-center gap-5">
          {/* Week nav */}
          <div className="flex items-center border border-sand-200">
            <button
              onClick={() => setCurrentWeek(w => subWeeks(w, 1))}
              aria-label="שבוע קודם"
              className="w-8 h-8 flex items-center justify-center hover:bg-sand-100 transition-colors text-sand-500 hover:text-sand-800"
            >
              ›
            </button>
            <span className="mono-time text-[13px] font-medium text-sand-800 px-3 min-w-[168px] text-center border-x border-sand-200 leading-8">
              {format(currentWeek, "d MMM", { locale: he })} — {format(addWeeks(currentWeek, 1), "d MMM yyyy", { locale: he })}
            </span>
            <button
              onClick={() => setCurrentWeek(w => addWeeks(w, 1))}
              aria-label="שבוע הבא"
              className="w-8 h-8 flex items-center justify-center hover:bg-sand-100 transition-colors text-sand-500 hover:text-sand-800"
            >
              ‹
            </button>
          </div>

          {/* Readouts — the state of this week, at a glance */}
          {schedule && (
            <div className="hidden lg:flex items-stretch gap-5">
              <div>
                <p className="label-caps text-sand-500">כיסוי</p>
                <p className={`mono-time text-[17px] font-semibold leading-tight ${coverageColor}`}>
                  {coverage}<span className="text-[11px] text-sand-400">%</span>
                </p>
              </div>
              <div className="w-px bg-sand-200" />
              <div>
                <p className="label-caps text-sand-500">ציון</p>
                <p className={`mono-time text-[17px] font-semibold leading-tight ${scoreColor}`}>
                  {score}<span className="text-[11px] text-sand-400">/100</span>
                </p>
              </div>
              <div className="w-px bg-sand-200" />
              <div>
                <p className="label-caps text-sand-500">קונפליקטים</p>
                <p className="flex items-center gap-1.5 leading-tight">
                  <span className={`w-2 h-2 flex-none ${conflicts.length > 0 ? 'bg-[#9A6B12]' : 'bg-verdigris-500'}`} />
                  <span className={`mono-time text-[17px] font-semibold ${conflicts.length > 0 ? 'text-[#9A6B12]' : 'text-sand-500'}`}>
                    {conflicts.length}
                  </span>
                </p>
              </div>
              {schedule.status === 'published' && (
                <>
                  <div className="w-px bg-sand-200" />
                  <div className="flex items-center">
                    <span className="label-caps text-verdigris-700 border border-verdigris-200 bg-verdigris-50 px-2 py-1">
                      פורסם
                    </span>
                  </div>
                </>
              )}
            </div>
          )}

          <div className="flex-1" />

          {/* Actions */}
          <div className="flex items-center gap-2">
            {schedule && (
              <button
                onClick={() => exportScheduleCSV(schedule, currentWeek)}
                className="flex items-center gap-1.5 px-3 py-2 bg-white text-slate-600 text-sm font-medium rounded-xl hover:bg-slate-100 transition border border-slate-200"
                title="ייצוא ל-CSV"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                CSV
              </button>
            )}
            {conflicts.length > 0 && (
              <button
                onClick={() => setShowConflicts(v => !v)}
                className="flex items-center gap-1.5 px-3 py-2 bg-amber-50 text-amber-700 text-sm font-medium rounded-xl hover:bg-amber-100 transition border border-amber-200"
              >
                <span className="w-5 h-5 bg-amber-400 text-white rounded-full text-xs flex items-center justify-center font-bold">
                  {conflicts.length}
                </span>
                קונפליקטים
              </button>
            )}

            <button
              onClick={() => setShiftModal({ mode: 'create' })}
              className="flex items-center gap-1.5 px-3 py-2 bg-white text-slate-700 text-sm font-medium rounded-xl hover:bg-slate-100 transition border border-slate-200"
              title="הוסף משמרת ידנית"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              משמרת
            </button>

            <button
              onClick={() => setShowOptimizer(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition shadow-sm shadow-indigo-200"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              הרץ אופטימייזר
            </button>

            {schedule && (
              <button
                onClick={() => publishMutation.mutate()}
                disabled={publishMutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-xl hover:bg-emerald-700 disabled:opacity-60 transition shadow-sm shadow-emerald-200"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {publishMutation.isPending ? 'שולח...' : 'פרסם לעובדים'}
              </button>
            )}
          </div>
        </div>

        {/* Onboarding banner */}
        {templates.length === 0 && (
          <div className="mx-5 mt-4 p-4 bg-indigo-50 border border-indigo-200 rounded-xl flex items-center gap-4">
            <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center flex-none">
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#6366f1" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-indigo-800">טרם הגדרת משמרות לעסק</p>
              <p className="text-xs text-indigo-600 mt-0.5">האופטימייזר לא יוכל לייצר סידור ללא הגדרת משמרות</p>
            </div>
            <Link
              href="/onboarding"
              className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition flex-none"
            >
              הגדר עכשיו ›
            </Link>
          </div>
        )}

        {/* Calendar area */}
        <div className="flex flex-1 overflow-hidden">
          <div className="flex-1 p-4 overflow-auto">
            {isLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center text-slate-400">
                  <div className="w-10 h-10 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                  <p className="text-sm">טוען סידור...</p>
                </div>
              </div>
            ) : schedule ? (
              <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden h-full">
                <WeeklyCalendar
                  schedule={schedule}
                  weekStart={currentWeek}
                  onShiftMove={handleShiftMove}
                  onShiftClick={(shiftId) => setShiftModal({ mode: 'edit', shiftId })}
                  onEmptyClick={(date) => setShiftModal({ mode: 'create', defaultDate: date })}
                  conflicts={conflicts}
                />
              </div>
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <div style={{width:80,height:80}} className="bg-indigo-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                    <svg width="40" height="40" style={{color:'#818cf8'}} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <p className="text-lg font-semibold text-slate-700 mb-1">אין סידור לשבוע זה</p>
                  <p className="text-sm text-slate-400 mb-6">הרץ אופטימייזר אוטומטי או בנה את הסידור ידנית</p>
                  <div className="flex gap-3 justify-center">
                    <button
                      onClick={() => setShowOptimizer(true)}
                      className="px-6 py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition shadow-sm"
                    >
                      הרץ אופטימייזר
                    </button>
                    <button
                      onClick={() => setShiftModal({ mode: 'create' })}
                      className="px-6 py-3 bg-white text-slate-700 border border-slate-200 font-medium rounded-xl hover:bg-slate-50 transition"
                    >
                      + משמרת ידנית
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Conflicts sidebar */}
          {showConflicts && conflicts.length > 0 && (
            <div className="w-72 border-r border-slate-200 bg-white shadow-sm">
              <ConflictPanel
                conflicts={conflicts}
                onResolve={() => qc.invalidateQueries({ queryKey: ['conflicts'] })}
              />
            </div>
          )}
        </div>
      </main>

      {showOptimizer && (
        <OptimizerPanel
          weekStart={currentWeek}
          onClose={() => setShowOptimizer(false)}
          onComplete={() => {
            setShowOptimizer(false)
            qc.invalidateQueries({ queryKey: ['schedule'] })
            qc.invalidateQueries({ queryKey: ['conflicts'] })
          }}
        />
      )}

      {shiftModal && (
        <ShiftModal
          mode={shiftModal.mode}
          weekStart={currentWeek}
          defaultDate={shiftModal.mode === 'create' ? shiftModal.defaultDate : undefined}
          shift={
            shiftModal.mode === 'edit' && schedule
              ? (() => {
                  const s = schedule.shifts.find((x: any) => x.id === shiftModal.shiftId)
                  return s
                    ? {
                        id: s.id,
                        date: s.date,
                        start_time: s.start_time,
                        end_time: s.end_time,
                        employee_id: s.employee_id,
                        template_id: (s as any).template_id ?? null,
                        shift_name: s.shift_name,
                      }
                    : undefined
                })()
              : undefined
          }
          onClose={() => setShiftModal(null)}
        />
      )}
    </div>
  )
}
