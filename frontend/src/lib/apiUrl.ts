/**
 * Single source of truth for the backend origin.
 *
 * NEXT_PUBLIC_* values are inlined into the bundle at BUILD time, not read at
 * runtime — so on Railway this must be set as a build variable (the frontend
 * Dockerfile takes it as an ARG). Setting it only as a runtime variable leaves
 * the deployed bundle pointing at the fallback below.
 */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
).replace(/\/$/, '')
