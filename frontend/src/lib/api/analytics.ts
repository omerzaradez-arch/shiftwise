import { apiClient } from './client'
import { format } from 'date-fns'

export const analyticsApi = {
  getFairness: async (weekStart: Date) => {
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

  getPayrollTrend: async (months = 6) => {
    const { data } = await apiClient.get('/api/v1/analytics/payroll-trend', {
      params: { months },
    })
    return data
  },

  getAttendanceStats: async () => {
    const { data } = await apiClient.get('/api/v1/analytics/attendance-stats')
    return data
  },
}
