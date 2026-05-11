export interface ScheduledShift {
  id: string
  date: string
  start_time: string
  end_time: string
  duration_hours: number
  shift_name: string
  shift_type: 'morning' | 'afternoon' | 'evening' | 'night'
  employee_id: string
  employee_name: string
  employee_role: 'senior' | 'junior' | 'trainee' | 'manager'
  status: 'assigned' | 'swap_requested' | 'swap_approved' | 'cancelled'
  is_manually_overridden: boolean
}

export interface Schedule {
  id: string
  week_start: string
  week_end: string
  status: 'collecting' | 'generated' | 'review' | 'changes_requested' | 'final' | 'published'
  optimizer_score: number
  coverage_percent: number
  shifts: ScheduledShift[]
  generated_at: string | null
  published_at: string | null
}

export interface Conflict {
  id: string
  type: 'close_open' | 'under_coverage' | 'overload' | 'no_senior' | 'constraint_violation'
  type_label: string
  severity: 'high' | 'medium' | 'low'
  date: string
  description: string
  suggestion: string | null
  affected_employee_ids: string[]
}

export interface Employee {
  id: string
  name: string
  phone: string
  email?: string
  role: 'senior' | 'junior' | 'trainee' | 'manager'
  employment_type: 'full_time' | 'part_time' | 'casual'
  max_hours_per_week: number
  min_hours_per_week: number
  skills: string[]
  is_active: boolean
}

export interface SwapRequest {
  id: string
  shift: ScheduledShift
  requester: Employee
  target_employee: Employee | null
  reason: string
  status: 'pending' | 'approved' | 'rejected' | 'auto_approved'
  created_at: string
}
