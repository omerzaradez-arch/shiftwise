import { apiClient } from './client'
import { format } from 'date-fns'

export const analyticsApi = {
  getFairness: async (weekStart: Date) => {
    // First get the week ID
    const scheduleRes = await apiClient.get('/api/v1/schedules/week', {
      params: { week_start: format(weekStart, 'yyyy-MM-dd') },
    }).catch(() => null)

    if (!scheduleRes?.data?.id) return []

    const { data } = await apiClient.get(`/api/v1/analytics/fairness/${scheduleRes.data.id}`)
    return data
  },

  getHoursDistribution: async (weeks = 8) => {
    const { data } = await apiClient.get('/api/v1/analytics/hours-distribution', {
      params: { weeks },
    })
    return data
  },
}
