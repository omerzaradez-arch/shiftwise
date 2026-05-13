'use client'

import Link from 'next/link'
import { useState, useEffect } from 'react'

const features = [
  {
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
      </svg>
    ),
    title: 'סידור אוטומטי בשניות',
    desc: 'במקום לבלות שעות על Excel — המערכת בונה את הסידור האופטימלי בלחיצת כפתור, תוך התחשבות בזמינויות, תפקידים וקונסטריינטים.',
  },
  {
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    ),
    title: 'התראות WhatsApp אוטומטיות',
    desc: 'כשהסידור מוכן — כל עובד מקבל הודעת WhatsApp עם המשמרות שלו. אין יותר "לא ידעתי", אין יותר שיחות מיותרות.',
  },
  {
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
    ),
    title: 'ניהול עובדים מלא',
    desc: 'הוספת עובדים, הגדרת תפקידים, מעקב אחר זמינויות — הכל במקום אחד. כל עובד ממלא זמינות מהטלפון.',
  },
  {
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/>
        <polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>
      </svg>
    ),
    title: 'החלפות משמרות חכמות',
    desc: 'עובד לא יכול להגיע? המערכת שולחת אוטומטית הודעת WhatsApp לכל הפנויים. מחליף נמצא — המנהל מאשר בלחיצה.',
  },
]

const steps = [
  { num: '01', title: 'מגדיר את העובדים', desc: 'מוסיף עובדים, תפקידים ושעות עבודה רצויות' },
  { num: '02', title: 'עובדים ממלאים זמינות', desc: 'כל עובד מקבל WhatsApp ועונה מה ימים נוחים לו' },
  { num: '03', title: 'AI בונה את הסידור', desc: 'המערכת מייצרת סידור אופטימלי תוך שניות' },
  { num: '04', title: 'לוחץ "פרסם"', desc: 'כל העובדים מקבלים הודעה עם המשמרות שלהם' },
]

