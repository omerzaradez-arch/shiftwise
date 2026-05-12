'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api/client'
import { shiftTemplatesApi, ShiftTemplateCreate } from '@/lib/api/shiftTemplates'
import { toast } from 'sonner'

const DAY_LABELS = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
const SHIFT_TYPES = [
  { value: 'morning', label: 'בוקר' },
  { value: 'afternoon', label: 'צהריים' },
  { value: 'evening', label: 'ערב' },
  { value: 'night', label: 'לילה' },
]

interface ShiftDraft extends ShiftTemplateCreate {
  _key: string
}

function makeShift(overrides: Partial<ShiftDraft> = {}): ShiftDraft {
  return {
    _key: Math.random().toString(36).slice(2),
    name: '',
    shift_type: 'morning',
    start_time: '08:00',
    end_time: '16:00',
    min_employees: 2,
    max_employees: 8,
    required_roles: { senior: 1, junior: 1 },
    days_of_week: [],
    ...overrides,
  }
}

const STEPS = ['פרטי העסק', 'הגדרת משמרות', 'סיום']

export default function OnboardingPage() {
  const router = useRouter()
  const [step, setStep] = useState(0)

  // Step 1 state
  const [orgName, setOrgName] = useState('')
  const [operatingDays, setOperatingDays] = useState<number[]>([0, 1, 2, 3, 4, 5])

  // Step 2 state
  const [shifts, setShifts] = useState<ShiftDraft[]>([
    makeShift({ name: 'משמרת בוקר', shift_type: 'morning', start_time: '07:00', end_time: '14:00' }),
    makeShift({ name: 'משמרת ערב', shift_type: 'evening', start_time: '14:00', end_time: '22:00' }),
  ])

  const saveSettingsMutation = useMutation({
    mutationFn: async () => {
      await apiClient.patch('/api/v1/settings/', {
        org_name: orgName || undefined,
        operating_days: operatingDays,
        onboarding_complete: true,
      })
    },
  })

  const saveTemplatesMutation = useMutation({
    mutationFn: async () => {
      for (const shift of shifts) {
        if (!shift.name.trim()) continue
        const { _key, ...data } = shift
        data.days_of_week = shift.days_of_week.length > 0 ? shift.days_of_week : operatingDays
        await shiftTemplatesApi.create(data)
      }
    },
  })

  async function handleStep1Next() {
    if (!orgName.trim()) {
      toast.error('נא להזין שם עסק')
      return
    }
    if (operatingDays.length === 0) {
      toast.error('נא לבחור לפחות יום פעילות אחד')
      return
    }
    // Pre-fill shifts with operating days
    setShifts((prev) =>
      prev.map((s) => ({ ...s, days_of_week: s.days_of_week.length ? s.days_of_week : operatingDays }))
    )
    setStep(1)
  }

  async function handleStep2Next() {
    const valid = shifts.filter((s) => s.name.trim())
    if (valid.length === 0) {
      toast.error('הגדר לפחות משמרת אחת')
      return
    }
    try {
      await saveSettingsMutation.mutateAsync()
      await saveTemplatesMutation.mutateAsync()
      setStep(2)
    } catch {
      toast.error('שגיאה בשמירת ההגדרות')
    }
  }

  function toggleDay(day: number, days: number[], setDays: (d: number[]) => void) {
    setDays(days.includes(day) ? days.filter((d) => d !== day) : [...days, day].sort())
  }

  function updateShift(key: string, changes: Partial<ShiftDraft>) {
    setShifts((prev) => prev.map((s) => (s._key === key ? { ...s, ...changes } : s)))
  }

  function removeShift(key: string) {
    setShifts((prev) => prev.filter((s) => s._key !== key))
  }

  const isPending = saveSettingsMutation.isPending || saveTemplatesMutation.isPending

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4" dir="rtl">
      {/* Header */}
      <div className="mb-8 text-center">
        <div className="w-12 h-12 bg-indigo-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-lg shadow-indigo-200">
          <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="white" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
        <h1 className="text-2xl font-bold text-slate-800">ברוכים הבאים ל-ShiftWise</h1>
        <p className="text-slate-500 mt-1 text-sm">הגדרת העסק תיקח כ-2 דקות</p>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className={`flex items-center gap-2 text-sm font-medium ${
              i === step ? 'text-indigo-600' : i < step ? 'text-emerald-600' : 'text-slate-400'
            }`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                i === step
                  ? 'bg-indigo-600 text-white'
                  : i < step
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-200 text-slate-500'
              }`}>
                {i < step ? '✓' : i + 1}
              </div>
              <span className="hidden sm:block">{label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`w-8 h-px ${i < step ? 'bg-emerald-400' : 'bg-slate-200'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 w-full max-w-xl">

        {/* ── STEP 1: Business Info ── */}
        {step === 0 && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-slate-800 mb-1">פרטי העסק</h2>
              <p className="text-sm text-slate-500">הזן את שם העסק ובחר באילו ימים הוא פתוח</p>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700">שם העסק</label>
              <input
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                placeholder="לדוגמה: מסעדת הים"
                className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent"
              />
            </div>

            <div className="space-y-3">
              <label className="text-sm font-medium text-slate-700">ימי פעילות</label>
              <div className="grid grid-cols-7 gap-1.5">
                {DAY_LABELS.map((label, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => toggleDay(i, operatingDays, setOperatingDays)}
                    className={`py-2 rounded-xl text-xs font-semibold transition-all ${
                      operatingDays.includes(i)
                        ? i === 6
                          ? 'bg-amber-500 text-white'
                          : 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              {operatingDays.includes(6) && (
                <p className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
                  שבת נבחרה — ודא שלעובדים יש הסכמה לעבוד בשבת
                </p>
              )}
            </div>

            <button
              onClick={handleStep1Next}
              className="w-full py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition text-sm"
            >
              המשך לשלב הבא ›
            </button>
          </div>
        )}

        {/* ── STEP 2: Shift Templates ── */}
        {step === 1 && (
          <div className="p-6 space-y-5">
            <div>
              <h2 className="text-lg font-bold text-slate-800 mb-1">הגדרת משמרות</h2>
              <p className="text-sm text-slate-500">הגדר את סוגי המשמרות בעסק שלך</p>
            </div>

            <div className="space-y-3 max-h-[420px] overflow-y-auto pl-1">
              {shifts.map((shift) => (
                <ShiftCard
                  key={shift._key}
                  shift={shift}
                  operatingDays={operatingDays}
                  onChange={(changes) => updateShift(shift._key, changes)}
                  onRemove={() => removeShift(shift._key)}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={() => setShifts((prev) => [...prev, makeShift({ days_of_week: [...operatingDays] })])}
              className="w-full py-2.5 border-2 border-dashed border-slate-200 rounded-xl text-sm font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600 transition flex items-center justify-center gap-2"
            >
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              הוסף משמרת
            </button>

            <div className="flex gap-3 pt-1">
              <button
                onClick={() => setStep(0)}
                className="flex-1 py-3 border border-slate-200 text-slate-600 font-medium rounded-xl hover:bg-slate-50 transition text-sm"
              >
                ‹ חזור
              </button>
              <button
                onClick={handleStep2Next}
                disabled={isPending}
                className="flex-1 py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition text-sm"
              >
                {isPending ? 'שומר...' : 'סיים הגדרה ›'}
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 3: Done ── */}
        {step === 2 && (
          <div className="p-8 text-center space-y-5">
            <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto">
              <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="#10b981" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-800">המשמרות הוגדרו!</h2>
              <p className="text-sm text-slate-500 mt-1">מה הצעד הבא?</p>
            </div>

            {/* Checklist */}
            <div className="bg-slate-50 rounded-xl p-4 text-right space-y-2.5">
              {[
                { done: true, label: 'הגדרת פרטי העסק' },
                { done: true, label: 'הגדרת משמרות' },
                { done: false, label: 'הוספת עובדים', href: '/employees' },
                { done: false, label: 'הרצת אופטימייזר', href: '/schedule' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-none text-xs font-bold ${
                    item.done ? 'bg-emerald-500 text-white' : 'bg-slate-200 text-slate-400'
                  }`}>
                    {item.done ? '✓' : i + 1}
                  </div>
                  <span className={`text-sm ${item.done ? 'text-slate-400 line-through' : 'text-slate-700 font-medium'}`}>
                    {item.label}
                  </span>
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => router.push('/employees')}
                className="flex-1 py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 transition text-sm"
              >
                הוסף עובדים ראשונים →
              </button>
              <button
                onClick={() => router.push('/schedule')}
                className="flex-1 py-3 border border-slate-200 text-slate-600 font-medium rounded-xl hover:bg-slate-50 transition text-sm"
              >
                עבור לסידור
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Shift Card Component ──

interface ShiftCardProps {
  shift: ShiftDraft
  operatingDays: number[]
  onChange: (changes: Partial<ShiftDraft>) => void
  onRemove: () => void
}

function ShiftCard({ shift, operatingDays, onChange, onRemove }: ShiftCardProps) {
  return (
    <div className="border border-slate-200 rounded-xl p-4 space-y-3 bg-slate-50">
      {/* Header row */}
      <div className="flex items-center gap-2">
        <input
          value={shift.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="שם המשמרת"
          className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm font-medium bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <select
          value={shift.shift_type}
          onChange={(e) => onChange({ shift_type: e.target.value })}
          className="px-2 py-2 border border-slate-200 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          {SHIFT_TYPES.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        <button
          onClick={onRemove}
          className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-red-500 transition rounded-lg hover:bg-red-50"
        >
          <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Times */}
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <label className="text-xs text-slate-500">שעת התחלה</label>
          <input
            type="time"
            value={shift.start_time}
            onChange={(e) => onChange({ start_time: e.target.value })}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">שעת סיום</label>
          <input
            type="time"
            value={shift.end_time}
            onChange={(e) => onChange({ end_time: e.target.value })}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>
      </div>

      {/* Employees */}
      <div className="grid grid-cols-3 gap-2">
        <div className="space-y-1">
          <label className="text-xs text-slate-500">מינ׳ עובדים</label>
          <input
            type="number"
            min={1}
            value={shift.min_employees}
            onChange={(e) => onChange({ min_employees: Number(e.target.value) })}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">ותיקים</label>
          <input
            type="number"
            min={0}
            value={shift.required_roles.senior ?? 0}
            onChange={(e) =>
              onChange({ required_roles: { ...shift.required_roles, senior: Number(e.target.value) } })
            }
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">זוטרים</label>
          <input
            type="number"
            min={0}
            value={shift.required_roles.junior ?? 0}
            onChange={(e) =>
              onChange({ required_roles: { ...shift.required_roles, junior: Number(e.target.value) } })
            }
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
        </div>
      </div>

      {/* Days */}
      <div className="space-y-1.5">
        <label className="text-xs text-slate-500">ימים פעילים למשמרת זו</label>
        <div className="flex gap-1 flex-wrap">
          {operatingDays.map((day) => (
            <button
              key={day}
              type="button"
              onClick={() => {
                const days = shift.days_of_week.includes(day)
                  ? shift.days_of_week.filter((d) => d !== day)
                  : [...shift.days_of_week, day].sort()
                onChange({ days_of_week: days })
              }}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                shift.days_of_week.includes(day)
                  ? day === 6
                    ? 'bg-amber-500 text-white'
                    : 'bg-indigo-600 text-white'
                  : 'bg-white border border-slate-200 text-slate-500 hover:border-indigo-300'
              }`}
            >
              {DAY_LABELS[day]}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
