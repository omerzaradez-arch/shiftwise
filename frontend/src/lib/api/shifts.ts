import { apiClient } from './client'
import { ScheduledShift } from '@/types/schedule'
import { format } from 'date-fns'

export const shiftsApi = {
  getMyShifts: async (weekStart: Date): Promise<ScheduledShift[]> => {
    const { data } = await apiClient.get('/api/v1/shifts/my', {
      params: { week_start: format(weekStart, 'yyyy-MM-dd') },
    })
    return data
  },

  getNextShift: async (): Promise<ScheduledShift | null> => {
    const { data } = await apiClient.get('/api/v1/shifts/next')
    return data
  },
}
