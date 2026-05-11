import { apiClient } from './client'

export const swapsApi = {
  requestSwap: async (shiftId: string, reason: string) => {
    const { data } = await apiClient.post('/api/v1/swaps/request', {
      shift_id: shiftId,
      reason,
    })
    return data
  },

  getPendingSwaps: async () => {
    const { data } = await apiClient.get('/api/v1/swaps/pending')
    return data
  },

  approveSwap: async (swapId: string) => {
    const { data } = await apiClient.post(`/api/v1/swaps/${swapId}/approve`)
    return data
  },

  rejectSwap: async (swapId: string, reason?: string) => {
    const { data } = await apiClient.post(`/api/v1/swaps/${swapId}/reject`, { reason })
    return data
  },

  getSuggestions: async (shiftId: string) => {
    const { data } = await apiClient.get(`/api/v1/swaps/suggestions/${shiftId}`)
    return data
  },
}
