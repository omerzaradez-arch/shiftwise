import { apiClient } from './client'
import { User } from '@/stores/authStore'

interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export const authApi = {
  login: async (phone: string, password: string): Promise<LoginResponse> => {
    const { data } = await apiClient.post('/api/v1/auth/login', { phone, password })
    return data
  },

  logout: async () => {
    await apiClient.post('/api/v1/auth/logout')
  },

  me: async (): Promise<User> => {
    const { data } = await apiClient.get('/api/v1/auth/me')
    return data
  },
}
