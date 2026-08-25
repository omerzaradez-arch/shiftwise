'use client'

import { useRef, useCallback, useState, useEffect } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import listPlugin from '@fullcalendar/list'
import interactionPlugin from '@fullcalendar/interaction'
import type { EventDropArg, EventClickArg, DateSelectArg } from '@fullcalendar/core'
import { format } from 'date-fns'
import { Schedule, Conflict } from '@/types/schedule'

// These are set inline on FullCalendar events, so they bypass Tailwind and have
// to carry the palette themselves.

// Role reads off the leading edge of each block, darkest for most senior.
const ROLE_COLORS: Record<string, string> = {
  manager: '#B8452C',
  senior:  '#345C52',
  junior:  '#7D7365',
  trainee: '#A69C8C',
}

// Shift blocks as tinted paper stock rather than saturated chips — the type
// stays readable and the board doesn't turn into a colour chart.
const SHIFT_BG: Record<string, string> = {
  morning:   '#FBE9CB',
  afternoon: '#DAE7E3',
  evening:   '#E8DCE6',
  night:     '#D9D4CA',
}

const INK = '#1E1B17'
const CONFLICT = '#9A6B12' // ochre — distinct from the vermilion of primary actions

interface Props {
  schedule: Schedule
  weekStart: Date
  onShiftMove: (shiftId: string, newEmployeeId: string, newDate: string) => void
  onShiftClick?: (shiftId: string) => void
  onEmptyClick?: (date: string) => void
  conflicts: Conflict[]
}

export function WeeklyCalendar({ schedule, weekStart, onShiftMove, onShiftClick, onEmptyClick, conflicts }: Props) {
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
    backgroundColor: SHIFT_BG[shift.shift_type] ?? '#F2EFE8',
    borderColor: conflictDates.has(shift.date) ? CONFLICT : ROLE_COLORS[shift.employee_role] ?? '#7D7365',
    textColor: INK,
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

  const handleEventClick = useCallback(
    (info: EventClickArg) => {
      if (onShiftClick) onShiftClick(info.event.extendedProps.shiftId)
    },
    [onShiftClick]
  )

  const handleSelect = useCallback(
    (info: DateSelectArg) => {
      if (onEmptyClick) {
        const d = format(info.start, 'yyyy-MM-dd')
        onEmptyClick(d)
      }
      info.view.calendar.unselect()
    },
    [onEmptyClick]
  )

  const renderEventContent = (eventInfo: any) => {
    const { role, shiftName, isManualOverride } = eventInfo.event.extendedProps
    // A hand-placed shift is marked by a rule under the name, the way a
    // corrected entry is struck on a paper roster — no emoji needed.
    const overrideMark = isManualOverride ? (
      <span
        className="inline-block w-1.5 h-1.5 flex-none"
        style={{ backgroundColor: '#B8452C' }}
        title="שובץ ידנית"
      />
    ) : null

    if (isMobile) {
      return (
        <div className="px-1 py-0.5 flex items-center gap-1.5">
          <span className="font-semibold text-xs">{eventInfo.event.title}</span>
          <span className="text-xs opacity-45">{shiftName}</span>
          {overrideMark}
        </div>
      )
    }
    return (
      <div className="p-1 overflow-hidden leading-tight">
        <div className="flex items-center gap-1.5">
          <span
            className="w-1.5 h-1.5 flex-none"
            style={{ backgroundColor: ROLE_COLORS[role] ?? '#A69C8C' }}
          />
          <span className="font-semibold text-xs truncate">{eventInfo.event.title}</span>
          {overrideMark}
        </div>
        <div className="text-[11px] opacity-55 mt-0.5 truncate">{shiftName}</div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-sand-200 shadow-card p-2 md:p-4 h-full overflow-auto">
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
        selectable={!isMobile && !!onEmptyClick}
        select={handleSelect}
        eventDrop={handleEventDrop}
        eventClick={handleEventClick}
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
