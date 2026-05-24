'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { ManagerNav } from '@/components/layout/ManagerNav'
import { toast } from 'sonner'

export default function AccountPage() {
  const router = useRouter()
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)

  const [currentPwd, setCurrentPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')
  const [busy, setBusy] = useState(false)

  const onChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPwd.length < 8) {
      toast.error('הסיסמה החדשה חייבת להיות לפחות 8 תווים')
      return
    }
    if (/^\d+$/.test(newPwd)) {
      toast.error('הסיסמה החדשה לא יכולה להיות מספרים בלבד')
      return
    }
    if (newPwd !== confirmPwd) {
      toast.error('האימות לא תואם לסיסמה החדשה')
      return
    }
    setBusy(true)
    try {
      await authApi.changePassword(currentPwd, newPwd)
      toast.success('הסיסמה הוחלפה. נכנס מחדש...')
      // The backend invalidated all sessions; force re-login.
      setTimeout(() => {
        logout()
        router.push('/login')
      }, 1200)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'שגיאה בהחלפת סיסמה')
    } finally {
      setBusy(false)
    }
  }

  const onLogoutEverywhere = async () => {
    if (!confirm('לנתק את החשבון מכל המכשירים? תצטרך להיכנס שוב.')) return
    setBusy(true)
    try {
      await authApi.logoutEverywhere()
      toast.success('נותקת מכל המכשירים')
      setTimeout(() => {
        logout()
        router.push('/login')
      }, 1000)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'שגיאה')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50" dir="rtl">
      <ManagerNav />
      <main className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-1">החשבון שלי</h1>
        <p className="text-sm text-slate-500 mb-6">
          {user?.name} · {user?.phone}
        </p>

        {/* Change password */}
        <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-4">
          <div className="px-6 py-4 border-b border-slate-100">
            <h2 className="text-base font-bold text-slate-900">החלפת סיסמה</h2>
            <p className="text-sm text-slate-500 mt-0.5">
              אחרי החלפה — תנותק מכל המכשירים ותצטרך להיכנס שוב.
            </p>
          </div>
          <form onSubmit={onChangePassword} className="px-6 py-5 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                סיסמה נוכחית
              </label>
              <input
                type="password"
                value={currentPwd}
                onChange={(e) => setCurrentPwd(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                סיסמה חדשה (8 תווים לפחות)
              </label>
              <input
                type="password"
                value={newPwd}
                onChange={(e) => setNewPwd(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                אימות סיסמה חדשה
              </label>
              <input
                type="password"
                value={confirmPwd}
                onChange={(e) => setConfirmPwd(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
            <button
              type="submit"
              disabled={busy}
              className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold py-2.5 rounded-lg transition"
            >
              {busy ? 'מחליף...' : 'החלף סיסמה'}
            </button>
          </form>
        </section>

        {/* Logout everywhere */}
        <section className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-4">
          <div className="px-6 py-4 border-b border-slate-100">
            <h2 className="text-base font-bold text-slate-900">אבטחה</h2>
            <p className="text-sm text-slate-500 mt-0.5">
              חושד שהחשבון נפרץ או שמכשיר אבד?
            </p>
          </div>
          <div className="px-6 py-5">
            <button
              onClick={onLogoutEverywhere}
              disabled={busy}
              className="w-full bg-rose-50 hover:bg-rose-100 disabled:opacity-60 text-rose-700 font-semibold py-2.5 rounded-lg transition border border-rose-200"
            >
              נתק את החשבון מכל המכשירים
            </button>
          </div>
        </section>

        <p className="text-xs text-slate-500 text-center mt-6">
          לבקשות פרטיות, מחיקת נתונים, או תמיכה — פנה ל-
          <a href="mailto:support@shiftwise.app" className="text-indigo-600 hover:underline">
            support@shiftwise.app
          </a>
        </p>
      </main>
    </div>
  )
}
