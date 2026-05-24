/**
 * Sentry — browser-side. Catches errors that happen in the user's browser.
 * Set NEXT_PUBLIC_SENTRY_DSN in Railway → frontend variables to enable.
 * Without DSN, Sentry no-ops silently.
 */
import * as Sentry from "@sentry/nextjs"

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "production",
    tracesSampleRate: 0.1, // sample 10% of page-loads for performance traces
    replaysSessionSampleRate: 0, // off; turn on later if you want session replay
    replaysOnErrorSampleRate: 0.1, // record replay on errors only
    sendDefaultPii: false,
    // Filter noisy errors that come from browser extensions / network glitches.
    ignoreErrors: [
      "ResizeObserver loop limit exceeded",
      "Non-Error promise rejection captured",
      /Network request failed/i,
    ],
  })
}
