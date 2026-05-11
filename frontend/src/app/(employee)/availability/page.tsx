'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, startOfWeek, addDays, addWeeks } from 'date-fns'
import { he } from 'date-fns/locale'
import { availabilityApi } from '@/lib/api/availability'
import { MobileNav } from '@/components/layout/MobileNav'
import { toast } from 'sonner'

const SHIFT_TYPES = [
  { id: 'morning', label: 'בוקר', time: '08:00–16:00', emoji: '🌅', color: 'border-amber-400 bg-amber-50 text-amber-700' },
  { id: 'afternoon', label: 'צהריים', time: '12:00–20:00', emoji: '☀️', color: 'border-blue-400 bg-blue-50 text-blue-700' },
  { id: 'evening', label: 'ערב', time: '16:00–00:00', emoji: '🌙', color: 'border-purple-400 bg-purple-50 text-purple-700' },
]

const DAYS_HE = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']

type Step = 1 | 2 | 3

export default function AvailabilityPage() {
  const qc = useQueryClient()
  const nextWeekStart = startOfWeek(addWeeks(new Date(), 1), { weekStartsOn: 0 })

  const [step, setStep] = useState<Step>(1)
  const [blockedDays, setBlockedDays] = useState<Set<number>>(new Set())
  const [desiredShifts, setDesiredShifts] = useState(3)
  const [preferredTypes, setPreferredTypes] = useState<Set<string>>(new Set())
  const [notes, setNotes] = useState('')

  const { data: existingSubmission } = useQuery({
    queryKey: ['availability', nextWeekStart.toISOString()],
    queryFn: () => availabilityApi.getSubmission(nextWeekStart),
  })

  const mutation = useMutation({
    mutationFn: availabilityApi.submit,
    onSuccess: () => {
      toast.success('הזמינות שלך נשמרה בהצלחה!')
      qc.invalidateQueries({ queryKey: ['availability'] })
    },
    onError: () => toast.error('שגיאה בשמירה — נסה שוב'),
  })

  const toggleDay = (dayIndex: number) => {
    setBlockedDays((prev) => {
      const next = new Set(prev)
      next.has(dayIndex) ? next.delete(dayIndex) : next.add(dayIndex)
      return next
    })
  }

  const toggleShiftType = (type: string) => {
    setPreferredTypes((prev) => {
      const next = new Set(prev)
      next.has(type) ? next.delete(type) : next.add(type)
      return next
    })
  }

  const handleSubmit = () => {
    mutation.mutate({
      week_start: format(nextWeekStart, 'yyyy-MM-dd'),
      blocked_days: Array.from(blockedDays),
      desired_shifts_count: desiredShifts,
      preferred_shift_types: Array.from(preferredTypes),
      notes,
    })
    setStep(3)
  }

  const weekDays = Array.from({ length: 7 }, (_, i) => ({
    index: i,
    date: addDays(nextWeekStart, i),
    label: DAYS_HE[i],
  }))

  const STEP_LABELS = ['ימים חסומים', 'העדפות', 'אישור']

  return (
    <div className="min-h-screen bg-slate-50 pb-28" dir="rtl">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-4 pt-12 pb-4 sticky top-0 z-10 shadow-sm">
        <h1 className="text-lg font-bold text-slate-900">שליחת זמינות</h1>
        <p className="text-xs text-slate-400 mt-0.5">
          שבוע {format(nextWeekStart, "d MMM", { locale: he })} —{' '}
          {format(addDays(nextWeekStart, 6), "d MMM yyyy", { locale: he })}
        </p>

        {/* Step progress */}
        <div className="flex items-center gap-2 mt-4">
          {STEP_LABELS.map((label, i) => {
            const s = i + 1
            const done = s < step
            const active = s === step
            return (
              <div key={s} className="flex items-center gap-2 flex-1">
                <div className="flex items-center gap-1.5">
                  <div className={`w-5 h-5 rounded-full text-xs font-bold flex items-center justify-center transition-all ${
                    done ? 'bg-indigo-600 text-white' : active ? 'bg-indigo-600 text-white ring-4 ring-indigo-100' : 'bg-slate-200 text-slate-400'
                  }`}>
                    {done ? '✓' : s}
                  </div>
                  <span className={`text-xs font-medium hidden sm:block ${active ? 'text-indigo-600' : done ? 'text-slate-500' : 'text-slate-400'}`}>
                    {label}
                  </span>
                </div>
                {i < STEP_LABELS.length - 1 && (
                  <div className={`flex-1 h-0.5 rounded-full ${done ? 'bg-indigo-600' : 'bg-slate-200'}`} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="px-4 py-6">
        {/* Step 1: Blocked days */}
        {step === 1 && (
          <div>
            <h2 className="text-lg font-bold text-slate-900 mb-1">אילו ימים אתה לא יכול?</h2>
            <p className="text-sm text-slate-500 mb-5">לחץ על הימים שאתה חסום בהם — ייצבעו באדום</p>

            <div className="grid grid-cols-4 gap-2.5">
              {weekDays.map(({ index, date, label }) => (
                <button
                  key={index}
                  onClick={() => toggleDay(index)}
                  className={`flex flex-col items-center p-3 rounded-2xl border-2 transition-all active:scale-95 ${
                    blockedDays.has(index)
                      ? 'border-red-400 bg-red-50 text-red-700 shadow-sm'
                      : 'border-slate-200 bg-white text-slate-700'
                  }`}
                >
                  <span className="text-xs font-semibold opacity-70">{label}</span>
                  <span className="text-xl font-bold mt-1">{format(date, 'd')}</span>
                  {blockedDays.has(index)
                    ? <span className="text-red-400 mt-1 text-xs">✗</span>
                    : <span className="text-slate-200 mt-1 text-xs">✓</span>
                  }
                </button>
              ))}
            </div>

            <div className="mt-6 bg-white rounded-2xl border border-slate-100 p-4 flex items-center justify-between">
              <span className="text-sm text-slate-600">
                <span className="font-bold text-slate-900">{7 - blockedDays.size}</span> ימים פנויים
              </span>
              <span className="text-sm text-slate-400">
                {blockedDays.size > 0 ? `${blockedDays.size} חסומים` : 'הכל פנוי'}
              </span>
            </div>

            <button
              onClick={() => setStep(2)}
              className="w-full bg-indigo-600 text-white font-bold py-4 rounded-2xl mt-5 transition hover:bg-indigo-700 active:bg-indigo-800 shadow-lg shadow-indigo-200"
            >
              המשך ←
            </button>
          </div>
        )}

        {/* Step 2: Preferences */}
        {step === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900 mb-1">כמה משמרות אתה רוצה?</h2>
              <p className="text-sm text-slate-500">ואיזה סוג משמרות אתה מעדיף</p>
            </div>

            {/* Shifts count */}
            <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm font-semibold text-slate-700">מספר משמרות רצוי</span>
                <span className="text-3xl font-bold text-indigo-600">{desiredShifts}</span>
              </div>
              <input
                type="range"
                min={1}
                max={6}
                value={desiredShifts}
                onChange={(e) => setDesiredShifts(Number(e.target.value))}
                className="w-full accent-indigo-600 h-2"
              />
              <div className="flex justify-between text-xs text-slate-400 mt-2">
                {[1,2,3,4,5,6].map(n => (
                  <span key={n} className={n === desiredShifts ? 'text-indigo-600 font-bold' : ''}>{n}</span>
                ))}
              </div>
            </div>

            {/* Shift type preferences */}
            <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
              <p className="text-sm font-semibold text-slate-700 mb-3">העדפת סוג משמרת</p>
              <div className="flex gap-3">
                {SHIFT_TYPES.map((type) => (
                  <button
                    key={type.id}
                    onClick={() => toggleShiftType(type.id)}
                    className={`flex-1 p-3 rounded-xl border-2 transition-all text-center ${
                      preferredTypes.has(type.id) ? type.color : 'border-slate-200 bg-slate-50'
                    }`}
                  >
                    <span className="text-xl">{type.emoji}</span>
                    <p className="text-xs font-bold mt-1 text-slate-700">{type.label}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{type.time}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Notes */}
            <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
              <label className="text-sm font-semibold text-slate-700 mb-2 block">
                הערות נוספות
                <span className="text-slate-400 font-normal mr-1">(אופציונלי)</span>
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="לדוגמה: לא יכול אחרי 22:00 ביום שלישי..."
                rows={3}
                className="w-full text-sm border border-slate-200 rounded-xl p-3 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-slate-50"
              />
            </div>

            <div className="flex gap-3 pt-1">
              <button
                onClick={() => setStep(1)}
                className="flex-none px-6 py-4 rounded-2xl border border-slate-200 text-slate-600 font-semibold bg-white"
              >
                ← חזור
              </button>
              <button
                onClick={handleSubmit}
                disabled={mutation.isPending}
                className="flex-1 bg-indigo-600 text-white font-bold py-4 rounded-2xl transition hover:bg-indigo-700 disabled:opacity-60 shadow-lg shadow-indigo-200"
              >
                {mutation.isPending ? 'שולח...' : 'שלח זמינות ✓'}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Confirmation */}
        {step === 3 && (
          <div className="text-center py-10">
            <div className="w-20 h-20 bg-emerald-100 rounded-3xl flex items-center justify-center mx-auto mb-5">
              <svg className="w-10 h-10 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">הזמינות נשלחה!</h2>
            <p className="text-slate-500 mb-1">הסידור יפורסם ביום חמישי בבוקר</p>
            <p className="text-sm text-slate-400">ניתן לעדכן עד יום רביעי בערב</p>

            <div className="mt-6 bg-white rounded-2xl border border-slate-100 p-4 text-right space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">ימים פנויים</span>
                <span className="font-bold text-slate-800">{7 - blockedDays.size}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">משמרות רצויות</span>
                <span className="font-bold text-slate-800">{desiredShifts}</span>
              </div>
              {preferredTypes.size > 0 && (
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">העדפות</span>
                  <span className="font-bold text-slate-800">
                    {Array.from(preferredTypes).map(t => SHIFT_TYPES.find(s => s.id === t)?.label).join(', ')}
                  </span>
                </div>
              )}
            </div>

            <button
              onClick={() => setStep(1)}
              className="mt-6 text-indigo-600 text-sm font-semibold border border-indigo-200 px-6 py-3 rounded-xl hover:bg-indigo-50 transition"
            >
              עדכן זמינות
            </button>
          </div>
        )}
      </div>

      <MobileNav />
    </div>
  )
}
