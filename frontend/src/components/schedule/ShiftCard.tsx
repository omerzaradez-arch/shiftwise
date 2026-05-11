'use client'

import { format } from 'date-fns'
import { he } from 'date-fns/locale'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { swapsApi } from '@/lib/api/swaps'
import { ScheduledShift } from '@/types/schedule'
import { toast } from 'sonner'

const SHIFT_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  morning: { bg: 'bg-yellow-50', text: 'text-yellow-800', dot: 'bg-yellow-400' },
  afternoon: { bg: 'bg-blue-50', text: 'text-blue-800', dot: 'bg-blue-400' },
  evening: { bg: 'bg-purple-50', text: 'text-purple-800', dot: 'bg-purple-500' },
}

interface Props {
  shift: ScheduledShift
  showSwapButton?: boolean
}

export function ShiftCard({ shift, showSwapButton }: Props) {
  const qc = useQueryClient()
  const colors = SHIFT_COLORS[shift.shift_type] ?? SHIFT_COLORS.afternoon

  const swapMutation = useMutation({
    mutationFn: () => swapsApi.requestSwap(shift.id, ''),
    onSuccess: () => {
      toast.success('בקשת ההחלפה נשלחה!')
      qc.invalidateQueries({ queryKey: ['my-shifts'] })
    },
  })

  const statusLabel: Record<string, string> = {
    assigned: '',
    swap_requested: 'מבקש החלפה',
    swap_approved: 'הוחלף',
    cancelled: 'בוטל',
  }

  return (
    <div className={`rounded-2xl p-4 border border-transparent ${colors.bg} relative`}>
      {shift.status !== 'assigned' && (
        <span className="absolute top-3 left-3 text-xs font-medium text-gray-500">
          {statusLabel[shift.status]}
        </span>
      )}

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className={`w-2.5 h-2.5 rounded-full ${colors.dot}`} />
            <span className={`font-semibold text-sm ${colors.text}`}>
              {shift.shift_name}
            </span>
          </div>
          <p className="text-gray-900 font-medium">
            {format(new Date(shift.date), 'EEEE, d בMMMM', { locale: he })}
          </p>
          <p className="text-gray-500 text-sm mt-0.5">
            {shift.start_time} — {shift.end_time}
            <span className="mx-1.5">·</span>
            {shift.duration_hours} שעות
          </p>
        </div>

        {showSwapButton && shift.status === 'assigned' && (
          <button
            onClick={() => swapMutation.mutate()}
            disabled={swapMutation.isPending}
            className="text-xs font-medium text-gray-500 hover:text-blue-600 transition px-3 py-1.5 rounded-lg hover:bg-white border border-transparent hover:border-gray-200"
          >
            בקש החלפה
          </button>
        )}
      </div>
    </div>
  )
}
