import { apiClient } from './client'
import { format } from 'date-fns'

export interface AvailabilityPayload {
  week_start: string
  blocked_days: number[]
  desired_shifts_count: number
  preferred_shift_types: string[]
  notes: string
}

export const availabilityApi = {
  submit: async (payload: AvailabilityPayload) => {
    const { data } = await apiClient.post('/api/v1/availability/submit', payload)
    return data
  },

  getSubmission: async (weekStart: Date) => {
    try {
      const { data } = await apiClient.get('/api/v1/availability/my', {
        params: { week_start: format(weekStart, 'yyyy-MM-dd') },
      })
      return data
    } catch {
      return null
    }
  },

  getWeekStatus: async (weekStart: Date) => {
    const { data } = await apiClient.get('/api/v1/availability/week-status', {
      params: { week_start: format(weekStart, 'yyyy-MM-dd') },
    })
    return data
  },
}
