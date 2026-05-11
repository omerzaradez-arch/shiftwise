'use client'

import { useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { apiClient } from '@/lib/api/client'
import { ManagerNav } from '@/components/layout/ManagerNav'
import { toast } from 'sonner'

const schema = z.object({
  org_name: z.string().min(2, 'שם חייב להכיל לפחות 2 תווים'),
  min_staff_per_shift: z.coerce.number().min(1).max(20),
  min_senior_per_shift: z.coerce.number().min(0).max(10),
  availability_deadline_day: z.coerce.number().min(0).max(6),
  publish_day: z.coerce.number().min(0).max(6),
  notes: z.string().optional(),
})

type SettingsForm = z.infer<typeof schema>

const DAY_LABELS = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']

async function fetchSettings() {
  const { data } = await apiClient.get('/api/v1/settings/')
  return data
}

async function saveSettings(payload: SettingsForm) {
  const { data } = await apiClient.patch('/api/v1/settings/', payload)
  return data
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100">
        <h2 className="text-base font-bold text-slate-900">{title}</h2>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="px-6 py-5 space-y-4">{children}</div>
    </div>
  )
}

function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-4">
      <div className="w-48 flex-none pt-2.5">
        <p className="text-sm font-semibold text-slate-700">{label}</p>
        {hint && <p className="text-xs text-slate-400 mt-0.5">{hint}</p>}
      </div>
      <div className="flex-1">
        {children}
        {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
      </div>
    </div>
  )
}

const inputCls = "w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm bg-slate-50 focus:bg-white transition max-w-xs"
const selectCls = `${inputCls} bg-white`

export default function SettingsPage() {
  const qc = useQueryClient()

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: fetchSettings,
  })

  const mutation = useMutation({
    mutationFn: saveSettings,
    onSuccess: () => {
      toast.success('ההגדרות נשמרו בהצלחה')
      qc.invalidateQueries({ queryKey: ['settings'] })
    },
    onError: () => toast.error('שגיאה בשמירת ההגדרות'),
  })

  const { register, handleSubmit, reset, formState: { errors, isDirty } } = useForm<SettingsForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      org_name: '',
      min_staff_per_shift: 3,
      min_senior_per_shift: 1,
      availability_deadline_day: 3,
      publish_day: 4,
      notes: '',
    },
  })

  useEffect(() => {
    if (settings) {
      reset({
        org_name: settings.org_name ?? '',
        min_staff_per_shift: settings.min_staff_per_shift ?? 3,
        min_senior_per_shift: settings.min_senior_per_shift ?? 1,
        availability_deadline_day: settings.availability_deadline_day ?? 3,
        publish_day: settings.publish_day ?? 4,
        notes: settings.notes ?? '',
      })
    }
  }, [settings, reset])

  const onSubmit = (data: SettingsForm) => mutation.mutate(data)

  if (isLoading) {
    return (
      <div className="flex h-screen bg-slate-50" dir="rtl">
        <ManagerNav />
        <main className="flex-1 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </main>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden" dir="rtl">
      <ManagerNav />

      <main className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900">הגדרות</h1>
              <p className="text-sm text-slate-500 mt-0.5">הגדרות הארגון והמערכת</p>
            </div>
            {isDirty && (
              <button
                onClick={handleSubmit(onSubmit)}
                disabled={mutation.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition shadow-sm shadow-indigo-200"
              >
                {mutation.isPending ? 'שומר...' : 'שמור שינויים'}
              </button>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-6 max-w-2xl">
          {/* Organization */}
          <Section title="פרטי הארגון" subtitle="השם שמוצג לעובדים">
            <Field label="שם הארגון" error={errors.org_name?.message}>
              <input {...register('org_name')} className={inputCls} placeholder="שם המסעדה / עסק" />
            </Field>
          </Section>

          {/* Shift requirements */}
          <Section title="דרישות משמרת" subtitle="כמה עובדים נדרשים בכל משמרת">
            <Field label="עובדים מינימום" hint="מינימום עובדים בכל משמרת" error={errors.min_staff_per_shift?.message}>
              <input {...register('min_staff_per_shift')} type="number" min={1} max={20} className={inputCls} />
            </Field>
            <Field label="בכירים מינימום" hint="לפחות כמה עובדים בכירים" error={errors.min_senior_per_shift?.message}>
              <input {...register('min_senior_per_shift')} type="number" min={0} max={10} className={inputCls} />
            </Field>
          </Section>

          {/* Schedule workflow */}
          <Section title="לוח זמנים שבועי" subtitle="מתי עובדים שולחים זמינות ומתי הסידור מתפרסם">
            <Field label="דדליין זמינות" hint="יום האחרון לשליחת זמינות">
              <select {...register('availability_deadline_day')} className={selectCls}>
                {DAY_LABELS.map((d, i) => (
                  <option key={i} value={i}>יום {d}</option>
                ))}
              </select>
            </Field>
            <Field label="יום פרסום" hint="מתי מתפרסם הסידור לעובדים">
              <select {...register('publish_day')} className={selectCls}>
                {DAY_LABELS.map((d, i) => (
                  <option key={i} value={i}>יום {d}</option>
                ))}
              </select>
            </Field>
          </Section>

          {/* Notes */}
          <Section title="הערות למנהל" subtitle="הערות פנימיות — לא מוצגות לעובדים">
            <textarea
              {...register('notes')}
              placeholder="הערות, כללים מיוחדים, תזכורות..."
              rows={4}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm bg-slate-50 focus:bg-white transition resize-none"
            />
          </Section>

          {/* Info cards */}
          <Section title="מידע על המערכת">
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'תוכנית', value: settings?.plan === 'free' ? 'חינמי' : 'פרו', color: 'text-slate-700' },
                { label: 'אזור זמן', value: settings?.timezone ?? 'Asia/Jerusalem', color: 'text-slate-700' },
                { label: 'גרסה', value: 'v0.1.0', color: 'text-slate-500' },
              ].map((item) => (
                <div key={item.label} className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                  <p className="text-xs text-slate-400 mb-1">{item.label}</p>
                  <p className={`text-sm font-semibold ${item.color}`}>{item.value}</p>
                </div>
              ))}
            </div>
          </Section>

          <div className="pb-4">
            <button
              type="submit"
              disabled={mutation.isPending || !isDirty}
              className="px-6 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 disabled:opacity-40 transition shadow-sm shadow-indigo-200"
            >
              {mutation.isPending ? 'שומר...' : 'שמור הגדרות'}
            </button>
          </div>
        </form>
      </main>
    </div>
  )
}
