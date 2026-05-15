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

  register: async (
    orgName: string,
    name: string,
    phone: string,
    password: string,
    verificationCode: string,
    email?: string
  ): Promise<LoginResponse> => {
    const { data } = await apiClient.post('/api/v1/auth/register', {
      org_name: orgName,
      name,
      phone,
      password,
      email: email || '',
      verification_code: verificationCode,
    })
    return data
  },

  requestAccess: async (
    orgName: string,
    contactName: string,
    phone: string,
    email?: string,
    notes?: string
  ): Promise<{ ok: boolean; message: string }> => {
    const { data } = await apiClient.post('/api/v1/auth/request-access', {
      org_name: orgName,
      contact_name: contactName,
      phone,
      email: email || '',
      notes: notes || '',
    })
    return data
  },

  verifyCode: async (
    phone: string,
    code: string
  ): Promise<{ ok: boolean; org_name: string; contact_name: string; email: string }> => {
    const { data } = await apiClient.post('/api/v1/auth/verify-code', { phone, code })
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
