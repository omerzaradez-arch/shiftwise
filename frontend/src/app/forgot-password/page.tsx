'use client'

import { useState } from 'react'
import Link from 'next/link'
import { authApi } from '@/lib/api/auth'
import { toast } from 'sonner'

export default function ForgotPasswordPage() {
  const [phone, setPhone] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!phone || phone.length < 9) {
      toast.error('הזן מספר טלפון תקף')
      return
    }
    setLoading(true)
    try {
      const res = await authApi.forgotPassword(phone)
      setSent(true)
      toast.success(res.message)
    } catch (e: any) {
      const detail = e?.response?.data?.detail || 'שגיאה בשליחת הבקשה'
      toast.error(detail)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 px-4" dir="rtl">
      <div className="w-full max-w-md">
        <div className="bg-slate-900/60 backdrop-blur border border-white/5 rounded-2xl p-7 shadow-2xl">
          <h1 className="text-2xl font-bold text-white mb-1">שכחתי סיסמה</h1>
          <p className="text-sm text-slate-400 mb-6">
            נשלח לך סיסמה חדשה ל-WhatsApp של המנהל
          </p>

          {sent ? (
            <div className="space-y-4">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
                <p className="text-emerald-300 text-sm font-semibold">
                  ✓ הבקשה התקבלה
                </p>
                <p className="text-slate-300 text-xs mt-2 leading-relaxed">
                  אם המספר רשום במערכת ושייך למנהל, סיסמה חדשה נשלחה ל-WhatsApp שלך
                  בדקות הקרובות. בדוק את ההודעות.
                </p>
              </div>
              <Link
                href="/login"
                className="block text-center bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-indigo-900/40"
              >
                חזרה לכניסה
              </Link>
            </div>
          ) : (
            <form onSubmit={onSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-300 mb-2">
                  מספר טלפון של המנהל
                </label>
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="050-0000000"
                  type="tel"
                  className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-right text-sm"
                />
                <p className="text-xs text-slate-500 mt-2">
                  הסיסמה תישלח רק אם המספר רשום כמנהל במערכת.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-indigo-900/40"
              >
                {loading ? 'שולח...' : 'שלח סיסמה חדשה ל-WhatsApp'}
              </button>

              <Link
                href="/login"
                className="block text-center text-xs text-slate-400 hover:text-slate-300 mt-3"
              >
                ← חזרה לכניסה
              </Link>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-slate-600 mt-4">
          ShiftWise © {new Date().getFullYear()}
        </p>
      </div>
    </div>
  )
}