const pains = [
  'מבלה שעות על Excel בכל שבוע',
  'עובדים מתקשרים "לא ידעתי שיש לי משמרת"',
  'תיאום החלפות ב-WhatsApp ידני וכאוטי',
  'עובדים שוכחים למלא זמינות',
  'קשה לדעת מי פנוי לכסות משמרת חסרה',
]

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="min-h-screen bg-slate-900 text-white" dir="rtl">

      {/* Navbar */}
      <nav className={`fixed top-0 right-0 left-0 z-50 transition-all duration-300 ${scrolled ? 'bg-slate-900/95 backdrop-blur-sm border-b border-white/10 shadow-xl' : ''}`}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-900/60">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
            </div>
            <span className="text-xl font-bold text-white">ShiftWise</span>
          </div>

          {/* CTA buttons */}
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-slate-300 hover:text-white text-sm font-medium transition px-4 py-2">
              כניסה
            </Link>
            <Link href="/register" className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold px-5 py-2.5 rounded-xl transition shadow-lg shadow-indigo-900/40">
              התחל חינם
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative min-h-screen flex items-center pt-20">
        {/* Background blobs */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-purple-600/8 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-6xl mx-auto px-6 py-24 w-full">
          <div className="max-w-3xl">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 bg-indigo-600/20 border border-indigo-500/30 rounded-full px-4 py-1.5 mb-6">
              <span className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
              <span className="text-indigo-300 text-sm font-medium">ניהול משמרות חכם לעסקים</span>
            </div>

            {/* Headline */}
            <h1 className="text-5xl md:text-6xl font-black text-white leading-tight mb-6">
              תפסיק לבזבז שעות
              <span className="block text-transparent bg-clip-text bg-gradient-to-l from-indigo-400 to-purple-400">
                על סידור עובדים
              </span>
            </h1>

            <p className="text-xl text-slate-400 mb-10 leading-relaxed max-w-2xl">
              ShiftWise בונה את סידור המשמרות האופטימלי בשניות, שולח התראות WhatsApp לכל העובדים ומנהל החלפות אוטומטית — כל זאת ממסך אחד.
            </p>

            <div className="flex flex-wrap gap-4">
              <Link
                href="/register"
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-8 py-4 rounded-xl transition-all shadow-xl shadow-indigo-900/50 text-lg flex items-center gap-2"
              >
                התחל בחינם
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 5 5 12 12 19"/>
                </svg>
              </Link>
              <a
                href="#how-it-works"
                className="bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-8 py-4 rounded-xl transition text-lg"
              >
                איך זה עובד?
              </a>
            </div>

            {/* Social proof */}
            <div className="flex items-center gap-6 mt-10">
              <div className="flex -space-x-2 space-x-reverse">
                {['ד', 'מ', 'ר', 'א'].map((l, i) => (
                  <div key={i} className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 border-2 border-slate-900 flex items-center justify-center text-xs font-bold">
                    {l}
                  </div>
                ))}
              </div>
              <p className="text-slate-400 text-sm">
                <span className="text-white font-semibold">עסקים</span> כבר מנהלים משמרות עם ShiftWise
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pain Points */}
      <section className="py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-black text-white mb-3">מכיר את זה?</h2>
            <p className="text-slate-400">הכאבים שכל מנהל עסק חווה כל שבוע</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-4xl mx-auto">
            {pains.map((pain, i) => (
              <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-5 flex items-center gap-4">
                <div className="w-8 h-8 rounded-full bg-red-500/20 border border-red-500/30 flex items-center justify-center flex-shrink-0">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">{pain}</p>
              </div>
            ))}

            {/* Solution card */}
            <div className="bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 rounded-xl p-5 flex items-center gap-4 md:col-span-2 lg:col-span-1">
              <div className="w-8 h-8 rounded-full bg-indigo-500/30 border border-indigo-400/40 flex items-center justify-center flex-shrink-0">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <p className="text-indigo-300 text-sm font-semibold leading-relaxed">ShiftWise פותר את כל אלה — אוטומטית</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-black text-white mb-4">
              כל מה שצריך לנהל משמרות
            </h2>
            <p className="text-slate-400 text-lg max-w-2xl mx-auto">
              פלטפורמה אחת שמחליפה Excel, קבוצות WhatsApp ותיאום ידני
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {features.map((f, i) => (
              <div key={i} className="bg-white/5 hover:bg-white/[0.07] border border-white/10 rounded-2xl p-8 transition group">
                <div className="w-14 h-14 bg-indigo-600/20 border border-indigo-500/30 rounded-2xl flex items-center justify-center text-indigo-400 mb-5 group-hover:bg-indigo-600/30 transition">
                  {f.icon}
                </div>
                <h3 className="text-xl font-bold text-white mb-3">{f.title}</h3>
                <p className="text-slate-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-24 border-t border-white/5">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-black text-white mb-4">איך זה עובד?</h2>
            <p className="text-slate-400 text-lg">4 צעדים פשוטים מהרשמה לסידור שפורסם</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((s, i) => (
              <div key={i} className="relative">
                {i < steps.length - 1 && (
                  <div className="hidden lg:block absolute top-8 left-0 w-full h-px bg-gradient-to-l from-indigo-500/40 to-transparent pointer-events-none" />
                )}
                <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
                  <div className="text-4xl font-black text-indigo-600/40 mb-4">{s.num}</div>
                  <h3 className="text-lg font-bold text-white mb-2">{s.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="py-20 border-t border-white/5">
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { num: '< 30 שנ׳', label: 'לבניית סידור שבועי' },
              { num: '100%', label: 'עובדים מקבלים הודעה' },
              { num: '0', label: 'שיחות תיאום מיותרות' },
              { num: '24/7', label: 'גישה מכל מקום' },
            ].map((s, i) => (
              <div key={i}>
                <div className="text-3xl md:text-4xl font-black text-transparent bg-clip-text bg-gradient-to-l from-indigo-400 to-purple-400 mb-2">
                  {s.num}
                </div>
                <div className="text-slate-400 text-sm">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 border-t border-white/5">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <div className="bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border border-indigo-500/20 rounded-3xl p-12">
            <h2 className="text-3xl md:text-4xl font-black text-white mb-4">
              מוכן לחסוך שעות כל שבוע?
            </h2>
            <p className="text-slate-400 text-lg mb-8 leading-relaxed">
              הצטרף לעסקים שכבר מנהלים משמרות בצורה חכמה.
              <br />
              <span className="text-indigo-300 font-semibold">הרשמה חינמית — אין כרטיס אשראי.</span>
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/register"
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-10 py-4 rounded-xl transition-all shadow-xl shadow-indigo-900/50 text-lg"
              >
                פתח חשבון חינם
              </Link>
              <Link
                href="/login"
                className="bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-10 py-4 rounded-xl transition text-lg"
              >
                כניסה למערכת
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 bg-indigo-600 rounded-lg flex items-center justify-center">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
            </div>
            <span className="font-bold text-white">ShiftWise</span>
          </div>
          <p className="text-slate-500 text-sm">© {new Date().getFullYear()} ShiftWise — ניהול משמרות חכם לעסקים</p>
          <div className="flex gap-6 text-sm text-slate-500">
            <Link href="/login" className="hover:text-white transition">כניסה</Link>
            <Link href="/register" className="hover:text-white transition">הרשמה</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
