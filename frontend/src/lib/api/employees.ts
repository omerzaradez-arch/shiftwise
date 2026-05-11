import { apiClient } from './client'

export interface CreateEmployeePayload {
  name: string
  phone: string
  email?: string
  role: string
  employment_type: string
  max_hours_per_week: number
  min_hours_per_week: number
  password: string
}

export interface UpdateEmployeePayload {
  name?: string
  phone?: string
  email?: string
  role?: string
  employment_type?: string
  max_hours_per_week?: number
  min_hours_per_week?: number
}

export const employeesApi = {
  list: async () => {
    const { data } = await apiClient.get('/api/v1/employees/')
    return data
  },

  create: async (payload: CreateEmployeePayload) => {
    const { data } = await apiClient.post('/api/v1/employees/', payload)
    return data
  },

  update: async ({ id, ...payload }: UpdateEmployeePayload & { id: string }) => {
    const { data } = await apiClient.patch(`/api/v1/employees/${id}`, payload)
    return data
  },

  deactivate: async (id: string) => {
    const { data } = await apiClient.delete(`/api/v1/employees/${id}`)
    return data
  },
}
