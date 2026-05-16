'use client'

import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { apiClient } from '@/lib/api/client'
import { shiftTemplatesApi, ShiftTemplate, ShiftTemplateCreate } from '@/lib/api/shiftTemplates'
import { ManagerNav } from '@/components/layout/ManagerNav'
import { NotificationsToggle } from '@/components/NotificationsToggle'
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
const SHIFT_TYPES = [
  { value: 'morning', label: 'בוקר' },
  { value: 'afternoon', label: 'צהריים' },
  { value: 'evening', label: 'ערב' },
  { value: 'night', label: 'לילה' },
]
const SHIFT_TYPE_COLORS: Record<string, string> = {
  morning: 'bg-amber-100 text-amber-700',
  afternoon: 'bg-blue-100 text-blue-700',
  evening: 'bg-purple-100 text-purple-700',
  night: 'bg-slate-700 text-slate-100',
}

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
const smInput = "px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400 w-full"

// ── Shift Templates Section ────────────────────────────────────────────────────

interface EditingTemplate extends Partial<ShiftTemplateCreate> {
  id?: string
  isNew?: boolean
}

function ShiftTemplatesSection() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<EditingTemplate | null>(null)

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['shift-templates'],
    queryFn: shiftTemplatesApi.list,
  })

  const createMutation = useMutation({
    mutationFn: shiftTemplatesApi.create,
    onSuccess: () => { toast.success('המשמרת נוספה'); qc.invalidateQueries({ queryKey: ['shift-templates'] }); setEditing(null) },
    onError: () => toast.error('שגיאה בשמירה'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ShiftTemplateCreate> }) => shiftTemplatesApi.update(id, data),
    onSuccess: () => { toast.success('המשמרת עודכנה'); qc.invalidateQueries({ queryKey: ['shift-templates'] }); setEditing(null) },
    onError: () => toast.error('שגיאה בשמירה'),
  })

  const deleteMutation = useMutation({
    mutationFn: shiftTemplatesApi.delete,
    onSuccess: () => { toast.success('המשמרת נמחקה'); qc.invalidateQueries({ queryKey: ['shift-templates'] }) },
    onError: () => toast.error('שגיאה במחיקה'),
  })

  function handleSave() {
    if (!editing?.name?.trim() || !editing.start_time || !editing.end_time) {
      toast.error('מלא שם ושעות')
      return
    }
    const payload: ShiftTemplateCreate = {
      name: editing.name!,
      shift_type: editing.shift_type || 'morning',
      start_time: editing.start_time!,
      end_time: editing.end_time!,
      min_employees: editing.min_employees ?? 1,
      max_employees: editing.max_employees ?? 10,
      required_roles: editing.required_roles ?? {},
      days_of_week: editing.days_of_week ?? [0, 1, 2, 3, 4, 5],
    }
    if (editing.isNew) {
      createMutation.mutate(payload)
    } else {
      updateMutation.mutate({ id: editing.id!, data: payload })
    }
  }

  function startEdit(t: ShiftTemplate) {
    setEditing({ ...t })
  }

  function startNew() {
    setEditing({
      isNew: true,
      name: '',
      shift_type: 'morning',
      start_time: '08:00',
      end_time: '16:00',
      min_employees: 2,
      max_employees: 8,
      required_roles: { senior: 1, junior: 1 },
      days_of_week: [0, 1, 2, 3, 4, 5],
    })
  }

  function toggleEditDay(day: number) {
    const days = editing?.days_of_week ?? []
    setEditing((e) => ({
      ...e!,
      days_of_week: days.includes(day) ? days.filter((d) => d !== day) : [...days, day].sort(),
    }))
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-900">משמרות</h2>
          <p className="text-sm text-slate-500 mt-0.5">הגדר את סוגי המשמרות בעסק</p>
        </div>
        <button
          onClick={startNew}
          className="flex items-center gap-1.5 px-3 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-xl hover:bg-indigo-700 transition"
        >
          <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          הוסף משמרת
        </button>
      </div>

      <div className="divide-y divide-slate-100">
        {isLoading && (
          <div className="px-6 py-4 text-sm text-slate-400">טוען...</div>
        )}

        {!isLoading && templates.length === 0 && editing === null && (
          <div className="px-6 py-6 text-center text-sm text-slate-400">
            אין משמרות מוגדרות.{' '}
            <button onClick={startNew} className="text-indigo-600 hover:underline font-medium">הוסף את הראשונה</button>
          </div>
        )}

        {templates.map((t) => (
          <div key={t.id}>
            {editing?.id === t.id && !editing.isNew ? (
              <TemplateEditForm
                editing={editing}
                onChange={(changes) => setEditing((e) => ({ ...e!, ...changes }))}
                onToggleDay={toggleEditDay}
                onSave={handleSave}
                onCancel={() => setEditing(null)}
                isSaving={updateMutation.isPending}
              />
            ) : (
              <div className="px-6 py-4 flex items-center gap-4 hover:bg-slate-50 group transition">
                <span className={`text-xs px-2.5 py-1 rounded-lg font-semibold flex-none ${SHIFT_TYPE_COLORS[t.shift_type] ?? 'bg-slate-100 text-slate-600'}`}>
                  {SHIFT_TYPES.find((s) => s.value === t.shift_type)?.label ?? t.shift_type}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-800">{t.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {t.start_time}–{t.end_time} &nbsp;·&nbsp;
                    {t.days_of_week.map((d) => DAY_LABELS[d]?.[0]).join('')} &nbsp;·&nbsp;
                    מינ׳ {t.min_employees} עובדים
                  </p>
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                  <button
                    onClick={() => startEdit(t)}
                    className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition"
                    title="עריכה"
                  >
                    <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => { if (confirm(`למחוק את "${t.name}"?`)) deleteMutation.mutate(t.id) }}
                    className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                    title="מחיקה"
                  >
                    <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {/* New template form */}
        {editing?.isNew && (
          <TemplateEditForm
            editing={editing}
            onChange={(changes) => setEditing((e) => ({ ...e!, ...changes }))}
            onToggleDay={toggleEditDay}
            onSave={handleSave}
            onCancel={() => setEditing(null)}
            isSaving={createMutation.isPending}
            isNew
          />
        )}
      </div>
    </div>
  )
}

interface TemplateEditFormProps {
  editing: EditingTemplate
  onChange: (changes: Partial<EditingTemplate>) => void
  onToggleDay: (day: number) => void
  onSave: () => void
  onCancel: () => void
  isSaving: boolean
  isNew?: boolean
}

function TemplateEditForm({ editing, onChange, onToggleDay, onSave, onCancel, isSaving, isNew }: TemplateEditFormProps) {
  return (
    <div className="px-6 py-4 bg-indigo-50 border-r-4 border-indigo-500 space-y-3">
      <p className="text-xs font-bold text-indigo-700 uppercase tracking-wider">{isNew ? 'משמרת חדשה' : 'עריכת משמרת'}</p>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs text-slate-500">שם</label>
          <input value={editing.name ?? ''} onChange={(e) => onChange({ name: e.target.value })} placeholder="משמרת בוקר" className={smInput} />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">סוג</label>
          <select value={editing.shift_type ?? 'morning'} onChange={(e) => onChange({ shift_type: e.target.value })} className={smInput}>
            {SHIFT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">שעת התחלה</label>
          <input type="time" value={editing.start_time ?? ''} onChange={(e) => onChange({ start_time: e.target.value })} className={smInput} />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">שעת סיום</label>
          <input type="time" value={editing.end_time ?? ''} onChange={(e) => onChange({ end_time: e.target.value })} className={smInput} />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">מינ׳ עובדים</label>
          <input type="number" min={1} value={editing.min_employees ?? 1} onChange={(e) => onChange({ min_employees: Number(e.target.value) })} className={smInput} />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">מקס׳ עובדים</label>
          <input type="number" min={1} value={editing.max_employees ?? 10} onChange={(e) => onChange({ max_employees: Number(e.target.value) })} className={smInput} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <label className="text-xs text-slate-500">ותיקים נדרשים</label>
          <input type="number" min={0} value={editing.required_roles?.senior ?? 0}
            onChange={(e) => onChange({ required_roles: { ...editing.required_roles, senior: Number(e.target.value) } })}
            className={smInput} />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-slate-500">זוטרים נדרשים</label>
          <input type="number" min={0} value={editing.required_roles?.junior ?? 0}
            onChange={(e) => onChange({ required_roles: { ...editing.required_roles, junior: Number(e.target.value) } })}
            className={smInput} />
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs text-slate-500">ימים פעילים</label>
        <div className="flex gap-1">
          {DAY_LABELS.map((label, i) => (
            <button key={i} type="button" onClick={() => onToggleDay(i)}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                editing.days_of_week?.includes(i)
                  ? i === 6 ? 'bg-amber-500 text-white' : 'bg-indigo-600 text-white'
                  : 'bg-white border border-slate-200 text-slate-500 hover:border-indigo-300'
              }`}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <button onClick={onCancel} className="px-4 py-2 border border-slate-200 text-slate-600 text-sm font-medium rounded-xl hover:bg-white transition">ביטול</button>
        <button onClick={onSave} disabled={isSaving} className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition">
          {isSaving ? 'שומר...' : 'שמור'}
        </button>
      </div>
    </div>
  )
}

// ── Location Section ──────────────────────────────────────────────────────────

function LocationSection({ currentSettings }: { currentSettings: any }) {
  const qc = useQueryClient()
  const [lat, setLat] = useState<string>('')
  const [lng, setLng] = useState<string>('')
  const [radius, setRadius] = useState<number>(200)
  const [detecting, setDetecting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (currentSettings) {
      setLat(currentSettings.location_lat?.toString() ?? '')
      setLng(currentSettings.location_lng?.toString() ?? '')
      setRadius(currentSettings.location_radius ?? 200)
    }
  }, [currentSettings])

  const detectLocation = () => {
    if (!navigator.geolocation) { toast.error('הדפדפן לא תומך ב-GPS'); return }
    setDetecting(true)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6))
        setLng(pos.coords.longitude.toFixed(6))
        setDetecting(false)
        toast.success('המיקום זוהה בהצלחה ✅')
      },
      () => { toast.error('לא ניתן לזהות מיקום — אפשר הרשאה בדפדפן'); setDetecting(false) },
      { timeout: 10000 }
    )
  }

  const handleSave = async () => {
    if (!lat || !lng) { toast.error('חסרים נתוני מיקום'); return }
    setSaving(true)
    try {
      await apiClient.patch('/api/v1/settings/', {
        location_lat: parseFloat(lat),
        location_lng: parseFloat(lng),
        location_radius: radius,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
      qc.invalidateQueries({ queryKey: ['settings'] })
      toast.success('מיקום העסק נשמר ✅')
    } catch {
      toast.error('שגיאה בשמירה')
    } finally {
      setSaving(false)
    }
  }

  const hasLocation = lat && lng

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100">
        <h2 className="text-base font-bold text-slate-900">📍 מיקום העסק</h2>
        <p className="text-sm text-slate-500 mt-0.5">
          מגדיר מיקום GPS של העסק — המערכת תאמת שעובדים נמצאים בטווח בעת כניסה לעבודה
        </p>
      </div>

      <div className="px-6 py-5 space-y-5">
        {/* Detect button */}
        <div>
          <button
            type="button"
            onClick={detectLocation}
            disabled={detecting}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition disabled:opacity-60"
          >
            {detecting ? (
              <>
                <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                מזהה מיקום...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
                </svg>
                זהה מיקום נוכחי
              </>
            )}
          </button>
          <p className="text-xs text-slate-400 mt-1.5">לחץ מהמחשב / טלפון כשאתה נמצא בעסק</p>
        </div>

        {/* Coordinates */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600">קו רוחב (Latitude)</label>
            <input
              type="number"
              step="0.000001"
              value={lat}
              onChange={e => setLat(e.target.value)}
              placeholder="31.771959"
              className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition font-mono"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-600">קו אורך (Longitude)</label>
            <input
              type="number"
              step="0.000001"
              value={lng}
              onChange={e => setLng(e.target.value)}
              placeholder="35.217018"
              className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition font-mono"
            />
          </div>
        </div>

        {/* Radius slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-600">טווח מותר מהעסק</label>
            <span className="text-sm font-bold text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-lg">{radius} מ׳</span>
          </div>
          <input
            type="range"
            min={50}
            max={500}
            step={50}
            value={radius}
            onChange={e => setRadius(Number(e.target.value))}
            className="w-full accent-indigo-600"
          />
          <div className="flex justify-between text-xs text-slate-400">
            <span>50 מ׳ (הכי מדויק)</span>
            <span>500 מ׳ (הכי גמיש)</span>
          </div>
        </div>

        {/* Map preview */}
        {hasLocation && (
          <div className="rounded-xl overflow-hidden border border-slate-200">
            <iframe
              title="מיקום העסק"
              width="100%"
              height="220"
              loading="lazy"
              src={`https://www.openstreetmap.org/export/embed.html?bbox=${parseFloat(lng)-0.003},${parseFloat(lat)-0.002},${parseFloat(lng)+0.003},${parseFloat(lat)+0.002}&layer=mapnik&marker=${lat},${lng}`}
              className="block"
            />
            <div className="px-3 py-2 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 text-center">
              📍 מיקום העסק — טווח: {radius} מטר
            </div>
          </div>
        )}

        {/* Save button */}
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !hasLocation}
          className={`flex items-center gap-2 px-5 py-2.5 text-sm font-semibold rounded-xl transition disabled:opacity-40 ${
            saved
              ? 'bg-emerald-500 text-white'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white'
          }`}
        >
          {saving ? 'שומר...' : saved ? '✅ נשמר!' : 'שמור מיקום'}
        </button>
      </div>
    </div>
  )
}

// ── Main Settings Page ─────────────────────────────────────────────────────────

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

      <main className="flex-1 overflow-auto pt-14 md:pt-0 pb-20 md:pb-0">
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
          <Section title="פרטי הארגון" subtitle="השם שמוצג לעובדים">
            <Field label="שם הארגון" error={errors.org_name?.message}>
              <input {...register('org_name')} className={inputCls} placeholder="שם המסעדה / עסק" />
            </Field>
          </Section>

          <Section title="דרישות משמרת" subtitle="כמה עובדים נדרשים בכל משמרת">
            <Field label="עובדים מינימום" hint="מינימום עובדים בכל משמרת" error={errors.min_staff_per_shift?.message}>
              <input {...register('min_staff_per_shift')} type="number" min={1} max={20} className={inputCls} />
            </Field>
            <Field label="בכירים מינימום" hint="לפחות כמה עובדים בכירים" error={errors.min_senior_per_shift?.message}>
              <input {...register('min_senior_per_shift')} type="number" min={0} max={10} className={inputCls} />
            </Field>
          </Section>

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

          <Section title="הערות למנהל" subtitle="הערות פנימיות — לא מוצגות לעובדים">
            <textarea
              {...register('notes')}
              placeholder="הערות, כללים מיוחדים, תזכורות..."
              rows={4}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm bg-slate-50 focus:bg-white transition resize-none"
            />
          </Section>

          <div className="pb-2">
            <button
              type="submit"
              disabled={mutation.isPending || !isDirty}
              className="px-6 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 disabled:opacity-40 transition shadow-sm shadow-indigo-200"
            >
              {mutation.isPending ? 'שומר...' : 'שמור הגדרות'}
            </button>
          </div>
        </form>

        {/* Location Section — outside the main form */}
        <div className="px-6 pb-6 max-w-2xl">
          <LocationSection currentSettings={settings} />
        </div>

        {/* Push Notifications */}
        <div className="px-6 pb-6 max-w-2xl">
          <NotificationsToggle />
        </div>

        {/* Shift Templates — outside the form */}
        <div className="px-6 pb-6 max-w-2xl">
          <ShiftTemplatesSection />
        </div>

        {/* Info */}
        <div className="px-6 pb-8 max-w-2xl">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100">
              <h2 className="text-base font-bold text-slate-900">מידע על המערכת</h2>
            </div>
            <div className="px-6 py-5">
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'תוכנית', value: settings?.plan === 'free' ? 'חינמי' : 'פרו' },
                  { label: 'אזור זמן', value: settings?.timezone ?? 'Asia/Jerusalem' },
                  { label: 'גרסה', value: 'v0.1.0' },
                ].map((item) => (
                  <div key={item.label} className="bg-slate-50 rounded-xl p-3 border border-slate-100">
                    <p className="text-xs text-slate-400 mb-1">{item.label}</p>
                    <p className="text-sm font-semibold text-slate-700">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
