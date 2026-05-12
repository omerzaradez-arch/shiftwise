import { apiClient } from './client'
import { Schedule, Conflict } from '@/types/schedule'
import { format } from 'date-fns'

export const scheduleApi = {
  getWeekSchedule: async (weekStart: Date): Promise<Schedule | null> => {
    try {
      const { data } = await apiClient.get('/api/v1/schedules/week', {
        params: { week_start: format(weekStart, 'yyyy-MM-dd') },
      })
      return data
    } catch (e: any) {
      if (e.response?.status === 404) return null
      throw e
    }
  },

  generateSchedule: async (weekStart: Date) => {
    const { data } = await apiClient.post('/api/v1/schedules/generate/sync', {
      week_start: format(weekStart, 'yyyy-MM-dd'),
    }, { timeout: 60000 })
    return data
  },

  publishSchedule: async (scheduleId: string) => {
    const { data } = await apiClient.post(`/api/v1/schedules/${scheduleId}/publish`)
    return data
  },

  moveShift: async (shiftId: string, employeeId: string, newDate: string) => {
    const { data } = await apiClient.patch(`/api/v1/shifts/${shiftId}/move`, {
      employee_id: employeeId,
      date: newDate,
    })
    return data
  },

  getConflicts: async (weekStart: Date): Promise<Conflict[]> => {
    const { data } = await apiClient.get('/api/v1/schedules/conflicts', {
      params: { week_start: format(weekStart, 'yyyy-MM-dd') },
    })
    return data
  },

  exportPdf: async (scheduleId: string): Promise<Blob> => {
    const { data } = await apiClient.get(`/api/v1/schedules/${scheduleId}/pdf`, {
      responseType: 'blob',
    })
    return data
  },
}
