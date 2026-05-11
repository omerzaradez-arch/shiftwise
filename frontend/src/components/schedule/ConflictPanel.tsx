'use client'

import { Conflict } from '@/types/schedule'

const SEVERITY_STYLE: Record<string, string> = {
  high: 'bg-red-50 border-red-200 text-red-700',
  medium: 'bg-amber-50 border-amber-200 text-amber-700',
  low: 'bg-blue-50 border-blue-200 text-blue-600',
}

const SEVERITY_ICON: Record<string, string> = {
  high: '🔴',
  medium: '🟡',
  low: '🔵',
}

interface Props {
  conflicts: Conflict[]
  onResolve: (conflictId: string) => void
}

export function ConflictPanel({ conflicts, onResolve }: Props) {
  return (
    <div className="w-72 border-r border-gray-200 bg-white p-4 overflow-y-auto">
      <h3 className="font-semibold text-gray-900 mb-1">קונפליקטים</h3>
      <p className="text-xs text-gray-400 mb-4">{conflicts.length} בעיות שדורשות תשומת לב</p>

      <div className="space-y-3">
        {conflicts.map((conflict) => (
          <div
            key={conflict.id}
            className={`rounded-xl p-3 border text-sm ${SEVERITY_STYLE[conflict.severity]}`}
          >
            <div className="flex items-start gap-2">
              <span className="mt-0.5">{SEVERITY_ICON[conflict.severity]}</span>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 text-xs">{conflict.type_label}</p>
                <p className="mt-0.5 text-xs opacity-80">{conflict.description}</p>

                {conflict.suggestion && (
                  <p className="mt-1.5 text-xs font-medium">
                    הצעה: {conflict.suggestion}
                  </p>
                )}

                <button
                  onClick={() => onResolve(conflict.id)}
                  className="mt-2 text-xs underline underline-offset-2 opacity-70 hover:opacity-100"
                >
                  סמן כפתור
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
