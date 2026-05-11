'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { employeesApi } from '@/lib/api/employees'
import { Employee } from '@/types/schedule'
import { ManagerNav } from '@/components/layout/ManagerNav'
import { toast } from 'sonner'

const ROLE_LABELS: Record<string, string> = {
  manager: 'מנהל',
  senior: 'בכיר',
  junior: 'עובד',
  trainee: 'מתמחה',
}

const ROLE_COLORS: Record<string, string> = {
  manager: 'bg-purple-100 text-purple-700',
  senior: 'bg-indigo-100 text-indigo-700',
  junior: 'bg-blue-100 text-blue-700',
  trainee: 'bg-slate-100 text-slate-600',
}

const EMPLOYMENT_LABELS: Record<string, string> = {
  full_time: 'מלא',
  part_time: 'חלקי',
  casual: 'שעתי',
}

const createEmployeeSchema = z.object({
  name: z.string().min(2, 'שם חייב להכיל לפחות 2 תווים'),
  phone: z.string().min(9, 'מספר טלפון לא תקין'),
  email: z.string().email('אימייל לא תקין').optional().or(z.literal('')),
  role: z.enum(['manager', 'senior', 'junior', 'trainee']),
  employment_type: z.enum(['full_time', 'part_time', 'casual']),
  max_hours_per_week: z.coerce.number().min(1).max(60),
  min_hours_per_week: z.coerce.number().min(0).max(60),
  password: z.string().min(4, 'סיסמה חייבת להכיל לפחות 4 תווים'),
})

const editEmployeeSchema = z.object({
  name: z.string().min(2, 'שם חייב להכיל לפחות 2 תווים'),
  phone: z.string().min(9, 'מספר טלפון לא תקין'),
  email: z.string().email('אימייל לא תקין').optional().or(z.literal('')),
  role: z.enum(['manager', 'senior', 'junior', 'trainee']),
  employment_type: z.enum(['full_time', 'part_time', 'casual']),
  max_hours_per_week: z.coerce.number().min(1).max(60),
  min_hours_per_week: z.coerce.number().min(0).max(60),
})

type CreateEmployeeForm = z.infer<typeof createEmployeeSchema>
type EditEmployeeForm = z.infer<typeof editEmployeeSchema>

function FormField({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-slate-700 mb-1.5">{label}</label>
      {children}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  )
}

const inputCls = "w-full px-4 py-2.5 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm bg-slate-50 focus:bg-white transition"
const selectCls = `${inputCls} bg-white`

