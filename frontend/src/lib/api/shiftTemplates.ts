import { apiClient } from './client'

export interface ShiftTemplate {
  id: string
  name: string
  shift_type: string
  start_time: string
  end_time: string
  min_employees: number
  max_employees: number
  required_roles: Record<string, number>
  days_of_week: number[]
  is_active: boolean
  duration_hours: number
}

export interface ShiftTemplateCreate {
  name: string
  shift_type: string
  start_time: string
  end_time: string
  min_employees: number
  max_employees: number
  required_roles: Record<string, number>
  days_of_week: number[]
}

export const shiftTemplatesApi = {
  list: (): Promise<ShiftTemplate[]> =>
    apiClient.get('/api/v1/shift-templates/').then((r) => r.data),

  create: (data: ShiftTemplateCreate): Promise<ShiftTemplate> =>
    apiClient.post('/api/v1/shift-templates/', data).then((r) => r.data),

  update: (id: string, data: Partial<ShiftTemplateCreate>): Promise<ShiftTemplate> =>
    apiClient.put(`/api/v1/shift-templates/${id}`, data).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/api/v1/shift-templates/${id}`).then(() => undefined),
}
