'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/lib/api/auth'
import { toast } from 'sonner'

type Mode = 'request' | 'complete'

export default function RegisterPage() {
  const router = useRouter()
  const { setUser, setToken } = useAuthStore()
  const [mode, setMode] = useState<Mode>('request')

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4" dir="rtl">
      <div className="fixed top-0 right-0 w-96 h-96 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="fixed bottom-0 left-0 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-sm relative z-10">
        {/* Logo */}
        <div className="text-center mb-6">
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

        {/* Mode tabs */}
        <div className="flex bg-white/5 rounded-xl p-1 mb-4">
          <button
            onClick={() => setMode('request')}
            className={`flex-1 py-2 rounded-lg text-sm font-semibold transition ${
              mode === 'request' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'
            }`}
          >
            1️⃣ בקש גישה
          </button>
          <button
            onClick={() => setMode('complete')}
            className={`flex-1 py-2 rounded-lg text-sm font-semibold transition ${
              mode === 'complete' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-white'
            }`}
          >
            2️⃣ יש לי קוד
          </button>
        </div>

        <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-2xl p-6 shadow-2xl">
          {mode === 'request' ? (
            <RequestAccessForm onSwitchToComplete={() => setMode('complete')} />
          ) : (
            <CompleteRegistrationForm
              onSuccess={(token, user) => {
                setToken(token)
                setUser(user)
                router.push('/schedule')
              }}
            />
          )}

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

// ── Step 1: Request Access ──────────────────────────────────────────────────────

function RequestAccessForm({ onSwitchToComplete }: { onSwitchToComplete: () => void }) {
  const [orgName, setOrgName] = useState('')
  const [contactName, setContactName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orgName || !contactName || !phone) {
      toast.error('נא למלא שם עסק, שם איש קשר וטלפון')
      return
    }
    setLoading(true)
    try {
      await authApi.requestAccess(orgName, contactName, phone, email, notes)
      setSubmitted(true)
      toast.success('הבקשה נשלחה!')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'שגיאה בשליחת בקשה')
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <div className="text-center py-4">
        <div className="w-16 h-16 mx-auto bg-emerald-500/20 rounded-full flex items-center justify-center mb-4">
          <span className="text-3xl">✅</span>
        </div>
        <h2 className="text-lg font-bold text-white mb-2">הבקשה התקבלה</h2>
        <p className="text-sm text-slate-400 mb-6 leading-relaxed">
          נחזור אליך בהקדם עם קוד אימות.<br />
          לאחר שתקבל את הקוד, חזור לכאן ולחץ <span className="text-indigo-300 font-semibold">״יש לי קוד״</span> כדי להשלים את ההרשמה.
        </p>
        <button
          onClick={onSwitchToComplete}
          className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-indigo-900/40"
        >
          יש לי כבר קוד אימות
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-white mb-1">בקשת גישה למערכת</h2>
        <p className="text-slate-400 text-xs mb-4">מלא את הפרטים — ניצור איתך קשר עם קוד אימות אישי</p>
      </div>

      <FieldInput label="שם העסק *" value={orgName} onChange={setOrgName} placeholder="מסעדת הים" />
      <FieldInput label="שם איש קשר *" value={contactName} onChange={setContactName} placeholder="ישראל ישראלי" />
      <FieldInput label="מספר טלפון *" value={phone} onChange={setPhone} placeholder="050-0000000" type="tel" />
      <FieldInput label="אימייל" value={email} onChange={setEmail} placeholder="user@example.com" type="email" />

      <div>
        <label className="block text-sm font-semibold text-slate-300 mb-2">הערות (אופציונלי)</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="כמה עובדים? סוג העסק?"
          rows={2}
          className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-right text-sm"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-indigo-900/40"
      >
        {loading ? 'שולח...' : 'שלח בקשה'}
      </button>
    </form>
  )
}

// ── Step 2: Complete Registration ───────────────────────────────────────────────

function CompleteRegistrationForm({
  onSuccess,
}: {
  onSuccess: (token: string, user: any) => void
}) {
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [verified, setVerified] = useState(false)
  const [orgName, setOrgName] = useState('')
  const [contactName, setContactName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)

  const verifyCode = async () => {
    if (!phone || !code) {
      toast.error('נא למלא טלפון וקוד אימות')
      return
    }
    setLoading(true)
    try {
      const res = await authApi.verifyCode(phone, code)
      setOrgName(res.org_name)
      setContactName(res.contact_name)
      setEmail(res.email)
      setVerified(true)
      toast.success(`קוד אומת! ברוך הבא, ${res.contact_name}`)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'קוד שגוי')
    } finally {
      setLoading(false)
    }
  }

  const completeRegistration = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!password || password.length < 6) {
      toast.error('סיסמה חייבת להכיל לפחות 6 תווים')
      return
    }
    if (password !== confirm) {
      toast.error('הסיסמאות לא תואמות')
      return
    }
    setLoading(true)
    try {
      const res = await authApi.register(orgName, contactName, phone, password, code, email)
      toast.success(`ברוך הבא ${contactName}! העסק נפתח בהצלחה 🎉`)
      onSuccess(res.access_token, res.user)
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'שגיאה בהרשמה')
    } finally {
      setLoading(false)
    }
  }

  if (!verified) {
    return (
      <div className="space-y-4">
        <div>
          <h2 className="text-lg font-bold text-white mb-1">השלמת הרשמה</h2>
          <p className="text-slate-400 text-xs mb-4">הזן את הטלפון וקוד האימות שקיבלת</p>
        </div>

        <FieldInput label="מספר טלפון" value={phone} onChange={setPhone} placeholder="050-0000000" type="tel" />

        <div>
          <label className="block text-sm font-semibold text-slate-300 mb-2">קוד אימות (6 ספרות)</label>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            placeholder="000000"
            maxLength={6}
            className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-center text-2xl tracking-[0.5em] font-mono"
          />
        </div>

        <button
          onClick={verifyCode}
          disabled={loading || code.length !== 6}
          className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-indigo-900/40"
        >
          {loading ? 'בודק...' : 'אמת קוד'}
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={completeRegistration} className="space-y-4">
      <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-3 mb-2">
        <p className="text-emerald-300 text-sm font-semibold">✓ הקוד אומת</p>
        <p className="text-slate-300 text-xs mt-1">{orgName} · {contactName}</p>
      </div>

      <div>
        <label className="block text-sm font-semibold text-slate-300 mb-2">בחר סיסמה</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-sm"
        />
      </div>

      <div>
        <label className="block text-sm font-semibold text-slate-300 mb-2">אימות סיסמה</label>
        <input
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="••••••••"
          className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-sm"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white font-bold py-3 rounded-xl transition shadow-lg shadow-emerald-900/40"
      >
        {loading ? 'יוצר חשבון...' : 'צור חשבון 🎉'}
      </button>
    </form>
  )
}

// ── Shared Input ────────────────────────────────────────────────────────────────

function FieldInput({
  label, value, onChange, placeholder, type = 'text',
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-slate-300 mb-2">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition text-right text-sm"
      />
    </div>
  )
}
