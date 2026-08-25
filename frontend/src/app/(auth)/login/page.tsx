'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/lib/api/auth'
import { toast } from 'sonner'

const loginSchema = z.object({
  phone: z.string().min(9, 'מספר טלפון לא תקין'),
  password: z.string().min(1, 'סיסמה נדרשת'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const { setUser, setToken } = useAuthStore()
  const [loading, setLoading] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    setLoading(true)
    try {
      const res = await authApi.login(data.phone, data.password)
      setToken(res.access_token)
      setUser(res.user)
      router.push(res.user.role === 'employee' ? '/dashboard' : '/schedule')
    } catch {
      toast.error('פרטי התחברות שגויים')
    } finally {
      setLoading(false)
    }
  }

  const field =
    'w-full bg-transparent border-0 border-b border-sand-300 px-0 py-2.5 text-[15px] ' +
    'text-sand-900 placeholder:text-sand-400 focus:outline-none focus:border-vermilion-600 ' +
    'focus:ring-0 transition-colors'

  return (
    <div className="min-h-screen bg-sand-50 flex items-center justify-center p-5" dir="rtl">
      {/* Ruled paper — the timesheet this product replaces. */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 opacity-[0.5]"
        style={{
          backgroundImage: 'repeating-linear-gradient(to bottom, #E4DFD5 0 1px, transparent 1px 46px)',
        }}
      />

      <div className="w-full max-w-[380px] relative">
        <header className="mb-9">
          <div className="flex items-baseline gap-2.5">
            <span className="h-2.5 w-2.5 bg-vermilion-600" />
            <h1 className="font-display text-[34px] leading-none font-black text-sand-900 tracking-tightest">
              ShiftWise
            </h1>
          </div>
          <p className="label-caps mt-3">ניהול משמרות לעסקים</p>
        </header>

        <div className="bg-white border border-sand-200 shadow-card">
          <div className="border-b border-sand-200 px-7 py-4">
            <h2 className="font-display text-[19px] text-sand-900">כניסה למערכת</h2>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="px-7 py-7 flex flex-col gap-6">
            <div>
              <label htmlFor="phone" className="label-caps block mb-1">מספר טלפון</label>
              <input id="phone" {...register('phone')} type="tel" dir="ltr"
                placeholder="050-0000000" autoComplete="tel"
                className={`${field} text-right mono-time`} />
              {errors.phone && (
                <p className="text-vermilion-700 text-xs mt-1.5">{errors.phone.message}</p>
              )}
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-1">
                <label htmlFor="password" className="label-caps">סיסמה</label>
                <a href="/forgot-password"
                  className="text-xs text-sand-500 hover:text-vermilion-600 transition-colors">
                  שכחתי סיסמה
                </a>
              </div>
              <input id="password" {...register('password')} type="password"
                placeholder="••••••••" autoComplete="current-password" className={field} />
              {errors.password && (
                <p className="text-vermilion-700 text-xs mt-1.5">{errors.password.message}</p>
              )}
            </div>

            <button type="submit" disabled={loading}
              className="w-full bg-vermilion-600 hover:bg-vermilion-700 disabled:opacity-55
                         disabled:cursor-not-allowed text-white font-semibold text-[15px]
                         py-3 transition-colors">
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-30" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="3" />
                    <path className="opacity-90" fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  נכנס…
                </span>
              ) : 'כניסה'}
            </button>
          </form>
        </div>

        <p className="text-sm text-sand-500 mt-6">
          עסק חדש?{' '}
          <a href="/register" className="text-vermilion-700 hover:text-vermilion-600 font-semibold">
            פתיחת חשבון
          </a>
        </p>

        <p className="label-caps mt-10 text-sand-400">ShiftWise © 2026</p>
      </div>
    </div>
  )
}