export default function EmployeesPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editEmployee, setEditEmployee] = useState<Employee | null>(null)
  const [search, setSearch] = useState('')
  const [filterRole, setFilterRole] = useState<string>('all')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data: employees = [], isLoading } = useQuery({
    queryKey: ['employees'],
    queryFn: employeesApi.list,
  })

  const createMutation = useMutation({
    mutationFn: employeesApi.create,
    onSuccess: () => {
      toast.success('עובד נוסף בהצלחה!')
      qc.invalidateQueries({ queryKey: ['employees'] })
      setShowForm(false)
      resetCreate()
    },
    onError: () => toast.error('שגיאה בהוספת עובד'),
  })

  const updateMutation = useMutation({
    mutationFn: employeesApi.update,
    onSuccess: () => {
      toast.success('פרטי העובד עודכנו')
      qc.invalidateQueries({ queryKey: ['employees'] })
      setEditEmployee(null)
    },
    onError: () => toast.error('שגיאה בעדכון עובד'),
  })

  const deleteMutation = useMutation({
    mutationFn: employeesApi.deactivate,
    onSuccess: () => {
      toast.success('העובד הוסר מהמערכת')
      qc.invalidateQueries({ queryKey: ['employees'] })
      setDeleteConfirm(null)
    },
  })

  const {
    register: registerCreate,
    handleSubmit: handleCreate,
    reset: resetCreate,
    formState: { errors: createErrors },
  } = useForm<CreateEmployeeForm>({
    resolver: zodResolver(createEmployeeSchema),
    defaultValues: { role: 'junior', employment_type: 'part_time', max_hours_per_week: 25, min_hours_per_week: 0 },
  })

  const {
    register: registerEdit,
    handleSubmit: handleEdit,
    reset: resetEdit,
    formState: { errors: editErrors },
  } = useForm<EditEmployeeForm>({
    resolver: zodResolver(editEmployeeSchema),
  })

  const openEdit = (emp: Employee) => {
    setEditEmployee(emp)
    resetEdit({
      name: emp.name,
      phone: emp.phone,
      email: emp.email ?? '',
      role: emp.role as any,
      employment_type: emp.employment_type as any,
      max_hours_per_week: emp.max_hours_per_week,
      min_hours_per_week: emp.min_hours_per_week,
    })
  }

  const onSubmitCreate = (data: CreateEmployeeForm) => createMutation.mutate(data)
  const onSubmitEdit = (data: EditEmployeeForm) =>
    updateMutation.mutate({ id: editEmployee!.id, ...data })

  const filtered = employees.filter((e: Employee) => {
    const matchSearch = e.name.includes(search) || e.phone.includes(search)
    const matchRole = filterRole === 'all' || e.role === filterRole
    return matchSearch && matchRole
  })

  const stats = {
    total: employees.length,
    fullTime: employees.filter((e: Employee) => e.employment_type === 'full_time').length,
    partTime: employees.filter((e: Employee) => e.employment_type === 'part_time').length,
    seniors: employees.filter((e: Employee) => e.role === 'senior' || e.role === 'manager').length,
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden" dir="rtl">
      <ManagerNav />

      <main className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white border-b border-slate-200 px-6 py-4 sticky top-0 z-20">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-slate-900">ניהול עובדים</h1>
              <p className="text-sm text-slate-500 mt-0.5">{employees.length} עובדים פעילים</p>
            </div>
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition shadow-sm shadow-indigo-200"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              הוסף עובד
            </button>
          </div>
        </div>

        <div className="p-6">
          {/* Stats */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[
              { label: 'סה"כ עובדים', value: stats.total, color: 'text-slate-900' },
              { label: 'משרה מלאה', value: stats.fullTime, color: 'text-indigo-600' },
              { label: 'משרה חלקית', value: stats.partTime, color: 'text-blue-600' },
              { label: 'עובדים בכירים', value: stats.seniors, color: 'text-purple-600' },
            ].map((s) => (
              <div key={s.label} className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
                <p className="text-sm text-slate-500 mb-1">{s.label}</p>
                <p className={`text-3xl font-bold ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="flex gap-3 mb-5">
            <div className="relative flex-1 max-w-xs">
              <svg className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
                fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="חיפוש עובד..."
                className="w-full pr-9 pl-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              />
            </div>

            <div className="flex gap-2">
              {['all', 'manager', 'senior', 'junior', 'trainee'].map((role) => (
                <button
                  key={role}
                  onClick={() => setFilterRole(role)}
                  className={`px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
                    filterRole === role
                      ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-200'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {role === 'all' ? 'הכל' : ROLE_LABELS[role]}
                </button>
              ))}
            </div>
          </div>

          {/* Table */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            {isLoading ? (
              <div className="p-8 text-center text-slate-400">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                טוען עובדים...
              </div>
            ) : filtered.length === 0 ? (
              <div className="p-12 text-center text-slate-400">
                <div className="w-16 h-16 bg-slate-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                  <svg className="w-8 h-8 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <p className="font-medium">לא נמצאו עובדים</p>
              </div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50/50">
                    <th className="text-right text-xs font-semibold text-slate-400 uppercase px-5 py-3">שם</th>
                    <th className="text-right text-xs font-semibold text-slate-400 uppercase px-5 py-3">תפקיד</th>
                    <th className="text-right text-xs font-semibold text-slate-400 uppercase px-5 py-3">סוג משרה</th>
                    <th className="text-right text-xs font-semibold text-slate-400 uppercase px-5 py-3">שעות/שבוע</th>
                    <th className="text-right text-xs font-semibold text-slate-400 uppercase px-5 py-3">טלפון</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((emp: Employee, i: number) => (
                    <tr
                      key={emp.id}
                      className={`border-b border-slate-50 hover:bg-slate-50/70 transition-colors ${
                        i === filtered.length - 1 ? 'border-0' : ''
                      }`}
                    >
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-bold text-sm flex-none">
                            {emp.name[0]}
                          </div>
                          <div>
                            <p className="font-semibold text-slate-900">{emp.name}</p>
                            {emp.email && <p className="text-xs text-slate-400">{emp.email}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold ${ROLE_COLORS[emp.role]}`}>
                          {ROLE_LABELS[emp.role]}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-600">
                        {EMPLOYMENT_LABELS[emp.employment_type]}
                      </td>
                      <td className="px-5 py-4">
                        <div className="text-sm font-medium text-slate-900">{emp.max_hours_per_week} שעות</div>
                        {emp.min_hours_per_week > 0 && (
                          <div className="text-xs text-slate-400">מינ׳ {emp.min_hours_per_week}</div>
                        )}
                      </td>
                      <td className="px-5 py-4 text-sm text-slate-500 dir-ltr text-left">
                        {emp.phone}
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1 justify-end">
                          {deleteConfirm === emp.id ? (
                            <>
                              <span className="text-xs text-slate-500 ml-1">בטוח?</span>
                              <button
                                onClick={() => deleteMutation.mutate(emp.id)}
                                className="text-xs text-red-600 font-semibold hover:underline px-1"
                              >
                                מחק
                              </button>
                              <button
                                onClick={() => setDeleteConfirm(null)}
                                className="text-xs text-slate-400 hover:underline px-1"
                              >
                                ביטול
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => openEdit(emp)}
                                className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                title="ערוך"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                              </button>
                              <button
                                onClick={() => setDeleteConfirm(emp.id)}
                                className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                title="הסר"
                              >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </main>

      {/* Add Employee Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={(e) => e.target === e.currentTarget && setShowForm(false)}>
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white rounded-t-2xl">
              <h2 className="text-lg font-bold text-slate-900">הוספת עובד חדש</h2>
              <button onClick={() => { setShowForm(false); resetCreate() }}
                className="p-2 hover:bg-slate-100 rounded-xl transition text-slate-400">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleCreate(onSubmitCreate)} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <FormField label="שם מלא *" error={createErrors.name?.message}>
                  <input {...registerCreate('name')} placeholder="ישראל ישראלי" className={inputCls} />
                </FormField>
                <FormField label="טלפון *" error={createErrors.phone?.message}>
                  <input {...registerCreate('phone')} placeholder="050-0000000" className={inputCls} />
                </FormField>
              </div>
              <FormField label="אימייל">
                <input {...registerCreate('email')} type="email" placeholder="example@email.com" className={inputCls} />
              </FormField>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="תפקיד *">
                  <select {...registerCreate('role')} className={selectCls}>
                    <option value="trainee">מתמחה</option>
                    <option value="junior">עובד</option>
                    <option value="senior">בכיר</option>
                    <option value="manager">מנהל</option>
                  </select>
                </FormField>
                <FormField label="סוג משרה *">
                  <select {...registerCreate('employment_type')} className={selectCls}>
                    <option value="casual">שעתי</option>
                    <option value="part_time">משרה חלקית</option>
                    <option value="full_time">משרה מלאה</option>
                  </select>
                </FormField>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="מקסימום שעות/שבוע">
                  <input {...registerCreate('max_hours_per_week')} type="number" min={1} max={60} className={inputCls} />
                </FormField>
                <FormField label="מינימום שעות/שבוע">
                  <input {...registerCreate('min_hours_per_week')} type="number" min={0} className={inputCls} />
                </FormField>
              </div>
              <FormField label="סיסמה זמנית *" error={createErrors.password?.message}>
                <input {...registerCreate('password')} type="text" placeholder="לפחות 4 תווים" className={inputCls} />
                <p className="text-xs text-slate-400 mt-1">העובד יוכל לשנות את הסיסמה בהמשך</p>
              </FormField>

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => { setShowForm(false); resetCreate() }}
                  className="flex-none px-5 py-2.5 border border-slate-200 rounded-xl text-slate-600 text-sm hover:bg-slate-50">
                  ביטול
                </button>
                <button type="submit" disabled={createMutation.isPending}
                  className="flex-1 bg-indigo-600 text-white font-bold py-2.5 rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition text-sm shadow-sm shadow-indigo-200">
                  {createMutation.isPending ? 'מוסיף...' : 'הוסף עובד'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Employee Modal */}
      {editEmployee && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={(e) => e.target === e.currentTarget && setEditEmployee(null)}>
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-100 flex items-center justify-between sticky top-0 bg-white rounded-t-2xl">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center text-white font-bold text-sm">
                  {editEmployee.name[0]}
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">עריכת עובד</h2>
                  <p className="text-xs text-slate-400">{editEmployee.name}</p>
                </div>
              </div>
              <button onClick={() => setEditEmployee(null)}
                className="p-2 hover:bg-slate-100 rounded-xl transition text-slate-400">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleEdit(onSubmitEdit)} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <FormField label="שם מלא *" error={editErrors.name?.message}>
                  <input {...registerEdit('name')} className={inputCls} />
                </FormField>
                <FormField label="טלפון *" error={editErrors.phone?.message}>
                  <input {...registerEdit('phone')} className={inputCls} />
                </FormField>
              </div>
              <FormField label="אימייל">
                <input {...registerEdit('email')} type="email" className={inputCls} />
              </FormField>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="תפקיד *">
                  <select {...registerEdit('role')} className={selectCls}>
                    <option value="trainee">מתמחה</option>
                    <option value="junior">עובד</option>
                    <option value="senior">בכיר</option>
                    <option value="manager">מנהל</option>
                  </select>
                </FormField>
                <FormField label="סוג משרה *">
                  <select {...registerEdit('employment_type')} className={selectCls}>
                    <option value="casual">שעתי</option>
                    <option value="part_time">משרה חלקית</option>
                    <option value="full_time">משרה מלאה</option>
                  </select>
                </FormField>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <FormField label="מקסימום שעות/שבוע">
                  <input {...registerEdit('max_hours_per_week')} type="number" min={1} max={60} className={inputCls} />
                </FormField>
                <FormField label="מינימום שעות/שבוע">
                  <input {...registerEdit('min_hours_per_week')} type="number" min={0} className={inputCls} />
                </FormField>
              </div>

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setEditEmployee(null)}
                  className="flex-none px-5 py-2.5 border border-slate-200 rounded-xl text-slate-600 text-sm hover:bg-slate-50">
                  ביטול
                </button>
                <button type="submit" disabled={updateMutation.isPending}
                  className="flex-1 bg-indigo-600 text-white font-bold py-2.5 rounded-xl hover:bg-indigo-700 disabled:opacity-60 transition text-sm shadow-sm shadow-indigo-200">
                  {updateMutation.isPending ? 'שומר...' : 'שמור שינויים'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
