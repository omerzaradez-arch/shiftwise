import type { Metadata, Viewport } from 'next'
import { Assistant, Frank_Ruhl_Libre, IBM_Plex_Mono } from 'next/font/google'
import { Providers } from '@/components/providers'
import { Toaster } from 'sonner'
import Script from 'next/script'
import './globals.css'

// Inter carries no Hebrew, so every Hebrew glyph in the app was silently
// falling back to whatever the OS supplies — the reason the typography read as
// unconsidered. These three all ship real Hebrew.
const assistant = Assistant({
  subsets: ['hebrew', 'latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-assistant',
})

// Display only — a Hebrew serif with actual character, used for the wordmark
// and page titles and nowhere else.
const frank = Frank_Ruhl_Libre({
  subsets: ['hebrew', 'latin'],
  weight: ['500', '700', '900'],
  variable: '--font-frank',
})

// Times and figures. A schedule lives or dies on digits lining up.
const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-plex-mono',
})

export const metadata: Metadata = {
  title: 'ShiftWise — ניהול משמרות חכם',
  description: 'ניהול משמרות חכם לעסקים — סידורים, נוכחות ושכר',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'ShiftWise',
  },
  other: {
    'mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
    'apple-mobile-web-app-title': 'ShiftWise',
  },
}

export const viewport: Viewport = {
  themeColor: '#1E1B17',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" suppressHydrationWarning>
      <head>
        <link rel="apple-touch-icon" href="/icon.svg" />
        <link rel="icon" type="image/svg+xml" href="/icon.svg" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
      </head>
      <body className={`${assistant.variable} ${frank.variable} ${plexMono.variable} font-sans`}>
        <Providers>
          {children}
          <Toaster position="top-center" richColors />
        </Providers>
        <Script id="sw-register" strategy="afterInteractive">{`
          if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/sw.js')
              .then(r => console.log('[SW] registered', r.scope))
              .catch(e => console.log('[SW] error', e))
          }
        `}</Script>
      </body>
    </html>
  )
}
