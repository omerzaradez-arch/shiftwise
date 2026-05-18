'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { he } from 'date-fns/locale'
import { scheduleApi } from '@/lib/api/schedule'
import { shiftTemplatesApi } from '@/lib/api/shiftTemplates'
import { employeesApi } from '@/lib/api/employees'
import { toast } from 'sonner'

interface ExistingShift {
  id: string
  date: string
  start_time: string
  end_time: string
  employee_id: string
  template_id?: string | null
  shift_name?: string
}

interface Props {
  mode: 'create' | 'edit'
  shift?: ExistingShift
  defaultDate?: string
  weekStart: Date
  onClose: () => void
}

export function ShiftModal({ mode, shift, defaultDate, weekStart, onClose }: Props) {
  const qc = useQueryClient()

  const { data: templates = [] } = useQuery({
    queryKey: ['shift-templates'],
    queryFn: shiftTemplatesApi.list,
  })

  const { data: employees = [] } = useQuery({
    queryKey: ['employees'],
    queryFn: employeesApi.list,
  })

  const [selectedDate, setSelectedDate] = useState(
    shift?.date ?? defaultDate ?? format(weekStart, 'yyyy-MM-dd')
  )
  const [templateId, setTemplateId] = useState<string>(shift?.template_id ?? '')
  const [employeeId, setEmployeeId] = useState<string>(shift?.employee_id ?? '')
  const [startTime, setStartTime] = useState<string>(shift?.start_time ?? '')
  const [endTime, setEndTime] = useState<string>(shift?.end_time ?? '')
  const [overrideTimes, setOverrideTimes] = useState(false)

  useEffect(() => {
    if (mode === 'create' && templateId && !overrideTimes) {
      const t = templates.find((x: any) => x.id === templateId)
      if (t) {
        setStartTime(t.start_time?.slice(0, 5) ?? '')
        setEndTime(t.end_time?.slice(0, 5) ?? '')
      }
    }
  }, [templateId, templates, mode, overrideTimes])

  const createMut = useMutation({
    mutationFn: () => scheduleApi.createShift({
      week_start: format(weekStart, 'yyyy-MM-dd'),
      date: selectedDate,
      template_id: templateId,
      employee_id: employeeId,
      start_time: overrideTimes ? startTime : undefined,
      end_time: overrideTimes ? endTime : undefined,
    }),
    onSuccess: () => {
      toast.success('המשמרת נוצרה')
      qc.invalidateQueries({ queryKey: ['schedule'] })
      qc.invalidateQueries({ queryKey: ['conflicts'] })
      onClose()
    },
    onError: () => toast.error('שגיאה ביצירת המשמרת'),
  })

  const updateMut = useMutation({
    mutationFn: () => scheduleApi.updateShift(shift!.id, {
      date: selectedDate,
      template_id: templateId || undefined,
      employee_id: employeeId,
      start_time: startTime || undefined,
      end_time: endTime || undefined,
    }),
    onSuccess: () => {
      toast.success('המשמרת עודכנה')
      qc.invalidateQueries({ queryKey: ['schedule'] })
      qc.invalidateQueries({ queryKey: ['conflicts'] })
      onClose()
    },
    onError: () => toast.error('שגיאה בעדכון המשמרת'),
  })

  const deleteMut = useMutation({
    mutationFn: () => scheduleApi.deleteShift(shift!.id),
    onSuccess: () => {
      toast.success('המשמרת נמחקה')
      qc.invalidateQueries({ queryKey: ['schedule'] })
      qc.invalidateQueries({ queryKey: ['conflicts'] })
      onClose()
    },
    onError: () => toast.error('שגיאה במחיקה'),
  })

  const handleSave = () => {
    if (!employeeId || !templateId) {
      toast.error('יש לבחור עובד ותבנית משמרת')
      return
    }
    if (mode === 'create') createMut.mutate()
    else updateMut.mutate()
  }

  const handleDelete = () => {
    if (confirm('למחוק את המשמרת? פעולה זו אינה הפיכה.')) {
      deleteMut.mutate()
    }
  }

  const dateLabel = (() => {
    try {
      return format(new Date(selectedDate), 'EEEE d MMM', { locale: he })
    } catch {
      return selectedDate
    }
  })()

  const isSaving = createMut.isPending || updateMut.isPending
  const isDeleting = deleteMut.isPending

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4" dir="rtl" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">
            {mode === 'create' ? 'משמרת חדשה' : 'עריכת משמרת'}
          </h2>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-slate-100 text-slate-400">✕</button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1.5 block">תאריך</label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full px-3 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
            />
            <p className="text-xs text-slate-400 mt-1">{dateLabel}</p>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1.5 block">תבנית משמרת</label>
            <select
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              className="w-full px-3 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm bg-white"
            >
              <option value="">— בחר תבנית —</option>
              {templates.map((t: any) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.start_time?.slice(0, 5)}–{t.end_time?.slice(0, 5)})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-600 mb-1.5 block">עובד</label>
            <select
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              className="w-full px-3 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm bg-white"
            >
              <option value="">— בחר עובד —</option>
              {employees.map((e: any) => (
                <option key={e.id} value={e.id}>{e.name} ({e.role})</option>
              ))}
            </select>
          </div>

          <div className="border-t border-slate-100 pt-4">
            <label className="flex items-center gap-2 cursor-pointer mb-3">
              <input
                type="checkbox"
                checked={overrideTimes}
                onChange={(e) => setOverrideTimes(e.target.checked)}
                className="w-4 h-4 accent-indigo-600"
              />
              <span className="text-sm font-medium text-slate-700">שעות מותאמות אישית</span>
            </label>
            {overrideTimes && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">התחלה</label>
                  <input
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">סיום</label>
                  <input
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-sm"
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-slate-100 flex items-center gap-2">
          {mode === 'edit' && (
            <button
              onClick={handleDelete}
              disabled={isDeleting || isSaving}
              className="px-4 py-2.5 rounded-xl bg-red-50 text-red-600 text-sm font-semibold hover:bg-red-100 disabled:opacity-50"
            >
              {isDeleting ? 'מוחק...' : 'מחק'}
            </button>
          )}
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="px-4 py-2.5 rounded-xl text-slate-600 text-sm font-medium hover:bg-slate-100"
          >
            ביטול
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || isDeleting}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-bold hover:bg-indigo-700 disabled:opacity-50 shadow-sm shadow-indigo-200"
          >
            {isSaving ? 'שומר...' : (mode === 'create' ? 'צור משמרת' : 'שמור')}
          </button>
        </div>
      </div>
    </div>
  )
}
