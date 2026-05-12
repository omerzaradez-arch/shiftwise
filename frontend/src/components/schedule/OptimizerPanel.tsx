'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { format } from 'date-fns'
import { he } from 'date-fns/locale'
import { scheduleApi } from '@/lib/api/schedule'
import { toast } from 'sonner'

interface Props {
  weekStart: Date
  onClose: () => void
  onComplete: () => void
}

type OptimizeStatus = 'idle' | 'running' | 'done' | 'error'

export function OptimizerPanel({ weekStart, onClose, onComplete }: Props) {
  const [status, setStatus] = useState<OptimizeStatus>('idle')
  const [result, setResult] = useState<{ score: number; coverage: number; conflicts: number } | null>(null)

  const mutation = useMutation({
    mutationFn: () => scheduleApi.generateSchedule(weekStart),
    onMutate: () => setStatus('running'),
    onSuccess: (data) => {
      setStatus('done')
      setResult(data)
    },
    onError: () => {
      setStatus('error')
      toast.error('האופטימייזר נכשל — נסה שוב')
    },
  })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-gray-100">
          <h2 className="text-lg font-bold text-gray-900">הרצת אופטימייזר</h2>
          <p className="text-sm text-gray-500 mt-1">
            שבוע {format(weekStart, "d MMM yyyy", { locale: he })}
          </p>
        </div>

        <div className="p-6">
          {status === 'idle' && (
            <div>
              <div className="bg-indigo-50 rounded-xl p-4 mb-6">
                <p className="text-sm font-medium text-indigo-900 mb-2">
                  האופטימייזר יבצע:
                </p>
                <ul className="text-sm text-indigo-700 space-y-1.5">
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full flex-none" />
                    כיסוי מלא של כל המשמרות
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full flex-none" />
                    הוגנות מלאה בין עובדים
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full flex-none" />
                    כיבוד אילוצי זמינות
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full flex-none" />
                    כיבוד העדפות בוקר/ערב
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full flex-none" />
                    עובד בכיר בכל משמרת
                  </li>
                </ul>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="flex-none px-5 py-3 border border-gray-200 rounded-xl text-gray-600 text-sm font-medium hover:bg-gray-50"
                >
                  ביטול
                </button>
                <button
                  onClick={() => mutation.mutate()}
                  className="flex-1 bg-indigo-600 text-white font-semibold py-3 rounded-xl hover:bg-indigo-700 transition"
                >
                  הרץ עכשיו
                </button>
              </div>
            </div>
          )}

          {status === 'running' && (
            <div className="text-center py-8">
              <div className="relative w-20 h-20 mx-auto mb-4">
                <div className="absolute inset-0 rounded-full border-4 border-indigo-100" />
                <div className="absolute inset-0 rounded-full border-4 border-indigo-600 border-t-transparent animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center text-2xl">
                  🧠
                </div>
              </div>
              <p className="font-semibold text-gray-900 mb-1">מחשב סידור אופטימלי...</p>
              <p className="text-sm text-gray-400">זה אורך עד 30 שניות</p>
            </div>
          )}

          {status === 'done' && result && (
            <div>
              <div className="text-center mb-6">
                <div className="text-5xl mb-3">🎉</div>
                <p className="font-bold text-gray-900 text-lg">הסידור מוכן!</p>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-6">
                <div className="bg-green-50 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-green-600">{result.score}</p>
                  <p className="text-xs text-green-700 mt-0.5">ציון / 100</p>
                </div>
                <div className="bg-blue-50 rounded-xl p-3 text-center">
                  <p className="text-2xl font-bold text-blue-600">{result.coverage}%</p>
                  <p className="text-xs text-blue-700 mt-0.5">כיסוי</p>
                </div>
                <div className={`rounded-xl p-3 text-center ${result.conflicts > 0 ? 'bg-amber-50' : 'bg-gray-50'}`}>
                  <p className={`text-2xl font-bold ${result.conflicts > 0 ? 'text-amber-600' : 'text-gray-600'}`}>
                    {result.conflicts}
                  </p>
                  <p className={`text-xs mt-0.5 ${result.conflicts > 0 ? 'text-amber-700' : 'text-gray-500'}`}>
                    קונפליקטים
                  </p>
                </div>
              </div>

              <button
                onClick={onComplete}
                className="w-full bg-green-600 text-white font-semibold py-3 rounded-xl hover:bg-green-700 transition"
              >
                צפה בסידור
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
