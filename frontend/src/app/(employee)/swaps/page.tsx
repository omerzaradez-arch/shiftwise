'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format, startOfWeek, addWeeks } from 'date-fns'
import { he } from 'date-fns/locale'
import { shiftsApi } from '@/lib/api/shifts'
import { swapsApi } from '@/lib/api/swaps'
import { MobileNav } from '@/components/layout/MobileNav'
import { toast } from 'sonner'

export default function SwapsPage() {
  const qc = useQueryClient()
  const weekStart = startOfWeek(new Date(), { weekStartsOn: 0 })
  const [selectedShiftId, setSelectedShiftId] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const [step, setStep] = useState<'select' | 'confirm' | 'done'>('select')

  const { data: myShifts = [], isLoading } = useQuery({
    queryKey: ['my-shifts', weekStart.toISOString()],
    queryFn: () => shiftsApi.getMyShifts(weekStart),
  })

  const { data: suggestions = [] } = useQuery({
    queryKey: ['swap-suggestions', selectedShiftId],
    queryFn: () => swapsApi.getSuggestions(selectedShiftId!),
    enabled: !!selectedShiftId && step === 'confirm',
  })

  const requestMutation = useMutation({
    mutationFn: ({ shiftId, reason }: { shiftId: string; reason: string }) =>
      swapsApi.requestSwap(shiftId, reason),
    onSuccess: () => {
      toast.success('בקשת ההחלפה נשלחה למנהל')
      qc.invalidateQueries({ queryKey: ['my-shifts'] })
      setStep('done')
    },
    onError: () => toast.error('שגיאה בשליחת הבקשה'),
  })

  const swappableShifts = myShifts.filter(
    (s: any) => s.status === 'assigned'
  )

  const selectedShift = myShifts.find((s: any) => s.id === selectedShiftId)

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      <div className="bg-white border-b border-gray-100 px-4 pt-12 pb-4 sticky top-0 z-10">
        <h1 className="text-xl font-bold text-gray-900">בקשת החלפה</h1>
        <p className="text-sm text-gray-400 mt-0.5">בחר משמרת שרוצה להחליף</p>
      </div>

      <div className="px-4 py-5">
        {step === 'select' && (
          <>
            {isLoading ? (
              <div className="space-y-3">
                {[1, 2].map((i) => (
                  <div key={i} className="h-20 bg-white rounded-2xl animate-pulse border border-gray-100" />
                ))}
              </div>
            ) : swappableShifts.length === 0 ? (
              <div className="text-center py-16 text-gray-400">
                <p className="text-4xl mb-3">🔄</p>
                <p className="font-medium">אין משמרות להחלפה</p>
                <p className="text-sm mt-1">רק משמרות מאושרות ניתן להחליף</p>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm font-medium text-gray-500 mb-2">
                  בחר משמרת:
                </p>
                {swappableShifts.map((shift: any) => (
                  <button
                    key={shift.id}
                    onClick={() => {
                      setSelectedShiftId(shift.id)
                      setStep('confirm')
                    }}
                    className={`w-full text-right bg-white rounded-2xl p-4 border-2 transition-all shadow-sm ${
                      selectedShiftId === shift.id
                        ? 'border-blue-500'
                        : 'border-gray-100 hover:border-gray-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-gray-900">
                          {format(new Date(shift.date), 'EEEE, d בMMMM', { locale: he })}
                        </p>
                        <p className="text-sm text-gray-500 mt-0.5">
                          {shift.start_time}–{shift.end_time} · {shift.shift_name}
                        </p>
                      </div>
                      <svg className="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        )}

        {step === 'confirm' && selectedShift && (
          <div>
            <button
              onClick={() => { setStep('select'); setSelectedShiftId(null) }}
              className="flex items-center gap-1 text-sm text-gray-400 mb-5 hover:text-gray-600"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              חזור
            </button>

            {/* Selected shift summary */}
            <div className="bg-blue-50 rounded-2xl p-4 mb-5">
              <p className="text-xs font-semibold text-blue-600 uppercase mb-1">המשמרת לבקשת החלפה</p>
              <p className="font-bold text-gray-900">
                {format(new Date(selectedShift.date), 'EEEE, d בMMMM', { locale: he })}
              </p>
              <p className="text-sm text-gray-600">
                {selectedShift.start_time}–{selectedShift.end_time} · {selectedShift.shift_name}
              </p>
            </div>

            {/* Reason */}
            <div className="bg-white rounded-2xl p-4 border border-gray-100 mb-4">
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                סיבה (אופציונלי)
              </label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="לדוגמה: אירוע משפחתי, מחלה..."
                rows={3}
                className="w-full text-sm border border-gray-200 rounded-xl p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Suggestions */}
            {suggestions.length > 0 && (
              <div className="bg-white rounded-2xl p-4 border border-gray-100 mb-5">
                <p className="text-sm font-medium text-gray-700 mb-3">
                  עובדים שיכולים להחליף אותך:
                </p>
                <div className="flex flex-wrap gap-2">
                  {suggestions.map((s: any) => (
                    <div
                      key={s.employee_id}
                      className="flex items-center gap-2 bg-gray-50 rounded-xl px-3 py-2"
                    >
                      <div className="w-6 h-6 rounded-full bg-indigo-500 flex items-center justify-center text-white text-xs font-bold">
                        {s.name[0]}
                      </div>
                      <span className="text-sm text-gray-700">{s.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={() => requestMutation.mutate({ shiftId: selectedShiftId!, reason })}
              disabled={requestMutation.isPending}
              className="w-full bg-blue-600 text-white font-semibold py-4 rounded-2xl hover:bg-blue-700 disabled:opacity-60 transition"
            >
              {requestMutation.isPending ? 'שולח בקשה...' : 'שלח בקשת החלפה'}
            </button>
          </div>
        )}

        {step === 'done' && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📨</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">הבקשה נשלחה!</h2>
            <p className="text-gray-500 mb-1">המנהל יקבל את הבקשה ויאשר בהקדם</p>
            <p className="text-sm text-gray-400">תקבל עדכון כשהבקשה תטופל</p>
            <button
              onClick={() => { setStep('select'); setSelectedShiftId(null); setReason('') }}
              className="mt-8 text-blue-600 font-medium text-sm"
            >
              בקשה נוספת
            </button>
          </div>
        )}
      </div>

      <MobileNav />
    </div>
  )
}
