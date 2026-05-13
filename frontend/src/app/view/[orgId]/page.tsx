'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'

const API = process.env.NEXT_PUBLIC_API_URL || 'https://shiftwise-production.up.railway.app'

interface ShiftEntry { name: string; start: string; end: string }
interface Day {
  date: string
  day_name: string
  morning: ShiftEntry[]
  evening: ShiftEntry[]
}
interface ScheduleData {
  org_name: string
  week_start: string
  week_end: string
  days: Day[]
}

function fmt(d: string) {
  return new Date(d).toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit' })
}

export default function PublicSchedulePage() {
  const { orgId } = useParams<{ orgId: string }>()
  const [data, setData] = useState<ScheduleData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = async () => {
    try {
      const res = await fetch(`${API}/api/v1/public/schedule/${orgId}`)
      if (!res.ok) throw new Error()
      const json = await res.json()
      setData(json)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 5 * 60 * 1000) // refresh every 5 min
    return () => clearInterval(interval)
  }, [orgId])

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-gray-500 text-lg">טוען סידור...</div>
    </div>
  )

  if (error || !data) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-red-500 text-lg">לא נמצא סידור</div>
    </div>
  )

  if (!data.week_start) return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-gray-400 text-lg">אין סידור מפורסם</div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50" dir="rtl">
      {/* Header */}
      <div className="bg-indigo-600 text-white py-5 px-4 text-center shadow">
        <div className="text-2xl font-bold">{data.org_name}</div>
        <div className="text-indigo-200 text-sm mt-1">
          סידור שבוע {fmt(data.week_start)} – {fmt(data.week_end)}
        </div>
      </div>

      {/* Schedule table */}
      <div className="max-w-2xl mx-auto p-4 space-y-3">
        {data.days.map((day) => (
          <div key={day.date} className="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100">
            {/* Day header */}
            <div className="bg-indigo-50 px-4 py-2 flex items-center gap-2 border-b border-indigo-100">
              <span className="font-bold text-indigo-700">{day.day_name}</span>
              <span className="text-gray-400 text-sm">{fmt(day.date)}</span>
            </div>

            <div className="divide-y divide-gray-50">
              {/* Morning */}
              <ShiftRow
                label="בוקר 🌅"
                color="blue"
                entries={day.morning}
              />
              {/* Evening */}
              <ShiftRow
                label="ערב 🌆"
                color="purple"
                entries={day.evening}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="text-center text-gray-300 text-xs pb-8">
        מתעדכן אוטומטית • ShiftWise
      </div>
    </div>
  )
}

function ShiftRow({ label, color, entries }: {
  label: string
  color: 'blue' | 'purple'
  entries: ShiftEntry[]
}) {
  const colors = {
    blue: 'text-blue-700 bg-blue-50',
    purple: 'text-purple-700 bg-purple-50',
  }
  const nameColors = {
    blue: 'bg-blue-100 text-blue-800',
    purple: 'bg-purple-100 text-purple-800',
  }

  return (
    <div className="px-4 py-3 flex items-start gap-3">
      <span className={`text-xs font-medium px-2 py-1 rounded-lg mt-0.5 whitespace-nowrap ${colors[color]}`}>
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {entries.length === 0 ? (
          <span className="text-gray-300 text-sm">—</span>
        ) : entries.map((e, i) => (
          <span key={i} className={`text-sm font-medium px-2.5 py-1 rounded-xl ${nameColors[color]}`}>
            {e.name}
            <span className="text-xs opacity-60 mr-1">{e.start}–{e.end}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
