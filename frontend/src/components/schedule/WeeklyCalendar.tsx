'use client'

import { useRef, useCallback, useState, useEffect } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventDropArg } from '@fullcalendar/core'
import { format } from 'date-fns'
import { Schedule, Conflict } from '@/types/schedule'

const ROLE_COLORS: Record<string, string> = {
  senior: '#6366F1',
  junior: '#3B82F6',
  trainee: '#94A3B8',
  manager: '#8B5CF6',
}

const SHIFT_BG: Record<string, string> = {
  morning: '#FEF3C7',
  afternoon: '#DBEAFE',
  evening: '#EDE9FE',
}

interface Props {
  schedule: Schedule
  weekStart: Date
  onShiftMove: (shiftId: string, newEmployeeId: string, newDate: string) => void
  conflicts: Conflict[]
}

export function WeeklyCalendar({ schedule, weekStart, onShiftMove, conflicts }: Props) {
  const calendarRef = useRef<FullCalendar>(null)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // When weekStart or mobile mode changes, update the calendar's date/view
  useEffect(() => {
    const api = calendarRef.current?.getApi()
    if (!api) return
    api.gotoDate(weekStart)
    api.changeView(isMobile ? 'listWeek' : 'timeGridWeek')
  }, [weekStart, isMobile])

  const conflictDates = new Set(conflicts.map((c) => c.date))

  const events = schedule.shifts.map((shift) => ({
    id: shift.id,
    title: shift.employee_name,
    start: `${shift.date}T${shift.start_time}`,
    end: `${shift.date}T${shift.end_time}`,
    backgroundColor: SHIFT_BG[shift.shift_type] ?? '#F1F5F9',
    borderColor: conflictDates.has(shift.date) ? '#F59E0B' : ROLE_COLORS[shift.employee_role] ?? '#3B82F6',
    textColor: '#1E293B',
    extendedProps: {
      shiftId: shift.id,
      employeeId: shift.employee_id,
      role: shift.employee_role,
      shiftName: shift.shift_name,
      isManualOverride: shift.is_manually_overridden,
    },
  }))

  const handleEventDrop = useCallback(
    (info: EventDropArg) => {
      const { event } = info
      const newDate = format(event.start!, 'yyyy-MM-dd')
      onShiftMove(
        event.extendedProps.shiftId,
        event.extendedProps.employeeId,
        newDate
      )
    },
    [onShiftMove]
  )

  const renderEventContent = (eventInfo: any) => {
    const { role, shiftName, isManualOverride } = eventInfo.event.extendedProps
    if (isMobile) {
      return (
        <div className="px-1 py-0.5">
          <span className="font-semibold text-xs">{eventInfo.event.title}</span>
          <span className="text-xs opacity-60 mx-1">·</span>
          <span className="text-xs opacity-70">{shiftName}</span>
          {isManualOverride && <span className="text-xs ml-1">✏️</span>}
        </div>
      )
    }
    return (
      <div className="p-1 overflow-hidden">
        <div className="flex items-center gap-1">
          <div
            className="w-2 h-2 rounded-full flex-none"
            style={{ backgroundColor: ROLE_COLORS[role] ?? '#94A3B8' }}
          />
          <span className="font-semibold text-xs truncate">
            {eventInfo.event.title}
          </span>
          {isManualOverride && (
            <span className="text-xs opacity-60" title="עודכן ידנית">✏️</span>
          )}
        </div>
        <div className="text-xs opacity-70 mt-0.5">{shiftName}</div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-2 md:p-4 h-full overflow-auto">
      <FullCalendar
        ref={calendarRef}
        plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
        initialView={isMobile ? 'listWeek' : 'timeGridWeek'}
        initialDate={weekStart}
        locale="he"
        direction="rtl"
        headerToolbar={false}
        {...{ schedulerLicenseKey: 'GPL-My-Project-Is-Open-Source' } as any}
        editable={!isMobile}
        droppable={!isMobile}
        eventDrop={handleEventDrop}
        events={events}
        eventContent={renderEventContent}
        slotMinTime="07:00:00"
        slotMaxTime="24:00:00"
        height={isMobile ? 'auto' : 700}
        allDaySlot={false}
        slotDuration="01:00:00"
        nowIndicator={true}
        scrollTime="10:00:00"
        dayHeaderFormat={{ weekday: 'short', day: 'numeric', month: 'short' }}
        listDayFormat={{ weekday: 'long', day: 'numeric', month: 'short' }}
        listDaySideFormat={false}
        noEventsText="אין משמרות השבוע"
      />
    </div>
  )
}
