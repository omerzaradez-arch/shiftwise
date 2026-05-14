'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { he } from 'date-fns/locale'
import { swapsApi } from '@/lib/api/swaps'
import { ManagerNav } from '@/components/layout/ManagerNav'
import { SwapRequest } from '@/types/schedule'
import { toast } from 'sonner'

const STATUS_CONFIG: Record<string, { label: string; style: string }> = {
  pending: { label: 'ממתין', style: 'bg-amber-100 text-amber-700' },
  approved: { label: 'אושר', style: 'bg-green-100 text-green-700' },
  rejected: { label: 'נדחה', style: 'bg-red-100 text-red-700' },
  auto_approved: { label: 'אושר אוטו׳', style: 'bg-blue-100 text-blue-700' },
}

export default function RequestsPage() {
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState<'pending' | 'history'>('pending')
  const [selectedSwap, setSelectedSwap] = useState<string | null>(null)

  const { data: pendingSwaps = [], isLoading } = useQuery({
    queryKey: ['swaps', 'pending'],
    queryFn: swapsApi.getPendingSwaps,
  })

  const { data: suggestions = [] } = useQuery({
    queryKey: ['swap-suggestions', selectedSwap],
    queryFn: () => swapsApi.getSuggestions(selectedSwap!),
    enabled: !!selectedSwap,
  })

  const approveMutation = useMutation({
    mutationFn: swapsApi.approveSwap,
    onSuccess: () => {
      toast.success('הבקשה אושרה')
      qc.invalidateQueries({ queryKey: ['swaps'] })
      qc.invalidateQueries({ queryKey: ['schedule'] })
      setSelectedSwap(null)
    },
    onError: () => toast.error('שגיאה באישור הבקשה'),
  })

  const rejectMutation = useMutation({
    mutationFn: (swapId: string) => swapsApi.rejectSwap(swapId),
    onSuccess: () => {
      toast.success('הבקשה נדחתה')
      qc.invalidateQueries({ queryKey: ['swaps'] })
      setSelectedSwap(null)
    },
  })

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden" dir="rtl">
      <ManagerNav />

      <main className="flex-1 overflow-auto pt-14 md:pt-0 pb-20 md:pb-0">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900">בקשות החלפה</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                {pendingSwaps.length > 0
                  ? `${pendingSwaps.length} בקשות ממתינות לאישור`
                  : 'אין בקשות ממתינות'}
              </p>
            </div>

            <div className="flex gap-1 bg-gray-100 p-1 rounded-xl">
              {(['pending', 'history'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === tab
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab === 'pending' ? 'ממתינות' : 'היסטוריה'}
                  {tab === 'pending' && pendingSwaps.length > 0 && (
                    <span className="mr-2 inline-flex items-center justify-center w-5 h-5 bg-amber-500 text-white text-xs rounded-full">
                      {pendingSwaps.length}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="p-6">
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-28 bg-white rounded-2xl animate-pulse border border-gray-100" />
              ))}
            </div>
          ) : pendingSwaps.length === 0 ? (
            <div className="text-center py-20">
              <p className="text-5xl mb-4">✅</p>
              <p className="text-lg font-semibold text-gray-700">אין בקשות ממתינות</p>
              <p className="text-sm text-gray-400 mt-1">כשעובד יבקש החלפה — זה יופיע כאן</p>
            </div>
          ) : (
            <div className="space-y-3">
              {pendingSwaps.map((swap: any) => (
                <SwapCard
                  key={swap.id}
                  swap={swap}
                  isSelected={selectedSwap === swap.id}
                  suggestions={selectedSwap === swap.id ? suggestions : []}
                  onSelect={() => setSelectedSwap(selectedSwap === swap.id ? null : swap.id)}
                  onApprove={(targetId) => approveMutation.mutate(swap.id)}
                  onReject={() => rejectMutation.mutate(swap.id)}
                  isLoading={approveMutation.isPending || rejectMutation.isPending}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function SwapCard({
  swap,
  isSelected,
  suggestions,
  onSelect,
  onApprove,
  onReject,
  isLoading,
}: {
  swap: any
  isSelected: boolean
  suggestions: any[]
  onSelect: () => void
  onApprove: (targetId?: string) => void
  onReject: () => void
  isLoading: boolean
}) {
  const [selectedReplacement, setSelectedReplacement] = useState<string | null>(null)

  return (
    <div className={`bg-white rounded-2xl border transition-all shadow-sm ${
      isSelected ? 'border-blue-300 shadow-blue-100' : 'border-gray-100'
    }`}>
      {/* Main row */}
      <div className="p-5 flex items-start gap-4">
        {/* Avatar */}
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-bold flex-none">
          {swap.requester?.name?.[0] ?? '?'}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <span className="font-semibold text-gray-900">{swap.requester?.name}</span>
              <span className="text-gray-400 mx-2">·</span>
              <span className="text-sm text-gray-500">
                {swap.shift
                  ? format(new Date(swap.shift.date), 'EEEE d בMMMM', { locale: he })
                  : ''}
              </span>
              {swap.shift && (
                <span className="text-sm text-gray-400 mr-2">
                  {swap.shift.start_time}–{swap.shift.end_time}
                </span>
              )}
            </div>
            <span className={`flex-none text-xs font-medium px-2.5 py-1 rounded-lg ${STATUS_CONFIG['pending'].style}`}>
              {STATUS_CONFIG['pending'].label}
            </span>
          </div>

          {swap.reason && (
            <p className="text-sm text-gray-500 mt-1 bg-gray-50 rounded-lg px-3 py-2 mt-2">
              &ldquo;{swap.reason}&rdquo;
            </p>
          )}

          <p className="text-xs text-gray-400 mt-2">
            נשלח {format(new Date(swap.created_at), "d בMMMM, HH:mm", { locale: he })}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="px-5 pb-4 flex items-center gap-3">
        <button
          onClick={onSelect}
          className="text-sm text-blue-600 font-medium hover:underline flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0" />
          </svg>
          {isSelected ? 'הסתר מחליפים' : 'הצג מחליפים מוצעים'}
        </button>

        <div className="flex-1" />

        <button
          onClick={onReject}
          disabled={isLoading}
          className="px-4 py-2 border border-gray-200 text-gray-600 text-sm font-medium rounded-xl hover:bg-gray-50 disabled:opacity-50 transition"
        >
          דחה
        </button>
        <button
          onClick={() => onApprove(selectedReplacement ?? undefined)}
          disabled={isLoading}
          className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-xl hover:bg-green-700 disabled:opacity-50 transition"
        >
          {isLoading ? 'מאשר...' : 'אשר'}
        </button>
      </div>

      {/* Replacement suggestions */}
      {isSelected && (
        <div className="px-5 pb-5 border-t border-gray-50 pt-4">
          <p className="text-xs font-semibold text-gray-500 uppercase mb-3">
            מחליפים מוצעים
          </p>
          {suggestions.length === 0 ? (
            <p className="text-sm text-gray-400">לא נמצאו מחליפים זמינים</p>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {suggestions.map((s: any) => (
                <button
                  key={s.employee_id}
                  onClick={() => setSelectedReplacement(
                    selectedReplacement === s.employee_id ? null : s.employee_id
                  )}
                  className={`p-3 rounded-xl border-2 text-right transition-all ${
                    selectedReplacement === s.employee_id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-100 bg-gray-50 hover:border-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-7 h-7 rounded-full bg-indigo-500 flex items-center justify-center text-white text-xs font-bold">
                      {s.name[0]}
                    </div>
                    <span className="text-sm font-medium text-gray-900">{s.name}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">{s.role === 'senior' ? 'בכיר' : 'עובד'}</span>
                    <span className={`text-xs font-semibold ${s.fit_score >= 90 ? 'text-green-600' : 'text-blue-600'}`}>
                      {s.fit_score}%
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
