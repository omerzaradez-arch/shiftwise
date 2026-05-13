'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/lib/api/auth'
import { toast } from 'sonner'

const schema = z.object({
  org_name: z.string().min(2, 'שם העסק נדרש'),
  name: z.string().min(2, 'שם נדרש'),
  phone: z.string().min(9, 'מספר טלפון לא תקין'),
  password: z.string().min(6, 'סיסמה חייבת להכיל לפחות 6 תווים'),
  confirm: z.string(),
}).refine(d => d.password === d.confirm, {
  message: 'הסיסמאות לא תואמות',
  path: ['confirm'],
})

type Form = z.infer<typeof schema>

export default function RegisterPage() {
  const router = useRouter()
  const { setUser, setToken } = useAuthStore()
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: Form) => {
    setLoading(true)
    try {
      const res = await authApi.register(data.org_name, data.name, data.phone, data.password)
      setToken(res.access_token)
      setUser(res.user)
      toast.success(`ברוך הבא, ${data.name}! העסק ${data.org_name} נוצר בהצלחה`)
      router.push('/schedule')
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'שגיאה בהרשמה'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4" dir="rtl">
      <div className="fixed top-0 right-0 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 left-0 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-sm relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-indigo-600 rounded-2xl mb-4 shadow-2xl shadow-indigo-900/60">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="16" y1="2" x2="16" y2="6"/>
              <line x1="8" y1="2" x2="8" y2="6"/>
              <line x1="3" y1="10" x2="21" y2="10"/>
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white">ShiftWise</h1>
          <p className="text-slate-400 text-sm mt-1">פתיחת עסק חדש</p>
        </div>

        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-8 shadow-2xl">
          <h2 className="text-lg font-bold text-white mb-1">יצירת חשבון</h2>
          <p className="text-slate-400 text-sm mb-6">מלא פרטים לפתיחת עסק חדש</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">שם העסק</label>
              <input
                {...register('org_name')}
                placeholder="מסעדת הים"
                className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-right text-sm"
              />
              {errors.org_name && <p className="text-red-400 text-xs mt-1">{errors.org_name.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">שם המנהל</label>
              <input
                {...register('name')}
                placeholder="ישראל ישראלי"
                className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-right text-sm"
              />
              {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">מספר טלפון</label>
              <input
                {...register('phone')}
                type="tel"
                placeholder="050-0000000"
                className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-right text-sm"
              />
              {errors.phone && <p className="text-red-400 text-xs mt-1">{errors.phone.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">סיסמה</label>
              <input
                {...register('password')}
                type="password"
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-sm"
              />
              {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>}
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">אימות סיסמה</label>
              <input
                {...register('confirm')}
                type="password"
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-sm"
              />
              {errors.confirm && <p className="text-red-400 text-xs mt-1">{errors.confirm.message}</p>}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-bold py-3 rounded-xl transition-all shadow-lg shadow-indigo-900/40 mt-2"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  יוצר חשבון...
                </span>
              ) : 'צור חשבון'}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-4">
            כבר יש לך חשבון?{' '}
            <Link href="/login" className="text-indigo-400 hover:text-indigo-300 font-medium">
              התחבר
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
